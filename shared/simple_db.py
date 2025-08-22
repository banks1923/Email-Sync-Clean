"""
Dead simple database operations. No abstraction astronauts allowed.
For a single user who just wants things to work.
"""

import contextlib
import hashlib
import json
import os
import sqlite3
import time
import uuid
from collections.abc import Callable, Generator
from datetime import datetime
from pathlib import Path
from typing import Any

# Import new error handling and retry utilities
from loguru import logger

from .retry_helper import retry_database

# Configure logging for batch operations
# Logger is now imported globally from loguru


class DBMetrics:
    """Simple metrics tracking for database operations."""
    def __init__(self):
        self.slow_sql_count = 0
        self.busy_events = 0
        self.checkpoint_ms = 0.0  # Changed to float for time calculations
        self.total_queries = 0
    
    def report(self):
        """Report metrics on exit or demand."""
        if self.total_queries > 0:
            logger.info(f"DB Metrics: {self.total_queries} queries, "
                       f"{self.slow_sql_count} slow (>{100}ms), "
                       f"{self.busy_events} busy events, "
                       f"{self.checkpoint_ms:.0f}ms in checkpoints")


class SimpleDB:
    """The entire database layer in under 100 lines. No BS."""

    def __init__(self, db_path: str = "data/emails.db") -> None:
        self.db_path = db_path
        self._ensure_data_directories()
        self.batch_stats = {
            "total_operations": 0,
            "total_records": 0,
            "total_inserted": 0,
            "total_ignored": 0,
            "total_time_seconds": 0.0,
            "avg_records_per_second": 0.0,
        }
        # Initialize metrics tracking
        self.metrics = DBMetrics()
        # Initialize with optimized SQLite settings
        self._initialize_pragmas()

    def _initialize_pragmas(self) -> None:
        """Initialize SQLite with optimized settings for single-user performance."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                # Configure and verify on startup
                self._configure_connection(conn, verify=True)
        except Exception as e:
            logger.warning(f"Could not initialize SQLite pragmas: {e}")

    def _configure_connection(self, conn: sqlite3.Connection, verify: bool = False) -> None:
        """Configure SQLite connection with optimized pragmas."""
        # Enable foreign keys (already had this)
        conn.execute("PRAGMA foreign_keys=ON")
        
        # Performance optimizations for single-user system
        conn.execute("PRAGMA journal_mode=WAL")        # Persists per DB file
        conn.execute("PRAGMA synchronous=NORMAL")      # Safe for single-user, faster
        conn.execute("PRAGMA busy_timeout=5000")       # 5 second timeout
        
        # Cache size from environment or default to 64MB
        cache_kb = int(os.getenv("SIMPLEDB_CACHE_KB", "64000"))
        conn.execute(f"PRAGMA cache_size=-{abs(cache_kb)}")
        
        # Memory for temp tables
        conn.execute("PRAGMA temp_store=MEMORY")
        
        # Memory-mapped I/O (opt-in via environment variable)
        mmap_bytes = int(os.getenv("SIMPLEDB_MMAP_BYTES", "0"))
        if mmap_bytes > 0:
            conn.execute(f"PRAGMA mmap_size={mmap_bytes}")
        
        # Verify settings on first connection
        if verify:
            jm = conn.execute("PRAGMA journal_mode").fetchone()[0].upper()
            if jm != "WAL":
                logger.warning(f"Failed to set WAL mode, got: {jm}. May be on network FS.")
            
            sync = conn.execute("PRAGMA synchronous").fetchone()[0]
            cache = conn.execute("PRAGMA cache_size").fetchone()[0]
            mmap = conn.execute("PRAGMA mmap_size").fetchone()[0]
            
            logger.info(f"SQLite config: mode={jm}, sync={sync}, cache={abs(cache)}KB, mmap={mmap}B")

    def _ensure_data_directories(self) -> None:
        """Ensure /data/ directory structure exists for document processing pipeline."""
        # Get project root (parent of shared directory)
        project_root = Path(__file__).parent.parent
        data_dir = project_root / "data"

        # Define required subdirectories
        subdirs = ["raw", "staged", "processed", "quarantine", "export"]

        # Create directories if they don't exist
        for subdir in subdirs:
            dir_path = data_dir / subdir
            try:
                dir_path.mkdir(parents=True, exist_ok=True)
                # Ensure .gitkeep exists
                gitkeep = dir_path / ".gitkeep"
                if not gitkeep.exists():
                    gitkeep.touch()
            except Exception as e:
                logger.warning(f"Could not create data directory {dir_path}: {e}")

        # Log successful initialization
        if data_dir.exists():
            logger.debug(f"Data directories verified at {data_dir}")

    @contextlib.contextmanager
    def durable_txn(self, conn: sqlite3.Connection) -> Generator[None, None, None]:
        """Context manager for critical operations requiring full durability."""
        prev_sync = conn.execute("PRAGMA synchronous").fetchone()[0]
        conn.execute("PRAGMA synchronous=FULL")
        try:
            conn.execute("BEGIN IMMEDIATE")
            yield conn
            conn.commit()
            logger.debug("Durable transaction committed with FULL synchronous")
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.execute(f"PRAGMA synchronous={prev_sync}")

    @retry_database
    def execute(self, query: str, params: tuple = ()) -> sqlite3.Cursor:
        """Just run SQL. No enterprise patterns. Now with retry for database locks."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                self._configure_connection(conn)
                
                # Track metrics
                self.metrics.total_queries += 1
                
                # Slow-query logging
                t0 = time.perf_counter()
                cursor = conn.execute(query, params) if params else conn.execute(query)
                dt_ms = (time.perf_counter() - t0) * 1000
                
                if dt_ms > 100:  # Log queries slower than 100ms
                    self.metrics.slow_sql_count += 1
                    logger.info(f"Slow SQL: {dt_ms:.1f}ms, rows={cursor.rowcount}, query={query[:50]}")
                
                conn.commit()
                return cursor
        except sqlite3.OperationalError as e:
            if "database is locked" in str(e) or "SQLITE_BUSY" in str(e):
                self.metrics.busy_events += 1
                logger.warning(f"Database busy/locked: {e}")
            raise
        except sqlite3.Error as e:
            logger.error(f"Database execute error: {e}, Query: {query[:100]}")
            raise

    @retry_database
    def fetch(self, query: str, params: tuple = ()) -> list[dict]:
        """Run query and get results as dicts. With retry for database locks."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                self._configure_connection(conn)
                
                # Track metrics
                self.metrics.total_queries += 1
                
                # Slow-query logging
                t0 = time.perf_counter()
                results = conn.execute(query, params).fetchall()
                dt_ms = (time.perf_counter() - t0) * 1000
                
                if dt_ms > 100:  # Log queries slower than 100ms
                    self.metrics.slow_sql_count += 1
                    logger.info(f"Slow SQL: {dt_ms:.1f}ms, rows={len(results)}, query={query[:50]}")
                
                return [dict(row) for row in results]
        except sqlite3.OperationalError as e:
            if "database is locked" in str(e) or "SQLITE_BUSY" in str(e):
                self.metrics.busy_events += 1
                logger.warning(f"Database busy/locked: {e}")
            return []
        except sqlite3.Error as e:
            logger.error(f"Database fetch error: {e}, Query: {query[:100]}")
            return []

    def fetch_one(self, query: str, params: tuple = ()) -> dict | None:
        """Get single result as dict."""
        results = self.fetch(query, params)
        return results[0] if results else None

    # Content operations (replaces ContentWriter)
    def add_content(
        self,
        content_type: str,
        title: str,
        content: str,
        metadata: dict | None = None,
        source_path: str | None = None,
    ) -> str:
        """Add content to content_unified table - emails, transcripts, PDFs. Returns content ID."""
        # Calculate content hash for deduplication
        normalized_title = (title or "").strip().lower()
        normalized_content = (content or "").strip()
        hash_input = f"{content_type}:{normalized_title}:{normalized_content}"
        content_hash = hashlib.sha256(hash_input.encode("utf-8")).hexdigest()

        # Check if content already exists by hash
        existing = self.fetch_one(
            "SELECT id FROM content_unified WHERE sha256 = ?", (content_hash,)
        )

        if existing:
            logger.info(
                f"Duplicate content detected, returning existing ID: {existing['id']}"
            )
            return existing["id"]

        # Generate numeric source_id from hash
        source_id = abs(hash(content_hash)) % 2147483647  # Ensure it fits in INTEGER
        
        cursor = self.execute(
            """
            INSERT OR IGNORE INTO content_unified (source_type, source_id, title, body, sha256, ready_for_embedding)
            VALUES (?, ?, ?, ?, ?, ?)
        """,
            (
                content_type,  # Maps to source_type
                source_id,
                title,
                content,  # Maps to body
                content_hash,  # Maps to sha256
                1  # Mark ready for embedding
            ),
        )
        
        # Get the auto-generated ID
        if cursor.lastrowid:
            return str(cursor.lastrowid)
        else:
            # If insert was ignored due to duplicate, find existing ID
            existing = self.fetch_one(
                "SELECT id FROM content_unified WHERE sha256 = ?", (content_hash,)
            )
            return str(existing["id"]) if existing else str(source_id)

    def add_email_message(
        self,
        message_content: str,
        thread_id: str,
        email_id: str,
        sender: str = None,
        date: str = None,
        subject: str = None,
        depth: int = 0,
        message_type: str = "extracted"
    ) -> str:
        """
        Add individual email message from thread parsing.
        Special handling for legal case evidence preservation.
        """
        # For legal cases, include sender and date in hash to catch harassment patterns
        # This ensures repeated identical messages from same sender are preserved as evidence
        hash_input = f"email_message:{sender}:{date}:{message_content}"
        content_hash = hashlib.sha256(hash_input.encode("utf-8")).hexdigest()
        
        # Check for existing message
        existing = self.fetch_one(
            "SELECT id FROM content_unified WHERE sha256 = ?", (content_hash,)
        )
        
        if existing:
            logger.info(f"Duplicate message detected from {sender} at {date}, returning existing ID: {existing['id']}")
            return existing["id"]
        
        # Generate source_id
        source_id = abs(hash(content_hash)) % 2147483647
        
        # Create descriptive title
        title = f"{subject} - {sender}" if subject and sender else f"Message from {sender}" if sender else "Email Message"
        
        cursor = self.execute(
            """
            INSERT OR IGNORE INTO content_unified (source_type, source_id, title, body, sha256, ready_for_embedding)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                "email_message",
                source_id,
                title,
                message_content,
                content_hash,
                1  # Ready for embedding
            ),
        )
        
        # Get the auto-generated ID
        if cursor.lastrowid:
            message_id = str(cursor.lastrowid)
            logger.info(f"Stored email message from {sender}: {message_id}")
            return message_id
        else:
            # If insert was ignored, find existing
            existing = self.fetch_one(
                "SELECT id FROM content_unified WHERE sha256 = ?", (content_hash,)
            )
            return str(existing["id"]) if existing else str(source_id)
    
    def upsert_content(
        self,
        source_type: str,
        external_id: str,
        content_type: str,
        title: str,
        content: str,
        metadata: dict = None,
        parent_content_id: str = None
    ) -> str:
        """
        Upsert content using business key (source_type, external_id).

        Args:
            source_type: Type of source (email, pdf, transcript, etc.)
            external_id: External identifier (message_id, file_hash, etc.)  
            content_type: Type of content (ignored - use source_type)
            title: Content title
            content: Actual content text
            metadata: Optional metadata dict (ignored - not in schema)
            parent_content_id: Optional parent content ID (ignored - not in schema)

        Returns:
            Content ID from database
        """
        import hashlib

        # Convert external_id to numeric source_id
        source_id = abs(hash(external_id)) % 2147483647

        # Calculate content hash for deduplication
        content_hash = hashlib.sha256(content.encode()).hexdigest()

        # UPSERT operation using actual content_unified schema
        # Columns: id, source_type, source_id, title, body, created_at, ready_for_embedding, sha256, chunk_index
        self.execute("""
            INSERT INTO content_unified (source_type, source_id, title, body, sha256, ready_for_embedding)
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(source_type, source_id) DO UPDATE SET
                title = excluded.title,
                body = excluded.body,
                sha256 = excluded.sha256,
                ready_for_embedding = excluded.ready_for_embedding
        """, (source_type, source_id, title, content, content_hash, 1))

        # Get the ID of the upserted record
        result = self.fetch_one(
            "SELECT id FROM content_unified WHERE source_type = ? AND source_id = ?",
            (source_type, source_id)
        )

        if result:
            logger.info(f"Content upserted: {source_type}:{external_id} -> {result['id']}")
            return str(result['id'])
        else:
            logger.error(f"Failed to upsert content: {source_type}:{external_id}")
            return str(source_id)

    def update_content(self, content_id: str, **kwargs) -> bool:
        """Update content fields. Returns True if successful."""
        if not kwargs:
            return False
            
        # Build dynamic update query
        set_clauses = []
        params = []
        
        for field, value in kwargs.items():
            if field in ["title", "content", "content_type", "metadata", "source_path"]:
                if field == "metadata" and isinstance(value, dict):
                    value = json.dumps(value)
                set_clauses.append(f"{field} = ?")
                params.append(value)
        
        if not set_clauses:
            return False
            
        # Add updated timestamp
        set_clauses.append("updated_at = CURRENT_TIMESTAMP")
        
        # Recalculate content-derived fields if content changed
        if "content" in kwargs:
            content = kwargs["content"]
            set_clauses.extend(["word_count = ?", "char_count = ?"])
            params.extend([len(content.split()) if content else 0, len(content) if content else 0])
        
        params.append(content_id)
        query = f"UPDATE content_unified SET {', '.join(set_clauses)} WHERE id = ?"
        
        cursor = self.execute(query, tuple(params))
        return cursor.rowcount > 0

    def delete_content(self, content_id: str) -> bool:
        """Delete content by ID. Returns True if successful."""
        cursor = self.execute("DELETE FROM content_unified WHERE id = ?", (content_id,))
        return cursor.rowcount > 0

    # Simple thread tracking methods
    def add_thread_tracking(self, thread_id: str, message_count: int, status: str = "processed") -> bool:
        """Add or update thread processing status. Simple and direct."""
        self.execute(
            """
            INSERT OR REPLACE INTO thread_tracking 
            (thread_id, message_count, status, last_updated)
            VALUES (?, ?, ?, CURRENT_TIMESTAMP)
            """,
            (thread_id, message_count, status)
        )
        return True

    def get_thread_status(self, thread_id: str) -> dict | None:
        """Get thread processing status."""
        return self.fetch_one(
            "SELECT * FROM thread_tracking WHERE thread_id = ?", 
            (thread_id,)
        )

    def list_processed_threads(self, limit: int = 100) -> list[dict]:
        """List recently processed threads."""
        return self.fetch(
            "SELECT * FROM thread_tracking ORDER BY last_updated DESC LIMIT ?",
            (limit,)
        )

    def add_document_chunk(self, chunk_data: dict) -> str:
        """Add PDF document chunk. Returns chunk_id."""
        chunk_id = chunk_data.get("chunk_id", str(uuid.uuid4()))

        self.execute(
            """
            INSERT INTO content_unified (id, file_path, file_name, chunk_index,
                text_content, char_count, file_size, file_hash,
                source_type, processed_time, content_type, ready_for_embedding,
                extraction_method
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
            (
                chunk_id,
                chunk_data["file_path"],
                chunk_data["file_name"],
                chunk_data["chunk_index"],
                chunk_data["text_content"],
                chunk_data["char_count"],
                chunk_data.get("file_size", 0),
                chunk_data.get("file_hash"),
                chunk_data.get("source_type", "upload"),
                chunk_data.get("processed_time", datetime.now().isoformat()),
                chunk_data.get("content_type", "document"),
                chunk_data.get("ready_for_embedding", 0),
                chunk_data.get("extraction_method", "pdfplumber"),
            ),
        )

        return chunk_id

    def get_content(self, content_id: str) -> dict | None:
        """Get content by ID."""
        return self.fetch_one("SELECT * FROM content_unified WHERE id = ?", (content_id,))

    def search_content(
        self,
        keyword: str,
        content_type: str | None = None,
        limit: int = 50,
        filters: dict | None = None,
    ) -> list[dict]:
        """Search content with optional filters."""
        from .date_utils import get_date_range

        # Base WHERE clause
        where_clauses = ["(title LIKE ? OR body LIKE ?)"]
        params = [f"%{keyword}%", f"%{keyword}%"]

        # Add content type filter
        if content_type:
            where_clauses.append("source_type = ?")
            params.append(content_type)

        # Add filters if provided
        if filters:
            # Date range filtering
            since = filters.get("since")
            until = filters.get("until")
            if since or until:
                start_date, end_date = get_date_range(since, until)
                if start_date:
                    where_clauses.append("created_at >= ?")
                    params.append(start_date.isoformat())
                if end_date:
                    where_clauses.append("created_at <= ?")
                    params.append(end_date.isoformat())

            # Content types filtering (multiple types)
            content_types = filters.get("content_types")
            if content_types and isinstance(content_types, list):
                placeholders = ",".join(["?"] * len(content_types))
                where_clauses.append(f"source_type IN ({placeholders})")
                params.extend(content_types)

            # Tags filtering
            tags = filters.get("tags")
            if tags:
                if isinstance(tags, str):
                    tags = [tags]
                if isinstance(tags, list):
                    tag_logic = filters.get("tag_logic", "OR").upper()
                    if tag_logic == "AND":
                        for tag in tags:
                            where_clauses.append(
                                "(metadata LIKE ? OR title LIKE ? OR body LIKE ?)"
                            )
                            tag_pattern = f"%{tag}%"
                            params.extend([tag_pattern, tag_pattern, tag_pattern])
                    else:  # OR logic
                        tag_conditions = []
                        for tag in tags:
                            tag_conditions.append(
                                "(metadata LIKE ? OR title LIKE ? OR body LIKE ?)"
                            )
                            tag_pattern = f"%{tag}%"
                            params.extend([tag_pattern, tag_pattern, tag_pattern])
                        if tag_conditions:
                            where_clauses.append(f"({' OR '.join(tag_conditions)})")

        # Build final query
        where_clause = " AND ".join(where_clauses)
        query = f"SELECT * FROM content_unified WHERE {where_clause} ORDER BY created_at DESC LIMIT ?"
        params.append(limit)

        return self.fetch(query, tuple(params))

    def get_content_stats(self) -> dict:
        """Get simple stats."""
        stats = {}
        
        # Get content count from the CORRECT table (content_unified not content)
        content_result = self.fetch_one("SELECT COUNT(*) as count FROM content_unified")
        stats["total_content"] = content_result["count"] if content_result else 0
        
        # Get content by type from content_unified
        type_results = self.fetch(
            "SELECT source_type, COUNT(*) as count FROM content_unified GROUP BY source_type"
        )
        stats["content_by_type"] = {row["source_type"]: row["count"] for row in type_results} if type_results else {}
        
        # Get actual document count from documents table
        doc_result = self.fetch_one("SELECT COUNT(*) as count FROM documents")
        stats["total_documents"] = doc_result["count"] if doc_result else 0
        
        # Get breakdown by source type
        stats["total_emails"] = stats["content_by_type"].get("email", 0)
        stats["total_pdfs"] = stats["content_by_type"].get("pdf", 0)
        stats["total_transcripts"] = stats["content_by_type"].get("transcript", 0)
            
        # Add database size
        db_info = self.fetch_one("SELECT page_count * page_size as size FROM pragma_page_count(), pragma_page_size()")
        stats["database_size_bytes"] = db_info["size"] if db_info else 0
        
        return stats

    def get_content_count(self, content_type: str | None = None) -> int:
        """Get count of content entries by type.
        
        Args:
            content_type: Optional type filter ('email', 'pdf', 'transcript', etc.)
                         If None, returns total count across all types.
        
        Returns:
            Count of content entries
        """
        stats = self.get_content_stats()
        if content_type is not None:
            # Map plural collection names to singular content types
            type_mapping = {
                'emails': 'email',
                'pdfs': 'pdf',
                'transcriptions': 'transcript',
                'notes': 'note'
            }
            # Use mapped type if available, otherwise use as-is
            mapped_type = type_mapping.get(content_type, content_type)
            # Return count for specific type from content_by_type dict
            return int(stats.get("content_by_type", {}).get(mapped_type, 0))
        # Return total count
        return int(stats.get("total_content", 0))
    
    def get_connection(self):
        """Get database connection for direct SQL operations.
        
        Returns:
            sqlite3.Connection: A new database connection with configured pragmas
            
        Note:
            Prefer using higher-level SimpleDB methods when possible.
            This is provided for maintenance scripts that need direct access.
            Caller is responsible for closing the connection.
        """
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        self._configure_connection(conn)
        return conn

    # Batch operations for deduplication (Task 1.1 + 1.4)
    def batch_insert(
        self,
        table_name: str,
        columns: list[str],
        data_list: list[tuple],
        batch_size: int = 1000,
        progress_callback: Callable[[int, int], None] | None = None,
    ) -> dict[str, Any]:
        """
        Generic batch insert with INSERT OR IGNORE for deduplication.
        Includes timing, logging, and performance metrics.
        Returns stats with performance data.
        """
        if not data_list:
            logger.debug(f"Empty data list for {table_name}, skipping")
            return {"total": 0, "inserted": 0, "ignored": 0, "time_seconds": 0}

        start_time = time.time()
        logger.info(f"Starting batch insert to {table_name}: {len(data_list)} records")

        # NOTE: Metrics count one 'query' per chunked executemany(), not per row,
        # to avoid inflating totals during large batches.

        # Build INSERT OR IGNORE query
        placeholders = ",".join(["?"] * len(columns))
        column_names = ",".join(columns)
        query = f"INSERT OR IGNORE INTO {table_name} ({column_names}) VALUES ({placeholders})"

        total_processed = 0
        total_inserted = 0
        errors = []

        # Process in chunks for memory efficiency
        with sqlite3.connect(self.db_path) as conn:
            # Ensure pragmas are applied on this connection as well
            self._configure_connection(conn)
            for i in range(0, len(data_list), batch_size):
                chunk = data_list[i : i + batch_size]
                attempts = 0
                max_attempts = 3
                backoff = 0.1  # seconds

                while True:
                    chunk_start = time.time()
                    try:
                        # Acquire write lock up-front; keep transaction short
                        conn.execute("BEGIN IMMEDIATE")
                        cursor = conn.executemany(query, chunk)
                        conn.commit()

                        # Metrics & counters
                        self.metrics.total_queries += 1  # count per chunk
                        total_inserted += cursor.rowcount
                        total_processed += len(chunk)

                        # Chunk performance logging
                        chunk_time = time.time() - chunk_start
                        if chunk_time * 1000 > 100:
                            self.metrics.slow_sql_count += 1
                            logger.info(
                                f"Slow batch SQL: {chunk_time*1000:.1f}ms, rows={cursor.rowcount}, "
                                f"table={table_name}, chunk={i//batch_size + 1}"
                            )
                        chunk_rate = len(chunk) / chunk_time if chunk_time > 0 else 0
                        logger.debug(
                            f"Chunk {i//batch_size + 1}: {len(chunk)} records, "
                            f"{chunk_time:.2f}s, {chunk_rate:.0f} rec/s"
                        )

                        # Progress callback with percentage
                        if progress_callback:
                            percentage = (total_processed / len(data_list)) * 100
                            progress_callback(total_processed, len(data_list))
                            logger.debug(
                                f"Progress: {percentage:.1f}% ({total_processed}/{len(data_list)})"
                            )

                        break  # success, next chunk

                    except sqlite3.OperationalError as e:
                        # Handle transient lock/contention with limited retries
                        if "database is locked" in str(e) or "SQLITE_BUSY" in str(e):
                            self.metrics.busy_events += 1
                            attempts += 1
                            logger.warning(
                                f"Database busy on batch {i//batch_size + 1} (attempt {attempts}/{max_attempts}): {e}"
                            )
                            # Rollback any partial work in this txn
                            with contextlib.suppress(Exception):
                                conn.rollback()
                            if attempts < max_attempts:
                                time.sleep(backoff)
                                backoff *= 2
                                continue
                        # Non-retryable or max attempts reached
                        logger.error(f"Error in batch {i//batch_size + 1}: {str(e)}")
                        errors.append({"batch": i // batch_size + 1, "error": str(e)})
                        # Ensure rollback before moving on
                        with contextlib.suppress(Exception):
                            conn.rollback()
                        break
                    except Exception as e:
                        logger.error(f"Error in batch {i//batch_size + 1}: {str(e)}")
                        errors.append({"batch": i // batch_size + 1, "error": str(e)})
                        with contextlib.suppress(Exception):
                            conn.rollback()
                        break

        # Calculate final metrics
        elapsed = time.time() - start_time
        rate = len(data_list) / elapsed if elapsed > 0 else 0
        ignored = len(data_list) - total_inserted

        # Update cumulative stats
        self.batch_stats["total_operations"] += 1
        self.batch_stats["total_records"] += len(data_list)
        self.batch_stats["total_inserted"] += total_inserted
        self.batch_stats["total_ignored"] += ignored
        self.batch_stats["total_time_seconds"] += elapsed
        self.batch_stats["avg_records_per_second"] = (
            self.batch_stats["total_records"] / self.batch_stats["total_time_seconds"]
            if self.batch_stats["total_time_seconds"] > 0
            else 0
        )

        # Log summary
        logger.info(
            f"Batch insert complete: {total_inserted}/{len(data_list)} inserted, "
            f"{ignored} ignored, {elapsed:.2f}s, {rate:.0f} rec/s"
        )

        if errors:
            logger.warning(f"Batch insert had {len(errors)} errors")

        return {
            "total": len(data_list),
            "inserted": total_inserted,
            "ignored": ignored,
            "time_seconds": elapsed,
            "records_per_second": rate,
            "errors": errors,
        }

    # Batch content operations (Task 1.2 + 1.4)
    def batch_add_content(
        self,
        content_list: list[dict],
        batch_size: int = 1000,
        progress_callback: Callable[[int, int], None] | None = None,
    ) -> dict[str, Any]:
        """
        Batch add content with auto-generation of IDs and metadata.
        Includes enhanced logging and performance tracking.
        Returns: {'stats': {total/inserted/ignored}, 'content_ids': [...]}
        """
        if not content_list:
            logger.debug("Empty content list, skipping batch_add_content")
            return {"stats": {"total": 0, "inserted": 0, "ignored": 0}, "content_ids": []}

        logger.info(f"Processing {len(content_list)} content items for batch insert")
        start_time = time.time()

        # Prepare data tuples with auto-generated fields
        prepared_data = []
        content_ids = []
        total_chars = 0

        for idx, item in enumerate(content_list):
            # Calculate char count
            content = item.get("content", "")
            char_count = len(content) if content else 0
            total_chars += char_count

            # Calculate content hash for deduplication
            content_type = item.get("content_type", "unknown")
            title = item.get("title", "")
            normalized_title = (title or "").strip().lower()
            normalized_content = (content or "").strip()
            hash_input = f"{content_type}:{normalized_title}:{normalized_content}"
            content_hash = hashlib.sha256(hash_input.encode("utf-8")).hexdigest()

            # Generate numeric source_id from hash
            source_id = abs(hash(content_hash)) % 2147483647

            # Create tuple for batch insert (matches content_unified schema)
            # Columns: source_type, source_id, title, body, sha256, ready_for_embedding
            prepared_data.append(
                (
                    content_type,  # source_type
                    source_id,     # source_id
                    title,         # title  
                    content,       # body
                    content_hash,  # sha256
                    1,             # ready_for_embedding
                )
            )
            
            # Store the auto-generated ID for returning
            content_ids.append(str(source_id))

            if (idx + 1) % 100 == 0:
                logger.debug(f"Prepared {idx + 1}/{len(content_list)} content items")

        prep_time = time.time() - start_time
        logger.info(
            f"Data preparation complete: {prep_time:.2f}s, "
            f"{total_chars} chars"
        )

        # Use batch_insert with content_unified table columns
        columns = [
            "source_type",
            "source_id", 
            "title",
            "body",
            "sha256",
            "ready_for_embedding",
        ]

        stats = self.batch_insert("content_unified", columns, prepared_data, batch_size, progress_callback)

        # Log content-specific stats
        logger.info(
            f"Content batch complete: {stats['inserted']} new items, "
            f"avg {total_chars//len(content_list)} chars/item"
        )

        return {"stats": stats, "content_ids": content_ids}

    # Batch document operations (Task 1.3 + 1.4)
    def batch_add_document_chunk(
        self,
        chunk_list: list[dict],
        batch_size: int = 1000,
        progress_callback: Callable[[int, int], None] | None = None,
    ) -> dict[str, Any]:
        """
        Batch add document chunks for PDF processing.
        Includes enhanced logging and performance metrics.
        Returns: {'stats': {total/inserted/ignored}, 'chunk_ids': [...]}
        """
        if not chunk_list:
            logger.debug("Empty chunk list, skipping batch_add_document_chunk")
            return {"stats": {"total": 0, "inserted": 0, "ignored": 0}, "chunk_ids": []}

        logger.info(f"Processing {len(chunk_list)} document chunks for batch insert")
        start_time = time.time()

        # Prepare data tuples with auto-generated fields
        prepared_data = []
        chunk_ids = []
        total_chars = 0
        file_paths = set()

        for idx, chunk in enumerate(chunk_list):
            # Auto-generate chunk_id if not provided
            chunk_id = chunk.get("chunk_id", str(uuid.uuid4()))
            chunk_ids.append(chunk_id)

            # Calculate char_count if not provided
            text_content = chunk.get("text_content", "")
            char_count = chunk.get("char_count", len(text_content) if text_content else 0)
            total_chars += char_count
            file_paths.add(chunk.get("file_path", "unknown"))

            # Create tuple for batch insert (matches content table + extraction_method)
            prepared_data.append(
                (
                    chunk_id,
                    chunk["file_path"],
                    chunk["file_name"],
                    chunk["chunk_index"],
                    text_content,
                    char_count,
                    chunk.get("file_size", 0),
                    chunk.get("file_hash"),
                    chunk.get("source_type", "upload"),
                    chunk.get("processed_time", datetime.now().isoformat()),
                    chunk.get("content_type", "document"),
                    chunk.get("ready_for_embedding", 0),
                    chunk.get("extraction_method", "pdfplumber"),
                )
            )

            if (idx + 1) % 100 == 0:
                logger.debug(f"Prepared {idx + 1}/{len(chunk_list)} document chunks")

        prep_time = time.time() - start_time
        logger.info(
            f"Data preparation complete: {prep_time:.2f}s, "
            f"{len(file_paths)} unique files, {total_chars} total chars"
        )

        # Use batch_insert with content table columns (correct primary key 'id')
        columns = [
            "id",
            "file_path",
            "file_name",
            "chunk_index",
            "text_content",
            "char_count",
            "file_size",
            "file_hash",
            "source_type",
            "processed_time",
            "content_type",
            "ready_for_embedding",
            "extraction_method",
        ]

        stats = self.batch_insert(
            "content", columns, prepared_data, batch_size, progress_callback
        )

        # Log document-specific stats
        logger.info(
            f"Document batch complete: {stats['inserted']} new chunks, "
            f"avg {total_chars//len(chunk_list)} chars/chunk"
        )

        return {"stats": stats, "chunk_ids": chunk_ids}

    # Intelligence Schema Methods (Task 2.2)
    def create_intelligence_tables(self):
        """Create document intelligence tables for unified intelligence modules."""
        try:
            # Read SQL schema from file
            schema_path = Path(__file__).parent / "intelligence_schema.sql"
            if schema_path.exists():
                with open(schema_path) as f:
                    schema_sql = f.read()

                # Execute each statement separately (SQLite limitation)
                statements = [stmt.strip() for stmt in schema_sql.split(";") if stmt.strip()]
                for statement in statements:
                    if statement:
                        self.execute(statement + ";")

                logger.info("Intelligence tables created successfully")
                return {
                    "success": True,
                    "tables_created": [
                        "document_summaries",
                        "document_intelligence",
                        "relationship_cache",
                    ],
                }
            else:
                # Fallback: inline schema if file not found
                self._create_inline_intelligence_schema()
                return {
                    "success": True,
                    "tables_created": [
                        "document_summaries",
                        "document_intelligence",
                        "relationship_cache",
                    ],
                }
        except Exception as e:
            logger.error(f"Failed to create intelligence tables: {e}")
            return {"success": False, "error": str(e)}

    def _create_inline_intelligence_schema(self) -> None:
        """Create intelligence tables with inline SQL (fallback method)."""
        # Document summaries table
        self.execute(
            """
            CREATE TABLE IF NOT EXISTS document_summaries (
                summary_id TEXT PRIMARY KEY DEFAULT (lower(hex(randomblob(16)))),
                document_id TEXT NOT NULL,
                summary_type TEXT NOT NULL CHECK(summary_type IN ('tfidf', 'textrank', 'combined')),
                summary_text TEXT,
                tf_idf_keywords TEXT,
                textrank_sentences TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (document_id) REFERENCES content_unified(id) ON DELETE CASCADE
            )
        """
        )

        # Document intelligence table
        self.execute(
            """
            CREATE TABLE IF NOT EXISTS document_intelligence (
                intelligence_id TEXT PRIMARY KEY DEFAULT (lower(hex(randomblob(16)))),
                document_id TEXT NOT NULL,
                intelligence_type TEXT NOT NULL,
                intelligence_data TEXT NOT NULL,
                confidence_score REAL DEFAULT 0.0 CHECK(confidence_score >= 0.0 AND confidence_score <= 1.0),
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (document_id) REFERENCES content_unified(id) ON DELETE CASCADE
            )
        """
        )

        # Relationship cache table
        self.execute(
            """
            CREATE TABLE IF NOT EXISTS relationship_cache (
                cache_id TEXT PRIMARY KEY DEFAULT (lower(hex(randomblob(16)))),
                source_id TEXT NOT NULL,
                target_id TEXT NOT NULL,
                relationship_type TEXT NOT NULL,
                strength REAL DEFAULT 0.0 CHECK(strength >= 0.0 AND strength <= 1.0),
                cached_data TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                expires_at TEXT,
                FOREIGN KEY (source_id) REFERENCES content_unified(id) ON DELETE CASCADE,
                FOREIGN KEY (target_id) REFERENCES content_unified(id) ON DELETE CASCADE,
                UNIQUE(source_id, target_id, relationship_type)
            )
        """
        )

        # Create indexes
        index_statements = [
            "CREATE INDEX IF NOT EXISTS idx_summaries_document ON document_summaries(document_id)",
            "CREATE INDEX IF NOT EXISTS idx_summaries_type ON document_summaries(summary_type)",
            "CREATE INDEX IF NOT EXISTS idx_intelligence_document ON document_intelligence(document_id)",
            "CREATE INDEX IF NOT EXISTS idx_intelligence_type ON document_intelligence(intelligence_type)",
            "CREATE INDEX IF NOT EXISTS idx_cache_source ON relationship_cache(source_id)",
            "CREATE INDEX IF NOT EXISTS idx_cache_target ON relationship_cache(target_id)",
            "CREATE INDEX IF NOT EXISTS idx_cache_type ON relationship_cache(relationship_type)",
        ]

        for idx in index_statements:
            self.execute(idx)

        # Thread tracking table for Gmail thread processing
        self.execute(
            """
            CREATE TABLE IF NOT EXISTS thread_tracking (
                thread_id TEXT PRIMARY KEY,
                message_count INTEGER NOT NULL DEFAULT 0,
                status TEXT NOT NULL DEFAULT 'pending' CHECK(status IN ('pending', 'processed', 'failed')),
                last_updated TEXT DEFAULT CURRENT_TIMESTAMP
            )
            """
        )

    def migrate_schema(self):
        """Migrate database schema to latest version."""
        try:
            # Get current schema version
            current_version = self.get_schema_version()

            # Version 1: Add intelligence tables
            if current_version < 1:
                result = self.create_intelligence_tables()
                if result["success"]:
                    self._set_schema_version(1)
                    logger.info("Migrated to schema version 1")

            return {"success": True, "current_version": self.get_schema_version()}
        except Exception as e:
            logger.error(f"Schema migration failed: {e}")
            return {"success": False, "error": str(e)}

    def get_schema_version(self) -> int:
        """Get current database schema version."""
        try:
            # Create version table if it doesn't exist
            self.execute(
                """
                CREATE TABLE IF NOT EXISTS schema_version (
                    version INTEGER PRIMARY KEY,
                    migrated_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            """
            )

            result = self.fetch_one("SELECT MAX(version) as version FROM schema_version")
            return result["version"] if result and result["version"] else 0
        except Exception as e:
            logger.warning(f"Could not get schema version: {e}")
            return 0

    def _set_schema_version(self, version: int) -> None:
        """Set database schema version."""
        self.execute("INSERT INTO schema_version (version) VALUES (?)", (version,))

    # CRUD Operations for Intelligence Tables (Task 2.3)

    # Document Summaries Operations
    def add_document_summary(
        self,
        document_id: str,
        summary_type: str,
        summary_text: str = None,
        tf_idf_keywords: dict = None,
        textrank_sentences: list = None,
    ) -> str:
        """Add a document summary."""
        summary_id = str(uuid.uuid4())
        keywords_json = json.dumps(tf_idf_keywords) if tf_idf_keywords else None
        sentences_json = json.dumps(textrank_sentences) if textrank_sentences else None

        self.execute(
            """
            INSERT INTO document_summaries
            (summary_id, document_id, summary_type, summary_text, tf_idf_keywords, textrank_sentences)
            VALUES (?, ?, ?, ?, ?, ?)
        """,
            (summary_id, document_id, summary_type, summary_text, keywords_json, sentences_json),
        )

        return summary_id

    def get_document_summaries(self, document_id: str) -> list[dict]:
        """Get all summaries for a document."""
        results = self.fetch(
            """
            SELECT * FROM document_summaries
            WHERE document_id = ?
            ORDER BY created_at DESC
        """,
            (document_id,),
        )

        # Parse JSON fields
        for result in results:
            if result.get("tf_idf_keywords"):
                try:
                    result["tf_idf_keywords"] = json.loads(result["tf_idf_keywords"])
                except json.JSONDecodeError:
                    pass
            if result.get("textrank_sentences"):
                try:
                    result["textrank_sentences"] = json.loads(result["textrank_sentences"])
                except json.JSONDecodeError:
                    pass

        return results

    # Document Intelligence Operations
    def add_document_intelligence(
        self,
        document_id: str,
        intelligence_type: str,
        intelligence_data: dict,
        confidence_score: float = 0.0,
    ) -> str:
        """Add document intelligence data."""
        intelligence_id = str(uuid.uuid4())
        data_json = json.dumps(intelligence_data)

        self.execute(
            """
            INSERT INTO document_intelligence
            (intelligence_id, document_id, intelligence_type, intelligence_data, confidence_score)
            VALUES (?, ?, ?, ?, ?)
        """,
            (intelligence_id, document_id, intelligence_type, data_json, confidence_score),
        )

        return intelligence_id

    def get_document_intelligence(
        self, document_id: str, intelligence_type: str = None
    ) -> list[dict]:
        """Get intelligence data for a document."""
        if intelligence_type:
            query = """
                SELECT * FROM document_intelligence
                WHERE document_id = ? AND intelligence_type = ?
                ORDER BY created_at DESC
            """
            params = (document_id, intelligence_type)
        else:
            query = """
                SELECT * FROM document_intelligence
                WHERE document_id = ?
                ORDER BY created_at DESC
            """
            params = (document_id,)

        results = self.fetch(query, params)

        # Parse JSON fields
        for result in results:
            if result.get("intelligence_data"):
                try:
                    result["intelligence_data"] = json.loads(result["intelligence_data"])
                except json.JSONDecodeError:
                    pass

        return results

    def get_document_summary(self, summary_id: str) -> dict | None:
        """Get a single document summary by summary ID."""
        result = self.fetch_one(
            "SELECT * FROM document_summaries WHERE summary_id = ?",
            (summary_id,)
        )
        
        if result and result.get("tf_idf_keywords"):
            try:
                result["tf_idf_keywords"] = json.loads(result["tf_idf_keywords"])
            except json.JSONDecodeError:
                pass
        if result and result.get("textrank_sentences"):
            try:
                result["textrank_sentences"] = json.loads(result["textrank_sentences"])
            except json.JSONDecodeError:
                pass
                
        return result

    def get_summaries_for_document(self, document_id: str) -> list[dict]:
        """Get all summaries for a document (alias for get_document_summaries)."""
        return self.get_document_summaries(document_id)

    def get_intelligence_for_document(self, document_id: str, intelligence_type: str = None) -> list[dict]:
        """Get intelligence data for a document (alias for get_document_intelligence)."""
        return self.get_document_intelligence(document_id, intelligence_type)

    def get_intelligence_by_id(self, intelligence_id: str) -> dict | None:
        """Get a single document intelligence record by intelligence ID."""
        result = self.fetch_one(
            "SELECT * FROM document_intelligence WHERE intelligence_id = ?",
            (intelligence_id,)
        )
        
        if result and result.get("intelligence_data"):
            try:
                result["intelligence_data"] = json.loads(result["intelligence_data"])
            except json.JSONDecodeError:
                pass
                
        return result

    # Relationship Cache Operations
    def add_relationship_cache(
        self,
        source_id: str,
        target_id: str,
        relationship_type: str,
        strength: float = 0.0,
        cached_data: dict = None,
        ttl_hours: int = None,
    ) -> str:
        """Add or update a cached relationship."""
        cache_id = str(uuid.uuid4())
        data_json = json.dumps(cached_data) if cached_data else None
        expires_at = None

        if ttl_hours:
            expires_at = f"datetime('now', '+{ttl_hours} hours')"

        # Use INSERT OR REPLACE to handle unique constraint
        self.execute(
            """
            INSERT OR REPLACE INTO relationship_cache
            (cache_id, source_id, target_id, relationship_type, strength, cached_data, expires_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
            (cache_id, source_id, target_id, relationship_type, strength, data_json, expires_at),
        )

        return cache_id

    def get_relationship_cache(
        self, source_id: str = None, target_id: str = None, relationship_type: str = None
    ) -> list[dict]:
        """Get cached relationships with flexible filtering."""
        conditions = []
        params = []

        if source_id:
            conditions.append("source_id = ?")
            params.append(source_id)
        if target_id:
            conditions.append("target_id = ?")
            params.append(target_id)
        if relationship_type:
            conditions.append("relationship_type = ?")
            params.append(relationship_type)

        # Filter out expired entries
        conditions.append("(expires_at IS NULL OR expires_at > datetime('now'))")

        where_clause = " AND ".join(conditions) if conditions else "1=1"

        results = self.fetch(
            f"""
            SELECT * FROM relationship_cache
            WHERE {where_clause}
            ORDER BY strength DESC, created_at DESC
        """,
            tuple(params),
        )

        # Parse JSON fields
        for result in results:
            if result.get("cached_data"):
                try:
                    result["cached_data"] = json.loads(result["cached_data"])
                except json.JSONDecodeError:
                    pass

        return results

    def clean_expired_cache(self) -> int:
        """Remove expired cache entries."""
        cursor = self.execute(
            """
            DELETE FROM relationship_cache
            WHERE expires_at IS NOT NULL AND expires_at < datetime('now')
        """
        )
        return cursor.rowcount

    # Enhanced Database Caching Methods
    def cache_computation_result(
        self,
        cache_key: str,
        result_data: dict,
        ttl_hours: int = 24,
        cache_type: str = "computation",
    ) -> str:
        """
        Cache expensive computation results with TTL.

        Args:
            cache_key: Unique key for the cached result
            result_data: The computation result to cache
            ttl_hours: Time-to-live in hours (default: 24)
            cache_type: Type of cache entry (default: computation)

        Returns:
            Cache ID
        """
        # Use source_id as cache_key, target_id as cache_type
        return self.add_relationship_cache(
            source_id=cache_key,
            target_id=cache_type,
            relationship_type="cached_result",
            strength=1.0,
            cached_data=result_data,
            ttl_hours=ttl_hours,
        )

    def get_cached_result(self, cache_key: str, cache_type: str = "computation") -> dict | None:
        """
        Get cached computation result.

        Args:
            cache_key: Cache key to look up
            cache_type: Type of cache entry

        Returns:
            Cached data or None if not found/expired
        """
        results = self.get_relationship_cache(
            source_id=cache_key, target_id=cache_type, relationship_type="cached_result"
        )

        if results:
            return results[0].get("cached_data")
        return None

    def cache_document_similarity(
        self,
        doc1_id: str,
        doc2_id: str,
        similarity_score: float,
        similarity_method: str = "cosine",
        metadata: dict = None,
        ttl_hours: int = 168,  # 1 week default
    ) -> str:
        """
        Cache document similarity calculation.

        Args:
            doc1_id: First document ID
            doc2_id: Second document ID
            similarity_score: Computed similarity score
            similarity_method: Method used (cosine, jaccard, etc.)
            metadata: Additional metadata about the calculation
            ttl_hours: Time-to-live in hours (default: 1 week)

        Returns:
            Cache ID
        """
        cache_data = {
            "similarity_score": similarity_score,
            "method": similarity_method,
            "computed_at": time.time(),
            "metadata": metadata or {},
        }

        return self.add_relationship_cache(
            source_id=doc1_id,
            target_id=doc2_id,
            relationship_type="similarity",
            strength=similarity_score,
            cached_data=cache_data,
            ttl_hours=ttl_hours,
        )

    def get_cached_similarity(self, doc1_id: str, doc2_id: str) -> float | None:
        """
        Get cached similarity score between two documents.

        Args:
            doc1_id: First document ID
            doc2_id: Second document ID

        Returns:
            Similarity score or None if not cached/expired
        """
        # Try both directions since similarity is symmetric
        for source, target in [(doc1_id, doc2_id), (doc2_id, doc1_id)]:
            results = self.get_relationship_cache(
                source_id=source, target_id=target, relationship_type="similarity"
            )
            if results:
                cached_data = results[0].get("cached_data", {})
                return cached_data.get("similarity_score")

        return None

    def cache_entity_extraction(
        self,
        content_id: str,
        entities: list[dict],
        extractor_version: str = "default",
        ttl_hours: int = 72,  # 3 days default
    ) -> str:
        """
        Cache entity extraction results.

        Args:
            content_id: Content ID that entities were extracted from
            entities: List of extracted entities
            extractor_version: Version of the extractor used
            ttl_hours: Time-to-live in hours (default: 3 days)

        Returns:
            Cache ID
        """
        cache_data = {
            "entities": entities,
            "extractor_version": extractor_version,
            "extracted_at": time.time(),
            "entity_count": len(entities),
        }

        return self.add_relationship_cache(
            source_id=content_id,
            target_id="entity_extraction",
            relationship_type="entities",
            strength=min(1.0, len(entities) / 10.0),  # Normalize to 0-1 range
            cached_data=cache_data,
            ttl_hours=ttl_hours,
        )

    def get_cached_entities(self, content_id: str) -> list[dict] | None:
        """
        Get cached entity extraction results.

        Args:
            content_id: Content ID to get entities for

        Returns:
            List of entities or None if not cached/expired
        """
        results = self.get_relationship_cache(
            source_id=content_id, target_id="entity_extraction", relationship_type="entities"
        )

        if results:
            cached_data = results[0].get("cached_data", {})
            return cached_data.get("entities")
        return None

    def cache_search_results(
        self,
        query: str,
        results: list[dict],
        search_params: dict = None,
        ttl_hours: int = 1,  # Short TTL for search results
    ) -> str:
        """
        Cache search results for faster repeated queries.

        Args:
            query: Search query string
            results: Search results to cache
            search_params: Additional search parameters (filters, etc.)
            ttl_hours: Time-to-live in hours (default: 1 hour)

        Returns:
            Cache ID
        """
        import hashlib

        # Create cache key from query and params
        cache_key_data = {"query": query, "params": search_params or {}}
        cache_key = hashlib.sha256(json.dumps(cache_key_data, sort_keys=True).encode()).hexdigest()

        cache_data = {
            "query": query,
            "results": results,
            "search_params": search_params,
            "result_count": len(results),
            "cached_at": time.time(),
        }

        return self.add_relationship_cache(
            source_id=cache_key,
            target_id="search_results",
            relationship_type="search",
            strength=min(1.0, len(results) / 10.0),  # Normalize to 0-1 range
            cached_data=cache_data,
            ttl_hours=ttl_hours,
        )

    def get_cached_search_results(
        self, query: str, search_params: dict = None
    ) -> list[dict] | None:
        """
        Get cached search results.

        Args:
            query: Search query string
            search_params: Search parameters used

        Returns:
            Cached search results or None if not found/expired
        """
        import hashlib

        # Recreate cache key
        cache_key_data = {"query": query, "params": search_params or {}}
        cache_key = hashlib.sha256(json.dumps(cache_key_data, sort_keys=True).encode()).hexdigest()

        results = self.get_relationship_cache(
            source_id=cache_key, target_id="search_results", relationship_type="search"
        )

        if results:
            cached_data = results[0].get("cached_data", {})
            return cached_data.get("results")
        return None

    def invalidate_cache_for_content(self, content_id: str) -> int:
        """
        Invalidate all cached data related to a specific content ID.

        Args:
            content_id: Content ID to invalidate cache for

        Returns:
            Number of cache entries removed
        """
        cursor = self.execute(
            """
            DELETE FROM relationship_cache
            WHERE source_id = ? OR target_id = ?
            """,
            (content_id, content_id),
        )
        return cursor.rowcount

    def get_cache_statistics(self) -> dict[str, any]:
        """
        Get database cache statistics.

        Returns:
            Dictionary with cache statistics
        """
        stats = {}

        # Total cache entries
        total_entries = self.fetch_one("SELECT COUNT(*) as count FROM relationship_cache")
        stats["total_entries"] = total_entries["count"] if total_entries else 0

        # Entries by type
        type_stats = self.fetch(
            """
            SELECT relationship_type, COUNT(*) as count
            FROM relationship_cache
            GROUP BY relationship_type
        """
        )
        stats["entries_by_type"] = {row["relationship_type"]: row["count"] for row in type_stats}

        # Expired entries
        expired_count = self.fetch_one(
            """
            SELECT COUNT(*) as count FROM relationship_cache
            WHERE expires_at IS NOT NULL AND expires_at < datetime('now')
        """
        )
        stats["expired_entries"] = expired_count["count"] if expired_count else 0

        # Cache age distribution
        age_stats = self.fetch_one(
            """
            SELECT
                MIN(created_at) as oldest_entry,
                MAX(created_at) as newest_entry,
                AVG(julianday('now') - julianday(created_at)) as avg_age_days
            FROM relationship_cache
        """
        )
        stats.update(age_stats or {})

        return stats

    def validate_pipeline_directories(self) -> dict[str, bool]:
        """Validate that all pipeline directories exist and are writable."""
        results = {}
        data_dir = Path(self.db_path).parent / "data"
        pipeline_dirs = ["raw", "staged", "processed", "quarantine", "export"]

        for dir_name in pipeline_dirs:
            dir_path = data_dir / dir_name
            try:
                # Check existence
                exists = dir_path.exists()
                # Check if it's a directory
                is_dir = dir_path.is_dir() if exists else False
                # Check writability by trying to create a temp file
                writable = False
                if is_dir:
                    try:
                        test_file = dir_path / f".write_test_{uuid.uuid4().hex[:8]}"
                        test_file.touch()
                        test_file.unlink()
                        writable = True
                    except Exception:
                        writable = False

                results[dir_name] = exists and is_dir and writable
            except Exception as e:
                logger.error(f"Error checking directory {dir_name}: {e}")
                results[dir_name] = False

        return results

    def get_pipeline_stats(self) -> dict[str, int]:
        """Get file counts for each pipeline directory."""
        stats = {}
        data_dir = Path(self.db_path).parent / "data"
        pipeline_dirs = ["raw", "staged", "processed", "quarantine", "export"]

        for dir_name in pipeline_dirs:
            dir_path = data_dir / dir_name
            try:
                if dir_path.exists() and dir_path.is_dir():
                    # Count non-hidden files
                    file_count = len(
                        [
                            f
                            for f in dir_path.iterdir()
                            if f.is_file() and not f.name.startswith(".")
                        ]
                    )
                    stats[dir_name] = file_count
                else:
                    stats[dir_name] = 0
            except Exception as e:
                logger.error(f"Error counting files in {dir_name}: {e}")
                stats[dir_name] = -1

        return stats

    def db_maintenance(self, wal_threshold_mb: int = 64) -> dict:
        """Perform database maintenance: optimize and checkpoint WAL.
        Run this after large batch operations.
        
        Args:
            wal_threshold_mb: Only checkpoint if WAL file exceeds this size (MB)
        """
        try:
            # Check WAL file size if it exists
            wal_path = Path(f"{self.db_path}-wal")
            wal_size_mb = 0
            should_checkpoint = True
            
            if wal_path.exists():
                wal_size_mb = wal_path.stat().st_size / (1024 * 1024)
                should_checkpoint = wal_size_mb > wal_threshold_mb
                logger.debug(f"WAL size: {wal_size_mb:.1f}MB, threshold: {wal_threshold_mb}MB")
            
            with sqlite3.connect(self.db_path) as conn:
                self._configure_connection(conn)
                
                # Always optimize query planner statistics
                conn.execute("PRAGMA optimize")
                
                checkpoint_result = None
                if should_checkpoint:
                    # Checkpoint and truncate WAL file
                    t0 = time.perf_counter()
                    result = conn.execute("PRAGMA wal_checkpoint(TRUNCATE)").fetchone()
                    checkpoint_ms = (time.perf_counter() - t0) * 1000
                    self.metrics.checkpoint_ms += checkpoint_ms
                    
                    checkpoint_result = {
                        "wal_pages_moved": result[0] if result else 0,
                        "wal_pages_total": result[1] if result else 0,
                        "checkpoint_ms": round(checkpoint_ms, 1)
                    }
                    logger.info(f"WAL checkpoint completed in {checkpoint_ms:.1f}ms")
                
                # Get database stats after maintenance
                page_count = conn.execute("PRAGMA page_count").fetchone()[0]
                page_size = conn.execute("PRAGMA page_size").fetchone()[0]
                db_size_mb = (page_count * page_size) / (1024 * 1024)
                
                maintenance_stats = {
                    "success": True,
                    "db_size_mb": round(db_size_mb, 2),
                    "wal_size_mb": round(wal_size_mb, 2),
                    "checkpoint": checkpoint_result,
                    "timestamp": datetime.now().isoformat()
                }
                
                logger.info(f"Database maintenance completed: {maintenance_stats}")
                return maintenance_stats
                
        except Exception as e:
            logger.error(f"Database maintenance failed: {e}")
            return {"success": False, "error": str(e)}

    # Batch operations for intelligence tables
    def batch_add_summaries(self, summaries: list[dict], batch_size: int = 1000) -> dict:
        """Batch add document summaries."""
        if not summaries:
            return {"total": 0, "inserted": 0}

        prepared_data = []
        for summary in summaries:
            summary_id = summary.get("summary_id", str(uuid.uuid4()))
            keywords_json = (
                json.dumps(summary.get("tf_idf_keywords"))
                if summary.get("tf_idf_keywords")
                else None
            )
            sentences_json = (
                json.dumps(summary.get("textrank_sentences"))
                if summary.get("textrank_sentences")
                else None
            )

            prepared_data.append(
                (
                    summary_id,
                    summary["document_id"],
                    summary["summary_type"],
                    summary.get("summary_text"),
                    keywords_json,
                    sentences_json,
                )
            )

        columns = [
            "summary_id",
            "document_id",
            "summary_type",
            "summary_text",
            "tf_idf_keywords",
            "textrank_sentences",
        ]
        return self.batch_insert("document_summaries", columns, prepared_data, batch_size)

    # Vector processing methods
    
    def get_all_content_ids(self, content_type: str = None) -> list[str]:
        """Get all content IDs, optionally filtered by type. Streams in pages of 1000."""
        query = "SELECT id FROM content_unified"
        params = ()
        
        if content_type:
            query += " WHERE source_type = ?"
            params = (content_type,)
        
        query += " ORDER BY id"
        
        cursor = self.execute(query, params)
        return [row[0] for row in cursor.fetchall()]
    
    def get_content_by_ids(self, ids: list[str]) -> list[dict]:
        """Get content by IDs, batching ≤500 to avoid SQLite 999 limit."""
        if not ids:
            return []
        
        results = []
        # Batch to avoid SQLite's 999 variable limit
        batch_size = 500
        
        for i in range(0, len(ids), batch_size):
            batch_ids = ids[i:i + batch_size]
            placeholders = ",".join("?" * len(batch_ids))
            query = f"SELECT * FROM content_unified WHERE id IN ({placeholders})"
            
            cursor = self.execute(query, tuple(batch_ids))
            # Convert sqlite3.Row objects to dictionaries
            batch_results = [dict(row) for row in cursor.fetchall()]
            results.extend(batch_results)
        
        return results
    
    def mark_content_vectorized(self, content_id: str) -> bool:
        """Mark single content as vectorized."""
        try:
            cursor = self.execute(
                "UPDATE content_unified SET ready_for_embedding = 1 WHERE id = ?",
                (content_id,)
            )
            return cursor.rowcount > 0
        except Exception as e:
            logger.error(f"Failed to mark content {content_id} as vectorized: {e}")
            return False
    
    def batch_mark_vectorized(self, content_ids: list[str]) -> int:
        """Batch mark content as vectorized, chunking to ≤500."""
        if not content_ids:
            return 0
        
        total_updated = 0
        batch_size = 500
        
        for i in range(0, len(content_ids), batch_size):
            batch_ids = content_ids[i:i + batch_size]
            placeholders = ",".join("?" * len(batch_ids))
            query = f"UPDATE content_unified SET ready_for_embedding = 1 WHERE id IN ({placeholders})"
            
            try:
                cursor = self.execute(query, tuple(batch_ids))
                total_updated += cursor.rowcount
            except Exception as e:
                logger.error(f"Failed to batch mark vectorized for {len(batch_ids)} items: {e}")
                continue
        
        return total_updated


# That's it. That's the whole database layer.
