"""Legal Evidence Tracker - Simple EID management for email evidence.

Direct implementation following CLAUDE.md principles:
- Simple functions, no abstractions
- Direct database access
- Flat structure
"""

import re
import sqlite3
from datetime import datetime
from typing import Any

from loguru import logger

from shared.simple_db import SimpleDB


class EvidenceTracker:
    """
    Track emails with legal Evidence IDs (EIDs) for court references.
    """

    def __init__(self, db_path: str = "data/system_data/emails.db"):
        """
        Initialize with database connection.
        """
        self.db = SimpleDB(db_path)
        self._ensure_schema()

    def _ensure_schema(self):
        """
        Add legal tracking columns to individual_messages table if needed.
        """
        # Add EID column if it doesn't exist
        try:
            self.db.execute(
                """
                ALTER TABLE individual_messages ADD COLUMN eid TEXT UNIQUE
            """
            )
            logger.info("Added eid column to individual_messages table")
        except sqlite3.OperationalError:
            pass  # Column already exists

        # Note: thread_id already exists in individual_messages by default
        # Create index for EID lookups
        try:
            self.db.execute(
                """
                CREATE INDEX idx_eid ON individual_messages(eid)
            """
            )
        except sqlite3.OperationalError:
            pass  # Index already exists

    def generate_eid(self, message_id: str, datetime_utc: str) -> str:
        """Generate unique Evidence ID for email.

        Format: EID-YYYY-NNNN where NNNN is a unique number for that year.
        """
        # Extract year from datetime
        year = datetime_utc[:4] if datetime_utc else str(datetime.now().year)

        # Get the highest EID number for this year
        cursor = self.db.execute(
            """
            SELECT eid FROM individual_messages 
            WHERE eid LIKE ? 
            ORDER BY eid DESC LIMIT 1
        """,
            (f"EID-{year}-%",),
        )

        last_eid = cursor.fetchone()

        if last_eid and last_eid[0]:
            # Extract number and increment
            match = re.match(r"EID-\d{4}-(\d{4})", last_eid[0])
            if match:
                next_num = int(match.group(1)) + 1
            else:
                next_num = 1
        else:
            next_num = 1

        return f"EID-{year}-{next_num:04d}"

    def assign_eids(self, limit: int | None = None) -> dict[str, Any]:
        """
        Assign EIDs to all emails that don't have them yet.
        """
        # Get emails without EIDs
        query = """
            SELECT message_hash, message_id, date_sent, thread_id 
            FROM individual_messages 
            WHERE eid IS NULL
            ORDER BY date_sent, message_hash
        """

        if limit:
            query += f" LIMIT {limit}"

        cursor = self.db.execute(query)
        emails = cursor.fetchall()

        assigned = 0
        for email in emails:
            eid = self.generate_eid(email["message_id"], email["date_sent"])

            self.db.execute(
                """
                UPDATE individual_messages SET eid = ? WHERE message_hash = ?
            """,
                (eid, email["message_hash"]),
            )

            assigned += 1

        logger.info(f"Assigned {assigned} new EIDs")

        return {"success": True, "assigned": assigned, "total_without_eid": len(emails)}

    def assign_thread_ids(self) -> dict[str, Any]:
        """
        Group emails by thread based on subject similarity.
        """
        # Get all emails
        cursor = self.db.execute(
            """
            SELECT message_hash, subject, date_sent, sender_email
            FROM individual_messages 
            ORDER BY date_sent
        """
        )

        emails = cursor.fetchall()

        # Simple thread detection: normalize subject
        threads = {}
        thread_count = 0

        for email in emails:
            # Normalize subject by removing Re:, Fwd:, etc.
            subject = email["subject"] or ""
            normalized = re.sub(r"^(Re:|Fwd:|Fw:)\s*", "", subject, flags=re.IGNORECASE).strip()
            normalized = re.sub(r"\s+", " ", normalized).lower()

            # Create thread key from normalized subject + participants
            thread_key = f"{normalized}"

            if thread_key not in threads:
                thread_count += 1
                threads[thread_key] = f"THREAD-{thread_count:04d}"

            # Update email with thread ID
            self.db.execute(
                """
                UPDATE individual_messages SET thread_id = ? WHERE message_hash = ?
            """,
                (threads[thread_key], email["message_hash"]),
            )

        logger.info(f"Assigned {thread_count} thread IDs to {len(emails)} emails")

        return {"success": True, "threads_created": thread_count, "emails_processed": len(emails)}

    def get_email_evidence(self, eid: str) -> dict[str, Any] | None:
        """
        Get email evidence by EID.
        """
        cursor = self.db.execute(
            """
            SELECT im.eid, im.message_id, im.subject, im.sender_email,
                   im.recipients, im.date_sent, im.thread_id, cu.body as content
            FROM individual_messages im
            JOIN content_unified cu ON cu.source_id = im.message_hash
            WHERE cu.source_type = 'email_message'
              AND im.eid = ?
        """,
            (eid,),
        )

        result = cursor.fetchone()
        if result:
            return dict(result)
        return None

    def get_thread_emails(self, thread_id: str) -> list[dict[str, Any]]:
        """
        Get all emails in a thread, ordered chronologically.
        """
        cursor = self.db.execute(
            """
            SELECT im.eid, im.message_id, im.subject, im.sender_email,
                   im.recipients, im.date_sent, cu.body as content
            FROM individual_messages im
            JOIN content_unified cu ON cu.source_id = im.message_hash
            WHERE cu.source_type = 'email_message'
              AND im.thread_id = ?
            ORDER BY im.date_sent
        """,
            (thread_id,),
        )

        return [dict(row) for row in cursor.fetchall()]

    def search_by_pattern(self, pattern: str, limit: int = 100) -> list[dict[str, Any]]:
        """
        Search emails for specific patterns (for legal discovery).
        """
        cursor = self.db.execute(
            """
            SELECT im.eid, im.message_id, im.subject, im.sender_email,
                   im.date_sent, im.thread_id, cu.body as content
            FROM individual_messages im
            JOIN content_unified cu ON cu.source_id = im.message_hash
            WHERE cu.source_type = 'email_message'
              AND (cu.body LIKE ? OR im.subject LIKE ?)
            ORDER BY im.date_sent DESC
            LIMIT ?
        """,
            (f"%{pattern}%", f"%{pattern}%", limit),
        )

        return [dict(row) for row in cursor.fetchall()]

    def get_evidence_summary(self) -> dict[str, Any]:
        """
        Get summary statistics for evidence tracking.
        """
        stats = {}

        # Total emails with EIDs
        cursor = self.db.execute("SELECT COUNT(*) FROM individual_messages WHERE eid IS NOT NULL")
        stats["emails_with_eid"] = cursor.fetchone()[0]

        # Total without EIDs
        cursor = self.db.execute("SELECT COUNT(*) FROM individual_messages WHERE eid IS NULL")
        stats["emails_without_eid"] = cursor.fetchone()[0]

        # Total threads
        cursor = self.db.execute(
            "SELECT COUNT(DISTINCT thread_id) FROM individual_messages WHERE thread_id IS NOT NULL"
        )
        stats["total_threads"] = cursor.fetchone()[0]

        # Date range
        cursor = self.db.execute("SELECT MIN(date_sent), MAX(date_sent) FROM individual_messages")
        result = cursor.fetchone()
        stats["date_range"] = {"earliest": result[0], "latest": result[1]}

        return stats


# Simple factory function
def get_evidence_tracker(db_path: str = "data/system_data/emails.db") -> EvidenceTracker:
    """
    Get evidence tracker instance.
    """
    return EvidenceTracker(db_path)
