"""
PDF Service - Consolidated service following new pattern

Architecture:
- Consolidates pdf_processing pipeline into single service
- Maintains service independence through database-only communication
- Uses modular components for clean separation
- Returns standard {"success": bool, "error": str} format
"""

import os
import sys
import threading
from datetime import datetime
from typing import Any

from loguru import logger

# Add project root to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from infrastructure.pipelines.data_pipeline import DataPipelineOrchestrator
from infrastructure.pipelines.document_exporter import DocumentExporter
from pdf.database_error_recovery import DatabaseErrorRecovery
from pdf.database_health_monitor import DatabaseHealthMonitor
from pdf.ocr.ocr_coordinator import OCRCoordinator
from pdf.pdf_health import PDFHealthManager
from pdf.pdf_processor_enhanced import EnhancedPDFProcessor
from pdf.pdf_storage_enhanced import EnhancedPDFStorage
from pdf.pdf_validator import PDFValidator
from shared.service_interfaces import IService
from shared.simple_db import SimpleDB
from summarization import get_document_summarizer

# Resource protection constants
MAX_CONCURRENT_UPLOADS = 10  # Maximum concurrent upload operations
DEFAULT_CHUNK_SIZE = 900
DEFAULT_CHUNK_OVERLAP = 100

# Global concurrency control
_upload_semaphore = threading.Semaphore(MAX_CONCURRENT_UPLOADS)


