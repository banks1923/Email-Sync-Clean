"""Timeline Service for Email and Document Management.

Provides chronological view and navigation of emails, documents, and
related content.
"""

from typing import Any

from loguru import logger

from config.settings import get_db_path
from shared.db.simple_db import SimpleDB


class TimelineService:
    """
    Timeline management for chronological content navigation.
    """

    def __init__(self, db_path: str = None):
        # Use centralized config if no path provided
        if db_path is None:
            db_path = get_db_path()
        self.db_path = db_path
        self.db = SimpleDB(db_path)
        # Logger is now imported globally from loguru
        self._ensure_timeline_tables()

    def _ensure_timeline_tables(self):
        """
        Create timeline-specific tables.
        """
        timeline_events_schema = """
        CREATE TABLE IF NOT EXISTS timeline_events (
            event_id TEXT PRIMARY KEY,
            event_type TEXT NOT NULL,
            content_id TEXT,
            title TEXT NOT NULL,
            description TEXT,
            event_date TEXT NOT NULL,
            created_date TEXT DEFAULT CURRENT_TIMESTAMP,
            metadata TEXT,
            source_type TEXT,
            importance_score INTEGER DEFAULT 0
        )
        """

        timeline_relationships_schema = """
        CREATE TABLE IF NOT EXISTS timeline_relationships (
            relationship_id TEXT PRIMARY KEY,
            parent_event_id TEXT NOT NULL,
            child_event_id TEXT NOT NULL,
            relationship_type TEXT DEFAULT 'related',
            created_date TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (parent_event_id) REFERENCES timeline_events(event_id),
            FOREIGN KEY (child_event_id) REFERENCES timeline_events(event_id)
        )
        """

        indexes = [
            "CREATE INDEX IF NOT EXISTS idx_timeline_date ON timeline_events(event_date)",
            "CREATE INDEX IF NOT EXISTS idx_timeline_type ON timeline_events(event_type)",
            "CREATE INDEX IF NOT EXISTS idx_timeline_importance ON timeline_events(importance_score)",
            "CREATE INDEX IF NOT EXISTS idx_relationships_parent ON timeline_relationships(parent_event_id)",
        ]

        try:
            self.db.execute(timeline_events_schema)
            self.db.execute(timeline_relationships_schema)
            for index in indexes:
                self.db.execute(index)
        except Exception as e:
            logger.error(f"Error creating timeline tables: {e}")

    def sync_emails_to_timeline(self, limit: int = 100) -> dict[str, Any]:
        """
        Sync recent emails to timeline events.
        """
        try:
            # Get emails from the individual_messages table (v2 schema)
            email_query = """
                SELECT im.message_id, im.subject, im.sender_email as sender, im.date_sent as datetime_utc
                FROM individual_messages im
                WHERE im.date_sent IS NOT NULL AND im.date_sent != ''
                ORDER BY im.date_sent DESC
                LIMIT ?
            """

            emails = self.db.fetch(email_query, (limit,))
            if not emails:
                return {"success": False, "error": "No emails found to sync"}

            synced_count = 0
            for email in emails:
                event_result = self._create_timeline_event(
                    event_type="email",
                    content_id=email["message_id"],
                    title=email["subject"] or "No Subject",
                    description=f"Email from {email['sender']}",
                    event_date=email["datetime_utc"],
                    metadata={"sender": email["sender"]},
                    source_type="gmail",
                )
                if event_result["success"]:
                    synced_count += 1

            return {"success": True, "synced_events": synced_count}

        except Exception as e:
            logger.error(f"Error syncing emails to timeline: {e}")
            return {"success": False, "error": str(e)}

    def sync_documents_to_timeline(self, limit: int = 50) -> dict[str, Any]:
        """
        Sync recent documents to timeline events.
        """
        try:
            doc_query = """
                SELECT chunk_id, file_name, processed_time, char_count
                FROM documents
                WHERE processed_time IS NOT NULL
                ORDER BY processed_time DESC
                LIMIT ?
            """

            documents = self.db.fetch(doc_query, (limit,))
            if not documents:
                return {"success": False, "error": "No documents found to sync"}

            synced_count = 0
            for doc in documents:
                event_result = self._create_timeline_event(
                    event_type="document",
                    content_id=doc["chunk_id"],
                    title=f"Document: {doc['file_name']}",
                    description=f"Document chunk ({doc['char_count']} chars)",
                    event_date=doc["processed_time"],
                    metadata={"file_name": doc["file_name"], "char_count": doc["char_count"]},
                    source_type="upload",
                )
                if event_result["success"]:
                    synced_count += 1

            return {"success": True, "synced_events": synced_count}

        except Exception as e:
            logger.error(f"Error syncing documents to timeline: {e}")
            return {"success": False, "error": str(e)}

    def get_timeline_view(
        self,
        start_date: str | None = None,
        end_date: str | None = None,
        event_types: list[str] | None = None,
        limit: int = 50,
    ) -> dict[str, Any]:
        """
        Get chronological timeline view with filtering.
        """
        try:
            from .database import TimelineDatabase

            timeline_db = TimelineDatabase(self.db_path)

            if event_types:
                # Get events for each type separately and combine
                all_events = []
                for event_type in event_types:
                    result = timeline_db.get_timeline_events(
                        start_date=start_date,
                        end_date=end_date,
                        event_type=event_type,
                        limit=limit // len(event_types),
                    )
                    if result["success"]:
                        all_events.extend(result["events"])

                # Sort combined results by date
                all_events.sort(key=lambda x: x["event_date"], reverse=True)
                all_events = all_events[:limit]

                return {"success": True, "timeline": all_events, "count": len(all_events)}
            else:
                return timeline_db.get_timeline_events(start_date, end_date, None, limit)

        except Exception as e:
            logger.error(f"Error getting timeline view: {e}")
            return {"success": False, "error": str(e)}

    def _create_timeline_event(
        self,
        event_type: str,
        content_id: str,
        title: str,
        description: str,
        event_date: str,
        metadata: dict | None = None,
        source_type: str | None = None,
        importance_score: int = 0,
    ) -> dict[str, Any]:
        """
        Create timeline event using database operations.
        """
        try:
            from .database import TimelineDatabase

            timeline_db = TimelineDatabase(self.db_path)
            return timeline_db.create_timeline_event(
                event_type=event_type,
                title=title,
                event_date=event_date,
                content_id=content_id,
                description=description,
                metadata=metadata,
                source_type=source_type,
                importance_score=importance_score,
            )

        except Exception as e:
            logger.error(f"Error creating timeline event: {e}")
            return {"success": False, "error": str(e)}


def get_timeline_service(db_path: str = None) -> TimelineService:
    """Factory function to create TimelineService instance.

    Args:
        db_path: Path to the database file

    Returns:
        TimelineService instance
    """
    # Use centralized config if no path provided
    if db_path is None:
        db_path = get_db_path()
    return TimelineService(db_path)
