"""
Document Processing Pipeline Router

Routes documents through the appropriate processor based on format.
Manages the complete document lifecycle from raw to export.
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Any

from loguru import logger

from .format_detector import FormatDetector
from .lifecycle_manager import DocumentLifecycleManager
from .naming_convention import NamingConvention
from .processors import DocxProcessor, MarkdownProcessor, TextProcessor

# Import PDF processor if available
try:
    from pdf.main import get_pdf_service

    PDF_AVAILABLE = True
except ImportError:
    PDF_AVAILABLE = False
    PDFService = None

# Import shared database
try:
    from shared.simple_db import SimpleDB

    DB_AVAILABLE = True
except ImportError:
    DB_AVAILABLE = False
    SimpleDB = None

# Logger is now imported globally from loguru


class DocumentPipeline:
    """Main document processing pipeline router."""

    def __init__(self, base_path: str = "data", db_path: str = "emails.db"):
        """
        Initialize document pipeline.

        Args:
            base_path: Base path for document folders
            db_path: Path to database
        """
        self.lifecycle = DocumentLifecycleManager(base_path)
        self.naming = NamingConvention()
        self.detector = FormatDetector()

        # Initialize processors
        self.processors = {
            "txt": TextProcessor(),
            "md": MarkdownProcessor(),
            "docx": DocxProcessor(),
        }

        # Add PDF processor if available
        if PDF_AVAILABLE:
            from pdf.wiring import build_pdf_service
            self.processors["pdf"] = build_pdf_service(db_path)

        # Initialize database if available
        self.db = SimpleDB(db_path) if DB_AVAILABLE else None

        self.stats = {"processed": 0, "failed": 0, "quarantined": 0, "unsupported": 0}

        logger.info(
            f"Document pipeline initialized with processors: {list(self.processors.keys())}"
        )

    def process_document(
        self, file_path: Path, case_name: str | None = None, doc_type: str | None = None
    ) -> dict[str, Any]:
        """
        Process a single document through the pipeline.

        Args:
            file_path: Path to document
            case_name: Case identifier for naming
            doc_type: Document type for naming

        Returns:
            Processing result
        """
        try:
            # Detect format
            format_type = self.detector.detect_format(file_path)

            if not format_type:
                self.stats["unsupported"] += 1
                return {
                    "success": False,
                    "error": f"Unsupported format: {file_path.suffix}",
                    "file": str(file_path),
                }

            # Get appropriate processor
            processor = self.processors.get(format_type)

            if not processor:
                self.stats["unsupported"] += 1
                return {
                    "success": False,
                    "error": f"No processor for format: {format_type}",
                    "file": str(file_path),
                }

            # Move to staged with naming convention
            staged_name = self.naming.staged_name(file_path, case_name, doc_type)
            staged_path = self.lifecycle.move_to_staged(file_path, staged_name)

            # Process document
            if format_type == "pdf" and PDF_AVAILABLE:
                # Use PDF service for PDF files
                result = processor.upload_single_pdf(str(staged_path))
            else:
                result = processor.process(staged_path)

            if not result.get("success"):
                # Move to quarantine on failure
                self.lifecycle.quarantine_file(
                    staged_path, result.get("error", "Processing failed")
                )
                self.stats["quarantined"] += 1
                return result

            # Save processed content
            processed_name = self.naming.processed_name(staged_path, format="md")
            processed_path = self.lifecycle.folders["processed"] / processed_name

            # Write processed content as markdown
            self._save_processed_content(processed_path, result)

            # Move staged file to processed
            self.lifecycle.move_to_processed(staged_path, f"{processed_name}.original")

            # Store in database if available
            if self.db and result.get("content"):
                db_result = self._store_in_database(result, processed_name, format_type)
                result["database_id"] = db_result.get("content_id")

            # Move to export
            export_name = self.naming.export_name(processed_name, case_name, doc_type)
            export_path = self.lifecycle.move_to_export(processed_path, export_name)

            self.stats["processed"] += 1

            return {
                "success": True,
                "format": format_type,
                "processed_file": str(export_path),
                "original_file": str(file_path),
                "metadata": result.get("metadata", {}),
                "metrics": result.get("metrics", {}),
                "database_id": result.get("database_id"),
            }

        except Exception as e:
            logger.error(f"Pipeline processing failed for {file_path}: {e}")
            self.stats["failed"] += 1

            # Try to quarantine if possible
            try:
                if file_path.exists():
                    self.lifecycle.quarantine_file(file_path, str(e))
            except Exception:
                pass

            return {"success": False, "error": str(e), "file": str(file_path)}

    def _save_processed_content(self, output_path: Path, result: dict[str, Any]):
        """
        Save processed content as markdown with metadata.

        Args:
            output_path: Path to save processed content
            result: Processing result
        """
        try:
            # Create markdown with frontmatter
            lines = ["---"]

            # Add metadata as YAML frontmatter
            metadata = result.get("metadata", {})
            metadata["processed_at"] = result.get("processed_at", datetime.now().isoformat())
            metadata["format"] = result.get("format", "unknown")

            for key, value in metadata.items():
                if isinstance(value, (str, int, float, bool)):
                    lines.append(f"{key}: {value}")
                elif isinstance(value, (list, dict)):
                    lines.append(f"{key}: {json.dumps(value)}")

            lines.append("---")
            lines.append("")

            # Add content
            content = result.get("content", "")
            lines.append(content)

            # Write file
            output_path.write_text("\n".join(lines), encoding="utf-8")
            logger.info(f"Saved processed content to {output_path}")

        except Exception as e:
            logger.error(f"Failed to save processed content: {e}")
            raise

    def _store_in_database(
        self, result: dict[str, Any], doc_id: str, format_type: str
    ) -> dict[str, Any]:
        """
        Store document in database.

        Args:
            result: Processing result
            doc_id: Document ID
            format_type: Document format

        Returns:
            Database storage result
        """
        try:
            metadata = result.get("metadata", {})
            metadata["format"] = format_type
            metadata["doc_id"] = doc_id
            metadata["metrics"] = result.get("metrics", {})

            content_id = self.db.add_content(
                content_type="document",
                title=metadata.get("title", metadata.get("filename", doc_id)),
                content=result.get("content", ""),
                metadata=metadata,
            )

            return {"success": True, "content_id": content_id}

        except Exception as e:
            logger.error(f"Database storage failed: {e}")
            return {"success": False, "error": str(e)}

    def process_directory(
        self,
        directory_path: str,
        case_name: str | None = None,
        doc_type: str | None = None,
        recursive: bool = False,
    ) -> dict[str, Any]:
        """
        Process all documents in a directory.

        Args:
            directory_path: Path to directory
            case_name: Case identifier for naming
            doc_type: Document type for naming
            recursive: Process subdirectories

        Returns:
            Batch processing results
        """
        dir_path = Path(directory_path)

        if not dir_path.exists():
            return {"success": False, "error": f"Directory not found: {directory_path}"}

        # Find all supported files
        pattern = "**/*" if recursive else "*"
        files = []

        for file_path in dir_path.glob(pattern):
            if file_path.is_file() and self.detector.is_supported_format(file_path):
                files.append(file_path)

        if not files:
            return {"success": True, "message": "No supported documents found", "stats": self.stats}

        # Process each file
        results = []
        for file_path in files:
            result = self.process_document(file_path, case_name, doc_type)
            results.append(
                {
                    "file": str(file_path),
                    "success": result["success"],
                    "format": result.get("format"),
                    "error": result.get("error"),
                }
            )

        return {"success": True, "total_files": len(files), "results": results, "stats": self.stats}

    def get_pipeline_stats(self) -> dict[str, Any]:
        """Get pipeline statistics."""
        folder_stats = self.lifecycle.get_folder_stats()

        return {
            "pipeline_stats": self.stats,
            "folder_stats": folder_stats,
            "supported_formats": list(self.processors.keys()),
            "database_available": self.db is not None,
        }