class PDFService(IService):
    """Consolidated PDF service with integrated processing capabilities"""

    def __init__(self, db_path: str = "emails.db") -> None:
        self.db_path = db_path
        self.health_monitor = DatabaseHealthMonitor(db_path)
        self.error_recovery = DatabaseErrorRecovery(db_path)
        # Logger is now imported globally from loguru

        # Initialize modular components with OCR support
        self.processor = EnhancedPDFProcessor(DEFAULT_CHUNK_SIZE, DEFAULT_CHUNK_OVERLAP)
        self.storage = EnhancedPDFStorage(db_path)
        self.validator = PDFValidator()
        self.ocr = OCRCoordinator()  # Add OCR coordinator
        self.summarizer = get_document_summarizer()  # Add document summarizer
        self.db = SimpleDB(db_path)  # Add database for summary storage
        self.pipeline = DataPipelineOrchestrator()  # Add data pipeline orchestrator
        self.exporter = DocumentExporter()  # Add document exporter

        # Set up logging first
        log_file = f"logs/pdf_service_{datetime.now().strftime('%Y%m%d')}.log"
        os.makedirs(os.path.dirname(log_file), exist_ok=True)
        
        # Use loguru logger (imported globally)
        self.logger = logger  # Set instance logger to global loguru logger

        self.health_manager = PDFHealthManager(
            self.processor, self.storage, self.validator, self.health_monitor, self.logger
        )

        # Set up error recovery alerting
        self.error_recovery.add_alert_callback(self._handle_database_alert)

    def health_check(self) -> dict[str, Any]:
        """Perform comprehensive health check for PDF service"""
        return self.health_manager.perform_health_check()

    def upload_single_pdf(
        self, pdf_path: str, source: str = "upload", use_pipeline: bool = True
    ) -> dict[str, Any]:
        """Upload single PDF with integrated processing and pipeline support"""
        with _upload_semaphore:
            try:
                # Add to pipeline if enabled
                if use_pipeline:
                    pipeline_result = self.pipeline.add_to_raw(pdf_path, copy=True)
                    if not pipeline_result["success"]:
                        logger.warning(f"Pipeline add failed: {pipeline_result['error']}")
                    else:
                        # Use pipeline path for processing
                        pdf_path = pipeline_result["path"]
                        # Move to staged for processing
                        staged_result = self.pipeline.move_to_staged(os.path.basename(pdf_path))
                        if staged_result["success"]:
                            pdf_path = staged_result["path"]

                # Basic validation
                validation_result = self.validator.validate_pdf_file(pdf_path)
                if not validation_result["success"]:
                    if use_pipeline:
                        self.pipeline.move_to_quarantine(
                            os.path.basename(pdf_path),
                            validation_result.get("error", "Validation failed"),
                        )
                    return validation_result

                # Check resource limits
                resource_check = self.validator.check_resource_limits(pdf_path)
                if not resource_check["success"]:
                    if use_pipeline:
                        self.pipeline.move_to_quarantine(
                            os.path.basename(pdf_path),
                            resource_check.get("error", "Resource limit exceeded"),
                        )
                    return resource_check

                # Check for duplicates
                file_hash = self.storage.hash_file(pdf_path)
                if self.storage.is_duplicate(file_hash):
                    if use_pipeline:
                        # Move to processed since it's already in the system
                        self.pipeline.move_to_processed(
                            os.path.basename(pdf_path), {"status": "duplicate", "hash": file_hash}
                        )
                    return {
                        "success": True,
                        "skipped": True,
                        "reason": "File already exists in database",
                    }

                # Process PDF
                result = self._process_pdf_internal(pdf_path, file_hash, source)

                # Update pipeline based on result
                if use_pipeline:
                    if result.get("success"):
                        metadata = {
                            "processed_at": datetime.now().isoformat(),
                            "chunks": result.get("chunks_processed", 0),
                            "extraction_method": result.get("extraction_method", "unknown"),
                            "hash": file_hash,
                        }
                        self.pipeline.move_to_processed(os.path.basename(pdf_path), metadata)
                    else:
                        self.pipeline.move_to_quarantine(
                            os.path.basename(pdf_path), result.get("error", "Processing failed")
                        )

                return result

            except Exception as e:
                logger.error(f"Upload failed for {pdf_path}: {str(e)}")
                return {"success": False, "error": f"Upload failed: {str(e)}"}

    def upload_directory(self, directory_path: str, limit: int | None = None) -> dict[str, Any]:
        """Upload directory of PDFs with batch processing"""
        try:
            pdf_files = self._prepare_pdf_files(directory_path, limit)
            if "error" in pdf_files:
                return pdf_files

            results = self._process_pdf_files(pdf_files["files"])
            return {"success": True, "results": results, "total_processed": len(pdf_files["files"])}

        except Exception as e:
            logger.error(f"Directory upload failed: {str(e)}")
            return {"success": False, "error": f"Directory upload failed: {str(e)}"}

    def _prepare_pdf_files(self, directory_path: str, limit: int | None) -> dict[str, Any]:
        """Prepare and validate PDF files for processing"""
        if not os.path.exists(directory_path):
            return {"error": "Directory does not exist"}

        pdf_files = self.storage.find_pdf_files(directory_path)
        if not pdf_files:
            return {"error": "No PDF files found in directory"}

        if limit:
            pdf_files = pdf_files[:limit]

        return {"files": pdf_files}

    def _process_pdf_files(self, pdf_files: list[str]) -> dict[str, Any]:
        """Process list of PDF files and collect results"""
        results = {"success_count": 0, "skipped_count": 0, "error_count": 0, "details": []}

        for pdf_file in pdf_files:
            result = self.upload_single_pdf(pdf_file)
            self._update_results(results, pdf_file, result)

        return results

    def _update_results(self, results: dict[str, Any], pdf_file: str, result: dict[str, Any]) -> None:
        """Update results counters based on processing result"""
        if result.get("success"):
            if result.get("skipped"):
                results["skipped_count"] += 1
            else:
                results["success_count"] += 1
        else:
            results["error_count"] += 1

        results["details"].append({"file": os.path.basename(pdf_file), "result": result})

    def get_pdf_stats(self) -> dict[str, Any]:
        """Get PDF collection statistics"""
        # Update storage path if it changed
        if hasattr(self, "db_path") and self.storage.db_path != self.db_path:
            self.storage.db_path = self.db_path
        return self.storage.get_enhanced_pdf_stats()

    def _process_pdf_internal(self, pdf_path: str, file_hash: str, source: str) -> dict[str, Any]:
        """Internal PDF processing with OCR and legal metadata support"""
        try:
            # Use OCR coordinator for better OCR handling
            ocr_result = self.ocr.process_pdf_with_ocr(pdf_path)

            if ocr_result.get("ocr_used") and ocr_result.get("success"):
                # OCR was used and successful
                # Format chunks as expected by storage
                chunks = [
                    {
                        "chunk_id": f"{file_hash}_0",
                        "text": ocr_result["text"],
                        "chunk_index": 0,
                        "extraction_method": "ocr",
                    }
                ]
                extraction_method = "ocr"
                ocr_confidence = ocr_result.get("confidence", 0)
                result = {
                    "success": True,
                    "chunks": chunks,
                    "extraction_method": extraction_method,
                    "ocr_confidence": ocr_confidence,
                    "legal_metadata": ocr_result.get("metadata", {}),
                }
            else:
                # Regular text extraction
                result = self.processor.extract_and_chunk_pdf(pdf_path, force_ocr=False)
            if not result["success"]:
                return result

            # Store chunks with metadata in database
            storage_result = self.storage.store_chunks_with_metadata(
                pdf_path,
                file_hash,
                result["chunks"],
                extraction_method=result.get("extraction_method"),
                ocr_confidence=result.get("ocr_confidence"),
                legal_metadata=result.get("legal_metadata"),
                source=source,
            )
            if not storage_result["success"]:
                return storage_result

            # Generate and store document summary
            try:
                # Combine all chunks for summarization
                chunks = result.get("chunks", [])
                full_text = " ".join([chunk.get("text", "") for chunk in chunks])

                if (
                    full_text and len(full_text) > 100
                ):  # Only summarize if we have meaningful content
                    # Generate summary
                    summary = self.summarizer.extract_summary(
                        full_text,
                        max_sentences=5,  # More sentences for legal documents
                        max_keywords=15,  # More keywords for legal terms
                        summary_type="combined",
                    )

                    # Store summary in database if we have a content_id
                    content_id = storage_result.get("content_id")

                    if content_id and summary:
                        summary_id = self.db.add_document_summary(
                            document_id=content_id,
                            summary_type="combined",
                            summary_text=summary.get("summary_text"),
                            tf_idf_keywords=summary.get("tf_idf_keywords"),
                            textrank_sentences=summary.get("textrank_sentences"),
                        )

                        if summary_id:
                            logger.info(f"Generated summary for {os.path.basename(pdf_path)}")

                            # Export document to markdown (don't fail upload if this fails)
                            try:
                                export_result = self.exporter.save_to_export(
                                    content_id, os.path.splitext(os.path.basename(pdf_path))[0]
                                )
                                if export_result["success"]:
                                    logger.info(
                                        f"Exported {os.path.basename(pdf_path)} to {export_result['filename']}"
                                    )
                                else:
                                    logger.warning(
                                        f"Export failed for {pdf_path}: {export_result.get('error')}"
                                    )
                            except Exception as export_e:
                                logger.warning(f"Could not export {pdf_path}: {export_e}")

            except Exception as e:
                # Don't fail the upload if summarization fails
                logger.warning(f"Could not generate summary for {pdf_path}: {e}")

            filename = os.path.basename(pdf_path)
            file_size_mb = os.path.getsize(pdf_path) / (1024 * 1024)
            chunk_count = len(result.get("chunks", []))
            logger.info(f"Successfully processed: {filename} ({chunk_count} chunks)")

            return {
                "success": True,
                "file_name": filename,
                "chunks_processed": chunk_count,
                "file_size_mb": round(file_size_mb, 2),
                "file_hash": file_hash,
                "content_id": storage_result.get("content_id"),
            }

        except Exception as e:
            logger.error(f"Internal processing failed for {pdf_path}: {str(e)}")
            return {"success": False, "error": f"Processing failed: {str(e)}"}

    def _handle_database_alert(self, alert) -> None:
        """Handle database alerts from error recovery system"""
        logger.warning(
            f"Database Alert [{alert.severity.value}] {alert.error_type}: {alert.message}"
        )

    def create_database_backup(self, backup_name: str | None = None) -> dict[str, Any]:
        """Create database backup for disaster recovery"""
        return self.error_recovery.create_backup(backup_name)

    def get_recovery_status(self) -> dict[str, Any]:
        """Get current database recovery system status"""
        return self.error_recovery.get_recovery_status()
