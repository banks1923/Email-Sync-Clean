"""Timeline-Based Relationship Engine for Knowledge Graph.

Extracts temporal data from content and creates chronological
relationships. Follows CLAUDE.md principles: simple patterns, functions
under 30 lines.
"""

import json
import re
from datetime import datetime, timedelta

from dateutil import parser as date_parser
from loguru import logger

from shared.simple_db import SimpleDB

from .main import KnowledgeGraphService

# Logger is now imported globally from loguru


class TimelineRelationships:
    """
    Create and manage temporal relationships in the knowledge graph.
    """

    def __init__(self, db_path: str = "emails.db"):
        self.kg_service = KnowledgeGraphService(db_path)
        self.db = SimpleDB(db_path)
        self.time_window_hours = 24  # Default clustering window

    def extract_content_dates(self, content_id: str) -> datetime | None:
        """
        Extract primary date from content based on type.
        """
        content = self.db.fetch_one(
            "SELECT content_type, metadata, created_time FROM content WHERE id = ?",
            (content_id,),
        )

        if not content:
            return None

        # Handle different content types
        if content["content_type"] == "email":
            return self._extract_email_date(content_id)
        elif content["content_type"] == "pdf":
            return self._extract_pdf_date(content_id, content["metadata"])
        elif content["content_type"] == "transcript":
            return self._extract_transcript_date(content_id, content["metadata"])
        else:
            # Fallback to created_time
            return self._parse_date_string(content["created_time"])

    def _extract_email_date(self, content_id: str) -> datetime | None:
        """
        Extract date from email record.
        """
        email = self.db.fetch_one(
            "SELECT datetime_utc FROM emails WHERE message_id = ?", (content_id,)
        )

        if email and email["datetime_utc"]:
            return self._parse_date_string(email["datetime_utc"])
        return None

    def _extract_pdf_date(self, content_id: str, metadata_json: str) -> datetime | None:
        """
        Extract date from PDF metadata.
        """
        if metadata_json:
            try:
                metadata = json.loads(metadata_json)
                # Look for common date fields in PDF metadata
                for field in ["creation_date", "modified_date", "date", "Date"]:
                    if field in metadata:
                        return self._parse_date_string(metadata[field])
            except json.JSONDecodeError:
                logger.warning(f"Invalid JSON metadata for PDF {content_id}")

        # Try to extract from documents table
        doc = self.db.fetch_one(
            "SELECT processed_time FROM documents WHERE chunk_id = ?", (content_id,)
        )

        if doc and doc["processed_time"]:
            return self._parse_date_string(doc["processed_time"])
        return None

    def _extract_transcript_date(self, content_id: str, metadata_json: str) -> datetime | None:
        """
        Extract date from transcript metadata.
        """
        if metadata_json:
            try:
                metadata = json.loads(metadata_json)
                # Look for recording date or transcription date
                for field in ["recording_date", "transcription_date", "date"]:
                    if field in metadata:
                        return self._parse_date_string(metadata[field])
            except json.JSONDecodeError:
                logger.warning(f"Invalid JSON metadata for transcript {content_id}")
        return None

    def _parse_date_string(self, date_str: str) -> datetime | None:
        """
        Parse various date string formats.
        """
        if not date_str:
            return None

        try:
            # Try dateutil parser first (handles many formats)
            return date_parser.parse(date_str)
        except (ValueError, TypeError):
            # Fallback to pattern matching
            return self._parse_date_patterns(str(date_str))

    def _parse_date_patterns(self, date_str: str) -> datetime | None:
        """
        Parse dates using regex patterns.
        """
        patterns = [
            (r"(\d{4})-(\d{2})-(\d{2})", "ymd"),  # YYYY-MM-DD
            (r"(\d{2})/(\d{2})/(\d{4})", "mdy"),  # MM/DD/YYYY
            (r"(\d{2})-(\d{2})-(\d{4})", "mdy"),  # MM-DD-YYYY
        ]

        for pattern, fmt in patterns:
            match = re.search(pattern, date_str)
            if match:
                try:
                    if fmt == "ymd":
                        return datetime(
                            int(match.group(1)), int(match.group(2)), int(match.group(3))
                        )
                    else:  # mdy
                        return datetime(
                            int(match.group(3)), int(match.group(1)), int(match.group(2))
                        )
                except ValueError:
                    continue

        logger.debug(f"Could not parse date: {date_str}")
        return None

    def create_temporal_relationships(self, batch_size: int = 100) -> dict:
        """
        Create temporal relationships for all content.
        """
        logger.info("Creating temporal relationships for all content")

        # Get all content with dates
        content_dates = self._get_all_content_dates()

        if len(content_dates) < 2:
            return {"processed": 0, "relationships_created": 0}

        # Sort by date
        sorted_content = sorted(content_dates, key=lambda x: x[1])

        # Create sequential relationships
        sequential_created = self._create_sequential_relationships(sorted_content)

        # Create concurrent relationships (within time window)
        concurrent_created = self._create_concurrent_relationships(sorted_content)

        result = {
            "processed": len(content_dates),
            "relationships_created": sequential_created + concurrent_created,
            "sequential": sequential_created,
            "concurrent": concurrent_created,
        }

        logger.info(f"Temporal relationship creation complete: {result}")
        return result

    def _create_sequential_relationships(self, sorted_content: list[tuple[str, datetime]]) -> int:
        """
        Create sequential temporal relationships.
        """
        relationships_created = 0

        for i in range(len(sorted_content) - 1):
            current_id, current_date = sorted_content[i]
            next_id, next_date = sorted_content[i + 1]

            # Create preceded_by/followed_by relationship
            edge_id = self.kg_service.add_edge(
                current_id,
                next_id,
                "followed_by",
                strength=self._calculate_temporal_strength(current_date, next_date),
                metadata={
                    "current_date": current_date.isoformat(),
                    "next_date": next_date.isoformat(),
                    "time_delta_hours": (next_date - current_date).total_seconds() / 3600,
                },
            )

            if edge_id:
                relationships_created += 1

        return relationships_created

    def _get_all_content_dates(self) -> list[tuple[str, datetime]]:
        """
        Get all content IDs with their dates.
        """
        content_items = self.db.fetch("SELECT id FROM content")

        content_dates = []
        for item in content_items:
            date = self.extract_content_dates(item["content_id"])
            if date:
                content_dates.append((item["content_id"], date))

        return content_dates

    def _calculate_temporal_strength(self, date1: datetime, date2: datetime) -> float:
        """
        Calculate relationship strength based on time proximity.
        """
        delta = abs((date2 - date1).total_seconds())

        # Strength decreases with time distance
        # 1.0 for same day, 0.5 for week, 0.3 for month, etc.
        if delta < 86400:  # Same day
            return 1.0
        elif delta < 604800:  # Same week
            return 0.7
        elif delta < 2592000:  # Same month
            return 0.5
        elif delta < 31536000:  # Same year
            return 0.3
        else:
            return 0.1

    def _create_concurrent_relationships(self, sorted_content: list[tuple[str, datetime]]) -> int:
        """
        Create relationships for content within time windows.
        """
        relationships_created = 0

        for i, (current_id, current_date) in enumerate(sorted_content):
            concurrent_count = self._process_time_window(
                sorted_content, i, current_id, current_date
            )
            relationships_created += concurrent_count

        return relationships_created

    def _process_time_window(
        self, sorted_content: list, index: int, current_id: str, current_date: datetime
    ) -> int:
        """
        Process concurrent relationships within a time window.
        """
        window_end = current_date + timedelta(hours=self.time_window_hours)
        relationships_created = 0

        j = index + 1
        while j < len(sorted_content) and sorted_content[j][1] <= window_end:
            next_id, next_date = sorted_content[j]

            edge_id = self.kg_service.add_edge(
                current_id,
                next_id,
                "concurrent_with",
                strength=0.8,
                metadata={
                    "time_window_hours": self.time_window_hours,
                    "dates": [current_date.isoformat(), next_date.isoformat()],
                },
            )

            if edge_id:
                relationships_created += 1
            j += 1

        return relationships_created

    def find_temporal_cluster(self, content_id: str, window_days: int = 7) -> list[dict]:
        """
        Find all content within a time window of given content.
        """
        # Get date for target content
        target_date = self.extract_content_dates(content_id)

        if not target_date:
            logger.warning(f"No date found for content {content_id}")
            return []

        # Calculate window boundaries
        window_start = target_date - timedelta(days=window_days)
        window_end = target_date + timedelta(days=window_days)

        # Get all content with dates in window
        all_dates = self._get_all_content_dates()

        cluster = []
        for cid, date in all_dates:
            if cid != content_id and window_start <= date <= window_end:
                cluster.append(
                    {
                        "content_id": cid,
                        "date": date.isoformat(),
                        "time_delta_days": abs((date - target_date).days),
                        "relationship": self._determine_temporal_relationship(target_date, date),
                    }
                )

        # Sort by proximity to target
        cluster.sort(key=lambda x: x["time_delta_days"])

        return cluster

    def _determine_temporal_relationship(self, date1: datetime, date2: datetime) -> str:
        """
        Determine the type of temporal relationship.
        """
        delta = (date2 - date1).total_seconds()

        if abs(delta) < 86400:  # Within 24 hours
            return "concurrent_with"
        elif delta > 0:
            return "followed_by"
        else:
            return "preceded_by"

    def get_timeline_context(self, content_id: str, before: int = 5, after: int = 5) -> dict:
        """
        Get timeline context around a piece of content.
        """
        target_date = self.extract_content_dates(content_id)

        if not target_date:
            return {"error": "No date found for content"}

        all_dates = self._get_all_content_dates()
        sorted_dates = sorted(all_dates, key=lambda x: x[1])

        # Find position of target in timeline
        target_idx = self._find_timeline_position(sorted_dates, content_id)

        if target_idx is None:
            return {"error": "Content not found in timeline"}

        # Get surrounding content
        before_content = self._get_before_content(sorted_dates, target_idx, target_date, before)
        after_content = self._get_after_content(sorted_dates, target_idx, target_date, after)

        return {
            "target": {"content_id": content_id, "date": target_date.isoformat()},
            "before": before_content,
            "after": after_content,
            "total_in_timeline": len(sorted_dates),
        }

    def _find_timeline_position(self, sorted_dates: list, content_id: str) -> int | None:
        """
        Find position of content in timeline.
        """
        for i, (cid, _) in enumerate(sorted_dates):
            if cid == content_id:
                return i
        return None

    def _get_before_content(
        self, sorted_dates: list, target_idx: int, target_date: datetime, count: int
    ) -> list[dict]:
        """
        Get content before target in timeline.
        """
        before_content = []
        for i in range(max(0, target_idx - count), target_idx):
            cid, date = sorted_dates[i]
            before_content.append(
                {
                    "content_id": cid,
                    "date": date.isoformat(),
                    "days_before": (target_date - date).days,
                }
            )
        return before_content

    def _get_after_content(
        self, sorted_dates: list, target_idx: int, target_date: datetime, count: int
    ) -> list[dict]:
        """
        Get content after target in timeline.
        """
        after_content = []
        for i in range(target_idx + 1, min(len(sorted_dates), target_idx + count + 1)):
            cid, date = sorted_dates[i]
            after_content.append(
                {
                    "content_id": cid,
                    "date": date.isoformat(),
                    "days_after": (date - target_date).days,
                }
            )
        return after_content

    def extract_legal_dates(self, text: str) -> list[dict]:
        """
        Extract legal-specific dates from text.
        """
        legal_dates = []

        # Patterns for legal dates
        patterns = {
            "court_date": r"(?:court date|hearing|trial).*?(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})",
            "filing_date": r"(?:filed|filing date).*?(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})",
            "deadline": r"(?:deadline|due by|must be).*?(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})",
            "effective_date": r"(?:effective|beginning|starting).*?(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})",
        }

        for date_type, pattern in patterns.items():
            matches = re.finditer(pattern, text, re.IGNORECASE)
            for match in matches:
                date_str = match.group(1)
                parsed_date = self._parse_date_string(date_str)

                if parsed_date:
                    legal_dates.append(
                        {
                            "type": date_type,
                            "date": parsed_date.isoformat(),
                            "original_text": match.group(0),
                        }
                    )

        return legal_dates

    def get_temporal_statistics(self) -> dict:
        """
        Get statistics about temporal relationships in the graph.
        """
        stats = {}

        # Count temporal relationship types
        stats["relationship_counts"] = self._get_relationship_counts()

        # Get date coverage
        all_dates = self._get_all_content_dates()
        stats["date_range"] = self._get_date_range_stats(all_dates)

        # Calculate temporal clustering
        stats["clustering"] = self._calculate_temporal_clustering(all_dates)

        return stats

    def _get_relationship_counts(self) -> dict:
        """
        Get counts of temporal relationship types.
        """
        relationship_counts = self.db.fetch(
            """
            SELECT relationship_type, COUNT(*) as count
            FROM kg_edges
            WHERE relationship_type IN ('preceded_by', 'followed_by', 'concurrent_with')
            GROUP BY relationship_type
        """
        )

        return {row["relationship_type"]: row["count"] for row in relationship_counts}

    def _get_date_range_stats(self, all_dates: list[tuple[str, datetime]]) -> dict:
        """
        Get date range statistics.
        """
        if all_dates:
            dates_only = [d for _, d in all_dates]
            return {
                "earliest": min(dates_only).isoformat(),
                "latest": max(dates_only).isoformat(),
                "total_dated_content": len(all_dates),
            }
        return {"message": "No dated content found"}

    def _calculate_temporal_clustering(self, content_dates: list[tuple[str, datetime]]) -> dict:
        """
        Calculate temporal clustering metrics.
        """
        if len(content_dates) < 2:
            return {"message": "Not enough data for clustering"}

        sorted_dates = sorted(content_dates, key=lambda x: x[1])

        # Calculate time gaps
        gaps = []
        for i in range(len(sorted_dates) - 1):
            gap = (sorted_dates[i + 1][1] - sorted_dates[i][1]).days
            gaps.append(gap)

        if gaps:
            return {
                "avg_gap_days": sum(gaps) / len(gaps),
                "min_gap_days": min(gaps),
                "max_gap_days": max(gaps),
                "clusters_detected": self._count_temporal_clusters(gaps),
            }

        return {"message": "No gaps to analyze"}

    def _count_temporal_clusters(self, gaps: list[int], threshold_days: int = 7) -> int:
        """
        Count distinct temporal clusters based on gaps.
        """
        clusters = 1  # Start with one cluster

        for gap in gaps:
            if gap > threshold_days:
                clusters += 1

        return clusters


def get_timeline_relationships(db_path: str = "emails.db") -> TimelineRelationships:
    """
    Factory function to get timeline relationships instance.
    """
    return TimelineRelationships(db_path)
