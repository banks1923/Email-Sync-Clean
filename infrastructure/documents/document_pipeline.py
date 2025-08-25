"""Document Processing Pipeline Router.

Routes documents through the appropriate processor based on format.
Manages the complete document lifecycle from raw to export.
"""

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

    PDF_AVAILABLE = True
except ImportError:
    PDF_AVAILABLE = False
    PDFService = None

# Import shared database
try:
    from shared.simple_db import SimpleDB
    from config.settings import get_db_path
    DB_AVAILABLE = True
except ImportError:
    DB_AVAILABLE = False
    SimpleDB = None
    get_db_path = lambda: "data/emails.db"

# Logger is now imported globally from loguru


class DocumentPipeline:
    """
    Main document processing pipeline router.
    """

    def __init__(self, base_path: str = "data", db_path: str = None):
        """Initialize document pipeline.

        Args:
            base_path: Base path for document folders
            db_path: Path to database
        """
        # Use centralized config if no path provided
        if db_path is None:
            db_path = get_db_path()
            
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
        """Process a document in place and save clean version.

        Args:
            file_path: Path to document (left unchanged)
            case_name: Case identifier for metadata
            doc_type: Document type for metadata

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

            # Process document in place
            if format_type == "pdf" and PDF_AVAILABLE:
                # Use PDF service for PDF files
                result = processor.upload_single_pdf(str(file_path))
            else:
                result = processor.process(file_path)

            if not result.get("success"):
                # Quarantine on failure (copy, don't move)
                quarantine_path = self.lifecycle.quarantine_file(
                    file_path, result.get("error", "Processing failed")
                )
                self.stats["quarantined"] += 1
                result["quarantine_path"] = str(quarantine_path)
                return result

            # Use simple processor to save clean version
            content = result.get("content", "")
            metadata = {
                "case_name": case_name,
                "doc_type": doc_type,
                "format_type": format_type,
                "processed_at": datetime.now().isoformat()
            }
            
            process_result = self.lifecycle.process_file(
                file_path, content, format_type, metadata
            )

            self.stats["processed"] += 1

            return {
                "success": True,
                "format": format_type,
                "processed_file": process_result.get("processed_path"),
                "original_file": str(file_path),
                "content_id": process_result.get("content_id"),
                "metadata": metadata,
                "metrics": result.get("metrics", {}),
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


    def process_directory(
        self,
        directory_path: str,
        case_name: str | None = None,
        doc_type: str | None = None,
        recursive: bool = False,
    ) -> dict[str, Any]:
        """Process all documents in a directory.

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
        """
        Get pipeline statistics.
        """
        folder_stats = self.lifecycle.get_folder_stats()

        return {
            "pipeline_stats": self.stats,
            "folder_stats": folder_stats,
            "supported_formats": list(self.processors.keys()),
            "database_available": self.db is not None,
        }
