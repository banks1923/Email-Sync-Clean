"""
Text-only PDF processor - replaces OCR functionality.
Handles born-digital PDFs with embedded text using pypdf.
For scanned PDFs, returns an error indicating external OCR is needed.
"""

from typing import Any
from pathlib import Path
from loguru import logger

try:
    import pypdf
except ImportError:
    pypdf = None


class TextOnlyProcessor:
    """
    Simplified PDF processor for text extraction without OCR.
    """
    
    def __init__(self):
        """Initialize the text-only processor."""
        pass
    
    def process_pdf_with_ocr(self, pdf_path: str) -> dict[str, Any]:
        """
        Legacy method name kept for compatibility.
        Only extracts text from born-digital PDFs.
        """
        return self.process_pdf(pdf_path)
    
    def process_pdf(self, pdf_path: str) -> dict[str, Any]:
        """
        Process PDF by extracting embedded text.
        Returns error for scanned PDFs that need OCR.
        """
        if not pypdf:
            return {
                "success": False,
                "error": "pypdf not installed. Run: pip install pypdf",
                "ocr_used": False
            }
        
        pdf_path = Path(pdf_path)
        if not pdf_path.exists():
            return {
                "success": False,
                "error": f"File not found: {pdf_path}",
                "ocr_used": False
            }
        
        try:
            text_content = []
            
            with open(pdf_path, "rb") as file:
                pdf_reader = pypdf.PdfReader(file)
                page_count = len(pdf_reader.pages)
                
                for page_num, page in enumerate(pdf_reader.pages):
                    try:
                        page_text = page.extract_text()
                        if page_text and page_text.strip():
                            text_content.append(page_text)
                    except Exception as e:
                        logger.debug(f"Failed to extract text from page {page_num}: {e}")
                        continue
            
            # Check if we extracted meaningful text
            full_text = "\n\n".join(text_content).strip()
            
            if not full_text or len(full_text) < 50:
                # This is likely a scanned PDF that needs OCR
                return {
                    "success": False,
                    "error": "PDF appears to be scanned (no embedded text). External OCR service required.",
                    "ocr_used": False,
                    "is_scanned": True,
                    "page_count": page_count
                }
            
            # Successfully extracted text
            return {
                "success": True,
                "text": full_text,
                "ocr_used": False,
                "extraction_method": "text",
                "page_count": page_count,
                "confidence": 1.0  # Text extraction is always 100% confident
            }
            
        except Exception as e:
            logger.error(f"Failed to process PDF {pdf_path}: {e}")
            return {
                "success": False,
                "error": f"PDF processing failed: {str(e)}",
                "ocr_used": False
            }