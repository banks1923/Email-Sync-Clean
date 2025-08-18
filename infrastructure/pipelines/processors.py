"""Document Processors for Pipeline

Base class and implementations for processing different document types.
"""

from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any

from loguru import logger

# Logger is now imported globally from loguru


class DocumentProcessor(ABC):
    """Abstract base class for document processors."""

    @abstractmethod
    def process(self, content: str, metadata: dict[str, Any]) -> tuple[str, dict[str, Any]]:
        """Process document content and metadata.

        Args:
            content: Raw document content
            metadata: Document metadata

        Returns:
            Tuple of (processed_content, updated_metadata)
        """

    @abstractmethod
    def validate(self, content: str, metadata: dict[str, Any]) -> tuple[bool, str | None]:
        """Validate document before processing.

        Args:
            content: Document content
            metadata: Document metadata

        Returns:
            Tuple of (is_valid, error_message)
        """

    def extract_metadata(self, content: str) -> dict[str, Any]:
        """Extract basic metadata from content.

        Args:
            content: Document content

        Returns:
            Dict: Extracted metadata
        """
        return {
            "content_length": len(content),
            "word_count": len(content.split()),
            "line_count": len(content.splitlines()),
            "extracted_at": datetime.utcnow().isoformat() + "Z",
        }


class EmailProcessor(DocumentProcessor):
    """Processor for email documents."""

    def process(self, content: str, metadata: dict[str, Any]) -> tuple[str, dict[str, Any]]:
        """Process email content.

        Args:
            content: Email content (headers + body)
            metadata: Email metadata

        Returns:
            Tuple of (processed_content, updated_metadata)
        """
        # Extract email components
        lines = content.splitlines()
        headers = {}
        body_start = 0

        # Parse headers
        for i, line in enumerate(lines):
            if not line.strip():
                body_start = i + 1
                break
            if ":" in line and not line.startswith(" "):
                key, value = line.split(":", 1)
                headers[key.strip()] = value.strip()

        # Extract body
        body = "\n".join(lines[body_start:]) if body_start < len(lines) else ""

        # Update metadata
        metadata.update(
            {
                "content_type": "email",
                "subject": headers.get("Subject", "No Subject"),
                "from": headers.get("From", ""),
                "to": headers.get("To", ""),
                "date": headers.get("Date", ""),
                "message_id": headers.get("Message-ID", ""),
                "headers": headers,
            }
        )

        # Add basic metadata
        metadata.update(self.extract_metadata(body))

        # Process content (clean up formatting)
        processed_content = body.strip()

        # Remove excessive blank lines
        while "\n\n\n" in processed_content:
            processed_content = processed_content.replace("\n\n\n", "\n\n")

        logger.info(f"Processed email: {metadata.get('subject', 'Unknown')}")
        return processed_content, metadata

    def validate(self, content: str, metadata: dict[str, Any]) -> tuple[bool, str | None]:
        """Validate email content.

        Args:
            content: Email content
            metadata: Email metadata

        Returns:
            Tuple of (is_valid, error_message)
        """
        if not content:
            return False, "Empty email content"

        # Check for basic email structure
        if "From:" not in content and "from" not in metadata:
            return False, "Missing From header"

        if "Subject:" not in content and "subject" not in metadata:
            logger.warning("Email missing subject header")

        return True, None


