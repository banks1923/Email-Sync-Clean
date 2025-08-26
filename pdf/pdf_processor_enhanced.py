"""
Enhanced PDF processor with OCR and legal metadata extraction Integrates OCR
capabilities and legal metadata into main PDF workflow.
"""

import json
from typing import Any

from loguru import logger

from .ocr import OCRCoordinator
from .ocr.enhanced_ocr_coordinator import EnhancedOCRCoordinator
from .pdf_processor import PDFProcessor

try:
    from ..vector.legal_metadata_extractor import LegalMetadataExtractor

    LEGAL_METADATA_AVAILABLE = True
except ImportError:
    LEGAL_METADATA_AVAILABLE = False


class EnhancedPDFProcessor:
    """
    PDF processor with OCR and legal metadata capabilities.
    """

    def __init__(
        self, chunk_size: int = 900, chunk_overlap: int = 100, use_enhanced_ocr: bool = True
    ) -> None:
        """
        Initialize with OCR support.
        """
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.use_enhanced_ocr = use_enhanced_ocr

        # Initialize both coordinators for fallback capability
        if use_enhanced_ocr:
            self.enhanced_ocr_coordinator = EnhancedOCRCoordinator()
            self.ocr_coordinator = OCRCoordinator()  # Fallback
        else:
            self.enhanced_ocr_coordinator = None
            self.ocr_coordinator = OCRCoordinator()

        self.pdf_processor = PDFProcessor(chunk_size, chunk_overlap)
        # Logger is now imported globally from loguru

        if LEGAL_METADATA_AVAILABLE:
            self.legal_extractor = LegalMetadataExtractor()
        else:
            self.legal_extractor = None

    def validate_dependencies(self) -> dict[str, Any]:
        """
        Validate all dependencies including OCR.
        """
        # Check enhanced OCR if available
        if self.use_enhanced_ocr and self.enhanced_ocr_coordinator:
            enhanced_validation = self.enhanced_ocr_coordinator.validate_enhanced_setup()
            ocr_ready = enhanced_validation.get("ready", False)
            ocr_details = enhanced_validation
        else:
            standard_validation = self.ocr_coordinator.validate_setup()
            ocr_ready = standard_validation.get("ready", False)
            ocr_details = standard_validation

        pdf_validation = self.pdf_processor.validate_dependencies()
        pdf_ready = pdf_validation.get("success", False)

        result = {
            "ocr": ocr_details,
            "pdf": pdf_validation,
            "legal_metadata": LEGAL_METADATA_AVAILABLE,
            "enhanced_ocr_enabled": self.use_enhanced_ocr,
        }
        # Legal metadata is optional - don't make it a hard requirement
        result["all_available"] = ocr_ready and pdf_ready
        return result

    def extract_and_chunk_pdf(
        self, pdf_path: str, force_ocr: bool = False, quality_gates_enabled: bool = True
    ) -> dict[str, Any]:
        """
        Extract text and create chunks with enhanced OCR and quality gates
        support.
        """
        try:
            # Use enhanced OCR coordinator if available
            if self.use_enhanced_ocr and self.enhanced_ocr_coordinator:
                ocr_result = self.enhanced_ocr_coordinator.process_pdf_with_enhanced_ocr(
                    pdf_path, force_ocr, quality_gates_enabled
                )
            else:
                # Fallback to standard OCR coordinator
                ocr_result = self.ocr_coordinator.process_pdf_with_ocr(pdf_path, force_ocr)

            if not ocr_result["success"]:
                return ocr_result

            # Extract processing metadata
            validation_status = ocr_result.get("validation_status", "ocr_done")
            quality_score = ocr_result.get("quality_score", 0.0)
            pipeline_metadata = ocr_result.get("pipeline_metadata", {})
            processing_stages = ocr_result.get("processing_stages", [])

            # Use OCR text if available, otherwise use regular extraction
            if ocr_result.get("ocr_used"):
                text = ocr_result["text"]
                extraction_method = ocr_result.get(
                    "method", "enhanced_ocr" if self.use_enhanced_ocr else "ocr"
                )
                ocr_confidence = ocr_result.get("confidence", 0.0)
            else:
                # Use regular text extraction (born-digital fast-path)
                text_result = self.pdf_processor.extract_text_from_pdf(pdf_path)
                if not text_result["success"]:
                    return text_result
                text = text_result["text"]
                extraction_method = "pypdf2"
                ocr_confidence = None

            # Create chunks
            chunks = self.pdf_processor.chunk_text(text)

            # Extract legal metadata if available
            legal_metadata = {}
            if self.legal_extractor and text:
                try:
                    legal_metadata = self.legal_extractor.extract_metadata(text)
                except Exception as e:
                    logger.warning(f"Legal metadata extraction failed: {e}")

            # Prepare chunks with metadata
            processed_chunks = []
            for i, chunk_text in enumerate(chunks):
                chunk_dict = {
                    "text": chunk_text,
                    "chunk_index": i,
                    "chunk_id": f"{pdf_path}_{i}",
                    "extraction_method": extraction_method,
                }

                if ocr_confidence is not None:
                    chunk_dict["ocr_confidence"] = ocr_confidence

                if legal_metadata:
                    chunk_dict["legal_metadata"] = json.dumps(legal_metadata)

                # Add enhanced OCR metadata if available
                if validation_status:
                    chunk_dict["validation_status"] = validation_status
                if quality_score:
                    chunk_dict["quality_score"] = quality_score
                if pipeline_metadata:
                    chunk_dict["pipeline_metadata"] = json.dumps(pipeline_metadata)

                processed_chunks.append(chunk_dict)

            return {
                "success": True,
                "chunks": processed_chunks,
                "chunk_count": len(processed_chunks),
                "extraction_method": extraction_method,
                "ocr_confidence": ocr_confidence,
                "legal_metadata": legal_metadata,
                "page_count": ocr_result.get("page_count", 1),
                "validation_status": validation_status,
                "quality_score": quality_score,
                "pipeline_metadata": pipeline_metadata,
                "processing_stages": processing_stages,
                "enhanced_ocr_enabled": self.use_enhanced_ocr,
            }

        except Exception as e:
            logger.error(f"Failed to process PDF {pdf_path}: {e}")
            return {"success": False, "error": str(e)}

    def should_use_ocr(self, pdf_path: str) -> dict[str, Any]:
        """
        Analyze PDF to determine if OCR is needed.
        """
        return self.ocr_coordinator.validator.should_use_ocr(pdf_path)

    # Legacy compatibility methods
    def extract_text_from_pdf(self, pdf_path: str) -> dict[str, Any]:
        """Legacy method - extract text with OCR support"""
        result = self.extract_and_chunk_pdf(pdf_path)
        if result["success"]:
            # Join chunks back into full text
            full_text = "\n\n".join(chunk["text"] for chunk in result["chunks"])
            return {"success": True, "text": full_text}
        return result

    def chunk_text(self, text: str) -> list[str]:
        """Legacy method - chunk text into smaller pieces"""
        return self.pdf_processor.chunk_text(text)
