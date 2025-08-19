"""
PDF data storage operations
"""

import hashlib
import os
from typing import Any

from shared.simple_db import SimpleDB


class PDFStorage:
    """Handles PDF data storage operations"""

    def __init__(self, db_path: str) -> None:
        self.db_path = db_path
        self.db = SimpleDB(db_path)

    def _get_db(self):
        """Get database instance, recreating if path changed"""
        if hasattr(self, "_last_db_path") and self._last_db_path != self.db_path:
            # Validate the path before creating SimpleDB
            import os

            if (
                not os.path.exists(os.path.dirname(self.db_path))
                and os.path.dirname(self.db_path) != ""
            ):
                raise Exception(f"Directory does not exist: {os.path.dirname(self.db_path)}")
            self.db = SimpleDB(self.db_path)
        self._last_db_path = self.db_path
        return self.db

    def hash_file(self, file_path: str) -> str:
        """Generate SHA256 hash of file for deduplication"""
        hasher = hashlib.sha256()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hasher.update(chunk)
        return hasher.hexdigest()

    def is_duplicate(self, file_hash: str) -> bool:
        """Check if file hash already exists in database"""
        try:
            import sqlite3

            with sqlite3.connect(self._get_db().db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                cursor.execute("SELECT 1 FROM documents WHERE file_hash = ? LIMIT 1", (file_hash,))
                result = cursor.fetchone() is not None
            return result
        except Exception:
            return False

    def store_chunks(
        self, pdf_path: str, file_hash: str, chunks: list[str], source: str
    ) -> dict[str, Any]:
        """Store PDF chunks in database using batch operations"""
        try:
            file_name = os.path.basename(pdf_path)

            # Handle test scenarios where file might not exist
            if os.path.exists(pdf_path):
                file_size = os.path.getsize(pdf_path)
            else:
                # For testing or when file is not accessible
                file_size = sum(len(chunk) for chunk in chunks)

            # Prepare chunk data for batch insert
            chunk_list = []
            for i, chunk in enumerate(chunks):
                chunk_list.append(
                    {
                        "chunk_id": f"{file_hash}_{i}",
                        "file_path": pdf_path,
                        "file_name": file_name,
                        "chunk_index": i,
                        "text_content": chunk,
                        "char_count": len(chunk),
                        "file_size": file_size,
                        "file_hash": file_hash,
                        "source_type": source,
                        "extraction_method": "pdfplumber",
                    }
                )

            # Use SimpleDB's batch_add_document_chunk method
            result = self.db.batch_add_document_chunk(chunk_list, batch_size=100)

            if result["stats"]["inserted"] > 0 or result["stats"]["ignored"] > 0:
                return {
                    "success": True,
                    "chunks_stored": result["stats"]["inserted"],
                    "chunks_ignored": result["stats"]["ignored"],
                    "total": len(chunks),
                }
            else:
                return {"success": False, "error": "No chunks were stored"}

        except Exception as e:
            return {"success": False, "error": f"Database storage failed: {str(e)}"}

    def get_pdf_stats(self) -> dict[str, Any]:
        """Get PDF collection statistics"""
        try:
            import sqlite3

            with sqlite3.connect(self._get_db().db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                stats = self._collect_document_stats(cursor)

            # Calculate derived stats
            avg_chunks = stats["chunk_count"] / stats["doc_count"] if stats["doc_count"] > 0 else 0
            avg_chars = (
                stats["total_chars"] / stats["chunk_count"] if stats["chunk_count"] > 0 else 0
            )
            storage_mb = (stats["total_chars"] * 1.5) / (1024 * 1024)  # Rough storage estimate

            return {
                "success": True,
                "stats": {
                    "total_documents": stats["doc_count"],
                    "total_chunks": stats["chunk_count"],
                    "total_characters": stats["total_chars"],
                    "avg_chunks_per_doc": round(avg_chunks, 1),
                    "avg_chars_per_chunk": round(avg_chars, 1),
                    "storage_mb_estimate": round(storage_mb, 1),
                    "vector_processed": stats["vector_processed"],
                    "vector_pending": stats["chunk_count"] - stats["vector_processed"],
                },
            }

        except Exception as e:
            return {"success": False, "error": f"Stats error: {str(e)}"}

    def _collect_document_stats(self, cursor) -> dict[str, Any]:
        """Collect document statistics from database"""
        # Get unique document count (by file_hash)
        cursor.execute(
            "SELECT COUNT(DISTINCT file_hash) FROM documents WHERE content_type = 'document'"
        )
        doc_count = cursor.fetchone()[0]

        # Get total chunk count
        cursor.execute("SELECT COUNT(*) FROM documents WHERE content_type = 'document'")
        chunk_count = cursor.fetchone()[0]

        # Get total size
        cursor.execute(
            """
            SELECT SUM(char_count)
            FROM documents
            WHERE content_type = 'document'
        """
        )
        total_chars = cursor.fetchone()[0] or 0

        # Get processing stats
        cursor.execute(
            """
            SELECT COUNT(*)
            FROM documents
            WHERE content_type = 'document' AND vector_processed = 1
        """
        )
        vector_processed = cursor.fetchone()[0]

        return {
            "doc_count": doc_count,
            "chunk_count": chunk_count,
            "total_chars": total_chars,
            "vector_processed": vector_processed,
        }

    def find_pdf_files(self, directory: str) -> list[str]:
        """Find all PDF files in directory recursively"""
        pdf_files = []
        for root, dirs, files in os.walk(directory):
            for file in files:
                if file.lower().endswith(".pdf"):
                    pdf_files.append(os.path.join(root, file))
        return sorted(pdf_files)
