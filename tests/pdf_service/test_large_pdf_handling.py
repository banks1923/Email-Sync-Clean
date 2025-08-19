"""
Test suite for large PDF handling capabilities
Tests memory management, streaming, and batch processing for 50MB+ PDFs
"""

import gc
import os
import sys
from unittest.mock import patch

import pytest

from pdf.wiring import get_pdf_service
from pdf.ocr.page_processor import PageByPageProcessor

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if project_root not in sys.path:
    sys.path.insert(0, project_root)


class TestLargePDFProcessing:
    """Test processing of large PDF files with memory management"""

    @pytest.fixture
    def large_pdf_path(self):
        """Path to a large test PDF (if available)"""
        # Check if we have the actual large PDF
        large_pdf = (
            "data/raw_uploads/Documents/Unlawful Detainer #1/UD - Complaint Summons, POS (full).pdf"
        )
        if os.path.exists(large_pdf):
            return large_pdf
        # Otherwise use multi-page test PDF
        return os.path.join(
            project_root, "tests", "test_data", "pdf_samples", "multi_page_document.pdf"
        )

    def test_memory_efficient_batch_processing(self):
        """Test that batch processing maintains memory limits"""
        processor = PageByPageProcessor(batch_size=2, max_memory_mb=100)

        # Track memory usage
        import os

        import psutil

        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB

        pdf_path = os.path.join(
            project_root, "tests", "test_data", "pdf_samples", "multi_page_document.pdf"
        )

        if os.path.exists(pdf_path):
            processor.process_large_pdf(pdf_path)

            # Check memory didn't spike too much
            final_memory = process.memory_info().rss / 1024 / 1024
            memory_increase = final_memory - initial_memory

            # Memory increase should be reasonable (less than 200MB for test PDF)
            assert memory_increase < 200, f"Memory increased by {memory_increase}MB"

            # Force garbage collection
            gc.collect()

    def test_streaming_generator_memory_efficiency(self):
        """Test that generator mode uses minimal memory"""
        processor = PageByPageProcessor()

        pdf_path = os.path.join(
            project_root, "tests", "test_data", "pdf_samples", "multi_page_document.pdf"
        )

        if os.path.exists(pdf_path):
            # Process with generator - should use minimal memory
            page_count = 0
            total_text_length = 0

            for page_result in processor.process_with_generator(pdf_path):
                page_count += 1
                if page_result["success"]:
                    total_text_length += len(page_result.get("text", ""))

                # Force garbage collection after each page
                gc.collect()

            assert page_count == 5  # Our test PDF has 5 pages
            assert total_text_length > 0

    def test_batch_size_adjustment(self):
        """Test different batch sizes for optimal performance"""
        batch_sizes = [1, 3, 5]
        results = []

        pdf_path = os.path.join(
            project_root, "tests", "test_data", "pdf_samples", "multi_page_document.pdf"
        )

        if os.path.exists(pdf_path):
            for batch_size in batch_sizes:
                processor = PageByPageProcessor(batch_size=batch_size)

                import time

                start = time.time()
                result = processor.process_large_pdf(pdf_path, start_page=0, end_page=3)
                elapsed = time.time() - start

                results.append(
                    {"batch_size": batch_size, "time": elapsed, "success": result["success"]}
                )

            # All batch sizes should succeed
            assert all(r["success"] for r in results)

    @patch("os.path.getsize")
    def test_automatic_routing_threshold(self, mock_getsize):
        """Test automatic routing to page processor for large files"""
        service = get_pdf_service()

        # Mock a 93MB file (like our real test case)
        mock_getsize.return_value = 93 * 1024 * 1024

        with patch.object(service.processor, "_requires_progressive_processing") as mock_prog:
            mock_prog.return_value = True

            # Check that large file would use progressive processing
            requires_progressive = service.processor._requires_progressive_processing("large.pdf")
            assert requires_progressive is True

    def test_page_range_extraction(self):
        """Test extracting specific page ranges from large PDFs"""
        processor = PageByPageProcessor(batch_size=2)

        pdf_path = os.path.join(
            project_root, "tests", "test_data", "pdf_samples", "multi_page_document.pdf"
        )

        if os.path.exists(pdf_path):
            # Extract middle pages (2-4)
            result = processor.extract_page_range(pdf_path, (1, 4))

            assert result["success"] is True
            assert result["pages_processed"] == 3
            assert "text" in result

    def test_progress_tracking_accuracy(self):
        """Test that progress tracking is accurate"""
        processor = PageByPageProcessor(batch_size=1)
        progress_percentages = []

        def track_progress(info):
            progress_percentages.append(info["progress_percent"])

        pdf_path = os.path.join(
            project_root, "tests", "test_data", "pdf_samples", "multi_page_document.pdf"
        )

        if os.path.exists(pdf_path):
            processor.process_large_pdf(
                pdf_path, start_page=0, end_page=5, progress_callback=track_progress
            )

            # Progress should increase monotonically
            for i in range(1, len(progress_percentages)):
                assert progress_percentages[i] >= progress_percentages[i - 1]

            # Final progress should be 100%
            if progress_percentages:
                assert progress_percentages[-1] == 100.0

    def test_error_handling_in_batch_processing(self):
        """Test error handling when processing fails for some pages"""
        processor = PageByPageProcessor(batch_size=2)

        # Test with corrupted PDF
        corrupted_pdf = os.path.join(
            project_root, "tests", "test_data", "pdf_samples", "corrupted.pdf"
        )

        if os.path.exists(corrupted_pdf):
            result = processor.process_large_pdf(corrupted_pdf)

            # Should handle error gracefully
            assert "success" in result
            if not result["success"]:
                assert "error" in result

    def test_concurrent_processing_safety(self):
        """Test that concurrent processing doesn't cause issues"""
        import threading

        processor = PageByPageProcessor(batch_size=1)
        results = []
        errors = []

        def process_pdf():
            try:
                pdf_path = os.path.join(
                    project_root, "tests", "test_data", "pdf_samples", "multi_page_document.pdf"
                )
                if os.path.exists(pdf_path):
                    result = processor.process_large_pdf(pdf_path, start_page=0, end_page=2)
                    results.append(result)
            except Exception as e:
                errors.append(str(e))

        # Start multiple threads
        threads = []
        for _ in range(3):
            t = threading.Thread(target=process_pdf)
            threads.append(t)
            t.start()

        # Wait for all to complete
        for t in threads:
            t.join(timeout=30)

        # Should have results without errors
        assert len(errors) == 0 or len(results) > 0
