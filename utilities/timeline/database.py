"""Timeline database operations.

Core database operations for timeline events and relationships.
"""

import json
import uuid
from typing import Any

from shared.simple_db import SimpleDB
from config.settings import get_db_path


class TimelineDatabase:
    """Database operations for timeline management."""

    def __init__(self, db_path: str = None):
        # Use centralized config if no path provided
        if db_path is None:
            db_path = get_db_path()
        self.db = SimpleDB(db_path)

    def create_timeline_event(
        self,
        event_type: str,
        title: str,
        event_date: str,
        content_id: str | None = None,
        description: str | None = None,
        metadata: dict | None = None,
        source_type: str | None = None,
        importance_score: int = 0,
    ) -> dict[str, Any]:
        """Create a new timeline event."""
        try:
            event_id = str(uuid.uuid4())
            metadata_json = json.dumps(metadata) if metadata else None

            query = """
                INSERT OR REPLACE INTO timeline_events
                (event_id, event_type, content_id, title, description,
                 event_date, metadata, source_type, importance_score)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """

            result = self.db.execute_query(
                query,
                (
                    event_id,
                    event_type,
                    content_id,
                    title,
                    description,
                    event_date,
                    metadata_json,
                    source_type,
                    importance_score,
                ),
            )

            if result["success"]:
                return {"success": True, "event_id": event_id}
            else:
                return {"success": False, "error": result["error"]}

        except Exception as e:
            return {"success": False, "error": f"Database error: {str(e)}"}

    def get_timeline_events(
        self,
        start_date: str | None = None,
        end_date: str | None = None,
        event_type: str | None = None,
        limit: int = 50,
    ) -> dict[str, Any]:
        """Get timeline events with optional filtering."""
        try:
            query_parts = ["SELECT * FROM timeline_events WHERE 1=1"]
            params = []

            if start_date:
                query_parts.append("AND event_date >= ?")
                params.append(start_date)

            if end_date:
                query_parts.append("AND event_date <= ?")
                params.append(end_date)

            if event_type:
                query_parts.append("AND event_type = ?")
                params.append(event_type)

            query_parts.append("ORDER BY event_date DESC LIMIT ?")
            params.append(limit)

            query = " ".join(query_parts)
            result = self.db.execute_query(query, tuple(params))

            if result["success"]:
                events = result["data"]
                # Parse metadata JSON
                for event in events:
                    if event.get("metadata"):
                        try:
                            event["metadata"] = json.loads(event["metadata"])
                        except json.JSONDecodeError:
                            event["metadata"] = {}

                return {"success": True, "events": events, "count": len(events)}
            else:
                return {"success": False, "error": result["error"]}

        except Exception as e:
            return {"success": False, "error": f"Database error: {str(e)}"}

    def create_event_relationship(
        self, parent_event_id: str, child_event_id: str, relationship_type: str = "related"
    ) -> dict[str, Any]:
        """Create relationship between timeline events."""
        try:
            relationship_id = str(uuid.uuid4())

            query = """
                INSERT INTO timeline_relationships
                (relationship_id, parent_event_id, child_event_id, relationship_type)
                VALUES (?, ?, ?, ?)
            """

            result = self.db.execute_query(
                query, (relationship_id, parent_event_id, child_event_id, relationship_type)
            )

            if result["success"]:
                return {"success": True, "relationship_id": relationship_id}
            else:
                return {"success": False, "error": result["error"]}

        except Exception as e:
            return {"success": False, "error": f"Database error: {str(e)}"}

    def get_related_events(self, event_id: str) -> dict[str, Any]:
        """Get events related to a specific event."""
        try:
            query = """
                SELECT te.*, tr.relationship_type
                FROM timeline_events te
                JOIN timeline_relationships tr ON (
                    te.event_id = tr.child_event_id OR te.event_id = tr.parent_event_id
                )
                WHERE (tr.parent_event_id = ? OR tr.child_event_id = ?)
                AND te.event_id != ?
            """

            result = self.db.execute_query(query, (event_id, event_id, event_id))

            if result["success"]:
                events = result["data"]
                for event in events:
                    if event.get("metadata"):
                        try:
                            event["metadata"] = json.loads(event["metadata"])
                        except json.JSONDecodeError:
                            event["metadata"] = {}

                return {"success": True, "related_events": events, "count": len(events)}
            else:
                return {"success": False, "error": result["error"]}

        except Exception as e:
            return {"success": False, "error": f"Database error: {str(e)}"}
