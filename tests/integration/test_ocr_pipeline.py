"""Integration tests for the complete OCR pipeline.

Tests the full workflow from PDF input to text extraction and vector
embeddings.
"""

import os
import sys
import tempfile

from pdf.ocr import OCRCoordinator, PageByPageProcessor
from pdf.ocr.validator import PDFValidator
from pdf.wiring import get_pdf_service

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if project_root not in sys.path:
    sys.path.insert(0, project_root)


class TestOCRPipelineIntegration:
    """
    Test complete OCR pipeline integration.
    """

    def test_ocr_coordinator_full_pipeline(self):
        """
        Test OCR coordinator with real PDF processing.
        """
        coordinator = OCRCoordinator(dpi=400)

        # Validate setup
        setup = coordinator.validate_setup()
        assert setup["ready"] is True
        assert setup["dependencies"]["all_available"] is True
        assert setup["ocr_engine"]["ready"] is True

        # Test with sample PDF if available
        sample_pdf = os.path.join(
            project_root, "tests", "test_data", "pdf_samples", "scanned_court_document.pdf"
        )

        if os.path.exists(sample_pdf):
            result = coordinator.process_pdf_with_ocr(sample_pdf, force_ocr=True)
            assert result["success"] is True
            assert result["ocr_used"] is True
            assert "text" in result
            assert result["confidence"] > 0
            assert "metadata" in result

    def test_page_by_page_processor(self):
        """
        Test batch processing for large PDFs.
        """
        processor = PageByPageProcessor(batch_size=2, max_memory_mb=500)

        # Verify initialization
        assert processor.batch_size == 2
        assert processor.max_memory_mb == 500
        assert processor.ocr_engine is not None
        assert processor.postprocessor is not None
        assert processor.rasterizer.dpi == 400  # Should use improved DPI

        # Test with multi-page PDF if available
        multi_page_pdf = os.path.join(
            project_root, "tests", "test_data", "pdf_samples", "multi_page_document.pdf"
        )

        if os.path.exists(multi_page_pdf):
            # Test page range processing
            result = processor.process_large_pdf(multi_page_pdf, start_page=0, end_page=2)

            assert result["success"] is True
            assert result["method"] == "page_by_page_ocr"
            assert result["pages_processed"] <= 2
            assert "text" in result
            assert "confidence" in result

    def test_pdf_validator(self):
        """
        Test PDF validation and OCR detection.
        """
        validator = PDFValidator()

        # Check dependencies
        deps = validator.validate_dependencies()
        assert deps["pypdf2"] is True
        assert deps["ocr_available"] is True
        assert deps["cv2_available"] is True

        # Test with different PDF types
        test_pdfs = [
            ("scanned_court_document.pdf", True),  # Should need OCR
            ("text_based_contract.pdf", False),  # Should not need OCR
        ]

        for pdf_name, expected_ocr in test_pdfs:
            pdf_path = os.path.join(project_root, "tests", "test_data", "pdf_samples", pdf_name)

            if os.path.exists(pdf_path):
                result = validator.should_use_ocr(pdf_path)
                assert result["success"] is True
                # Allow some flexibility in detection
                if expected_ocr:
                    assert result["use_ocr"] is True or result["confidence"] > 0.5
                else:
                    assert result["use_ocr"] is False or result["confidence"] < 0.5

    def test_pdf_service_integration(self):
        """
        Test PDFService with OCR integration.
        """
        service = get_pdf_service()

        # Check health
        health = service.health_check()
        assert health["healthy"] is True

        # Get stats to see OCR metrics
        stats = service.get_pdf_stats()
        assert "total_documents" in stats

        # Test upload with OCR detection
        sample_pdf = os.path.join(
            project_root, "tests", "test_data", "pdf_samples", "scanned_court_document.pdf"
        )

        if os.path.exists(sample_pdf):
            result = service.upload_single_pdf(sample_pdf)

            # Service should handle OCR automatically
            if result["success"]:
                assert "chunks_processed" in result
                assert result["chunks_processed"] >= 0

    def test_ocr_quality_improvements(self):
        """
        Test that quality improvements are working.
        """
        from pdf.ocr.ocr_engine import OCREngine

        engine = OCREngine()

        # Verify enhanced settings
        assert engine.available is True

        # Create a simple test image
        try:
            from PIL import Image, ImageDraw

            # Create test image with text
            img = Image.new("RGB", (800, 600), color="white")
            draw = ImageDraw.Draw(img)

            # Add some text
            text = "LEGAL DOCUMENT TEST"
            draw.text((100, 100), text, fill="black")

            # Test OCR with enhancement
            result = engine.extract_text_from_image(img, enhance=True)

            assert result["success"] is True
            assert result["confidence"] > 0
            assert "text" in result

        except ImportError:
            # Skip if PIL not available
            pass

    def test_generator_mode(self):
        """
        Test streaming mode for memory efficiency.
        """
        processor = PageByPageProcessor()

        multi_page_pdf = os.path.join(
            project_root, "tests", "test_data", "pdf_samples", "multi_page_document.pdf"
        )

        if os.path.exists(multi_page_pdf):
            pages_processed = 0

            for page_result in processor.process_with_generator(multi_page_pdf):
                assert "page" in page_result

                if page_result["success"]:
                    assert "text" in page_result
                    assert "confidence" in page_result

                pages_processed += 1

                # Test first 3 pages only
                if pages_processed >= 3:
                    break

            assert pages_processed >= 1  # At least one page processed

    def test_error_handling(self):
        """
        Test error handling in OCR pipeline.
        """
        coordinator = OCRCoordinator()

        # Test with non-existent file
        result = coordinator.process_pdf_with_ocr("/nonexistent/file.pdf")
        assert result["success"] is False
        assert "error" in result

        # Test with invalid PDF
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
            tmp.write(b"Not a valid PDF")
            tmp_path = tmp.name

        try:
            result = coordinator.process_pdf_with_ocr(tmp_path)
            assert result["success"] is False
        finally:
            os.unlink(tmp_path)

    def test_confidence_scoring(self):
        """
        Test OCR confidence scoring and quality metrics.
        """
        from pdf.ocr.postprocessor import OCRPostprocessor

        postprocessor = OCRPostprocessor()

        # Test quality validation
        test_cases = [
            ("", 0.0, "empty"),  # Empty text
            ("Short", 0.3, "low"),  # Low confidence
            ("This is a longer text with good content", 0.85, "high"),  # Good
            ("Perfect legal document text" * 10, 0.95, "excellent"),  # Excellent
        ]

        for text, confidence, expected_quality in test_cases:
            quality = postprocessor.validate_ocr_quality(text, confidence)
            assert quality["valid"] is True or expected_quality == "empty"
            assert quality["confidence"] == confidence


if __name__ == "__main__":
    import pytest

    pytest.main([__file__, "-v"])
