#!/usr/bin/env python3
"""
Simple Upload Processor - Direct file processing without pipeline complexity.

Replaces DataPipelineOrchestrator.add_to_raw() with direct SimpleDB processing.
Follows CLAUDE.md principles: Simple > Complex, Working > Perfect.
"""

import hashlib
import shutil
from datetime import datetime
from pathlib import Path
from typing import Any

from loguru import logger

from shared.db.simple_db import SimpleDB


class SimpleUploadProcessor:
    """Direct file upload processing.

    No pipeline directories, no state management.
    """

    def __init__(self, quarantine_dir: str = "data/system_data/quarantine"):
        self.quarantine_dir = Path(quarantine_dir)
        self.quarantine_dir.mkdir(parents=True, exist_ok=True)
        self.db = SimpleDB()

    def process_file(self, file_path: Path, source: str = "upload") -> dict[str, Any]:
        """Process file directly to database. No intermediate directories.

        Args:
            file_path: Path to file to process
            source: Source type (upload, pdf, email, etc.)

        Returns:
            Processing result with content_id or error info
        """
        if not file_path.exists():
            return {"success": False, "error": f"File not found: {file_path}"}

        try:
            # Extract content based on file type
            content = self._extract_content(file_path)

            # Validate extracted content
            if not content or len(content.strip()) < 20:
                # If still no content, log warning but continue
                if not content:
                    content = ""  # Ensure it's at least an empty string
                    logger.warning(
                        f"No content extracted from {file_path.name}, storing with empty body"
                    )

            # Generate file hash for deduplication
            file_hash = self._get_file_hash(file_path)

            # Store directly in database (even if content is empty - for tracking)
            content_id = self.db.add_content(
                content_type=source,
                title=file_path.name,
                content=content,
                metadata={
                    "original_path": str(file_path),
                    "file_hash": file_hash,
                    "file_size": file_path.stat().st_size,
                    "source": source,
                    "processed_at": datetime.now().isoformat(),
                    "content_length": len(content),
                    "extraction_status": "success" if content else "empty",
                },
            )

            logger.info(
                f"Processed {file_path.name} -> content_id: {content_id} ({len(content)} chars)"
            )

            # Generate summary for meaningful content
            summary_generated = False
            if content and len(content) > 100:  # Only summarize substantial content
                try:
                    from summarization import get_document_summarizer
                    summarizer = get_document_summarizer()
                    summary = summarizer.extract_summary(
                        content,
                        max_sentences=3,
                        max_keywords=10,
                        summary_type="combined"
                    )
                    
                    if summary and summary.get("summary_text"):
                        self.db.add_document_summary(
                            document_id=str(content_id),
                            summary_type="combined",
                            summary_text=summary.get("summary_text"),
                            tf_idf_keywords=summary.get("tf_idf_keywords"),
                            textrank_sentences=summary.get("textrank_sentences")
                        )
                        summary_generated = True
                        logger.info(f"Generated summary for {file_path.name}")
                except Exception as e:
                    logger.warning(f"Could not generate summary for {file_path.name}: {e}")

            return {
                "success": True,
                "content_id": content_id,
                "file_hash": file_hash,
                "content_length": len(content),
                "summary_generated": summary_generated,
                "message": f"File processed: {file_path.name} ({len(content)} chars extracted)",
            }

        except Exception as e:
            logger.error(f"Failed to process {file_path.name}: {e}")
            quarantine_path = self._quarantine_file(file_path, str(e))

            return {
                "success": False,
                "error": str(e),
                "quarantine_path": str(quarantine_path),
                "message": f"File quarantined due to error: {e}",
            }

    def process_directory(self, dir_path: Path, limit: int = None) -> dict[str, Any]:
        """
        Process all supported files in a directory.
        """
        if not dir_path.exists() or not dir_path.is_dir():
            return {"success": False, "error": f"Directory not found: {dir_path}"}

        supported_extensions = {".pdf", ".txt", ".md", ".docx"}
        files = [
            f
            for f in dir_path.iterdir()
            if f.is_file() and f.suffix.lower() in supported_extensions
        ]

        if limit:
            files = files[:limit]

        results = {
            "total_files": len(files),
            "success_count": 0,
            "failed_count": 0,
            "processed_files": [],
            "failed_files": [],
        }

        for file_path in files:
            result = self.process_file(file_path)

            if result["success"]:
                results["success_count"] += 1
                results["processed_files"].append(
                    {"file": file_path.name, "content_id": result["content_id"]}
                )
            else:
                results["failed_count"] += 1
                results["failed_files"].append({"file": file_path.name, "error": result["error"]})

        logger.info(
            f"Directory processing complete: {results['success_count']}/{results['total_files']} successful"
        )
        results["success"] = results["failed_count"] == 0

        return results

    def process_directory_recursive(
        self, dir_path: Path, extensions: list[str] = None
    ) -> dict[str, Any]:
        """
        Process all supported files in a directory recursively.
        """
        if not dir_path.exists() or not dir_path.is_dir():
            return {"success": False, "error": f"Directory not found: {dir_path}"}

        if extensions is None:
            extensions = [".pdf", ".txt", ".md", ".docx"]

        # Collect all files recursively
        files = []
        for ext in extensions:
            files.extend(dir_path.rglob(f"*{ext}"))

        results = {
            "total_files": len(files),
            "success_count": 0,
            "failed_count": 0,
            "processed_files": [],
            "failed_files": [],
        }

        for file_path in files:
            result = self.process_file(file_path, source="document")

            if result["success"]:
                results["success_count"] += 1
                results["processed_files"].append(
                    {
                        "file": file_path.name,
                        "path": str(file_path),
                        "content_id": result["content_id"],
                    }
                )
            else:
                results["failed_count"] += 1
                results["failed_files"].append(
                    {"file": file_path.name, "path": str(file_path), "error": result["error"]}
                )

        logger.info(
            f"Recursive directory processing complete: {results['success_count']}/{results['total_files']} successful"
        )
        results["success"] = results["failed_count"] == 0

        return results

    def _extract_content(self, file_path: Path) -> str:
        """
        Extract text content from file based on extension.
        """
        suffix = file_path.suffix.lower()

        if suffix == ".txt" or suffix == ".md":
            return file_path.read_text(encoding="utf-8")
        elif suffix == ".pdf":
            # Use OCR-enabled PDF service for extraction
            try:
                from pdf.wiring import build_pdf_service

                service = build_pdf_service()

                # First try the OCR coordinator directly
                result = service.ocr.process_pdf_with_ocr(str(file_path))

                if result.get("success") and result.get("text"):
                    extracted_text = result.get("text", "").strip()
                    if extracted_text and len(extracted_text) > 20:
                        logger.info(
                            f"PDF extraction successful: {file_path.name} ({len(extracted_text)} chars)"
                        )
                        return extracted_text

                # If OCR failed or returned empty, try direct text extraction
                logger.warning(
                    f"OCR extraction failed for {file_path.name}, trying direct text extraction"
                )

                # Try using pypdf directly for text-based PDFs
                try:
                    import pypdf

                    with open(file_path, "rb") as pdf_file:
                        pdf_reader = pypdf.PdfReader(pdf_file)
                        text_parts = []
                        for page_num in range(len(pdf_reader.pages)):
                            page = pdf_reader.pages[page_num]
                            page_text = page.extract_text()
                            if page_text:
                                text_parts.append(page_text)

                        combined_text = "\n".join(text_parts).strip()
                        if combined_text and len(combined_text) > 20:
                            logger.info(
                                f"Direct PDF text extraction successful: {file_path.name} ({len(combined_text)} chars)"
                            )
                            return combined_text
                except Exception as pypdf_error:
                    logger.warning(f"pypdf extraction also failed: {pypdf_error}")

                # If text extraction failed, the PDF likely needs OCR
                logger.error(f"PDF text extraction failed for {file_path.name}. Document may be scanned and needs external OCR.")

                # Store empty string instead of placeholder - this will be caught by validation
                return ""

            except ImportError as e:
                logger.error(f"Failed to import PDF service: {e}")
                return ""
            except Exception as e:
                logger.error(f"Unexpected error extracting PDF {file_path.name}: {e}")
                return ""
        elif suffix == ".docx":
            # Simple docx extraction (could be enhanced)
            try:
                import docx

                doc = docx.Document(file_path)
                return "\n".join([para.text for para in doc.paragraphs])
            except ImportError:
                logger.warning("python-docx not available, treating as binary")
                return f"[Binary DOCX file: {file_path.name}]"
        else:
            # Fallback for unsupported types
            return f"[Unsupported file type: {suffix}]"

    def _get_file_hash(self, file_path: Path) -> str:
        """
        Calculate SHA256 hash of file content.
        """
        sha256_hash = hashlib.sha256()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                sha256_hash.update(chunk)
        return sha256_hash.hexdigest()

    def _quarantine_file(self, file_path: Path, error_msg: str) -> Path:
        """
        Move problematic file to quarantine with error log.
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        quarantine_filename = f"{file_path.stem}_{timestamp}_failed{file_path.suffix}"
        quarantine_path = self.quarantine_dir / quarantine_filename

        # Copy file to quarantine (preserve original)
        shutil.copy2(file_path, quarantine_path)

        # Create error log
        error_log_path = quarantine_path.with_suffix(".error.txt")
        error_info = f"""Error processing file: {file_path}
Timestamp: {datetime.now().isoformat()}
Error: {error_msg}
Original path: {file_path}
Quarantine path: {quarantine_path}
"""
        error_log_path.write_text(error_info)

        logger.warning(f"File quarantined: {file_path.name} -> {quarantine_filename}")
        return quarantine_path


def get_upload_processor() -> SimpleUploadProcessor:
    """Get upload processor instance.

    Simple factory following CLAUDE.md principles.
    """
    return SimpleUploadProcessor()
