"""
Test suite for OCR components including PageByPageProcessor and OCRCoordinator
Tests new memory-efficient processing features added for large PDFs.
"""

import os
import sys
from unittest.mock import MagicMock, patch

from pdf.ocr.ocr_coordinator import OCRCoordinator
from pdf.ocr.page_processor import PageByPageProcessor
from pdf.pdf_processor import PDFProcessor

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if project_root not in sys.path:
    sys.path.insert(0, project_root)


class TestPageByPageProcessor:
    """
    Test the PageByPageProcessor for large PDF handling.
    """

    def test_init_with_custom_settings(self):
        """
        Test initialization with custom batch size and memory limits.
        """
        processor = PageByPageProcessor(batch_size=3, max_memory_mb=300)

        assert processor.batch_size == 3
        assert processor.max_memory_mb == 300
        assert processor.ocr_engine is not None
        assert processor.postprocessor is not None

    def test_process_large_pdf_with_page_range(self):
        """
        Test processing specific page range.
        """
        processor = PageByPageProcessor(batch_size=2)

        # Use the multi-page test PDF
        pdf_path = os.path.join(
            project_root, "tests", "test_data", "pdf_samples", "multi_page_document.pdf"
        )

        if os.path.exists(pdf_path):
            # Process only pages 1-3
            result = processor.process_large_pdf(pdf_path, start_page=0, end_page=3)

            assert result["success"] is True
            assert result["pages_processed"] == 3
            assert result["total_pages"] == 5
            assert "text" in result
            assert result["method"] == "page_by_page_ocr"

    def test_progress_callback(self):
        """
        Test that progress callbacks are invoked correctly.
        """
        processor = PageByPageProcessor(batch_size=1)

        # Track progress calls
        progress_updates = []

        def progress_callback(info):
            progress_updates.append(info)

        pdf_path = os.path.join(
            project_root, "tests", "test_data", "pdf_samples", "multi_page_document.pdf"
        )

        if os.path.exists(pdf_path):
            processor.process_large_pdf(
                pdf_path, start_page=0, end_page=2, progress_callback=progress_callback
            )

            # Should have progress updates for each batch
            assert len(progress_updates) > 0
            # Check progress structure
            for update in progress_updates:
                assert "current_page" in update
                assert "total_pages" in update
                assert "progress_percent" in update

    def test_generator_mode(self):
        """
        Test streaming results with generator.
        """
        processor = PageByPageProcessor()

        pdf_path = os.path.join(
            project_root, "tests", "test_data", "pdf_samples", "multi_page_document.pdf"
        )

        if os.path.exists(pdf_path):
            pages_processed = 0
            for page_result in processor.process_with_generator(pdf_path):
                pages_processed += 1
                assert "page" in page_result

                if page_result["success"]:
                    assert "text" in page_result
                    assert "confidence" in page_result

                # Stop after 2 pages for test speed
                if pages_processed >= 2:
                    break

            assert pages_processed >= 2


class TestOCRCoordinator:
    """
    Test the enhanced OCR coordinator with page processor integration.
    """

    def test_coordinator_initialization(self):
        """
        Test OCR coordinator initializes with all components.
        """
        coordinator = OCRCoordinator()

        assert coordinator.loader is not None
        assert coordinator.validator is not None
        assert coordinator.rasterizer is not None
        assert coordinator.engine is not None
        assert coordinator.postprocessor is not None

        # Check if page processor is available
        if hasattr(coordinator, "page_processor"):
            assert coordinator.page_processor is not None

    @patch("os.path.getsize")
    def test_large_file_routing(self, mock_getsize):
        """
        Test that large files are routed to page processor.
        """
        coordinator = OCRCoordinator()

        # Mock a 15MB file (should trigger page processor)
        mock_getsize.return_value = 15 * 1024 * 1024

        with patch.object(coordinator, "_extract_with_page_processor") as mock_page_proc:
            mock_page_proc.return_value = {
                "success": True,
                "text": "Extracted text",
                "method": "page_by_page_ocr",
            }

            # This should use page processor for large file
            with patch.object(coordinator.validator, "should_use_ocr") as mock_validator:
                mock_validator.return_value = {"success": True, "use_ocr": True}

                result = coordinator._extract_with_ocr("large_file.pdf")

                # Verify page processor was called
                if coordinator.page_processor:
                    mock_page_proc.assert_called_once()
                    assert result["method"] == "page_by_page_ocr"

    @patch("os.path.getsize")
    def test_small_file_standard_processing(self, mock_getsize):
        """
        Test that small files use standard processing.
        """
        coordinator = OCRCoordinator()

        # Mock a 5MB file (should not trigger page processor)
        mock_getsize.return_value = 5 * 1024 * 1024

        with patch.object(coordinator.rasterizer, "convert_pdf_to_images") as mock_raster:
            mock_raster.return_value = {"success": True, "images": [MagicMock()]}  # Mock image

            with patch.object(coordinator.engine, "extract_text_from_image") as mock_engine:
                mock_engine.return_value = {
                    "success": True,
                    "text": "Sample text",
                    "confidence": 0.95,
                }

                result = coordinator._extract_with_ocr("small_file.pdf")

                # Should use standard OCR, not page processor
                assert result["method"] == "ocr"
                mock_raster.assert_called_once()


class TestPDFProcessor:
    """
    Test the main PDF processor with new OCR integration.
    """

    def test_processor_with_ocr_coordinator(self):
        """
        Test that PDF processor properly uses OCR coordinator.
        """
        processor = PDFProcessor()

        assert processor.ocr_coordinator is not None

        # Validate dependencies
        deps = processor.validate_dependencies()
        assert "ocr" in deps
        assert "pdf" in deps
        assert "legal_metadata" in deps

    def test_should_use_ocr_delegation(self):
        """
        Test that should_use_ocr delegates to coordinator.
        """
        processor = PDFProcessor()

        pdf_path = os.path.join(
            project_root, "tests", "test_data", "pdf_samples", "business_proposal.pdf"
        )

        if os.path.exists(pdf_path):
            result = processor.should_use_ocr(pdf_path)
            assert "success" in result
            # Should have OCR analysis results
            if result["success"]:
                assert "is_scanned" in result or "use_ocr" in result

    def test_progressive_processing_trigger(self):
        """
        Test that large files trigger progressive processing.
        """
        processor = PDFProcessor()

        # Create a mock large file path
        with patch.object(processor, "_get_file_size_mb") as mock_size:
            mock_size.return_value = 60  # 60MB file

            # Check if progressive processing would be triggered
            requires_progressive = processor._requires_progressive_processing("large.pdf")
            assert requires_progressive is True

            # Small file should not trigger progressive
            mock_size.return_value = 10
            requires_progressive = processor._requires_progressive_processing("small.pdf")
            assert requires_progressive is False

    def test_timeout_calculation(self):
        """
        Test timeout calculation based on file size.
        """
        processor = PDFProcessor()

        with patch.object(processor, "_get_file_size_mb") as mock_size:
            # Large file should get extended timeout
            mock_size.return_value = 150  # 150MB
            timeout = processor._calculate_timeout("large.pdf", 300)
            assert timeout > 300  # Should be multiplied

            # Normal file gets standard timeout
            mock_size.return_value = 50
            timeout = processor._calculate_timeout("normal.pdf", 300)
            assert timeout == 300
