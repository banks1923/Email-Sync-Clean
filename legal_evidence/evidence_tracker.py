"""Legal Evidence Tracker - Simple EID management for email evidence.

Direct implementation following CLAUDE.md principles:
- Simple functions, no abstractions
- Direct database access
- Flat structure
"""

import re
from datetime import datetime
from typing import Any

from loguru import logger

from shared.simple_db import SimpleDB


class EvidenceTracker:
    """Track emails with legal Evidence IDs (EIDs) for court references."""
    
    def __init__(self, db_path: str = "data/emails.db"):
        """Initialize with database connection."""
        self.db = SimpleDB(db_path)
        self._ensure_schema()
        
    def _ensure_schema(self):
        """Add legal tracking columns to emails table if needed."""
        # Add EID and thread_id columns if they don't exist
        try:
            self.db.execute("""
                ALTER TABLE emails ADD COLUMN eid TEXT UNIQUE
            """)
            logger.info("Added eid column to emails table")
        except:
            pass  # Column already exists
            
        try:
            self.db.execute("""
                ALTER TABLE emails ADD COLUMN thread_id TEXT
            """)
            logger.info("Added thread_id column to emails table")
        except:
            pass  # Column already exists
            
        # Create index for faster thread lookups
        try:
            self.db.execute("""
                CREATE INDEX idx_thread_id ON emails(thread_id)
            """)
        except:
            pass  # Index already exists
    
    def generate_eid(self, message_id: str, datetime_utc: str) -> str:
        """Generate unique Evidence ID for email.
        
        Format: EID-YYYY-NNNN where NNNN is a unique number for that year.
        """
        # Extract year from datetime
        year = datetime_utc[:4] if datetime_utc else str(datetime.now().year)
        
        # Get the highest EID number for this year
        cursor = self.db.execute("""
            SELECT eid FROM emails 
            WHERE eid LIKE ? 
            ORDER BY eid DESC LIMIT 1
        """, (f"EID-{year}-%",))
        
        last_eid = cursor.fetchone()
        
        if last_eid and last_eid[0]:
            # Extract number and increment
            match = re.match(r'EID-\d{4}-(\d{4})', last_eid[0])
            if match:
                next_num = int(match.group(1)) + 1
            else:
                next_num = 1
        else:
            next_num = 1
            
        return f"EID-{year}-{next_num:04d}"
    
    def assign_eids(self, limit: int | None = None) -> dict[str, Any]:
        """Assign EIDs to all emails that don't have them yet."""
        # Get emails without EIDs
        query = """
            SELECT id, message_id, datetime_utc, thread_id 
            FROM emails 
            WHERE eid IS NULL
            ORDER BY datetime_utc, id
        """
        
        if limit:
            query += f" LIMIT {limit}"
            
        cursor = self.db.execute(query)
        emails = cursor.fetchall()
        
        assigned = 0
        for email in emails:
            eid = self.generate_eid(email['message_id'], email['datetime_utc'])
            
            self.db.execute("""
                UPDATE emails SET eid = ? WHERE id = ?
            """, (eid, email['id']))
            
            assigned += 1
            
        logger.info(f"Assigned {assigned} new EIDs")
        
        return {
            "success": True,
            "assigned": assigned,
            "total_without_eid": len(emails)
        }
    
    def assign_thread_ids(self) -> dict[str, Any]:
        """Group emails by thread based on subject similarity."""
        # Get all emails
        cursor = self.db.execute("""
            SELECT id, subject, datetime_utc, sender
            FROM emails 
            ORDER BY datetime_utc
        """)
        
        emails = cursor.fetchall()
        
        # Simple thread detection: normalize subject
        threads = {}
        thread_count = 0
        
        for email in emails:
            # Normalize subject by removing Re:, Fwd:, etc.
            subject = email['subject'] or ""
            normalized = re.sub(r'^(Re:|Fwd:|Fw:)\s*', '', subject, flags=re.IGNORECASE).strip()
            normalized = re.sub(r'\s+', ' ', normalized).lower()
            
            # Create thread key from normalized subject + participants
            thread_key = f"{normalized}"
            
            if thread_key not in threads:
                thread_count += 1
                threads[thread_key] = f"THREAD-{thread_count:04d}"
                
            # Update email with thread ID
            self.db.execute("""
                UPDATE emails SET thread_id = ? WHERE id = ?
            """, (threads[thread_key], email['id']))
            
        logger.info(f"Assigned {thread_count} thread IDs to {len(emails)} emails")
        
        return {
            "success": True,
            "threads_created": thread_count,
            "emails_processed": len(emails)
        }
    
    def get_email_evidence(self, eid: str) -> dict[str, Any] | None:
        """Get email evidence by EID."""
        cursor = self.db.execute("""
            SELECT eid, message_id, subject, sender, recipient_to,
                   datetime_utc, thread_id, content
            FROM emails
            WHERE eid = ?
        """, (eid,))
        
        result = cursor.fetchone()
        if result:
            return dict(result)
        return None
    
    def get_thread_emails(self, thread_id: str) -> list[dict[str, Any]]:
        """Get all emails in a thread, ordered chronologically."""
        cursor = self.db.execute("""
            SELECT eid, message_id, subject, sender, recipient_to,
                   datetime_utc, content
            FROM emails
            WHERE thread_id = ?
            ORDER BY datetime_utc
        """, (thread_id,))
        
        return [dict(row) for row in cursor.fetchall()]
    
    def search_by_pattern(self, pattern: str, limit: int = 100) -> list[dict[str, Any]]:
        """Search emails for specific patterns (for legal discovery)."""
        cursor = self.db.execute("""
            SELECT eid, message_id, subject, sender, datetime_utc,
                   thread_id, content
            FROM emails
            WHERE content LIKE ? OR subject LIKE ?
            ORDER BY datetime_utc DESC
            LIMIT ?
        """, (f"%{pattern}%", f"%{pattern}%", limit))
        
        return [dict(row) for row in cursor.fetchall()]
    
    def get_evidence_summary(self) -> dict[str, Any]:
        """Get summary statistics for evidence tracking."""
        stats = {}
        
        # Total emails with EIDs
        cursor = self.db.execute("SELECT COUNT(*) FROM emails WHERE eid IS NOT NULL")
        stats['emails_with_eid'] = cursor.fetchone()[0]
        
        # Total without EIDs
        cursor = self.db.execute("SELECT COUNT(*) FROM emails WHERE eid IS NULL")
        stats['emails_without_eid'] = cursor.fetchone()[0]
        
        # Total threads
        cursor = self.db.execute("SELECT COUNT(DISTINCT thread_id) FROM emails WHERE thread_id IS NOT NULL")
        stats['total_threads'] = cursor.fetchone()[0]
        
        # Date range
        cursor = self.db.execute("SELECT MIN(datetime_utc), MAX(datetime_utc) FROM emails")
        result = cursor.fetchone()
        stats['date_range'] = {
            'earliest': result[0],
            'latest': result[1]
        }
        
        return stats


# Simple factory function
def get_evidence_tracker(db_path: str = "data/emails.db") -> EvidenceTracker:
    """Get evidence tracker instance."""
    return EvidenceTracker(db_path)