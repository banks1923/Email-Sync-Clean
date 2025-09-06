"""Enhanced PDF processor for text extraction (without OCR).

Handles text-based PDFs and legal metadata extraction.
"""

from typing import Any

from loguru import logger

from .pdf_processor import PDFProcessor

try:
    from ..vector.legal_metadata_extractor import LegalMetadataExtractor
    LEGAL_METADATA_AVAILABLE = True
except ImportError:
    LEGAL_METADATA_AVAILABLE = False


class EnhancedPDFProcessor:
    """PDF processor with text extraction and legal metadata capabilities.

    OCR functionality has been removed - handled externally.
    """

    def __init__(
        self, chunk_size: int = 900, chunk_overlap: int = 100
    ) -> None:
        """
        Initialize text processor.
        """
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        
        # Initialize base processor for text extraction
        self.pdf_processor = PDFProcessor(chunk_size, chunk_overlap)
        
        if LEGAL_METADATA_AVAILABLE:
            self.legal_extractor = LegalMetadataExtractor()
        else:
            self.legal_extractor = None
            logger.debug("Legal metadata extractor not available")

    def extract_and_chunk_pdf(self, pdf_path: str) -> dict[str, Any]:
        """
        Extract text from PDF and chunk it.
        """
        # Extract text using pypdf
        extraction_result = self.pdf_processor.extract_text_from_pdf(pdf_path)
        
        if not extraction_result["success"]:
            # Check if this might be a scanned PDF
            error_msg = extraction_result.get("error", "")
            if "No text content" in error_msg:
                return {
                    "success": False,
                    "error": "PDF appears to be scanned (no embedded text). External OCR service required.",
                    "is_scanned": True
                }
            return extraction_result
        
        # Chunk the text
        text = extraction_result["text"]
        chunks_list = self.pdf_processor.chunk_text(text)
        
        if not chunks_list:
            return {
                "success": False,
                "error": "No chunks could be created from extracted text"
            }
        
        # Format chunks for storage
        chunks = []
        for idx, chunk_text in enumerate(chunks_list):
            chunk = {
                "chunk_id": f"chunk_{idx}",
                "text": chunk_text,
                "chunk_index": idx,
                "extraction_method": "text"
            }
            chunks.append(chunk)
        
        result = {
            "success": True,
            "chunks": chunks,
            "extraction_method": "text",
            "total_chunks": len(chunks)
        }
        
        # Extract legal metadata if available
        if self.legal_extractor:
            try:
                legal_metadata = self._extract_legal_metadata(text)
                if legal_metadata:
                    result["legal_metadata"] = legal_metadata
            except Exception as e:
                logger.warning(f"Failed to extract legal metadata: {e}")
        
        return result
    
    def _extract_legal_metadata(self, text: str) -> dict[str, Any]:
        """
        Extract legal metadata from text.
        """
        if not self.legal_extractor or not text:
            return {}
        
        try:
            metadata = self.legal_extractor.extract_metadata(text)
            
            # Clean up metadata for storage
            cleaned_metadata = {}
            for key, value in metadata.items():
                if value is not None:
                    if isinstance(value, (list, dict)):
                        if value:  # Only include non-empty collections
                            cleaned_metadata[key] = value
                    else:
                        cleaned_metadata[key] = value
            
            return cleaned_metadata
        except Exception as e:
            logger.error(f"Legal metadata extraction failed: {e}")
            return {}