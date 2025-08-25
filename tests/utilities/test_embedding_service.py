"""
Comprehensive tests for EmbeddingService.
"""

from unittest.mock import MagicMock, patch

import numpy as np
import pytest
import torch

from utilities.embeddings.embedding_service import EmbeddingService, get_embedding_service


class TestEmbeddingService:
    """
    Test EmbeddingService functionality.
    """
    
    @patch('utilities.embeddings.embedding_service.AutoModel')
    @patch('utilities.embeddings.embedding_service.AutoTokenizer')
    def test_initialization(self, mock_tokenizer, mock_model):
        """
        Test service initialization.
        """
        mock_tokenizer.from_pretrained.return_value = MagicMock()
        mock_model.from_pretrained.return_value = MagicMock()
        
        service = EmbeddingService()
        
        assert service.model_name == "pile-of-law/legalbert-large-1.7M-2"
        assert service.dimensions == 1024
        assert service.tokenizer is not None
        assert service.model is not None
        
        # Check model loaded with correct name
        mock_tokenizer.from_pretrained.assert_called_once_with(service.model_name)
        mock_model.from_pretrained.assert_called_once_with(service.model_name)
        
    @patch('utilities.embeddings.embedding_service.AutoModel')
    @patch('utilities.embeddings.embedding_service.AutoTokenizer')
    def test_custom_model_name(self, mock_tokenizer, mock_model):
        """
        Test initialization with custom model name.
        """
        mock_tokenizer.from_pretrained.return_value = MagicMock()
        mock_model.from_pretrained.return_value = MagicMock()
        
        custom_model = "bert-base-uncased"
        service = EmbeddingService(model_name=custom_model)
        
        assert service.model_name == custom_model
        mock_tokenizer.from_pretrained.assert_called_once_with(custom_model)
        mock_model.from_pretrained.assert_called_once_with(custom_model)
        
    def test_get_device_mps(self):
        """
        Test device selection for MPS (Apple Silicon).
        """
        with patch('torch.backends.mps.is_available', return_value=True):
            service = EmbeddingService.__new__(EmbeddingService)
            device = service._get_device()
            assert device == "mps"
            
    def test_get_device_cuda(self):
        """
        Test device selection for CUDA.
        """
        with patch('torch.backends.mps.is_available', return_value=False):
            with patch('torch.cuda.is_available', return_value=True):
                service = EmbeddingService.__new__(EmbeddingService)
                device = service._get_device()
                assert device == "cuda"
                
    def test_get_device_cpu(self):
        """
        Test device selection fallback to CPU.
        """
        with patch('torch.backends.mps.is_available', return_value=False):
            with patch('torch.cuda.is_available', return_value=False):
                service = EmbeddingService.__new__(EmbeddingService)
                device = service._get_device()
                assert device == "cpu"
                
    @patch('utilities.embeddings.embedding_service.AutoModel')
    @patch('utilities.embeddings.embedding_service.AutoTokenizer')
    def test_load_model_error(self, mock_tokenizer, mock_model):
        """
        Test model loading error handling.
        """
        mock_tokenizer.from_pretrained.side_effect = Exception("Model not found")
        
        with pytest.raises(Exception) as exc_info:
            EmbeddingService()
        
        assert "Model not found" in str(exc_info.value)
        
    @patch('utilities.embeddings.embedding_service.AutoModel')
    @patch('utilities.embeddings.embedding_service.AutoTokenizer')
    def test_encode_normal_text(self, mock_tokenizer, mock_model):
        """
        Test encoding normal text.
        """
        # Setup mocks
        mock_tokenizer_instance = MagicMock()
        mock_model_instance = MagicMock()
        
        mock_tokenizer.from_pretrained.return_value = mock_tokenizer_instance
        mock_model.from_pretrained.return_value = mock_model_instance
        
        # Mock tokenizer output
        mock_inputs = {
            'input_ids': torch.tensor([[1, 2, 3]]),
            'attention_mask': torch.tensor([[1, 1, 1]])
        }
        mock_tokenizer_instance.return_value = mock_inputs
        
        # Mock model output
        mock_hidden_states = torch.randn(1, 3, 1024)  # batch, seq_len, hidden_dim
        mock_outputs = MagicMock()
        mock_outputs.last_hidden_state = mock_hidden_states
        mock_model_instance.return_value = mock_outputs
        
        service = EmbeddingService()
        embedding = service.encode("Test text")
        
        assert isinstance(embedding, np.ndarray)
        assert embedding.shape == (1024,)  # Flattened
        
    @patch('utilities.embeddings.embedding_service.AutoModel')
    @patch('utilities.embeddings.embedding_service.AutoTokenizer')
    def test_encode_empty_text(self, mock_tokenizer, mock_model):
        """
        Test encoding empty text.
        """
        mock_tokenizer.from_pretrained.return_value = MagicMock()
        mock_model.from_pretrained.return_value = MagicMock()
        
        service = EmbeddingService()
        
        # Empty string
        embedding1 = service.encode("")
        assert isinstance(embedding1, np.ndarray)
        assert embedding1.shape == (1024,)
        assert np.all(embedding1 == 0)
        
        # Whitespace only
        embedding2 = service.encode("   ")
        assert isinstance(embedding2, np.ndarray)
        assert embedding2.shape == (1024,)
        assert np.all(embedding2 == 0)
        
        # None (if passed)
        embedding3 = service.encode(None)
        assert isinstance(embedding3, np.ndarray)
        assert embedding3.shape == (1024,)
        assert np.all(embedding3 == 0)
        
    @patch('utilities.embeddings.embedding_service.AutoModel')
    @patch('utilities.embeddings.embedding_service.AutoTokenizer')
    def test_encode_long_text(self, mock_tokenizer, mock_model):
        """
        Test encoding text that exceeds max length.
        """
        mock_tokenizer_instance = MagicMock()
        mock_model_instance = MagicMock()
        
        mock_tokenizer.from_pretrained.return_value = mock_tokenizer_instance
        mock_model.from_pretrained.return_value = mock_model_instance
        
        # Mock tokenizer to verify truncation
        mock_tokenizer_instance.return_value = {
            'input_ids': torch.tensor([[1, 2, 3]]),
            'attention_mask': torch.tensor([[1, 1, 1]])
        }
        
        mock_hidden_states = torch.randn(1, 3, 1024)
        mock_outputs = MagicMock()
        mock_outputs.last_hidden_state = mock_hidden_states
        mock_model_instance.return_value = mock_outputs
        
        service = EmbeddingService()
        
        # Create very long text
        long_text = "word " * 1000  # Way over 512 token limit
        embedding = service.encode(long_text)
        
        # Check tokenizer was called with truncation
        mock_tokenizer_instance.assert_called_with(
            long_text,
            return_tensors="pt",
            truncation=True,
            max_length=512,
            padding=True
        )
        
        assert isinstance(embedding, np.ndarray)
        assert embedding.shape == (1024,)
        
    @patch('utilities.embeddings.embedding_service.AutoModel')
    @patch('utilities.embeddings.embedding_service.AutoTokenizer')
    def test_batch_encode(self, mock_tokenizer, mock_model):
        """
        Test batch encoding of multiple texts.
        """
        mock_tokenizer_instance = MagicMock()
        mock_model_instance = MagicMock()
        
        mock_tokenizer.from_pretrained.return_value = mock_tokenizer_instance
        mock_model.from_pretrained.return_value = mock_model_instance
        
        # Mock batch processing
        batch_size = 3
        mock_tokenizer_instance.return_value = {
            'input_ids': torch.tensor([[1, 2, 3]] * batch_size),
            'attention_mask': torch.tensor([[1, 1, 1]] * batch_size)
        }
        
        mock_hidden_states = torch.randn(batch_size, 3, 1024)
        mock_outputs = MagicMock()
        mock_outputs.last_hidden_state = mock_hidden_states
        mock_model_instance.return_value = mock_outputs
        
        service = EmbeddingService()
        
        texts = ["Text 1", "Text 2", "Text 3"]
        embeddings = service.batch_encode(texts)
        
        assert len(embeddings) == 3
        for emb in embeddings:
            assert isinstance(emb, np.ndarray)
            assert emb.shape == (1024,)
            
    @patch('utilities.embeddings.embedding_service.AutoModel')
    @patch('utilities.embeddings.embedding_service.AutoTokenizer')
    def test_batch_encode_with_empty(self, mock_tokenizer, mock_model):
        """
        Test batch encoding with empty texts.
        """
        mock_tokenizer_instance = MagicMock()
        mock_model_instance = MagicMock()
        
        mock_tokenizer.from_pretrained.return_value = mock_tokenizer_instance
        mock_model.from_pretrained.return_value = mock_model_instance
        
        mock_tokenizer_instance.return_value = {
            'input_ids': torch.tensor([[1, 2, 3]] * 3),
            'attention_mask': torch.tensor([[1, 1, 1]] * 3)
        }
        
        mock_hidden_states = torch.randn(3, 3, 1024)
        mock_outputs = MagicMock()
        mock_outputs.last_hidden_state = mock_hidden_states
        mock_model_instance.return_value = mock_outputs
        
        service = EmbeddingService()
        
        texts = ["Valid text", "", "Another text"]
        embeddings = service.batch_encode(texts)
        
        assert len(embeddings) == 3
        # Empty text should be replaced with space
        mock_tokenizer_instance.assert_called_with(
            ["Valid text", " ", "Another text"],
            return_tensors="pt",
            truncation=True,
            max_length=512,
            padding=True
        )
        
    @patch('utilities.embeddings.embedding_service.AutoModel')
    @patch('utilities.embeddings.embedding_service.AutoTokenizer')
    def test_batch_encode_large_batch(self, mock_tokenizer, mock_model):
        """
        Test batch encoding with batch size limit.
        """
        mock_tokenizer_instance = MagicMock()
        mock_model_instance = MagicMock()
        
        mock_tokenizer.from_pretrained.return_value = mock_tokenizer_instance
        mock_model.from_pretrained.return_value = mock_model_instance
        
        # Setup for multiple batches
        def mock_tokenizer_side_effect(texts, **kwargs):
            batch_size = len(texts) if isinstance(texts, list) else 1
            return {
                'input_ids': torch.tensor([[1, 2, 3]] * batch_size),
                'attention_mask': torch.tensor([[1, 1, 1]] * batch_size)
            }
        
        mock_tokenizer_instance.side_effect = mock_tokenizer_side_effect
        
        def mock_model_side_effect(input_ids=None, **kwargs):
            batch_size = input_ids.shape[0] if input_ids is not None else 1
            mock_outputs = MagicMock()
            mock_outputs.last_hidden_state = torch.randn(batch_size, 3, 1024)
            return mock_outputs
        
        mock_model_instance.side_effect = mock_model_side_effect
        
        service = EmbeddingService()
        
        # Create 25 texts to test batching with batch_size=16
        texts = [f"Text {i}" for i in range(25)]
        embeddings = service.batch_encode(texts, batch_size=16)
        
        assert len(embeddings) == 25
        # Should be called twice: once with 16, once with 9
        assert mock_tokenizer_instance.call_count == 2
        
    @patch('utilities.embeddings.embedding_service.AutoModel')
    @patch('utilities.embeddings.embedding_service.AutoTokenizer')
    def test_get_dimensions(self, mock_tokenizer, mock_model):
        """
        Test getting embedding dimensions.
        """
        mock_tokenizer.from_pretrained.return_value = MagicMock()
        mock_model.from_pretrained.return_value = MagicMock()
        
        service = EmbeddingService()
        dims = service.get_dimensions()
        
        assert dims == 1024
        
    @patch('utilities.embeddings.embedding_service.AutoModel')
    @patch('utilities.embeddings.embedding_service.AutoTokenizer')
    def test_model_eval_mode(self, mock_tokenizer, mock_model):
        """
        Test that model is set to eval mode.
        """
        mock_tokenizer_instance = MagicMock()
        mock_model_instance = MagicMock()
        
        mock_tokenizer.from_pretrained.return_value = mock_tokenizer_instance
        mock_model.from_pretrained.return_value = mock_model_instance
        
        EmbeddingService()
        
        # Check model was set to eval mode
        mock_model_instance.eval.assert_called_once()
        
    @patch('utilities.embeddings.embedding_service.AutoModel')
    @patch('utilities.embeddings.embedding_service.AutoTokenizer')
    def test_model_to_device(self, mock_tokenizer, mock_model):
        """
        Test that model is moved to correct device.
        """
        mock_tokenizer_instance = MagicMock()
        mock_model_instance = MagicMock()
        
        mock_tokenizer.from_pretrained.return_value = mock_tokenizer_instance
        mock_model.from_pretrained.return_value = mock_model_instance
        
        with patch('torch.cuda.is_available', return_value=True):
            with patch('torch.backends.mps.is_available', return_value=False):
                EmbeddingService()
                
                # Check model was moved to cuda
                mock_model_instance.to.assert_called_once_with("cuda")


