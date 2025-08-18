"""PDF validation module - determines if PDF needs OCR."""

from typing import Any

from loguru import logger

try:
    import PyPDF2
except ImportError:
    PyPDF2 = None

# Logger is now imported globally from loguru


class PDFValidator:
    """Validates PDFs and determines processing requirements."""

    def __init__(self):
        self.dependencies_valid = self._check_dependencies()

    def _check_dependencies(self) -> bool:
        """Check if required dependencies are available."""
        return PyPDF2 is not None

    def validate_dependencies(self) -> dict[str, Any]:
        """Validate all required dependencies."""
        result = {
            "pypdf2": PyPDF2 is not None,
            "ocr_available": self._check_ocr_dependencies(),
            "cv2_available": self._check_cv2_dependencies(),
        }

        result["all_available"] = all(result.values())
        return result

    def _check_ocr_dependencies(self) -> bool:
        """Check OCR dependencies."""
        try:
            import pdf2image  # noqa: F401
            import pytesseract  # noqa: F401
            from PIL import Image  # noqa: F401

            return True
        except ImportError:
            return False

    def _check_cv2_dependencies(self) -> bool:
        """Check OpenCV dependencies."""
        try:
            import cv2  # noqa: F401
            import numpy as np  # noqa: F401

            return True
        except ImportError:
            return False

    def is_scanned_pdf(self, pdf_path: str) -> tuple[bool, float]:
        """
        Determine if PDF is scanned by checking text content.

        Returns:
            Tuple[bool, float]: (is_scanned, confidence)
        """
        if not PyPDF2:
            logger.warning("PyPDF2 not available, assuming PDF is scanned")
            return True, 0.5

        try:
            total_chars = 0
            page_count = 0

            with open(pdf_path, "rb") as file:
                reader = PyPDF2.PdfReader(file)
                page_count = len(reader.pages)

                if page_count == 0:
                    return True, 1.0

                # Sample first few pages
                sample_pages = min(5, page_count)
                for i in range(sample_pages):
                    try:
                        page = reader.pages[i]
                        text = page.extract_text() or ""
                        total_chars += len(text.strip())
                    except Exception:
                        continue

            # Calculate average chars per page
            avg_chars = total_chars / sample_pages if sample_pages > 0 else 0

            # Less than 100 chars per page likely means scanned
            is_scanned = avg_chars < 100
            confidence = 1.0 - min(avg_chars / 1000, 1.0)

            logger.info(
                f"PDF analysis: {avg_chars:.0f} chars/page, "
                f"scanned={is_scanned}, confidence={confidence:.2f}"
            )

            return is_scanned, confidence

        except Exception as e:
            logger.error(f"Error analyzing PDF: {e}")
            return True, 0.5  # Assume scanned on error

    def should_use_ocr(self, pdf_path: str, force_ocr: bool = False) -> dict[str, Any]:
        """Determine if OCR should be used for PDF processing."""
        if force_ocr:
            return {
                "success": True,
                "use_ocr": True,
                "reason": "OCR forced by user",
                "confidence": 1.0,
            }

        try:
            is_scanned, confidence = self.is_scanned_pdf(pdf_path)

            return {
                "success": True,
                "use_ocr": is_scanned,
                "is_scanned": is_scanned,
                "confidence": confidence,
                "reason": "Scanned PDF detected" if is_scanned else "Text PDF detected",
            }

        except Exception as e:
            logger.error(f"Error determining OCR need: {e}")
            return {
                "success": False,
                "error": str(e),
                "use_ocr": True,  # Default to OCR on error
                "confidence": 0.0,
            }
