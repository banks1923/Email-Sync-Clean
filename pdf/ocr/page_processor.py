"""Page-by-page processor for memory-efficient OCR of large PDFs."""

from collections.abc import Callable, Generator
from typing import Any

from loguru import logger

from .ocr_engine import OCREngine
from .postprocessor import OCRPostprocessor
from .rasterizer import PDFRasterizer

# Logger is now imported globally from loguru


class PageByPageProcessor:
    """Process large PDFs page by page to manage memory usage."""

    def __init__(self, batch_size: int = 5, max_memory_mb: int = 500):
        """
        Initialize processor with memory constraints.

        Args:
            batch_size: Number of pages to process at once
            max_memory_mb: Maximum memory usage in MB
        """
        self.batch_size = batch_size
        self.max_memory_mb = max_memory_mb
        self.ocr_engine = OCREngine()
        self.postprocessor = OCRPostprocessor()
        self.rasterizer = PDFRasterizer(dpi=400)

    def process_large_pdf(
        self,
        pdf_path: str,
        start_page: int = 0,
        end_page: int | None = None,
        progress_callback: Callable | None = None,
    ) -> dict[str, Any]:
        """
        Process PDF with page range support.

        Args:
            pdf_path: Path to PDF file
            start_page: Starting page (0-indexed)
            end_page: Ending page (exclusive)
            progress_callback: Function to call with progress updates

        Returns:
            Processing result with extracted text
        """
        try:
            # Get total page count
            import PyPDF2

            with open(pdf_path, "rb") as f:
                reader = PyPDF2.PdfReader(f)
                total_pages = len(reader.pages)

            if end_page is None:
                end_page = total_pages
            else:
                end_page = min(end_page, total_pages)

            pages_to_process = end_page - start_page
            page_texts = []
            confidences = []

            # Process in batches
            for batch_start in range(start_page, end_page, self.batch_size):
                batch_end = min(batch_start + self.batch_size, end_page)

                # Convert batch to images
                result = self.rasterizer.convert_pdf_to_images(
                    pdf_path,
                    first_page=batch_start + 1,  # pdf2image uses 1-indexing
                    last_page=batch_end,
                )

                if not result["success"]:
                    logger.error(f"Failed to rasterize pages {batch_start}-{batch_end}")
                    continue

                # Process each image in batch
                for i, image in enumerate(result["images"]):
                    current_page = batch_start + i

                    # Extract text
                    ocr_result = self.ocr_engine.extract_text_from_image(image)
                    if ocr_result["success"]:
                        page_texts.append(ocr_result["text"])
                        confidences.append(ocr_result["confidence"])
                    else:
                        page_texts.append("")
                        confidences.append(0.0)

                    # Report progress
                    if progress_callback:
                        progress = (current_page - start_page + 1) / pages_to_process
                        progress_callback(
                            {
                                "current_page": current_page + 1,
                                "total_pages": total_pages,
                                "progress_percent": int(progress * 100),
                            }
                        )

            # Merge results
            merged_text = self.postprocessor.merge_page_texts(page_texts)
            avg_confidence = sum(confidences) / len(confidences) if confidences else 0.0

            return {
                "success": True,
                "text": merged_text,
                "method": "page_by_page_ocr",
                "pages_processed": len(page_texts),
                "total_pages": total_pages,
                "confidence": avg_confidence,
            }

        except Exception as e:
            logger.error(f"Page-by-page processing failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "method": "page_by_page_ocr",
            }

    def process_with_generator(
        self, pdf_path: str, start_page: int = 0, end_page: int | None = None
    ) -> Generator[dict[str, Any], None, None]:
        """
        Process PDF and yield results page by page.

        Args:
            pdf_path: Path to PDF file
            start_page: Starting page (0-indexed)
            end_page: Ending page (exclusive)

        Yields:
            Dict with page text and metadata
        """
        try:
            # Get total pages
            import PyPDF2

            with open(pdf_path, "rb") as f:
                reader = PyPDF2.PdfReader(f)
                total_pages = len(reader.pages)

            if end_page is None:
                end_page = total_pages
            else:
                end_page = min(end_page, total_pages)

            # Process each page
            for page_num in range(start_page, end_page):
                # Convert single page
                result = self.rasterizer.convert_pdf_to_images(
                    pdf_path,
                    first_page=page_num + 1,
                    last_page=page_num + 1,
                )

                if not result["success"] or not result["images"]:
                    yield {
                        "success": False,
                        "page": page_num + 1,
                        "error": result.get("error", "Failed to convert page"),
                    }
                    continue

                # OCR the page
                ocr_result = self.ocr_engine.extract_text_from_image(result["images"][0])

                yield {
                    "success": ocr_result["success"],
                    "page": page_num + 1,
                    "text": ocr_result.get("text", ""),
                    "confidence": ocr_result.get("confidence", 0.0),
                }

        except Exception as e:
            logger.error(f"Generator processing failed: {e}")
            yield {
                "success": False,
                "error": str(e),
            }
