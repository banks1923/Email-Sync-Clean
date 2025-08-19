"""
Text document processor for TXT files.

Handles plain text files with encoding detection.
"""

from pathlib import Path
from typing import Any

import chardet
from loguru import logger

from .base_processor import BaseProcessor


class TextProcessor(BaseProcessor):
    """Processes plain text documents."""

    def __init__(self):
        """Initialize text processor."""
        super().__init__()
        self.format_type = "txt"
        self.supported_encodings = ["utf-8", "ascii", "latin-1", "cp1252", "utf-16"]

    def extract_text(self, file_path: Path) -> str:
        """
        Extract text from plain text file with encoding detection.

        Args:
            file_path: Path to text file

        Returns:
            Extracted text content
        """
        # Try UTF-8 first (most common)
        try:
            with open(file_path, encoding="utf-8") as f:
                content = f.read()
                logger.info(f"Read {file_path.name} as UTF-8")
                return self._normalize_text(content)
        except UnicodeDecodeError:
            pass

        # Detect encoding
        encoding = self._detect_encoding(file_path)

        if encoding:
            try:
                with open(file_path, encoding=encoding) as f:
                    content = f.read()
                    logger.info(f"Read {file_path.name} as {encoding}")
                    return self._normalize_text(content)
            except Exception as e:
                logger.error(f"Failed to read with detected encoding {encoding}: {e}")

        # Last resort - try with errors='ignore'
        try:
            with open(file_path, encoding="utf-8", errors="ignore") as f:
                content = f.read()
                logger.warning(f"Read {file_path.name} with errors ignored")
                return self._normalize_text(content)
        except Exception as e:
            logger.error(f"Failed to read text file: {e}")
            raise

    def _detect_encoding(self, file_path: Path) -> str:
        """
        Detect file encoding using chardet.

        Args:
            file_path: Path to file

        Returns:
            Detected encoding name
        """
        try:
            with open(file_path, "rb") as f:
                raw_data = f.read(10000)  # Read first 10KB for detection

            result = chardet.detect(raw_data)
            encoding = result.get("encoding")
            confidence = result.get("confidence", 0)

            if encoding and confidence > 0.7:
                logger.info(f"Detected encoding {encoding} with {confidence:.2f} confidence")
                return encoding.lower()

        except Exception as e:
            logger.error(f"Encoding detection failed: {e}")

        return "utf-8"  # Default fallback

    def _normalize_text(self, content: str) -> str:
        """
        Normalize text content.

        Args:
            content: Raw text content

        Returns:
            Normalized text
        """
        # Normalize line endings
        content = content.replace("\r\n", "\n").replace("\r", "\n")

        # Remove null bytes
        content = content.replace("\x00", "")

        # Strip trailing whitespace from lines
        lines = [line.rstrip() for line in content.split("\n")]

        # Remove excessive blank lines (max 2 consecutive)
        normalized_lines = []
        blank_count = 0

        for line in lines:
            if not line:
                blank_count += 1
                if blank_count <= 2:
                    normalized_lines.append(line)
            else:
                blank_count = 0
                normalized_lines.append(line)

        return "\n".join(normalized_lines)

    def extract_metadata(self, file_path: Path) -> dict[str, Any]:
        """
        Extract metadata from text file.

        Args:
            file_path: Path to text file

        Returns:
            Enhanced metadata for text files
        """
        # Get base metadata
        metadata = super().extract_metadata(file_path)

        # Add text-specific metadata
        try:
            # Detect encoding
            encoding = self._detect_encoding(file_path)
            metadata["encoding"] = encoding

            # Check for special formats
            with open(file_path, encoding=encoding, errors="ignore") as f:
                first_lines = [f.readline() for _ in range(5)]

            # Check if it might be a log file
            if any("ERROR" in line or "WARNING" in line or "INFO" in line for line in first_lines):
                metadata["text_type"] = "log"
            # Check if it might be CSV
            elif any("," in line for line in first_lines) and len(first_lines[0].split(",")) > 3:
                metadata["text_type"] = "csv_like"
            # Check if it might be code
            elif any(
                line.strip().startswith(("#", "//", "/*", "import", "from", "def", "class"))
                for line in first_lines
            ):
                metadata["text_type"] = "code"
            else:
                metadata["text_type"] = "plain"

        except Exception as e:
            logger.error(f"Failed to extract text metadata: {e}")
            metadata["text_type"] = "unknown"

        return metadata

    def validate_content(self, content: str) -> bool:
        """
        Validate text content.

        Args:
            content: Extracted text

        Returns:
            True if content is valid
        """
        if not super().validate_content(content):
            return False

        # Additional text-specific validation
        # Check if it's not a binary file mistaken for text
        control_chars = sum(1 for c in content[:1000] if ord(c) < 32 and c not in "\n\r\t")
        if control_chars > 50:  # Too many control characters
            logger.warning("Text file appears to contain binary data")
            return False

        return True
