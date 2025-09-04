#!/usr/bin/env python3
"""Tests for the new semantic-only search API.

Tests the minimal 2-function API: search() and find_literal().
"""

import unittest
from unittest.mock import patch, MagicMock
import numpy as np


class TestSemanticSearchAPI(unittest.TestCase):
    """Test the semantic-only search API."""
    
    def test_search_function_exists(self):
        """Test that search function is importable."""
        from search_intelligence import search
        self.assertTrue(callable(search))
    
    def test_find_literal_function_exists(self):
        """Test that find_literal function is importable."""
        from search_intelligence import find_literal
        self.assertTrue(callable(find_literal))
    
    @patch('search_intelligence.basic_search.get_vector_store')
    @patch('search_intelligence.basic_search.get_embedding_service')
    def test_search_basic(self, mock_embed_service, mock_vector_store):
        """Test basic semantic search."""
        from search_intelligence import search
        
        # Mock embedding service
        mock_embedder = MagicMock()
        mock_embedder.encode.return_value = np.ones(1024)  # 1024D vector
        mock_embed_service.return_value = mock_embedder
        
        # Mock vector store
        mock_store = MagicMock()
        mock_store.search.return_value = [
            {
                'id': '1',
                'score': 0.95,
                'payload': {
                    'content_id': '123',
                    'title': 'Test Document',
                    'source_type': 'email_message'
                }
            }
        ]
        mock_vector_store.return_value = mock_store
        
        # Perform search
        search("test query", limit=5)
        
        # Verify embedding was generated
        mock_embedder.encode.assert_called_once_with("test query")
        
        # Verify vector search was called
        mock_store.search.assert_called_once()
        call_args = mock_store.search.call_args
        self.assertEqual(len(call_args[1]['vector']), 1024)  # Check vector dimension
        self.assertEqual(call_args[1]['limit'], 5)
    
    @patch('search_intelligence.basic_search.SimpleDB')
    def test_find_literal_basic(self, mock_db_class):
        """Test literal pattern matching."""
        from search_intelligence import find_literal
        
        # Mock database
        mock_db = MagicMock()
        mock_db.fetch.return_value = [
            {
                'id': 1,
                'source_id': 'doc_1',
                'source_type': 'document',
                'title': 'Contract with BATES-00123',
                'body': 'This document BATES-00123 contains...',
                'metadata': None
            }
        ]
        mock_db_class.return_value = mock_db
        
        # Search for BATES number
        results = find_literal("BATES-00123", limit=10)
        
        # Verify SQL query was executed
        mock_db.fetch.assert_called_once()
        query = mock_db.fetch.call_args[0][0]
        self.assertIn("LIKE", query)  # Should use LIKE for pattern matching
        self.assertIn("%BATES-00123%", mock_db.fetch.call_args[0][1])  # Pattern in params
        
        # Check results
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]['title'], 'Contract with BATES-00123')
        self.assertEqual(results[0]['match_type'], 'literal')
    
    def test_vector_store_available(self):
        """Test vector store availability check."""
        from search_intelligence import vector_store_available
        
        with patch('search_intelligence.basic_search.get_vector_store') as mock_get_store:
            # Test available case
            mock_store = MagicMock()
            mock_store.count.return_value = 100
            mock_get_store.return_value = mock_store
            
            self.assertTrue(vector_store_available())
            
            # Test unavailable case
            mock_get_store.side_effect = Exception("Connection failed")
            self.assertFalse(vector_store_available())
    
    def test_filters_applied(self):
        """Test that filters are properly applied to search."""
        from search_intelligence import search
        
        with patch('search_intelligence.basic_search.get_vector_store') as mock_get_store:
            with patch('search_intelligence.basic_search.get_embedding_service') as mock_embed:
                mock_embedder = MagicMock()
                mock_embedder.encode.return_value = np.ones(1024)
                mock_embed.return_value = mock_embedder
                
                mock_store = MagicMock()
                mock_store.search.return_value = []
                mock_get_store.return_value = mock_store
                
                # Search with filters
                filters = {
                    'source_type': 'email_message',
                    'date_range': {'start': '2024-01-01'},
                    'party': 'John Doe',
                    'tags': ['urgent', 'contract']
                }
                
                search("test", filters=filters)
                
                # Check filters were passed to vector store
                call_args = mock_store.search.call_args[1]
                self.assertIn('filter', call_args)
                applied_filters = call_args['filter']
                self.assertEqual(applied_filters['source_type'], 'email_message')
                self.assertIn('gte', applied_filters['created_at'])
                self.assertEqual(applied_filters['party'], 'John Doe')
    
    # Removed deprecated service shim tests as service is being retired
    
    def test_no_keyword_search_functions(self):
        """Verify keyword search functions have been removed."""
        import search_intelligence.basic_search as basic_search
        
        # These should not exist
        self.assertFalse(hasattr(basic_search, 'calculate_weights'))
        self.assertFalse(hasattr(basic_search, '_keyword_search'))
        self.assertFalse(hasattr(basic_search, '_merge_results_rrf'))
    
    def test_no_environment_variables(self):
        """Verify environment variables for modes have been removed."""
        import search_intelligence.basic_search as basic_search
        import inspect
        
        # Get source code
        source = inspect.getsource(basic_search)
        
        # These env vars should not be referenced
        self.assertNotIn('ENABLE_DYNAMIC_WEIGHTS', source)
        self.assertNotIn('ENABLE_CHUNK_AGGREGATION', source)
        self.assertNotIn('MIN_CHUNK_QUALITY', source)
        self.assertNotIn('MAX_RESULTS_PER_SOURCE', source)


if __name__ == '__main__':
    unittest.main()
