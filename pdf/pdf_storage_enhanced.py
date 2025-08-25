"""
Enhanced PDF storage with legal metadata support Stores OCR confidence and
legal metadata alongside document chunks.
"""

import hashlib
import json
import os
from typing import Any

from shared.simple_db import SimpleDB


class EnhancedPDFStorage:
    """
    Enhanced PDF storage with metadata support.
    """

    def __init__(self, db_path: str) -> None:
        self.db_path = db_path
        self.db = SimpleDB(db_path)

    def _get_db(self):
        """
        Get database instance, recreating if path changed.
        """
        if hasattr(self, "_last_db_path") and self._last_db_path != self.db_path:
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
        """
        Generate SHA256 hash of file for deduplication.
        """
        hasher = hashlib.sha256()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hasher.update(chunk)
        return hasher.hexdigest()

    def is_duplicate(self, file_hash: str) -> bool:
        """
        Check if file hash already exists in database.
        """
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

    def store_chunks_with_metadata(
        self,
        pdf_path: str,
        file_hash: str,
        chunks: list[dict],
        extraction_method: str = None,
        ocr_confidence: float = None,
        legal_metadata: dict = None,
        source: str = "upload",
    ) -> dict[str, Any]:
        """
        Store PDF chunks with OCR and legal metadata.
        """
        try:
            file_name = os.path.basename(pdf_path)
            file_size = os.path.getsize(pdf_path)
            modified_time = os.path.getmtime(pdf_path)

            import sqlite3

            with sqlite3.connect(self._get_db().db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()

                for chunk in chunks:
                    # Extract chunk data
                    chunk_id = chunk.get("chunk_id")
                    text = chunk.get("text", "")
                    chunk_index = chunk.get("chunk_index", 0)

                    # Prepare legal metadata JSON
                    metadata_json = None
                    if legal_metadata or chunk.get("legal_metadata"):
                        # Prefer chunk-level metadata, fall back to file-level
                        meta = chunk.get("legal_metadata")
                        if isinstance(meta, str):
                            metadata_json = meta
                        elif meta:
                            metadata_json = json.dumps(meta)
                        elif legal_metadata:
                            metadata_json = json.dumps(legal_metadata)

                    cursor.execute(
                        """
                        INSERT OR REPLACE INTO documents (
                            chunk_id, file_path, file_name, chunk_index, text_content,
                            char_count, file_size, file_hash, source_type, modified_time,
                            processed_time, content_type, ready_for_embedding,
                            legal_metadata, extraction_method, ocr_confidence
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, datetime('now'),
                                  'document', 0, ?, ?, ?)
                    """,
                        (
                            chunk_id,
                            pdf_path,
                            file_name,
                            chunk_index,
                            text,
                            len(text),
                            file_size,
                            file_hash,
                            source,
                            modified_time,
                            metadata_json,
                            extraction_method or chunk.get("extraction_method"),
                            ocr_confidence or chunk.get("ocr_confidence"),
                        ),
                    )

                conn.commit()

                # Also add to content_unified table for unified access
                # Combine all chunks for the full document text
                full_text = " ".join([chunk.get("text", "") for chunk in chunks])
                content_id = self.db.upsert_content(
                    source_type="pdf",
                    external_id=file_hash,  # Use file hash as unique external ID
                    content_type="pdf",  # Required by method signature
                    title=file_name,
                    content=full_text,
                    metadata={
                        "source_path": pdf_path,
                        "extraction_method": extraction_method,
                        "ocr_confidence": ocr_confidence,
                        "legal_metadata": legal_metadata,
                        "chunk_count": len(chunks),
                    },
                )

            return {"success": True, "chunks_stored": len(chunks), "content_id": content_id}

        except Exception as e:
            return {"success": False, "error": f"Database storage failed: {str(e)}"}

    def get_enhanced_pdf_stats(self) -> dict[str, Any]:
        """
        Get enhanced PDF statistics including OCR and legal metadata.
        """
        try:
            import sqlite3

            with sqlite3.connect(self._get_db().db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()

                # Basic stats
                stats = self._collect_document_stats(cursor)

                # OCR stats
                cursor.execute(
                    """
                    SELECT extraction_method, COUNT(*)
                    FROM documents
                    WHERE content_type = 'document'
                    GROUP BY extraction_method
                """
                )
                extraction_methods = dict(cursor.fetchall())

                # Legal metadata stats
                cursor.execute(
                    """
                    SELECT COUNT(*)
                    FROM documents
                    WHERE content_type = 'document'
                    AND legal_metadata IS NOT NULL
                """
                )
                has_legal_metadata = cursor.fetchone()[0]

            # Calculate derived stats
            avg_chunks = stats["chunk_count"] / stats["doc_count"] if stats["doc_count"] > 0 else 0
            avg_chars = (
                stats["total_chars"] / stats["chunk_count"] if stats["chunk_count"] > 0 else 0
            )
            storage_mb = (stats["total_chars"] * 1.5) / (1024 * 1024)

            return {
                "success": True,
                "stats": {
                    "total_documents": stats["doc_count"],
                    "total_chunks": stats["chunk_count"],
                    "total_characters": stats["total_chars"],
                    "avg_chunks_per_doc": round(avg_chunks, 1),
                    "avg_chars_per_chunk": round(avg_chars, 1),
                    "storage_mb_estimate": round(storage_mb, 1),
                    "ready_for_embedding": stats["ready_for_embedding"],
                    "vector_pending": stats["chunk_count"] - stats["ready_for_embedding"],
                    "extraction_methods": extraction_methods,
                    "documents_with_legal_metadata": has_legal_metadata,
                    "ocr_processed": extraction_methods.get("ocr", 0),
                    "text_extracted": extraction_methods.get("text_extraction", 0),
                },
            }

        except Exception as e:
            return {"success": False, "error": f"Stats error: {str(e)}"}

    def _collect_document_stats(self, cursor) -> dict[str, Any]:
        """
        Collect document statistics from database.
        """
        cursor.execute(
            "SELECT COUNT(DISTINCT file_hash) FROM documents WHERE content_type = 'document'"
        )
        doc_count = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM documents WHERE content_type = 'document'")
        chunk_count = cursor.fetchone()[0]

        cursor.execute("SELECT SUM(char_count) FROM documents WHERE content_type = 'document'")
        total_chars = cursor.fetchone()[0] or 0

        cursor.execute(
            "SELECT COUNT(*) FROM documents WHERE content_type = 'document' AND ready_for_embedding = 1"
        )
        ready_for_embedding = cursor.fetchone()[0]

        return {
            "doc_count": doc_count,
            "chunk_count": chunk_count,
            "total_chars": total_chars,
            "ready_for_embedding": ready_for_embedding,
        }

    # Legacy compatibility
    def store_chunks(
        self, pdf_path: str, file_hash: str, chunks: list[str], source: str
    ) -> dict[str, Any]:
        """Legacy method - convert simple chunks to enhanced format"""
        enhanced_chunks = []
        for i, text in enumerate(chunks):
            enhanced_chunks.append(
                {
                    "chunk_id": f"{file_hash}_{i}",
                    "text": text,
                    "chunk_index": i,
                    "char_count": len(text),
                }
            )
        return self.store_chunks_with_metadata(
            pdf_path, file_hash, enhanced_chunks, extraction_method="text_extraction", source=source
        )

    def find_pdf_files(self, directory: str) -> list[str]:
        """
        Find all PDF files in directory recursively.
        """
        pdf_files = []
        for root, dirs, files in os.walk(directory):
            for file in files:
                if file.lower().endswith(".pdf"):
                    pdf_files.append(os.path.join(root, file))
        return sorted(pdf_files)
