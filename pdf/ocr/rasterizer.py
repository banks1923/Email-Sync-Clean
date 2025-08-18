"""PDF rasterizer module - converts PDF pages to images."""

from typing import Any

from loguru import logger

try:
    import pdf2image

    PDF2IMAGE_AVAILABLE = True
except ImportError:
    PDF2IMAGE_AVAILABLE = False

# Logger is now imported globally from loguru


class PDFRasterizer:
    """Converts PDF pages to images for OCR processing."""

    def __init__(self, dpi: int = 300):
        """
        Initialize rasterizer with DPI setting.

        Args:
            dpi: Resolution for PDF to image conversion
        """
        self.dpi = dpi
        self.available = PDF2IMAGE_AVAILABLE

    def convert_pdf_to_images(
        self, pdf_path: str, first_page: int = None, last_page: int = None
    ) -> dict[str, Any]:
        """
        Convert PDF pages to images.

        Args:
            pdf_path: Path to PDF file
            first_page: First page to convert (1-indexed)
            last_page: Last page to convert (inclusive)

        Returns:
            Dict with success status and images list
        """
        if not self.available:
            return {"success": False, "error": "pdf2image not available", "images": []}

        try:
            logger.info(f"Converting PDF to images at {self.dpi} DPI")

            # Convert PDF to PIL images
            images = pdf2image.convert_from_path(
                pdf_path, dpi=self.dpi, first_page=first_page, last_page=last_page
            )

            logger.info(f"Converted {len(images)} pages to images")

            return {"success": True, "images": images, "page_count": len(images), "dpi": self.dpi}

        except Exception as e:
            logger.error(f"Error converting PDF to images: {e}")
            return {"success": False, "error": str(e), "images": []}

    def convert_single_page(self, pdf_path: str, page_num: int) -> dict[str, Any]:
        """Convert a single PDF page to image."""
        return self.convert_pdf_to_images(pdf_path, page_num, page_num)

    def estimate_memory_usage(self, page_count: int) -> dict[str, Any]:
        """
        Estimate memory usage for conversion.

        Args:
            page_count: Number of pages to convert

        Returns:
            Dict with memory estimates
        """
        # Rough estimate: A4 page at 300 DPI = ~33MB uncompressed
        bytes_per_page = (8.5 * self.dpi) * (11 * self.dpi) * 3  # RGB
        total_mb = (bytes_per_page * page_count) / (1024 * 1024)

        return {
            "pages": page_count,
            "dpi": self.dpi,
            "estimated_mb": round(total_mb, 1),
            "warning": total_mb > 1000,  # Warn if >1GB
        }

    def validate_settings(self) -> dict[str, Any]:
        """Validate rasterizer settings."""
        warnings = []

        if self.dpi > 600:
            warnings.append(f"DPI {self.dpi} is very high, may use excessive memory")
        elif self.dpi < 200:
            warnings.append(f"DPI {self.dpi} is low, OCR quality may suffer")

        return {
            "dpi": self.dpi,
            "available": self.available,
            "warnings": warnings,
            "optimal_dpi_range": "200-400",
        }
