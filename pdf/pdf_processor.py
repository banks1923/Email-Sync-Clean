"""
PDF text extraction and chunking functionality.
"""

from typing import Any

from loguru import logger

try:
    import pypdf
except ImportError:
    pypdf = None


class PDFProcessor:
    """
    Handles PDF text extraction and chunking operations.
    """

    def __init__(self, chunk_size: int = 900, chunk_overlap: int = 100) -> None:
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        # Logger is now imported globally from loguru

    def validate_dependencies(self) -> dict[str, Any]:
        """
        Validate required dependencies.
        """
        if pypdf is None:
            return {
                "success": False,
                "error": "pypdf not installed. Run: pip install pypdf",
            }
        return {"success": True}

    def extract_text_from_pdf(self, pdf_path: str) -> dict[str, Any]:
        """
        Extract text from PDF using pypdf.
        """
        try:
            text_content = []

            with open(pdf_path, "rb") as file:
                pdf_reader = pypdf.PdfReader(file)

                for page_num, page in enumerate(pdf_reader.pages):
                    try:
                        page_text = page.extract_text()
                        if page_text.strip():
                            text_content.append(page_text)
                    except Exception as e:
                        logger.warning(
                            f"Failed to extract page {page_num} from {pdf_path}: {str(e)}"
                        )
                        continue

            if not text_content:
                return {"success": False, "error": "No text content could be extracted"}

            full_text = "\n\n".join(text_content)
            return {"success": True, "text": full_text}

        except Exception as e:
            return {"success": False, "error": f"Text extraction failed: {str(e)}"}

    def chunk_text(self, text: str) -> list[str]:
        """
        Chunk text into smaller pieces for processing.
        """
        if not text or not text.strip():
            return []

        chunks = []
        text = text.strip()
        start = 0

        while start < len(text):
            end = self._find_chunk_end(text, start)
            chunk = text[start:end].strip()

            if chunk:
                chunks.append(chunk)

            start = self._calculate_next_start(start, end)

        return chunks

    def _find_chunk_end(self, text: str, start: int) -> int:
        """
        Find optimal end position for current chunk.
        """
        end = start + self.chunk_size

        if end >= len(text):
            return len(text)

        # Find best break point
        optimal_end = self._find_sentence_break(text, start, end)
        if optimal_end > start:
            return optimal_end

        optimal_end = self._find_paragraph_break(text, start, end)
        if optimal_end > start:
            return optimal_end

        return self._find_word_break(text, start, end)

    def _find_sentence_break(self, text: str, start: int, end: int) -> int:
        """
        Find sentence ending within chunk range.
        """
        sentence_end = text.rfind(". ", start, end)
        if sentence_end > start + self.chunk_size // 2:
            return sentence_end + 2
        return -1

    def _find_paragraph_break(self, text: str, start: int, end: int) -> int:
        """
        Find paragraph break within chunk range.
        """
        para_end = text.rfind("\n\n", start, end)
        if para_end > start + self.chunk_size // 2:
            return para_end + 2
        return -1

    def _find_word_break(self, text: str, start: int, end: int) -> int:
        """
        Find word boundary within chunk range.
        """
        word_end = text.rfind(" ", start, end)
        if word_end > start + self.chunk_size // 2:
            return word_end + 1
        return end

    def _calculate_next_start(self, start: int, end: int) -> int:
        """
        Calculate next chunk start position with overlap.
        """
        return max(start + 1, end - self.chunk_overlap)
