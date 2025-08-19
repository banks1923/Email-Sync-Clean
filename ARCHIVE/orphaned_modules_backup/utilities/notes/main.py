"""Notes Service for Email and Document Management.

Provides note-taking functionality to bridge gaps between emails and documents.
"""

import json
import uuid
from typing import Any

from loguru import logger

from shared.simple_db import SimpleDB


class NotesService:
    """Notes management for connecting emails and documents."""

    def __init__(self, db_path: str = "emails.db"):
        self.db_path = db_path
        self.db = SimpleDB(db_path)
        # Logger is now imported globally from loguru
        self._ensure_notes_tables()

    def _ensure_notes_tables(self):
        """Create notes-specific tables."""
        notes_schema = """
        CREATE TABLE IF NOT EXISTS notes (
            note_id TEXT PRIMARY KEY,
            title TEXT NOT NULL,
            content TEXT NOT NULL,
            note_type TEXT DEFAULT 'general',
            created_date TEXT DEFAULT CURRENT_TIMESTAMP,
            modified_date TEXT DEFAULT CURRENT_TIMESTAMP,
            tags TEXT,
            importance_level INTEGER DEFAULT 1,
            archived BOOLEAN DEFAULT 0
        )
        """

        note_links_schema = """
        CREATE TABLE IF NOT EXISTS note_links (
            link_id TEXT PRIMARY KEY,
            note_id TEXT NOT NULL,
            linked_type TEXT NOT NULL,
            linked_id TEXT NOT NULL,
            link_description TEXT,
            created_date TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (note_id) REFERENCES notes(note_id)
        )
        """

        indexes = [
            "CREATE INDEX IF NOT EXISTS idx_notes_created ON notes(created_date)",
            "CREATE INDEX IF NOT EXISTS idx_notes_type ON notes(note_type)",
            "CREATE INDEX IF NOT EXISTS idx_notes_importance ON notes(importance_level)",
            "CREATE INDEX IF NOT EXISTS idx_note_links_note ON note_links(note_id)",
            "CREATE INDEX IF NOT EXISTS idx_note_links_linked ON note_links(linked_type, linked_id)",
        ]

        try:
            self.db.execute(notes_schema)
            self.db.execute(note_links_schema)
            for index in indexes:
                self.db.execute(index)
        except Exception as e:
            logger.error(f"Error creating notes tables: {e}")

    def create_note(
        self,
        title: str,
        content: str,
        note_type: str = "general",
        tags: list[str] | None = None,
        importance_level: int = 1,
    ) -> dict[str, Any]:
        """Create a new note."""
        try:
            note_id = str(uuid.uuid4())
            tags_json = json.dumps(tags) if tags else None

            query = """
                INSERT INTO notes (note_id, title, content, note_type, tags, importance_level)
                VALUES (?, ?, ?, ?, ?, ?)
            """

            self.db.execute(
                query, (note_id, title, content, note_type, tags_json, importance_level)
            )
            return {"success": True, "note_id": note_id}

        except Exception as e:
            logger.error(f"Error creating note: {e}")
            return {"success": False, "error": str(e)}

    def link_note_to_content(
        self, note_id: str, linked_type: str, linked_id: str, description: str | None = None
    ) -> dict[str, Any]:
        """Link a note to an email or document."""
        try:
            link_id = str(uuid.uuid4())

            query = """
                INSERT INTO note_links (link_id, note_id, linked_type, linked_id, link_description)
                VALUES (?, ?, ?, ?, ?)
            """

            self.db.execute(
                query, (link_id, note_id, linked_type, linked_id, description)
            )
            return {"success": True, "link_id": link_id}

        except Exception as e:
            logger.error(f"Error linking note: {e}")
            return {"success": False, "error": str(e)}

    def get_notes_for_content(self, content_type: str, content_id: str) -> dict[str, Any]:
        """Get all notes linked to specific content."""
        try:
            query = """
                SELECT n.*, nl.link_description, nl.created_date as link_created
                FROM notes n
                JOIN note_links nl ON n.note_id = nl.note_id
                WHERE nl.linked_type = ? AND nl.linked_id = ?
                AND n.archived = 0
                ORDER BY n.importance_level DESC, n.created_date DESC
            """

            notes = self.db.fetch(query, (content_type, content_id))
            
            for note in notes:
                if note.get("tags"):
                    try:
                        note["tags"] = json.loads(note["tags"])
                    except json.JSONDecodeError:
                        note["tags"] = []

            return {"success": True, "notes": notes, "count": len(notes)}

        except Exception as e:
            logger.error(f"Error getting notes for content: {e}")
            return {"success": False, "error": str(e)}

    def search_notes(
        self,
        query: str,
        note_type: str | None = None,
        tags: list[str] | None = None,
        limit: int = 20,
    ) -> dict[str, Any]:
        """Search notes by content and metadata."""
        try:
            search_parts = ["SELECT * FROM notes WHERE archived = 0"]
            params = []

            # Text search in title and content
            search_parts.append("AND (title LIKE ? OR content LIKE ?)")
            search_pattern = f"%{query}%"
            params.extend([search_pattern, search_pattern])

            if note_type:
                search_parts.append("AND note_type = ?")
                params.append(note_type)

            if tags:
                tag_conditions = []
                for tag in tags:
                    tag_conditions.append("tags LIKE ?")
                    params.append(f"%{tag}%")
                if tag_conditions:
                    search_parts.append(f"AND ({' OR '.join(tag_conditions)})")

            search_parts.append("ORDER BY importance_level DESC, created_date DESC LIMIT ?")
            params.append(limit)

            search_query = " ".join(search_parts)
            notes = self.db.fetch(search_query, tuple(params))
            
            for note in notes:
                if note.get("tags"):
                    try:
                        note["tags"] = json.loads(note["tags"])
                    except json.JSONDecodeError:
                        note["tags"] = []

            return {"success": True, "notes": notes, "count": len(notes)}

        except Exception as e:
            logger.error(f"Error searching notes: {e}")
            return {"success": False, "error": str(e)}
