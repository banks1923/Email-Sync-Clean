"""
Unit tests for SearchIntelligenceService query expansion functionality.

Tests the core query expansion logic that was fixed to prevent regressions.
"""
import pytest
from unittest.mock import Mock, patch
from search_intelligence.main import SearchIntelligenceService


class TestQueryExpansion:
    """Test query expansion functionality to prevent regressions."""

    @pytest.fixture
    def service(self):
        """Create SearchIntelligenceService with mocked dependencies."""
        with patch('search_intelligence.main.SimpleDB'), \
             patch('search_intelligence.main.get_vector_store'), \
             patch('search_intelligence.main.EntityService'), \
             patch('search_intelligence.main.get_embedding_service'), \
             patch('search_intelligence.main.get_document_summarizer'):
            
            service = SearchIntelligenceService()
            # Mock the database search to return test data
            service.db.search_content = Mock(return_value=[
                {"id": "1", "title": "Test Doc", "content": "test content", "source_type": "email"}
            ])
            return service

    def test_preprocess_query_basic(self, service):
        """Test basic query preprocessing."""
        # Test case conversion
        result = service._preprocess_query("LEGAL CASE")
        assert result == "legal case"
        
        # Test abbreviation expansion
        result = service._preprocess_query("llc contract")
        assert result == "limited liability company contract"
        
        # Test whitespace normalization
        result = service._preprocess_query("  multiple   spaces  ")
        assert result == "multiple spaces"

    def test_expand_query_basic(self, service):
        """Test query expansion with synonyms."""
        # Test legal synonym expansion
        result = service._expand_query("legal")
        assert "law" in result
        assert "judicial" in result
        
        # Test contract synonym expansion
        result = service._expand_query("contract")
        assert "agreement" in result
        assert "deal" in result
        
        # Test no expansion for unknown terms
        result = service._expand_query("unknownterm")
        assert result == []

    def test_expand_query_multiple_terms(self, service):
        """Test expansion with multiple expandable terms."""
        result = service._expand_query("legal contract")
        # Should include synonyms for both terms (first 2 each)
        assert "law" in result
        assert "judicial" in result
        assert "agreement" in result
        assert "deal" in result
        # Should not exceed 2 synonyms per term
        assert len(result) <= 4

    @patch('search_intelligence.main.logger')
    def test_smart_search_with_expansion_creates_or_query(self, mock_logger, service):
        """Test that expansion creates proper OR query (REGRESSION TEST)."""
        # Mock the fetch method to capture SQL queries
        service.db.fetch = Mock(return_value=[
            {"id": "1", "title": "Test", "body": "content", "source_type": "email"}
        ])
        
        # Test with expansion enabled
        result = service.smart_search_with_preprocessing("legal", limit=5, use_expansion=True)
        
        # Verify fetch was called with OR query
        service.db.fetch.assert_called_once()
        query, params = service.db.fetch.call_args
        
        # The SQL should contain OR conditions for expanded terms
        sql_query = query[0]
        assert "OR" in sql_query
        assert "title LIKE" in sql_query
        assert "body LIKE" in sql_query
        # Should have legal, law, judicial in the query
        assert "legal" in sql_query.lower()
        
        # Verify results are returned
        assert len(result) == 1
        assert result[0]["id"] == "1"

    @patch('search_intelligence.main.logger')
    def test_smart_search_without_expansion_uses_simple_query(self, mock_logger, service):
        """Test that disabled expansion uses simple search."""
        # Test with expansion disabled
        result = service.smart_search_with_preprocessing("legal", limit=5, use_expansion=False)
        
        # Should call simple search_content method
        service.db.search_content.assert_called_once_with("legal", limit=5, filters=None)
        
        # Verify results
        assert len(result) == 1

    @patch('search_intelligence.main.logger')
    def test_no_results_debug_logging(self, mock_logger, service):
        """Test debug logging for no-result queries."""
        # Mock empty results
        service.db.search_content = Mock(return_value=[])
        service.db.fetch = Mock(return_value=[])
        
        # Search with no results
        result = service.smart_search_with_preprocessing("nonexistentterm", use_expansion=True)
        
        # Verify empty results
        assert result == []
        
        # Verify debug logging was called
        mock_logger.debug.assert_called()
        debug_call = mock_logger.debug.call_args[0][0]
        assert "No results found for query" in debug_call
        assert "nonexistentterm" in debug_call

    def test_filter_support_with_expansion(self, service):
        """Test that filters work correctly with query expansion."""
        # Mock fetch to return results with content_type filter
        service.db.fetch = Mock(return_value=[
            {"id": "1", "title": "Email Test", "body": "content", "source_type": "email"}
        ])
        
        filters = {"content_types": ["email"]}
        result = service.smart_search_with_preprocessing("legal", filters=filters, use_expansion=True)
        
        # Verify fetch was called with filter in SQL
        service.db.fetch.assert_called_once()
        query, params = service.db.fetch.call_args
        sql_query = query[0]
        
        # Should include content type filter
        assert "source_type = 'email'" in sql_query or "email" in sql_query
        assert len(result) == 1

    def test_query_expansion_edge_cases(self, service):
        """Test edge cases in query expansion."""
        # Empty query
        result = service._expand_query("")
        assert result == []
        
        # Single character
        result = service._expand_query("a")
        assert result == []
        
        # Query with only non-expandable terms
        result = service._expand_query("xyz abc")
        assert result == []
        
        # Query with mixed expandable and non-expandable
        result = service._expand_query("legal xyz")
        assert "law" in result
        assert "judicial" in result

    def test_abbreviation_expansion_edge_cases(self, service):
        """Test edge cases in abbreviation expansion."""
        # Abbreviation at start
        result = service._preprocess_query("llc business")
        assert result == "limited liability company business"
        
        # Abbreviation at end  
        result = service._preprocess_query("business llc")
        assert result == "business limited liability company"
        
        # Multiple abbreviations
        result = service._preprocess_query("llc and inc")
        assert result == "limited liability company and incorporated"
        
        # Abbreviation as part of larger word (should not expand)
        result = service._preprocess_query("allocated")
        assert result == "allocated"  # Should NOT become "limited liability companycated"


