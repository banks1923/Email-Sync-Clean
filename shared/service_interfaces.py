from abc import ABC, abstractmethod
from typing import Any, Protocol


class FeatureUnavailable(Exception):
    """Raised when an optional feature is not wired"""


class IEmbedder(ABC):
    """Abstract interface for embedding providers."""

    @abstractmethod
    def generate_embedding(self, text: str) -> list[float]:
        """Generate a single embedding for the given text.

        Args:
            text: Input text to embed

        Returns:
            List of float values representing the embedding
        """

    @abstractmethod
    def generate_batch_embeddings(self, texts: list[str]) -> list[list[float]]:
        """Generate embeddings for a batch of texts.

        Args:
            texts: List of input texts to embed

        Returns:
            List of embedding vectors, one per input text
        """


class IServiceResponse(ABC):
    """Abstract interface for standardized service responses."""

    @abstractmethod
    def to_dict(self) -> dict[str, Any]:
        """Convert response to standardized dictionary format.

        Returns:
            Dict with keys: success (bool), data (Any), error (str or None)
        """
        return {"success": True, "data": None, "error": None}


class IService(ABC):
    """Abstract interface for all services."""

    @abstractmethod
    def health_check(self) -> dict[str, Any]:
        """Perform health check for the service.

        Returns:
            Dict with success status and health information
        """


# Protocol interfaces for PDF service providers (duck-typed, no ABC needed)

class OCRPort(Protocol):
    """Protocol for OCR processing providers"""
    def process_pdf_with_ocr(self, pdf_path: str) -> dict[str, Any]: ...


class PDFValidatorPort(Protocol):
    """Protocol for PDF validation providers"""
    def validate_pdf_path(self, pdf_path: str) -> dict[str, Any]: ...


class HealthMonitorPort(Protocol):
    """Protocol for health monitoring providers"""
    def get_health_metrics(self) -> dict[str, Any]: ...


class ErrorRecoveryPort(Protocol):
    """Protocol for error recovery providers"""
    def create_backup(self, backup_name: str | None = None) -> dict[str, Any]: ...
    def get_recovery_status(self) -> dict[str, Any]: ...
    def add_alert_callback(self, callback: Any) -> None: ...


class SummarizerPort(Protocol):
    """Protocol for document summarization providers"""
    def extract_summary(self, text: str, **kwargs: Any) -> dict[str, Any]: ...


class ExporterPort(Protocol):
    """Protocol for document export providers"""
    def save_to_export(self, content_id: int, filename: str) -> dict[str, Any]: ...


class PipelinePort(Protocol):
    """Protocol for document pipeline providers"""
    def add_to_raw(self, path: str, copy: bool = True) -> dict[str, Any]: ...
    def move_to_staged(self, filename: str) -> dict[str, Any]: ...
    def move_to_processed(self, filename: str) -> dict[str, Any]: ...


class PDFHealthManagerPort(Protocol):
    """Protocol for PDF health management providers"""
    def perform_health_check(self) -> dict[str, Any]: ...