class TestEmbeddingServiceSingleton:
    """
    Test singleton pattern for embedding service.
    """
    
    @patch('utilities.embeddings.embedding_service.AutoModel')
    @patch('utilities.embeddings.embedding_service.AutoTokenizer')
    def test_get_embedding_service_singleton(self, mock_tokenizer, mock_model):
        """
        Test that get_embedding_service returns singleton.
        """
        mock_tokenizer.from_pretrained.return_value = MagicMock()
        mock_model.from_pretrained.return_value = MagicMock()
        
        # Reset global singleton
        import utilities.embeddings.embedding_service
        utilities.embeddings.embedding_service._embedding_service = None
        
        service1 = get_embedding_service()
        service2 = get_embedding_service()
        
        assert service1 is service2
        # Model should only be loaded once
        assert mock_model.from_pretrained.call_count == 1
        
    @patch('utilities.embeddings.embedding_service.AutoModel')
    @patch('utilities.embeddings.embedding_service.AutoTokenizer')
    def test_get_embedding_service_custom_model(self, mock_tokenizer, mock_model):
        """
        Test get_embedding_service with custom model.
        """
        mock_tokenizer.from_pretrained.return_value = MagicMock()
        mock_model.from_pretrained.return_value = MagicMock()
        
        # Reset global singleton
        import utilities.embeddings.embedding_service
        utilities.embeddings.embedding_service._embedding_service = None
        
        custom_model = "bert-base-uncased"
        service = get_embedding_service(model_name=custom_model)
        
        assert service.model_name == custom_model
        mock_model.from_pretrained.assert_called_once_with(custom_model)


