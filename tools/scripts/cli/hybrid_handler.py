"""
HybridModeHandler - Advanced result merging and deduplication for vsearch hybrid mode.

Provides intelligent merging of database and analog search results with
sophisticated deduplication and ranking algorithms.
"""

import hashlib
import re
from collections import defaultdict
from datetime import datetime
from typing import Any, Dict, List, Optional, Set


class HybridModeHandler:
    """Handles intelligent merging and deduplication of hybrid search results"""

    def __init__(self, score_weights: Optional[Dict[str, float]] = None):
        """Initialize with configurable scoring weights"""
        self.score_weights = score_weights or {
            "exact_match": 2.0,  # Boost for exact query matches
            "title_match": 1.5,  # Boost for title matches
            "recent_doc": 1.2,  # Boost for recent documents
            "content_length": 0.1,  # Small boost for longer content
            "source_trust": 1.0,  # Base trust score by source
        }

        # Source trust scores (database generally more structured)
        self.source_trust = {"database": 1.0, "analog": 0.9}

    def merge_results(
        self,
        database_results: List[Dict[str, Any]],
        analog_results: List[Dict[str, Any]],
        limit: int = 10,
        query: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        Intelligently merge and deduplicate results from database and analog sources

        Args:
            database_results: Results from database search
            analog_results: Results from analog (markdown) search
            limit: Maximum number of results to return
            query: Original search query for relevance boosting

        Returns:
            Merged, deduplicated, and re-ranked results
        """
        # Prepare all results with source tags and normalized scores
        all_results = []

        for result in database_results:
            enhanced = self._enhance_result(result, "database", query)
            all_results.append(enhanced)

        for result in analog_results:
            enhanced = self._enhance_result(result, "analog", query)
            all_results.append(enhanced)

        # Deduplicate based on content similarity
        deduplicated = self._deduplicate_results(all_results)

        # Re-rank with enhanced scoring
        ranked = self._rerank_results(deduplicated, query)

        return ranked[:limit]

    def _enhance_result(
        self, result: Dict[str, Any], source: str, query: Optional[str]
    ) -> Dict[str, Any]:
        """Enhance result with metadata for better ranking"""
        enhanced = result.copy()
        enhanced["source"] = source
        enhanced["original_score"] = result.get("score", 0.0)

        # Calculate content fingerprint for deduplication
        enhanced["content_fingerprint"] = self._generate_fingerprint(result)

        # Calculate enhanced score
        enhanced["enhanced_score"] = self._calculate_enhanced_score(result, source, query)

        return enhanced

    def _generate_fingerprint(self, result: Dict[str, Any]) -> str:
        """Generate content fingerprint for deduplication"""
        # Use title + first 100 chars of content for fingerprinting
        title = result.get("title", "").lower().strip()
        content = result.get("content", "")[:100].lower().strip()

        # Clean and normalize text
        title = re.sub(r"\s+", " ", title)
        content = re.sub(r"\s+", " ", content)

        fingerprint_text = f"{title}|{content}"
        return hashlib.md5(fingerprint_text.encode("utf-8")).hexdigest()

    def _deduplicate_results(self, results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Remove duplicates based on content fingerprints and IDs"""
        seen_ids: Set[str] = set()
        deduplicated = []

        # Group by fingerprint to find potential duplicates
        fingerprint_groups = defaultdict(list)
        for result in results:
            fingerprint = result.get("content_fingerprint", "")
            fingerprint_groups[fingerprint].append(result)

        for fingerprint, group in fingerprint_groups.items():
            if len(group) == 1:
                # No duplicates for this fingerprint
                result = group[0]
                content_id = result.get("content_id", "")

                if content_id and content_id not in seen_ids:
                    seen_ids.add(content_id)
                    deduplicated.append(result)
                elif not content_id:
                    deduplicated.append(result)
            else:
                # Multiple results with same fingerprint - keep the best one
                best_result = self._select_best_duplicate(group)
                content_id = best_result.get("content_id", "")

                if content_id and content_id not in seen_ids:
                    seen_ids.add(content_id)
                    deduplicated.append(best_result)
                elif not content_id:
                    deduplicated.append(best_result)

        return deduplicated

    def _select_best_duplicate(self, duplicates: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Select the best result from a group of duplicates"""
        # Prefer database results, then by enhanced score
        duplicates.sort(
            key=lambda x: (
                x.get("source") == "database",  # Database first
                x.get("enhanced_score", 0.0),  # Then by score
            ),
            reverse=True,
        )

        return duplicates[0]

    def _calculate_enhanced_score(
        self, result: Dict[str, Any], source: str, query: Optional[str]
    ) -> float:
        """Calculate enhanced relevance score"""
        base_score = result.get("score", 0.0)

        # Apply source trust multiplier
        score = base_score * self.source_trust.get(source, 1.0)

        if query:
            # Apply query-specific boosts
            title = result.get("title", "").lower()
            content = result.get("content", "").lower()
            query_lower = query.lower()

            # Exact match boost
            if query_lower in title:
                score *= self.score_weights["title_match"]
            elif query_lower in content:
                score *= self.score_weights["exact_match"]

        # Recency boost (if date available)
        created_time = result.get("created_time")
        if created_time:
            try:
                if isinstance(created_time, str):
                    # Parse ISO format or other common formats
                    try:
                        created_dt = datetime.fromisoformat(created_time.replace("Z", "+00:00"))
                    except:
                        # Try other common formats
                        for fmt in ["%Y-%m-%d %H:%M:%S", "%Y-%m-%d", "%m/%d/%Y"]:
                            try:
                                created_dt = datetime.strptime(created_time, fmt)
                                break
                            except:
                                continue
                        else:
                            created_dt = None
                else:
                    created_dt = created_time

                if created_dt:
                    days_old = (datetime.now() - created_dt.replace(tzinfo=None)).days
                    if days_old < 30:  # Boost recent documents
                        score *= self.score_weights["recent_doc"]
            except Exception:
                # Ignore date parsing errors
                pass

        # Content length boost (longer content might be more comprehensive)
        content_length = len(result.get("content", ""))
        if content_length > 500:
            score *= 1.0 + self.score_weights["content_length"]

        return max(score, 0.0)  # Ensure non-negative

    def _rerank_results(
        self, results: List[Dict[str, Any]], query: Optional[str]
    ) -> List[Dict[str, Any]]:
        """Final ranking of deduplicated results"""
        # Sort by enhanced score
        results.sort(key=lambda x: x.get("enhanced_score", 0.0), reverse=True)

        # Clean up temporary fields before returning
        for result in results:
            result.pop("content_fingerprint", None)
            # Keep source and enhanced_score for debugging if needed

        return results

    def get_merge_stats(
        self, database_count: int, analog_count: int, final_count: int
    ) -> Dict[str, Any]:
        """Get statistics about the merge operation"""
        return {
            "database_results": database_count,
            "analog_results": analog_count,
            "total_before_merge": database_count + analog_count,
            "final_results": final_count,
            "duplicates_removed": (database_count + analog_count) - final_count,
            "deduplication_rate": (
                ((database_count + analog_count) - final_count)
                / max(database_count + analog_count, 1)
            )
            * 100,
        }
