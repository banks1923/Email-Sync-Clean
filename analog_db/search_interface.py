"""
SearchInterface for Analog Database - Simplified and refactored.

Main interface for markdown-aware search functionality using focused modules.
"""

import time
from pathlib import Path
from typing import Any, Dict, List, Optional

from loguru import logger

from .content_search import ContentSearcher
from .metadata_search import MetadataSearcher
from .vector_search import VectorSearcher


class SearchInterface:
    """Simplified markdown-aware search interface."""
    
    def __init__(self, base_path: Optional[Path] = None):
        """Initialize SearchInterface with focused components."""
        self.base_path = Path(base_path) if base_path else Path.cwd()
        self.analog_db_path = self.base_path / "analog_db"
        
        # Initialize specialized searchers
        self.content_searcher = ContentSearcher(self.base_path)
        self.metadata_searcher = MetadataSearcher(self.base_path)
        self.vector_searcher = VectorSearcher(self.base_path)
        
        # Performance tracking
        self._search_stats = {
            "total_searches": 0,
            "avg_search_time": 0.0,
            "cache_hits": 0,
            "cache_misses": 0
        }
        
        logger.info(f"SearchInterface initialized with base path: {self.base_path}")
    
    @property
    def documents_path(self) -> Path:
        """Get documents directory path."""
        return self.analog_db_path / "documents"
    
    @property
    def email_threads_path(self) -> Path:
        """Get email threads directory path."""
        return self.analog_db_path / "email_threads"
    
    def search_content(
        self,
        query: str,
        path: Optional[Path] = None,
        limit: int = 20,
        regex: bool = False,
        case_sensitive: bool = False
    ) -> List[Dict[str, Any]]:
        """Full-text search using ripgrep."""
        start_time = time.time()
        
        try:
            # Get content search results
            results = self.content_searcher.search_content(
                query, path, limit, regex, case_sensitive
            )
            
            # Enhance results with metadata
            enhanced_results = self._enhance_content_results(results)
            
            # Update performance stats
            self._update_search_stats(time.time() - start_time)
            
            logger.debug(f"Content search completed in {time.time() - start_time:.3f}s, {len(enhanced_results)} results")
            return enhanced_results
            
        except Exception as e:
            logger.error(f"Content search failed: {e}")
            return []
    
    def search_metadata(
        self,
        filters: Dict[str, Any],
        limit: int = 20
    ) -> List[Dict[str, Any]]:
        """Search by metadata fields."""
        start_time = time.time()
        
        try:
            results = self.metadata_searcher.search_metadata(filters, limit)
            self._update_search_stats(time.time() - start_time)
            
            logger.debug(f"Metadata search completed in {time.time() - start_time:.3f}s, {len(results)} results")
            return results
            
        except Exception as e:
            logger.error(f"Metadata search failed: {e}")
            return []
    
    def hybrid_search(
        self,
        query: str,
        metadata_filters: Optional[Dict[str, Any]] = None,
        limit: int = 20,
        use_vector: bool = True
    ) -> List[Dict[str, Any]]:
        """Combined content, metadata, and vector search."""
        start_time = time.time()
        
        try:
            all_results = self._collect_all_search_results(query, metadata_filters, limit, use_vector)
            final_results = self._process_hybrid_results(all_results, limit)
            
            self._update_search_stats(time.time() - start_time)
            
            logger.debug(f"Hybrid search completed in {time.time() - start_time:.3f}s, {len(final_results)} results")
            return final_results
            
        except Exception as e:
            logger.error(f"Hybrid search failed: {e}")
            return []
    
    def _collect_all_search_results(self, query: str, metadata_filters: Optional[Dict[str, Any]], limit: int, use_vector: bool) -> List[Dict[str, Any]]:
        """Collect results from all search methods."""
        all_results = []
        
        # Content search
        content_results = self.search_content(query, limit=limit)
        all_results.extend(self._score_content_results(content_results, query))
        
        # Metadata search if filters provided
        if metadata_filters:
            metadata_results = self.search_metadata(metadata_filters, limit=limit)
            all_results.extend(self._score_metadata_results(metadata_results))
        
        # Vector search if enabled
        if use_vector:
            vector_results = self._get_all_vector_results(query, limit//2)
            all_results.extend(vector_results)
        
        return all_results
    
    def get_search_stats(self) -> Dict[str, Any]:
        """Get search performance statistics."""
        stats = self._search_stats.copy()
        # Add metadata searcher cache stats
        stats["cache_hits"] = getattr(self.metadata_searcher, '_search_stats', {}).get('cache_hits', 0)
        stats["cache_misses"] = getattr(self.metadata_searcher, '_search_stats', {}).get('cache_misses', 0)
        return stats
    
    def clear_cache(self) -> None:
        """Clear all caches."""
        self.metadata_searcher.clear_cache()
        logger.info("Search interface cache cleared")
    
    def _get_markdown_files(self) -> List[Path]:
        """Get all markdown files (delegate to metadata searcher)."""
        return self.metadata_searcher._get_markdown_files()
    
    def _get_file_metadata(self, file_path: Path) -> Optional[Dict[str, Any]]:
        """Get file metadata (delegate to metadata searcher)."""
        return self.metadata_searcher._get_file_metadata(file_path)
    
    def _enhance_content_results(self, results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Add metadata to content search results."""
        enhanced_results = []
        
        for result in results:
            try:
                file_path = Path(result.get("file_path", ""))
                metadata = self.metadata_searcher._get_file_metadata(file_path)
                result["metadata"] = metadata or {}
                enhanced_results.append(result)
            except Exception as e:
                logger.debug(f"Failed to enhance result: {e}")
                enhanced_results.append(result)
        
        return enhanced_results
    
    def _score_content_results(self, results: List[Dict[str, Any]], query: str) -> List[Dict[str, Any]]:
        """Add relevance scores to content results."""
        scored_results = []
        query_terms = query.lower().split()
        
        for result in results:
            content = result.get("matched_content", "").lower()
            metadata = result.get("metadata", {})
            title = metadata.get("title", "").lower()
            
            # Calculate score based on query term frequency
            score = sum(content.count(term) for term in query_terms)
            
            # Boost for title matches
            score += sum(2.0 for term in query_terms if term in title)
            
            result["score"] = score
            result["source"] = "content"
            scored_results.append(result)
        
        return scored_results
    
    def _score_metadata_results(self, results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Add scores to metadata results."""
        for result in results:
            result["score"] = 10.0  # Fixed high score for exact metadata matches
            result["source"] = "metadata"
        
        return results
    
    def _get_all_vector_results(self, query: str, limit: int) -> List[Dict[str, Any]]:
        """Get combined vector search results with analog-first approach."""
        all_vector_results = []
        
        # PRIMARY: Analog semantic search (always works, files are source of truth)
        analog_results = self.vector_searcher.get_analog_semantic_results(query, limit)
        all_vector_results.extend(analog_results)
        logger.debug(f"Analog search: {len(analog_results)} results")
        
        # SECONDARY: Database vector search (optional enhancement)
        try:
            db_results = self.vector_searcher.get_database_vector_results(query, limit)
            all_vector_results.extend(db_results)
            logger.debug(f"Database search: {len(db_results)} results")
        except Exception as e:
            logger.info(f"Database search unavailable, continuing with analog-only: {e}")
        
        return all_vector_results
    
    def _process_hybrid_results(self, all_results: List[Dict[str, Any]], limit: int) -> List[Dict[str, Any]]:
        """Remove duplicates, rank, and limit results."""
        # Remove duplicates based on file path
        unique_results = self._deduplicate_results(all_results)
        
        # Sort by score (descending)
        ranked_results = sorted(unique_results, key=lambda x: x.get("score", 0.0), reverse=True)
        
        # Return top results
        return ranked_results[:limit]
    
    def _deduplicate_results(self, results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Remove duplicate results based on file path."""
        seen_files = set()
        unique_results = []
        
        for result in results:
            file_path = result.get("file_path", "")
            if file_path not in seen_files:
                seen_files.add(file_path)
                unique_results.append(result)
        
        return unique_results
    
    def _update_search_stats(self, search_time: float) -> None:
        """Update search performance statistics."""
        self._search_stats["total_searches"] += 1
        
        # Update running average
        total = self._search_stats["total_searches"]
        current_avg = self._search_stats["avg_search_time"]
        new_avg = ((current_avg * (total - 1)) + search_time) / total
        self._search_stats["avg_search_time"] = new_avg