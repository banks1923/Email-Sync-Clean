"""Schema migration shim for legacy tests.

Provides `ContentSchemaMigration` compatible with tests by migrating
legacy email/content tables to include expected columns and constraints.
"""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict
from uuid import UUID, uuid5


UUID_NAMESPACE = UUID("6ba7b810-9dad-11d1-80b4-00c04fd430c8")


@dataclass
class ContentSchemaMigration:
    db_path: str

    def _column_exists(self, cursor: sqlite3.Cursor, table: str, column: str) -> bool:
        cursor.execute(f"PRAGMA table_info({table})")
        return any(row[1] == column for row in cursor.fetchall())

    def _ensure_content_schema(self, conn: sqlite3.Connection) -> None:
        cursor = conn.cursor()
        # Ensure required columns on content table
        required_columns = ["source_type", "external_id"]
        for col in required_columns:
            if not self._column_exists(cursor, "content", col):
                cursor.execute(f"ALTER TABLE content ADD COLUMN {col} TEXT")

        # Unique index on (source_type, external_id) for idempotency
        cursor.execute(
            "CREATE UNIQUE INDEX IF NOT EXISTS idx_content_source_external "
            "ON content(source_type, external_id)"
        )

    def _migrate_emails(self, conn: sqlite3.Connection, dry_run: bool) -> int:
        cursor = conn.cursor()
        try:
            cursor.execute(
                "SELECT message_id, subject, content FROM emails"
            )
        except sqlite3.Error:
            # No emails table; nothing to migrate
            return 0

        rows = cursor.fetchall()
        migrated = 0
        for message_id, subject, body in rows:
            if not message_id:
                continue
            deterministic_id = str(uuid5(UUID_NAMESPACE, f"email:{message_id}"))
            if not dry_run:
                cursor.execute(
                    """
                    INSERT OR IGNORE INTO content (id, source_type, external_id, title, content)
                    VALUES (?, 'email', ?, ?, ?)
                    """,
                    (deterministic_id, message_id, subject or "", body or ""),
                )
                if cursor.rowcount:
                    migrated += 1
        return migrated

    def run_migration(self, dry_run: bool = True) -> Dict[str, Any]:
        metrics: Dict[str, Any] = {"emails_migrated": 0, "errors": []}
        try:
            # Ensure DB path directory exists
            Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
            with sqlite3.connect(self.db_path) as conn:
                self._ensure_content_schema(conn)
                migrated = self._migrate_emails(conn, dry_run=dry_run)
                if not dry_run:
                    conn.commit()
                metrics["emails_migrated"] = migrated
        except Exception as e:
            metrics["errors"].append(str(e))
        return metrics