class PDFProcessor(DocumentProcessor):
    """Processor for PDF documents."""

    def process(self, content: str, metadata: dict[str, Any]) -> tuple[str, dict[str, Any]]:
        """Process PDF text content.

        Args:
            content: Extracted PDF text
            metadata: PDF metadata

        Returns:
            Tuple of (processed_content, updated_metadata)
        """
        # Update metadata
        metadata.update(
            {"content_type": "pdf", "processed_at": datetime.utcnow().isoformat() + "Z"}
        )

        # Add basic metadata
        metadata.update(self.extract_metadata(content))

        # Process content
        processed_content = content.strip()

        # Clean up common PDF extraction artifacts
        processed_content = self._clean_pdf_artifacts(processed_content)

        # Extract title if possible (first non-empty line)
        lines = processed_content.splitlines()
        for line in lines[:10]:  # Check first 10 lines
            if line.strip() and len(line.strip()) > 5:
                metadata["extracted_title"] = line.strip()
                break

        logger.info(f"Processed PDF: {metadata.get('filename', 'Unknown')}")
        return processed_content, metadata

    def validate(self, content: str, metadata: dict[str, Any]) -> tuple[bool, str | None]:
        """Validate PDF content.

        Args:
            content: PDF text content
            metadata: PDF metadata

        Returns:
            Tuple of (is_valid, error_message)
        """
        if not content:
            return False, "Empty PDF content"

        # Check minimum content length
        if len(content.strip()) < 50:
            return False, "PDF content too short (possible extraction failure)"

        # Check for extraction errors
        if content.count("�") > len(content) * 0.1:
            return False, "Too many encoding errors in PDF extraction"

        return True, None

    def _clean_pdf_artifacts(self, text: str) -> str:
        """Clean common PDF extraction artifacts.

        Args:
            text: Raw PDF text

        Returns:
            str: Cleaned text
        """
        # Remove page numbers (common patterns)
        import re

        # Remove standalone page numbers (including "Page X" format)
        text = re.sub(r"^\d+\s*$", "", text, flags=re.MULTILINE)
        text = re.sub(r"^Page\s+\d+\s*$", "", text, flags=re.MULTILINE | re.IGNORECASE)

        # Remove common headers/footers
        text = re.sub(r"^Page \d+ of \d+\s*$", "", text, flags=re.MULTILINE)

        # Fix hyphenation at line breaks
        text = re.sub(r"(\w+)-\n(\w+)", r"\1\2", text)

        # Remove excessive whitespace
        text = re.sub(r"\n\s*\n\s*\n+", "\n\n", text)

        return text.strip()


class TranscriptionProcessor(DocumentProcessor):
    """Processor for transcription documents."""

    def process(self, content: str, metadata: dict[str, Any]) -> tuple[str, dict[str, Any]]:
        """Process transcription content.

        Args:
            content: Transcription text
            metadata: Transcription metadata

        Returns:
            Tuple of (processed_content, updated_metadata)
        """
        # Update metadata
        metadata.update(
            {"content_type": "transcription", "processed_at": datetime.utcnow().isoformat() + "Z"}
        )

        # Add basic metadata
        metadata.update(self.extract_metadata(content))

        # Process content
        processed_content = content.strip()

        # Format timestamps if present
        processed_content = self._format_timestamps(processed_content)

        # Add speaker labels if not present
        if not any(label in processed_content for label in ["Speaker:", "[Speaker", "SPEAKER"]):
            processed_content = f"[Speaker 1]\n{processed_content}"

        logger.info(f"Processed transcription: {metadata.get('filename', 'Unknown')}")
        return processed_content, metadata

    def validate(self, content: str, metadata: dict[str, Any]) -> tuple[bool, str | None]:
        """Validate transcription content.

        Args:
            content: Transcription text
            metadata: Transcription metadata

        Returns:
            Tuple of (is_valid, error_message)
        """
        if not content:
            return False, "Empty transcription content"

        # Check minimum content length
        if len(content.strip()) < 20:
            return False, "Transcription too short"

        return True, None

    def _format_timestamps(self, text: str) -> str:
        """Format timestamps in transcription.

        Args:
            text: Raw transcription text

        Returns:
            str: Text with formatted timestamps
        """
        import re

        # Format [00:00:00] timestamps
        text = re.sub(r"\[(\d{2}:\d{2}:\d{2})\]", r"\n[\1]\n", text)

        # Format 00:00:00 --> 00:00:00 timestamps (SRT format)
        text = re.sub(r"(\d{2}:\d{2}:\d{2})\s*-->\s*(\d{2}:\d{2}:\d{2})", r"\n[\1 - \2]\n", text)

        return text


# Factory function
def get_processor(document_type: str) -> DocumentProcessor:
    """Get appropriate processor for document type.

    Args:
        document_type: Type of document (email, pdf, transcription)

    Returns:
        DocumentProcessor: Appropriate processor instance

    Raises:
        ValueError: If document type is not supported
    """
    processors = {
        "email": EmailProcessor,
        "pdf": PDFProcessor,
        "transcription": TranscriptionProcessor,
        "transcript": TranscriptionProcessor,  # Alias
        "audio": TranscriptionProcessor,  # Alias
    }

    processor_class = processors.get(document_type.lower())
    if not processor_class:
        raise ValueError(f"Unsupported document type: {document_type}")

    return processor_class()
