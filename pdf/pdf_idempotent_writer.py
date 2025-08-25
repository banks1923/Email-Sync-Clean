"""
Transactional and Idempotent PDF Writer Ensures atomic writes with SHA256
deduplication and proper retry handling.
"""

import hashlib
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

from loguru import logger


class IdempotentPDFWriter:
    """
    Handles transactional, idempotent PDF writes with SHA256 deduplication.
    """
    
    def __init__(self, db_path: str = None):
        """
        Initialize with database path from environment or default.
        """
        from config.settings import DatabaseSettings
        self.db_path = db_path or DatabaseSettings().emails_db_path
        
    def compute_sha256(self, file_path: str) -> str:
        """
        Compute SHA256 hash of file contents.
        """
        sha256_hash = hashlib.sha256()
        with open(file_path, "rb") as f:
            for byte_block in iter(lambda: f.read(65536), b""):
                sha256_hash.update(byte_block)
        return sha256_hash.hexdigest()
    
    def check_existing(self, sha256: str) -> dict[str, Any] | None:
        """
        Check if document with this SHA256 already exists.
        """
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT chunk_id, status, attempt_count, error_message 
            FROM documents 
            WHERE sha256 = ? 
            LIMIT 1
        """, (sha256,))
        
        row = cursor.fetchone()
        conn.close()
        
        if row:
            return dict(row)
        return None
    
    def write_transactional(
        self, 
        file_path: str,
        chunks: list,
        metadata: dict[str, Any]
    ) -> dict[str, Any]:
        """Transactionally write PDF data with rollback on failure.

        Returns:
            {"success": bool, "status": str, "error": str|None, "exit_code": int}
            Exit codes: 0=success, 2=permanent_fail, 3=schema_error, 4=transient_fail
        """
        sha256 = self.compute_sha256(file_path)
        file_name = Path(file_path).name
        
        # Check existing
        existing = self.check_existing(sha256)
        if existing:
            if existing['status'] == 'processed':
                logger.info(f"PDF already processed: {sha256[:8]}...")
                return {
                    "success": True, 
                    "status": "duplicate",
                    "sha256": sha256,
                    "exit_code": 0
                }
            elif existing['status'] == 'failed':
                if existing['attempt_count'] >= 3:
                    logger.warning(f"PDF permanently failed after {existing['attempt_count']} attempts")
                    return {
                        "success": False,
                        "status": "permanent_failure", 
                        "error": existing['error_message'],
                        "exit_code": 2
                    }
                # Otherwise, proceed with retry
                logger.info(f"Retrying failed PDF (attempt {existing['attempt_count'] + 1})")
        
        # Begin transaction
        conn = sqlite3.connect(self.db_path)
        conn.execute("BEGIN IMMEDIATE")  # Lock for write
        
        try:
            cursor = conn.cursor()
            timestamp = datetime.now().isoformat()
            
            # Insert chunks
            for i, chunk in enumerate(chunks):
                chunk_id = f"{sha256}_{i}"
                
                cursor.execute("""
                    INSERT OR REPLACE INTO documents (
                        chunk_id, file_path, file_name, chunk_index,
                        text_content, file_hash, sha256,
                        char_count, word_count, pages,
                        extraction_method, ocr_confidence,
                        status, processed_at, metadata,
                        attempt_count
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    chunk_id, file_path, file_name, i,
                    chunk['text'], chunk.get('file_hash', sha256), sha256,
                    len(chunk['text']), len(chunk['text'].split()),
                    metadata.get('pages', 0),
                    metadata.get('extraction_method', 'unknown'),
                    metadata.get('ocr_confidence', 0.0),
                    'processed', timestamp, str(metadata),
                    0  # Reset attempt count on success
                ))
            
            # Insert into content_unified for search integration
            cursor.execute("""
                INSERT OR REPLACE INTO content_unified (
                    source_type, source_id, title, body, 
                    created_at, ready_for_embedding
                ) VALUES ('pdf', ?, ?, ?, ?, 1)
            """, (
                sha256[:16],  # Use first 16 chars of SHA as source_id
                file_name,
                ' '.join([c['text'][:500] for c in chunks[:3]]),  # First 500 chars from first 3 chunks
                timestamp
            ))
            
            # Commit transaction
            conn.commit()
            logger.success(f"Transactional write successful for {file_name} ({len(chunks)} chunks)")
            
            return {
                "success": True,
                "status": "processed",
                "sha256": sha256,
                "chunks_written": len(chunks),
                "exit_code": 0
            }
            
        except sqlite3.IntegrityError as e:
            conn.rollback()
            logger.error(f"Integrity error: {e}")
            self._mark_failed(sha256, str(e), is_permanent=True)
            return {
                "success": False,
                "status": "integrity_error",
                "error": str(e),
                "exit_code": 2  # Permanent failure
            }
            
        except sqlite3.OperationalError as e:
            conn.rollback()
            if "no such table" in str(e) or "no column" in str(e):
                logger.error(f"Schema error: {e}")
                return {
                    "success": False,
                    "status": "schema_error",
                    "error": str(e),
                    "exit_code": 3  # Schema mismatch
                }
            else:
                logger.error(f"Database locked or busy: {e}")
                self._mark_failed(sha256, str(e), is_permanent=False)
                return {
                    "success": False,
                    "status": "transient_error",
                    "error": str(e),
                    "exit_code": 4  # Transient failure
                }
                
        except Exception as e:
            conn.rollback()
            logger.error(f"Unexpected error: {e}")
            self._mark_failed(sha256, str(e), is_permanent=False)
            return {
                "success": False,
                "status": "unknown_error",
                "error": str(e),
                "exit_code": 4  # Treat as transient
            }
        finally:
            conn.close()
    
    def _mark_failed(self, sha256: str, error: str, is_permanent: bool = False):
        """
        Mark a document as failed with retry information.
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Get current attempt count
        cursor.execute("SELECT attempt_count FROM documents WHERE sha256 = ?", (sha256,))
        row = cursor.fetchone()
        attempt_count = (row[0] if row else 0) + 1
        
        # Calculate next retry time (exponential backoff)
        if is_permanent or attempt_count >= 3:
            next_retry = None  # No more retries
        else:
            backoff_minutes = 2 ** attempt_count  # 2, 4, 8 minutes
            next_retry = (datetime.now() + timedelta(minutes=backoff_minutes)).isoformat()
        
        cursor.execute("""
            UPDATE documents 
            SET status = 'failed',
                error_message = ?,
                attempt_count = ?,
                next_retry_at = ?
            WHERE sha256 = ?
        """, (error, attempt_count, next_retry, sha256))
        
        conn.commit()
        conn.close()
        
        logger.warning(f"Marked as failed: {sha256[:8]}... (attempt {attempt_count})")


# Integration helper for PDFService
def make_pdf_write_idempotent(pdf_service_instance):
    """Monkey-patch or wrap PDFService to use idempotent writer.

    Usage in PDFService.__init__:     from pdf.pdf_idempotent_writer
    import make_pdf_write_idempotent     make_pdf_write_idempotent(self)
    """
    writer = IdempotentPDFWriter()
    
    # Store original method
    original_process = pdf_service_instance._process_pdf_internal
    
    def wrapped_process(pdf_path: str, file_hash: str, source: str) -> dict[str, Any]:
        """
        Wrapped version with idempotent writes.
        """
        # First, do the extraction
        result = original_process(pdf_path, file_hash, source)
        
        if result.get("success") and result.get("chunks"):
            # Replace storage with idempotent writer
            write_result = writer.write_transactional(
                pdf_path,
                result["chunks"],
                {
                    "extraction_method": result.get("extraction_method"),
                    "ocr_confidence": result.get("ocr_confidence", 0),
                    "pages": result.get("pages", 0),
                    "source": source
                }
            )
            
            # Merge results
            result.update(write_result)
            result["chunks_processed"] = write_result.get("chunks_written", 0)
        
        return result
    
    # Replace method
    pdf_service_instance._process_pdf_internal = wrapped_process
    logger.info("PDFService enhanced with idempotent writer")