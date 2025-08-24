"""OCR coordinator - orchestrates the OCR pipeline."""

from typing import Any

from loguru import logger

from .loader import PDFLoader
from .ocr_engine import OCREngine
from .postprocessor import OCRPostprocessor
from .rasterizer import PDFRasterizer
from .validator import PDFValidator

# Logger is now imported globally from loguru


class OCRCoordinator:
    """Coordinates the complete OCR pipeline."""

    def __init__(self, dpi: int = 300) -> None:
        """Initialize OCR coordinator with all components."""
        self.loader = PDFLoader()
        self.validator = PDFValidator()
        self.rasterizer = PDFRasterizer(dpi=dpi)
        self.engine = OCREngine()
        self.postprocessor = OCRPostprocessor()

    def process_pdf_with_ocr(self, pdf_path: str, force_ocr: bool = False) -> dict[str, Any]:
        """
        Process PDF with OCR if needed.

        Args:
            pdf_path: Path to PDF file
            force_ocr: Force OCR even for text PDFs

        Returns:
            Dict with extracted text and metadata
        """
        # Validate file
        validation = self.loader.validate_pdf_file(pdf_path)
        if not validation["success"]:
            return validation

        # Check if OCR needed
        ocr_check = self.validator.should_use_ocr(pdf_path, force_ocr)
        if not ocr_check["success"]:
            return ocr_check

        if not ocr_check["use_ocr"]:
            return {
                "success": True,
                "method": "text_extraction",
                "text": "",  # Caller should use regular text extraction
                "ocr_used": False,
            }

        # Perform OCR
        return self._extract_with_ocr(pdf_path)

    def _extract_with_ocr(self, pdf_path: str) -> dict[str, Any]:
        """Extract text using OCR."""
        try:
            # Convert PDF to images
            raster_result = self.rasterizer.convert_pdf_to_images(pdf_path)
            if not raster_result["success"]:
                return raster_result

            # Process each page
            page_texts = []
            confidences = []

            for i, image in enumerate(raster_result["images"]):
                logger.info(f"Processing page {i+1}/{len(raster_result['images'])}")

                # Extract text from image
                ocr_result = self.engine.extract_text_from_image(image)
                if ocr_result["success"]:
                    page_texts.append(ocr_result["text"])
                    confidences.append(ocr_result["confidence"])
                else:
                    page_texts.append("")
                    confidences.append(0.0)

            # Merge and clean texts
            merged_text = self.postprocessor.merge_page_texts(page_texts)
            avg_confidence = sum(confidences) / len(confidences) if confidences else 0.0

            # Validate quality
            quality = self.postprocessor.validate_ocr_quality(merged_text, avg_confidence)

            # Extract metadata hints
            metadata = self.postprocessor.extract_metadata_hints(merged_text)

            return {
                "success": True,
                "method": "ocr",
                "text": merged_text,
                "ocr_used": True,
                "page_count": len(page_texts),
                "confidence": avg_confidence,
                "quality": quality,
                "metadata": metadata,
            }

        except Exception as e:
            logger.error(f"OCR processing failed: {e}")
            return {"success": False, "error": str(e), "method": "ocr"}

    def validate_setup(self) -> dict[str, Any]:
        """Validate complete OCR setup."""
        return {
            "dependencies": self.validator.validate_dependencies(),
            "rasterizer": self.rasterizer.validate_settings(),
            "ocr_engine": self.engine.validate_ocr_setup(),
            "ready": all(
                [
                    self.validator.validate_dependencies()["all_available"],
                    self.engine.validate_ocr_setup()["ready"],
                ]
            ),
        }