class TestParameterValidation:
    """Test parameter validation to prevent type mismatches."""

    @pytest.fixture
    def service(self):
        """Create service with mocked dependencies."""
        with patch('search_intelligence.main.SimpleDB'), \
             patch('search_intelligence.main.get_vector_store'), \
             patch('search_intelligence.main.EntityService'), \
             patch('search_intelligence.main.get_embedding_service'), \
             patch('search_intelligence.main.get_document_summarizer'):
            return SearchIntelligenceService()

    def test_extract_and_cache_entities_parameter_validation(self, service):
        """Test entity extraction parameter validation (REGRESSION TEST)."""
        # Mock dependencies
        service.db.get_content = Mock(return_value={
            "body": "test content", 
            "title": "test"
        })
        service.entity_service.extract_email_entities = Mock(return_value={
            "entities": [{"text": "test", "label": "TEST"}]
        })
        
        # Test with correct parameter name
        result = service.extract_and_cache_entities(doc_id="123")
        
        # Verify correct method was called with correct parameters
        service.entity_service.extract_email_entities.assert_called_once_with("123", "test content")
        assert len(result) == 1

    def test_analyze_document_similarity_parameter_validation(self, service):
        """Test similarity analysis parameter validation."""
        # Mock content retrieval
        service.db.get_content = Mock(return_value={
            "content": "test document content"
        })
        service.embedding_service.encode = Mock(return_value=[0.1, 0.2, 0.3])
        service.db.search_content = Mock(return_value=[])
        
        # Test with correct parameter name
        result = service.analyze_document_similarity(doc_id="123", threshold=0.7)
        
        # Verify method was called correctly
        service.db.get_content.assert_called_once_with(content_id="123")
        assert result == []  # No similar docs in mock

    def test_method_signature_consistency(self, service):
        """Test that method signatures are consistent across the service."""
        import inspect
        
        # Check extract_and_cache_entities signature
        sig = inspect.signature(service.extract_and_cache_entities)
        assert 'doc_id' in sig.parameters
        assert 'force_refresh' in sig.parameters
        
        # Check analyze_document_similarity signature  
        sig = inspect.signature(service.analyze_document_similarity)
        assert 'doc_id' in sig.parameters
        assert 'threshold' in sig.parameters
        assert 'limit' in sig.parameters