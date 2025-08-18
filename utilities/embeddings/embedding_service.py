"""Legal BERT embedding service implementation.

Convert text to 1024-dimensional vectors for semantic search.
"""

import numpy as np
import torch
from loguru import logger

# Logger is now imported globally from loguru


class EmbeddingService:
    """Convert text to vectors.

    That's it.
    """

    def __init__(self, model_name: str = "pile-of-law/legalbert-large-1.7M-2"):
        """
        Initialize with Legal BERT by default.
        """
        self.model_name = model_name
        self.tokenizer = None
        self.model = None
        self.device = self._get_device()
        self.dimensions = 1024  # Legal BERT dimensions
        self._load_model()

    def _get_device(self) -> str:
        """
        Get best available device.
        """
        if torch.backends.mps.is_available():
            return "mps"
        elif torch.cuda.is_available():
            return "cuda"
        else:
            return "cpu"

    def _load_model(self):
        """
        Load the model and tokenizer.
        """
        try:
            from transformers import AutoModel, AutoTokenizer

            logger.info(f"Loading {self.model_name} on {self.device}")
            self.tokenizer = AutoTokenizer.from_pretrained(self.model_name)
            self.model = AutoModel.from_pretrained(self.model_name)
            self.model.to(self.device)
            self.model.eval()
            logger.info(f"Model loaded successfully - dimensions: {self.dimensions}")
        except Exception as e:
            logger.error(f"Failed to load model: {e}")
            raise

    def encode(self, text: str) -> np.ndarray:
        """Convert text to vector.

        Simple.
        """
        if not text or not text.strip():
            return np.zeros(self.dimensions)

        with torch.no_grad():
            inputs = self.tokenizer(
                text, return_tensors="pt", truncation=True, max_length=512, padding=True
            ).to(self.device)

            outputs = self.model(**inputs)

            # Mean pooling over token embeddings
            outputs.last_hidden_state.mean(dim=1)

            # Move to CPU and convert to numpy
            embeddings = outputs.last_hidden_state.mean(dim=1)
            return embeddings.cpu().numpy().flatten()

    def batch_encode(self, texts: list[str], batch_size: int = 16) -> list[np.ndarray]:
        """
        Batch processing for efficiency.
        """
        embeddings = []

        for i in range(0, len(texts), batch_size):
            batch = texts[i : i + batch_size]

            # Skip empty texts
            batch = [t if t and t.strip() else " " for t in batch]

            with torch.no_grad():
                inputs = self.tokenizer(
                    batch, return_tensors="pt", truncation=True, max_length=512, padding=True
                ).to(self.device)

                outputs = self.model(**inputs)
                batch_embeddings = outputs.last_hidden_state.mean(dim=1)

                for embedding in batch_embeddings:
                    embeddings.append(embedding.cpu().numpy())

        return embeddings

    def get_dimensions(self) -> int:
        """
        Get embedding dimensions.
        """
        return self.dimensions


# Singleton pattern - reuse the same model instance
_embedding_service: EmbeddingService | None = None


def get_embedding_service(
    model_name: str = "pile-of-law/legalbert-large-1.7M-2",
) -> EmbeddingService:
    """
    Get or create singleton embedding service.
    """
    global _embedding_service
    if _embedding_service is None:
        _embedding_service = EmbeddingService(model_name)
    return _embedding_service
