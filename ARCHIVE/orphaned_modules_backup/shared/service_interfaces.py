from abc import ABC, abstractmethod
from typing import Any


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
