"""Text to vector embeddings service.

Provides Legal BERT 1024-dimensional embeddings for semantic search.
"""

from .embedding_service import EmbeddingService, get_embedding_service

__all__ = ["EmbeddingService", "get_embedding_service"]
