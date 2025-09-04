#!/usr/bin/env python3
"""
Test Vector ID Fix for Qdrant Compatibility

Verifies that vector IDs are properly formatted as integers for Qdrant storage.
Tests the fix applied to utilities/embeddings/batch_processor.py
"""

import hashlib
import unittest
from unittest.mock import Mock, patch

# Test the vector ID generation logic
class TestVectorIDGeneration(unittest.TestCase):
    """Test vector ID generation for Qdrant compatibility."""
    
    def test_database_id_conversion(self):
        """Test that database IDs are converted to integers."""
        # Simulate chunk with database ID
        chunk = {"id": "672", "source_id": "doc123:0"}
        
        # Expected: convert string ID to integer
        vector_id = int(chunk["id"])
        self.assertEqual(vector_id, 672)
        self.assertIsInstance(vector_id, int)
    
    def test_hash_based_id_generation(self):
        """Test generating numeric ID from source_id hash."""
        # Simulate chunk without database ID
        chunk = {"source_id": "ba2ba1f78e1d3c2c1e96d40fb47aa7296cc44e5bd082aa7bcc97077e8e166dfd:0"}
        
        # Generate stable numeric ID from source_id hash
        hash_bytes = hashlib.sha256(chunk["source_id"].encode()).digest()
        vector_id = int.from_bytes(hash_bytes[:8], 'big') % (2**53)  # Safe JavaScript integer
        
        # Verify it's a valid integer
        self.assertIsInstance(vector_id, int)
        self.assertGreater(vector_id, 0)
        self.assertLess(vector_id, 2**53)  # Within safe integer range
    
    def test_id_stability(self):
        """Test that same source_id produces same numeric ID."""
        source_id = "test_doc:0"
        
        # Generate ID twice
        hash_bytes1 = hashlib.sha256(source_id.encode()).digest()
        id1 = int.from_bytes(hash_bytes1[:8], 'big') % (2**53)
        
        hash_bytes2 = hashlib.sha256(source_id.encode()).digest()
        id2 = int.from_bytes(hash_bytes2[:8], 'big') % (2**53)
        
        # Should be identical
        self.assertEqual(id1, id2)
    
    @patch('utilities.embeddings.batch_processor.get_vector_store')
    @patch('utilities.embeddings.batch_processor.get_embedding_service')
    def test_batch_processor_integration(self, mock_embedding, mock_vector):
        """Test BatchEmbeddingProcessor with proper ID format."""
        from utilities.embeddings.batch_processor import BatchEmbeddingProcessor
        
        # Mock services
        mock_embed_service = Mock()
        mock_embed_service.batch_encode.return_value = [Mock(tolist=lambda: [0.1] * 1024)]
        mock_embedding.return_value = mock_embed_service
        
        mock_vector_store = Mock()
        mock_vector_store.batch_upsert.return_value = [672]
        mock_vector.return_value = mock_vector_store
        
        # Mock database
        with patch('utilities.embeddings.batch_processor.SimpleDB') as mock_db_class:
            mock_db = Mock()
            mock_db.get_chunks_for_embedding.return_value = [{
                "id": 672,
                "source_id": "doc123:0",
                "body": "Test content",
                "quality_score": 0.8
            }]
            mock_db.mark_chunk_embedded = Mock()
            mock_db_class.return_value = mock_db
            
            # Process chunks
            processor = BatchEmbeddingProcessor()
            processor._process_batch([{
                "id": 672,
                "source_id": "doc123:0", 
                "body": "Test content",
                "quality_score": 0.8
            }], dry_run=False)
            
            # Verify batch_upsert was called with integer ID
            mock_vector_store.batch_upsert.assert_called_once()
            call_args = mock_vector_store.batch_upsert.call_args
            points = call_args[1]["points"]
            
            # Check ID is integer, not string
            self.assertIsInstance(points[0]["id"], int)
            self.assertEqual(points[0]["id"], 672)
    
    def test_qdrant_id_requirements(self):
        """Test that generated IDs meet Qdrant requirements."""
        test_cases = [
            {"id": "123", "source_id": "doc1:0"},  # String ID from DB
            {"source_id": "abc123:0"},  # No DB ID, use hash
            {"id": 999, "source_id": "doc2:1"},  # Already integer
        ]
        
        for chunk in test_cases:
            if "id" in chunk and chunk["id"]:
                vector_id = int(chunk["id"])
            else:
                hash_bytes = hashlib.sha256(chunk["source_id"].encode()).digest()
                vector_id = int.from_bytes(hash_bytes[:8], 'big') % (2**53)
            
            # Verify meets Qdrant requirements:
            # 1. Must be integer
            self.assertIsInstance(vector_id, int)
            # 2. Must be positive  
            self.assertGreater(vector_id, 0)
            # 3. Must be within safe range
            self.assertLess(vector_id, 2**53)


if __name__ == "__main__":
    unittest.main()