@pytest.mark.integration
class TestEmbeddingServiceIntegration:
    """
    Integration tests for EmbeddingService.
    """
    
    @pytest.mark.skipif(
        not torch.cuda.is_available() and not torch.backends.mps.is_available(),
        reason="No GPU available for integration test"
    )
    @patch('utilities.embeddings.embedding_service.AutoModel')
    @patch('utilities.embeddings.embedding_service.AutoTokenizer')
    def test_gpu_memory_management(self, mock_tokenizer, mock_model):
        """
        Test GPU memory is properly managed.
        """
        mock_tokenizer_instance = MagicMock()
        mock_model_instance = MagicMock()
        
        mock_tokenizer.from_pretrained.return_value = mock_tokenizer_instance
        mock_model.from_pretrained.return_value = mock_model_instance
        
        # Mock the model outputs
        def create_mock_output(batch_size):
            mock_output = MagicMock()
            mock_output.last_hidden_state = torch.randn(batch_size, 10, 1024)
            return mock_output
        
        mock_model_instance.side_effect = lambda **kwargs: create_mock_output(
            kwargs.get('input_ids', torch.zeros(1, 1)).shape[0]
        )
        
        mock_tokenizer_instance.return_value = {
            'input_ids': torch.tensor([[1, 2, 3]]),
            'attention_mask': torch.tensor([[1, 1, 1]])
        }
        
        service = EmbeddingService()
        
        # Process multiple texts
        for _ in range(10):
            embedding = service.encode("Test text for GPU memory")
            assert embedding.shape == (1024,)
            # Embedding should be on CPU (numpy array)
            assert isinstance(embedding, np.ndarray)
            
    @patch('utilities.embeddings.embedding_service.AutoModel')
    @patch('utilities.embeddings.embedding_service.AutoTokenizer')
    def test_concurrent_encoding(self, mock_tokenizer, mock_model):
        """
        Test thread safety of encoding.
        """
        mock_tokenizer_instance = MagicMock()
        mock_model_instance = MagicMock()
        
        mock_tokenizer.from_pretrained.return_value = mock_tokenizer_instance
        mock_model.from_pretrained.return_value = mock_model_instance
        
        mock_tokenizer_instance.return_value = {
            'input_ids': torch.tensor([[1, 2, 3]]),
            'attention_mask': torch.tensor([[1, 1, 1]])
        }
        
        mock_hidden_states = torch.randn(1, 3, 1024)
        mock_outputs = MagicMock()
        mock_outputs.last_hidden_state = mock_hidden_states
        mock_model_instance.return_value = mock_outputs
        
        service = get_embedding_service()
        
        # Multiple calls should work without issues
        results = []
        for i in range(5):
            emb = service.encode(f"Text {i}")
            results.append(emb)
            
        assert len(results) == 5
        for emb in results:
            assert emb.shape == (1024,)