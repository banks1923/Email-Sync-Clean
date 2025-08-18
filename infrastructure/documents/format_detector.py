"""
Format Detection System

Detects document format using magic bytes and extensions.
"""

from pathlib import Path

from loguru import logger

# Logger is now imported globally from loguru


class FormatDetector:
    """Detects document format from file content and extension."""

    # Magic bytes for common formats
    MAGIC_BYTES = {
        b"%PDF": "pdf",
        b"PK\x03\x04": "docx",  # DOCX is a zip file
        b"PK\x05\x06": "docx",  # Empty DOCX
        b"PK\x07\x08": "docx",  # Spanned DOCX
        b"---\n": "md",  # YAML frontmatter
        b"---\r\n": "md",  # YAML frontmatter Windows
        b"# ": "md",  # Markdown heading
        b"## ": "md",
        b"### ": "md",
    }

    # File extensions mapping
    EXTENSIONS = {
        ".pdf": "pdf",
        ".docx": "docx",
        ".doc": "doc",  # Legacy Word
        ".txt": "txt",
        ".text": "txt",
        ".md": "md",
        ".markdown": "md",
        ".mdown": "md",
        ".mkd": "md",
    }

    def detect_format(self, file_path: Path) -> str | None:
        """
        Detect document format from file.

        Args:
            file_path: Path to document file

        Returns:
            Format string ('pdf', 'docx', 'txt', 'md') or None
        """
        if not file_path.exists():
            logger.error(f"File not found: {file_path}")
            return None

        # Try magic bytes first
        format_from_content = self._detect_by_content(file_path)
        if format_from_content:
            logger.info(f"Detected {format_from_content} format by content for {file_path.name}")
            return format_from_content

        # Fall back to extension
        format_from_ext = self._detect_by_extension(file_path)
        if format_from_ext:
            logger.info(f"Detected {format_from_ext} format by extension for {file_path.name}")
            return format_from_ext

        # Try to detect text file by reading
        if self._is_text_file(file_path):
            logger.info(f"Detected txt format by text analysis for {file_path.name}")
            return "txt"

        logger.warning(f"Could not detect format for {file_path.name}")
        return None

    def _detect_by_content(self, file_path: Path) -> str | None:
        """Detect format by reading file header."""
        try:
            with open(file_path, "rb") as f:
                header = f.read(10)

            # Check each magic byte pattern
            for magic, format_type in self.MAGIC_BYTES.items():
                if header.startswith(magic):
                    return format_type

            return None

        except Exception as e:
            logger.error(f"Error reading file header: {e}")
            return None

    def _detect_by_extension(self, file_path: Path) -> str | None:
        """Detect format by file extension."""
        ext = file_path.suffix.lower()
        return self.EXTENSIONS.get(ext)

    def _is_text_file(self, file_path: Path) -> bool:
        """
        Check if file is plain text by attempting to decode it.

        Args:
            file_path: Path to file

        Returns:
            True if file appears to be text
        """
        try:
            # Read first 1KB
            with open(file_path, "rb") as f:
                sample = f.read(1024)

            # Try to decode as UTF-8
            sample.decode("utf-8")

            # Check for high ratio of printable characters
            printable = sum(1 for b in sample if 32 <= b < 127 or b in (9, 10, 13))
            ratio = printable / len(sample) if sample else 0

            return ratio > 0.8

        except (UnicodeDecodeError, Exception):
            return False

    def is_supported_format(self, file_path: Path) -> bool:
        """
        Check if file format is supported.

        Args:
            file_path: Path to file

        Returns:
            True if format is supported
        """
        format_type = self.detect_format(file_path)
        return format_type in ["pdf", "docx", "txt", "md"]

    def get_supported_extensions(self) -> list:
        """Get list of supported file extensions."""
        return list(self.EXTENSIONS.keys())

    def get_format_info(self, format_type: str) -> dict:
        """
        Get information about a format type.

        Args:
            format_type: Format identifier

        Returns:
            Dictionary with format information
        """
        info = {
            "pdf": {
                "name": "Portable Document Format",
                "extensions": [".pdf"],
                "binary": True,
                "requires_special_handling": True,
                "processor": "PDFProcessor",
            },
            "docx": {
                "name": "Microsoft Word Document",
                "extensions": [".docx"],
                "binary": True,
                "requires_special_handling": True,
                "processor": "DocxProcessor",
            },
            "txt": {
                "name": "Plain Text",
                "extensions": [".txt", ".text"],
                "binary": False,
                "requires_special_handling": False,
                "processor": "TextProcessor",
            },
            "md": {
                "name": "Markdown",
                "extensions": [".md", ".markdown", ".mdown", ".mkd"],
                "binary": False,
                "requires_special_handling": False,
                "processor": "MarkdownProcessor",
            },
        }

        return info.get(format_type, {})
