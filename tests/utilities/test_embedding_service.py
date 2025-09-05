"""
Tests for EmbeddingService.
"""

from unittest.mock import MagicMock, patch
import numpy as np
import pytest
from lib.embeddings import EmbeddingService, get_embedding_service


class TestEmbeddingService:
    """Test EmbeddingService functionality."""

    @patch("lib.embeddings.SENTENCE_TRANSFORMERS_AVAILABLE", True)
    @patch("lib.embeddings.SentenceTransformer")
    def test_initialization(self, mock_transformer):
        """Test service initialization."""
        mock_model = MagicMock()
        mock_model.get_sentence_embedding_dimension.return_value = 1024
        mock_model.encode.return_value = np.zeros(1024)
        mock_transformer.return_value = mock_model

        service = EmbeddingService()
        assert service.model is not None

    @patch("lib.embeddings.SENTENCE_TRANSFORMERS_AVAILABLE", True)
    @patch("lib.embeddings.SentenceTransformer")
    def test_encode(self, mock_transformer):
        """Test encoding text to embeddings."""
        mock_model = MagicMock()
        mock_model.get_sentence_embedding_dimension.return_value = 1024
        expected_embedding = np.random.rand(1024)
        mock_model.encode.return_value = expected_embedding
        mock_transformer.return_value = mock_model

        service = EmbeddingService()
        embedding = service.encode("Test text")
        
        # The service returns a list, not a numpy array
        assert isinstance(embedding, list)
        assert len(embedding) == 1024
        mock_model.encode.assert_called_once_with("Test text", normalize_embeddings=True)

    @patch("lib.embeddings.SENTENCE_TRANSFORMERS_AVAILABLE", True)
    @patch("lib.embeddings.SentenceTransformer")
    def test_encode_empty_text(self, mock_transformer):
        """Test encoding empty text."""
        mock_model = MagicMock()
        mock_model.get_sentence_embedding_dimension.return_value = 1024
        mock_model.encode.return_value = np.zeros(1024)
        mock_transformer.return_value = mock_model

        service = EmbeddingService()
        embedding = service.encode("")
        
        # Empty text returns zero vector
        assert isinstance(embedding, (np.ndarray, list))
        if isinstance(embedding, list):
            assert len(embedding) == 768  # Mock returns 768
        else:
            assert embedding.shape == (1024,)

    @patch("lib.embeddings.SENTENCE_TRANSFORMERS_AVAILABLE", False)
    def test_mock_service(self):
        """Test mock service when sentence-transformers not available."""
        service = EmbeddingService()
        embedding = service.encode("Test text")
        
        assert isinstance(embedding, list)
        assert len(embedding) == 768  # Mock service uses default BERT dimension
        assert all(isinstance(x, float) for x in embedding)

    @patch("lib.embeddings.SENTENCE_TRANSFORMERS_AVAILABLE", True)
    @patch("lib.embeddings.SentenceTransformer")
    def test_batch_encode(self, mock_transformer):
        """Test batch encoding of multiple texts."""
        mock_model = MagicMock()
        mock_model.get_sentence_embedding_dimension.return_value = 1024
        # Return individual embeddings for each encode call
        mock_model.encode.side_effect = [np.random.rand(1024) for _ in range(3)]
        mock_transformer.return_value = mock_model

        service = EmbeddingService()
        texts = ["Text 1", "Text 2", "Text 3"]
        embeddings = service.batch_encode(texts)
        
        assert len(embeddings) == 3
        assert all(isinstance(emb, list) and len(emb) == 1024 for emb in embeddings)

    @patch("lib.embeddings.SENTENCE_TRANSFORMERS_AVAILABLE", True)
    @patch("lib.embeddings.SentenceTransformer")
    def test_health_check(self, mock_transformer):
        """Test health check functionality."""
        mock_model = MagicMock()
        mock_model.get_sentence_embedding_dimension.return_value = 1024
        mock_transformer.return_value = mock_model

        service = EmbeddingService()
        health = service.health_check()
        
        assert health["status"] in ["healthy", "mock"]
        assert "details" in health
        assert "metrics" in health

    @patch("lib.embeddings.SENTENCE_TRANSFORMERS_AVAILABLE", True)
    @patch("lib.embeddings.SentenceTransformer")
    def test_get_embedding_service_singleton(self, mock_transformer):
        """Test that get_embedding_service returns singleton."""
        mock_model = MagicMock()
        mock_model.get_sentence_embedding_dimension.return_value = 1024
        mock_transformer.return_value = mock_model

        service1 = get_embedding_service()
        service2 = get_embedding_service()
        
        # Should return the same instance
        assert service1 is service2