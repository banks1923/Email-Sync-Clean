import hashlib
import os
import sqlite3
import sys

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from loguru import logger

from config.settings import get_db_path
from gmail.validators import DateValidator, EmailValidator, InputSanitizer

# Logger is now imported globally from loguru


class EmailStorage:
    """
    SQLite storage backend for Gmail emails with deduplication and sync state
    tracking.
    """

    def __init__(self, db_path=None):
        """Initialize email storage with database path.

        Args:
            db_path: Path to SQLite database file.
        """
        # Use centralized config if no path provided
        if db_path is None:
            db_path = get_db_path()
        self.db_path = db_path
        self.init_db()

    def init_db(self):
        """
        Initialize database tables for emails, sync state, and attachments.
        """
        conn = sqlite3.connect(self.db_path)

        # Create emails table with content_hash for deduplication
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS emails (
                id INTEGER PRIMARY KEY,
                message_id TEXT UNIQUE NOT NULL,
                subject TEXT NOT NULL,
                sender TEXT NOT NULL,
                recipient_to TEXT,
                content TEXT,
                datetime_utc DATETIME,
                content_hash TEXT UNIQUE,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """
        )

        # Create sync_state table for incremental sync
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS sync_state (
                account_email TEXT PRIMARY KEY,
                last_history_id TEXT,
                last_sync_time DATETIME,
                last_message_id TEXT,
                sync_status TEXT DEFAULT 'idle',
                sync_in_progress BOOLEAN DEFAULT 0,
                messages_processed INTEGER DEFAULT 0,
                duplicates_found INTEGER DEFAULT 0,
                error_count INTEGER DEFAULT 0,
                last_error TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """
        )

        # Create attachments table
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS email_attachments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                message_id TEXT NOT NULL,
                filename TEXT,
                mime_type TEXT,
                size_bytes INTEGER,
                attachment_id TEXT,
                stored_path TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (message_id) REFERENCES emails(message_id)
            )
        """
        )

        conn.commit()
        conn.close()

    def generate_content_hash(self, email_data: dict) -> str:
        """Generate SHA-256 hash of email content for deduplication.

        Uses subject, sender, date, and body to create unique hash.
        """
        # Normalize data for consistent hashing
        subject = (email_data.get("subject") or "").strip().lower()
        sender = (email_data.get("sender") or "").strip().lower()
        date = (email_data.get("datetime_utc") or "").strip()
        content = (email_data.get("content") or "").strip()

        # Create hash string
        hash_input = f"{subject}|{sender}|{date}|{content}"
        content_hash = hashlib.sha256(hash_input.encode("utf-8")).hexdigest()

        return content_hash

    def _validate_required_fields(self, email_data):
        """
        Validate required fields in email data.
        """
        if not email_data.get("message_id"):
            return {"success": False, "error": "Missing message_id"}

        if not email_data.get("sender"):
            return {"success": False, "error": "Missing sender"}

        return {"success": True}

    def _validate_email_addresses(self, email_data):
        """
        Validate and clean email addresses.
        """
        # Validate sender email format with intelligent header parsing
        sender_validation = EmailValidator.validate_email_header(email_data["sender"])
        if not sender_validation["success"]:
            return {
                "success": False,
                "error": f"Invalid sender email: {sender_validation['error']}",
            }

        # Use extracted email for storage (clean format)
        clean_sender = sender_validation["extracted_email"]

        # Validate recipient if provided (also handle headers intelligently)
        clean_recipient = ""
        if email_data.get("recipient_to"):
            recipient_validation = EmailValidator.validate_email_header(email_data["recipient_to"])
            if not recipient_validation["success"]:
                return {
                    "success": False,
                    "error": f"Invalid recipient email: {recipient_validation['error']}",
                }
            clean_recipient = recipient_validation["extracted_email"]

        return {"success": True, "clean_sender": clean_sender, "clean_recipient": clean_recipient}

    def _validate_and_sanitize_data(self, email_data):
        """
        Validate datetime and sanitize subject.
        """
        # Validate datetime if provided
        if email_data.get("datetime_utc"):
            date_validation = DateValidator.validate_iso_datetime(email_data["datetime_utc"])
            if not date_validation["success"]:
                return {"success": False, "error": f"Invalid datetime: {date_validation['error']}"}

        # Sanitize subject
        if email_data.get("subject"):
            subject_sanitized = InputSanitizer.sanitize_search_query(
                email_data["subject"], max_length=500
            )
            if subject_sanitized["success"]:
                email_data["subject"] = subject_sanitized["query"]

        return {"success": True}

    def _insert_email_to_db(self, email_data, clean_sender, clean_recipient):
        """
        Insert email data into database with content hash.
        """
        # Generate content hash for deduplication
        content_hash = self.generate_content_hash(
            {
                "subject": email_data.get("subject", ""),
                "sender": clean_sender,
                "datetime_utc": email_data.get("datetime_utc", ""),
                "content": email_data.get("content", ""),
            }
        )

        conn = sqlite3.connect(self.db_path)
        try:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT OR IGNORE INTO emails
                (message_id, subject, sender, recipient_to, content, datetime_utc, content_hash)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
                (
                    email_data["message_id"],
                    email_data.get("subject", ""),
                    clean_sender,  # Use extracted clean email format
                    clean_recipient,  # Use extracted clean recipient format
                    email_data.get("content", ""),
                    email_data.get("datetime_utc", ""),
                    content_hash,
                ),
            )
            conn.commit()
            was_inserted = cursor.rowcount > 0

            if not was_inserted:
                logger.debug(
                    f"Duplicate email skipped: {email_data['message_id']} (hash: {content_hash[:8]}...)"
                )

            return {"success": True, "message": "Email saved", "inserted": was_inserted}
        except Exception as e:
            conn.rollback()
            logger.error(f"Failed to insert email: {e}")
            return {"success": False, "error": str(e)}
        finally:
            conn.close()

    def save_email(self, email_data):
        """
        Save email to database with validation.
        """
        # Validate required fields
        required_validation = self._validate_required_fields(email_data)
        if not required_validation["success"]:
            return required_validation

        # Validate and clean email addresses
        email_validation = self._validate_email_addresses(email_data)
        if not email_validation["success"]:
            return email_validation

        clean_sender = email_validation["clean_sender"]
        clean_recipient = email_validation["clean_recipient"]

        # Validate datetime and sanitize subject
        data_validation = self._validate_and_sanitize_data(email_data)
        if not data_validation["success"]:
            return data_validation

        # Insert to database
        return self._insert_email_to_db(email_data, clean_sender, clean_recipient)

    def save_emails_batch(self, email_list, batch_size=1000, progress_callback=None):
        """Batch save multiple emails with validation and deduplication.

        Uses INSERT OR IGNORE for automatic deduplication.
        """
        if not email_list:
            return {"success": True, "total": 0, "inserted": 0, "ignored": 0, "errors": []}

        # Prepare validated data
        prepared_data = []
        errors = []

        for idx, email_data in enumerate(email_list):
            # Validate required fields
            required_validation = self._validate_required_fields(email_data)
            if not required_validation["success"]:
                errors.append({"index": idx, "error": required_validation["error"]})
                continue

            # Validate and clean email addresses
            email_validation = self._validate_email_addresses(email_data)
            if not email_validation["success"]:
                errors.append({"index": idx, "error": email_validation["error"]})
                continue

            # Validate datetime and sanitize subject
            data_validation = self._validate_and_sanitize_data(email_data)
            if not data_validation["success"]:
                errors.append({"index": idx, "error": data_validation["error"]})
                continue

            # Generate content hash for deduplication
            content_hash = self.generate_content_hash(
                {
                    "subject": email_data.get("subject", ""),
                    "sender": email_validation["clean_sender"],
                    "datetime_utc": email_data.get("datetime_utc", ""),
                    "content": email_data.get("content", ""),
                }
            )

            # Add to prepared data
            prepared_data.append(
                (
                    email_data["message_id"],
                    email_data.get("subject", ""),
                    email_validation["clean_sender"],
                    email_validation["clean_recipient"],
                    email_data.get("content", ""),
                    email_data.get("datetime_utc", ""),
                    content_hash,
                )
            )

        # Batch insert using executemany
        conn = sqlite3.connect(self.db_path)
        try:
            total_inserted = 0
            for i in range(0, len(prepared_data), batch_size):
                chunk = prepared_data[i : i + batch_size]
                cursor = conn.executemany(
                    """
                    INSERT OR IGNORE INTO emails
                    (message_id, subject, sender, recipient_to, content, datetime_utc, content_hash)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    chunk,
                )
                total_inserted += cursor.rowcount

                if progress_callback:
                    progress_callback(min(i + batch_size, len(prepared_data)), len(prepared_data))

            conn.commit()

            return {
                "success": True,
                "total": len(email_list),
                "inserted": total_inserted,
                "ignored": len(prepared_data) - total_inserted,
                "validation_errors": len(errors),
                "errors": errors,
            }
        except Exception as e:
            conn.rollback()
            return {"success": False, "error": str(e), "validation_errors": errors}
        finally:
            conn.close()

    def get_emails(self, limit=100):
        """Retrieve emails from database ordered by date.

        Args:
            limit: Maximum number of emails to return.

        Returns:
            List of email dictionaries.
        """
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.execute(
            """
            SELECT * FROM emails
            ORDER BY datetime_utc DESC
            LIMIT ?
        """,
            (limit,),
        )
        emails = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return emails

    # Sync State Management Methods
    def get_sync_state(self, account_email: str) -> dict | None:
        """
        Get sync state for an email account.
        """
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.execute("SELECT * FROM sync_state WHERE account_email = ?", (account_email,))
        result = cursor.fetchone()
        conn.close()
        return dict(result) if result else None

    def update_sync_state(
        self,
        account_email: str,
        history_id: str = None,
        messages_processed: int = 0,
        duplicates_found: int = 0,
        status: str = "idle",
        error: str = None,
    ) -> dict:
        """
        Update sync state after successful sync.
        """
        conn = sqlite3.connect(self.db_path)
        try:
            cursor = conn.cursor()

            # Check if record exists
            existing = cursor.execute(
                "SELECT account_email FROM sync_state WHERE account_email = ?", (account_email,)
            ).fetchone()

            if existing:
                # Update existing record
                cursor.execute(
                    """
                    UPDATE sync_state
                    SET last_history_id = COALESCE(?, last_history_id),
                        last_sync_time = CURRENT_TIMESTAMP,
                        sync_status = ?,
                        messages_processed = messages_processed + ?,
                        duplicates_found = duplicates_found + ?,
                        last_error = ?,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE account_email = ?
                    """,
                    (
                        history_id,
                        status,
                        messages_processed,
                        duplicates_found,
                        error,
                        account_email,
                    ),
                )
            else:
                # Insert new record
                cursor.execute(
                    """
                    INSERT INTO sync_state
                    (account_email, last_history_id, last_sync_time, sync_status,
                     messages_processed, duplicates_found, last_error)
                    VALUES (?, ?, CURRENT_TIMESTAMP, ?, ?, ?, ?)
                    """,
                    (
                        account_email,
                        history_id,
                        status,
                        messages_processed,
                        duplicates_found,
                        error,
                    ),
                )

            conn.commit()
            logger.info(f"Sync state updated for {account_email}: {status}")
            return {"success": True}

        except Exception as e:
            conn.rollback()
            logger.error(f"Failed to update sync state: {e}")
            return {"success": False, "error": str(e)}
        finally:
            conn.close()

    def save_attachments(self, message_id: str, attachments: list[dict]) -> dict:
        """
        Save email attachment metadata.
        """
        if not attachments:
            return {"success": True, "count": 0}

        conn = sqlite3.connect(self.db_path)
        try:
            cursor = conn.cursor()
            for attachment in attachments:
                cursor.execute(
                    """
                    INSERT OR IGNORE INTO email_attachments
                    (message_id, filename, mime_type, size_bytes, attachment_id)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (
                        message_id,
                        attachment.get("filename", ""),
                        attachment.get("mime_type", ""),
                        attachment.get("size_bytes", 0),
                        attachment.get("attachment_id", ""),
                    ),
                )

            conn.commit()
            count = cursor.rowcount
            logger.debug(f"Saved {count} attachments for message {message_id}")
            return {"success": True, "count": count}

        except Exception as e:
            conn.rollback()
            logger.error(f"Failed to save attachments: {e}")
            return {"success": False, "error": str(e)}
        finally:
            conn.close()
