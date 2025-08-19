"""
Base processor for document processing.

Simple pattern following CLAUDE.md principles - no complex inheritance.
"""

from datetime import datetime
from pathlib import Path
from typing import Any

from loguru import logger


class BaseProcessor:
    """Base document processor with common functionality."""

    def __init__(self):
        """Initialize processor."""
        self.format_type = "unknown"

    def process(self, file_path: Path) -> dict[str, Any]:
        """
        Process document file.

        Args:
            file_path: Path to document

        Returns:
            Processing result with content and metadata
        """
        try:
            # Validate file
            if not file_path.exists():
                return {"success": False, "error": "File not found"}

            # Extract content
            content = self.extract_text(file_path)

            # Extract metadata
            metadata = self.extract_metadata(file_path)

            # Calculate metrics
            metrics = self.calculate_metrics(content)

            return {
                "success": True,
                "content": content,
                "metadata": metadata,
                "metrics": metrics,
                "format": self.format_type,
                "processed_at": datetime.now().isoformat(),
            }

        except Exception as e:
            logger.error(f"Processing failed for {file_path}: {e}")
            return {"success": False, "error": str(e)}

    def extract_text(self, file_path: Path) -> str:
        """
        Extract text content from file.
        Override in subclasses.

        Args:
            file_path: Path to document

        Returns:
            Extracted text
        """
        raise NotImplementedError("Subclasses must implement extract_text")

    def extract_metadata(self, file_path: Path) -> dict[str, Any]:
        """
        Extract metadata from file.

        Args:
            file_path: Path to document

        Returns:
            File metadata
        """
        stat = file_path.stat()

        return {
            "filename": file_path.name,
            "size_bytes": stat.st_size,
            "created_at": datetime.fromtimestamp(stat.st_ctime).isoformat(),
            "modified_at": datetime.fromtimestamp(stat.st_mtime).isoformat(),
            "extension": file_path.suffix.lower(),
        }

    def calculate_metrics(self, content: str) -> dict[str, Any]:
        """
        Calculate content metrics.

        Args:
            content: Text content

        Returns:
            Content metrics
        """
        lines = content.split("\n")
        words = content.split()

        return {
            "char_count": len(content),
            "word_count": len(words),
            "line_count": len(lines),
            "avg_word_length": sum(len(w) for w in words) / len(words) if words else 0,
            "avg_line_length": len(content) / len(lines) if lines else 0,
        }

    def validate_content(self, content: str) -> bool:
        """
        Validate extracted content.

        Args:
            content: Extracted text

        Returns:
            True if content is valid
        """
        # Basic validation - has content and reasonable length
        if not content or len(content.strip()) < 10:
            return False

        # Check for excessive binary garbage
        non_ascii = sum(1 for c in content if ord(c) > 127)
        if non_ascii / len(content) > 0.3:  # More than 30% non-ASCII
            return False

        return True
