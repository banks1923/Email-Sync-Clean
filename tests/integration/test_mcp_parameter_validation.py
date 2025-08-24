"""
Integration tests for MCP server parameter validation.

Tests the actual MCP function calls to ensure parameter mismatches are caught.
"""
from unittest.mock import Mock, patch
import sys
from pathlib import Path

# Add project root to path for imports
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))


class TestSearchIntelligenceMCPParameters:
    """Test Search Intelligence MCP parameter validation."""

    @patch('infrastructure.mcp_servers.search_intelligence_mcp.get_search_intelligence_service')
    def test_search_entities_parameter_mapping(self, mock_get_service):
        """Test search_entities correctly maps document_id to doc_id (REGRESSION TEST)."""
        from infrastructure.mcp_servers.search_intelligence_mcp import search_entities
        
        # Mock the service and its method
        mock_service = Mock()
        mock_service.extract_and_cache_entities.return_value = [
            {"text": "test entity", "label": "TEST", "confidence": 0.9}
        ]
        mock_get_service.return_value = mock_service
        
        # Call with document_id parameter (as MCP provides it)
        result = search_entities(document_id="test_doc_123", cache_results=True)
        
        # Verify the service method was called with correct parameter name
        mock_service.extract_and_cache_entities.assert_called_once_with(
            doc_id="test_doc_123", 
            force_refresh=False  # cache_results=True -> force_refresh=False
        )
        
        # Verify result formatting
        assert "Entity Extraction" in result
        assert "test entity" in result

    @patch('infrastructure.mcp_servers.search_intelligence_mcp.get_search_intelligence_service')
    def test_search_similar_parameter_mapping(self, mock_get_service):
        """Test search_similar correctly maps document_id to doc_id."""
        from infrastructure.mcp_servers.search_intelligence_mcp import search_similar
        
        # Mock the service
        mock_service = Mock()
        mock_service.analyze_document_similarity.return_value = [
            {
                "content_id": "similar_doc",
                "title": "Similar Document", 
                "similarity_score": 0.85,
                "content_type": "email"
            }
        ]
        mock_get_service.return_value = mock_service
        
        # Call with document_id parameter
        result = search_similar(document_id="test_doc_123", threshold=0.7, limit=5)
        
        # Verify correct parameter mapping
        mock_service.analyze_document_similarity.assert_called_once_with(
            doc_id="test_doc_123",
            threshold=0.7,
            limit=5
        )
        
        # Verify result formatting
        assert "Similar Documents" in result
        assert "similar_doc" in result

    @patch('infrastructure.mcp_servers.search_intelligence_mcp.get_search_intelligence_service')
    def test_search_smart_parameter_validation(self, mock_get_service):
        """Test search_smart parameter validation and query expansion."""
        from infrastructure.mcp_servers.search_intelligence_mcp import search_smart
        
        # Mock the service
        mock_service = Mock()
        mock_service.smart_search_with_preprocessing.return_value = [
            {
                "title": "Legal Document",
                "content": "This is legal content...",
                "source_type": "email",
                "relevance_score": 0.95
            }
        ]
        mock_service._expand_query.return_value = ["law", "judicial"]
        mock_get_service.return_value = mock_service
        
        # Test with query expansion enabled
        result = search_smart(
            query="legal",
            limit=10,
            use_expansion=True,
            content_type="email"
        )
        
        # Verify service method called with correct parameters
        expected_filters = {"content_types": ["email"]}
        mock_service.smart_search_with_preprocessing.assert_called_once_with(
            query="legal",
            limit=10,
            use_expansion=True,
            filters=expected_filters
        )
        
        # Verify expansion terms shown in output
        mock_service._expand_query.assert_called_once_with("legal")
        assert "Expanded Terms" in result
        assert "law, judicial" in result

    @patch('infrastructure.mcp_servers.search_intelligence_mcp.get_search_intelligence_service')
    def test_search_smart_no_expansion(self, mock_get_service):
        """Test search_smart without query expansion."""
        from infrastructure.mcp_servers.search_intelligence_mcp import search_smart
        
        mock_service = Mock()
        mock_service.smart_search_with_preprocessing.return_value = []
        mock_service._expand_query.return_value = []
        mock_get_service.return_value = mock_service
        
        # Test with expansion disabled
        result = search_smart(query="test", use_expansion=False)
        
        # Verify no expansion was attempted
        mock_service._expand_query.assert_called_once_with("test")
        assert "📭 No results found" in result

    @patch('infrastructure.mcp_servers.search_intelligence_mcp.SimpleDB')
    def test_search_summarize_parameter_validation(self, mock_db_class):
        """Test search_summarize parameter validation."""
        from infrastructure.mcp_servers.search_intelligence_mcp import search_summarize
        
        # Mock database and summarizer
        mock_db = Mock()
        mock_db.get_content.return_value = {
            "content": "This is a test document for summarization.",
            "title": "Test Document"
        }
        mock_db_class.return_value = mock_db
        
        with patch('infrastructure.mcp_servers.search_intelligence_mcp.get_document_summarizer') as mock_get_summarizer:
            mock_summarizer = Mock()
            mock_summarizer.extract_summary.return_value = {
                "sentences": ["This is a summary sentence."],
                "keywords": {"test": 0.8, "document": 0.7},
                "method": "combined",
                "word_count": 10
            }
            mock_get_summarizer.return_value = mock_summarizer
            
            # Test summarization with document_id
            result = search_summarize(
                document_id="test_doc_123",
                max_sentences=3,
                max_keywords=10
            )
            
            # Verify database query
            mock_db.get_content.assert_called_once_with("test_doc_123")
            
            # Verify summarizer call
            mock_summarizer.extract_summary.assert_called_once_with(
                text="This is a test document for summarization.",
                max_sentences=3,
                max_keywords=10,
                summary_type="combined"
            )
            
            # Verify output format
            assert "Document Summary" in result
            assert "Key Sentences" in result
            assert "Top Keywords" in result


class TestLegalIntelligenceMCPParameters:
    """Test Legal Intelligence MCP parameter validation."""

    @patch('infrastructure.mcp_servers.legal_intelligence_mcp.get_legal_intelligence_service')
    def test_legal_extract_entities_parameter_validation(self, mock_get_service):
        """Test legal entity extraction parameter validation."""
        from infrastructure.mcp_servers.legal_intelligence_mcp import legal_extract_entities
        
        # Mock the service
        mock_service = Mock()
        mock_service.extract_legal_entities.return_value = {
            "entities": [
                {"text": "John Doe", "label": "PERSON", "confidence": 0.95},
                {"text": "24NNCV06082", "label": "CASE_NUMBER", "confidence": 0.90}
            ]
        }
        mock_get_service.return_value = mock_service
        
        # Test entity extraction
        result = legal_extract_entities(
            content="This case John Doe vs Jane Smith, case 24NNCV06082",
            case_id="24NNCV"
        )
        
        # Verify service method called correctly
        mock_service.extract_legal_entities.assert_called_once_with(
            "This case John Doe vs Jane Smith, case 24NNCV06082",
            case_id="24NNCV"
        )
        
        # Verify output format
        assert "Legal Entity Extraction" in result
        assert "John Doe" in result
        assert "24NNCV06082" in result

    @patch('infrastructure.mcp_servers.legal_intelligence_mcp.get_legal_intelligence_service')
    def test_legal_timeline_events_parameter_validation(self, mock_get_service):
        """Test legal timeline parameter validation."""
        from infrastructure.mcp_servers.legal_intelligence_mcp import legal_timeline_events
        
        mock_service = Mock()
        mock_service.generate_case_timeline.return_value = {
            "events": [
                {
                    "date": "2024-06-08",
                    "event": "Case filed",
                    "document_id": "doc_123",
                    "importance": "high"
                }
            ],
            "gaps": [],
            "summary": "Timeline contains 1 event"
        }
        mock_get_service.return_value = mock_service
        
        # Test timeline generation
        result = legal_timeline_events(
            case_number="24NNCV06082",
            start_date="2024-01-01",
            end_date="2024-12-31"
        )
        
        # Verify service method called
        mock_service.generate_case_timeline.assert_called_once_with(
            "24NNCV06082",
            start_date="2024-01-01",
            end_date="2024-12-31"
        )
        
        assert "Legal Timeline" in result
        assert "Case filed" in result

    @patch('infrastructure.mcp_servers.legal_intelligence_mcp.get_legal_intelligence_service')
    def test_legal_knowledge_graph_parameter_validation(self, mock_get_service):
        """Test legal knowledge graph parameter validation."""
        from infrastructure.mcp_servers.legal_intelligence_mcp import legal_knowledge_graph
        
        mock_service = Mock()
        mock_service.build_relationship_graph.return_value = {
            "nodes": [{"id": "doc_1", "title": "Legal Doc 1"}],
            "edges": [{"source": "doc_1", "target": "doc_2", "weight": 0.8}],
            "stats": {"node_count": 1, "edge_count": 1}
        }
        mock_get_service.return_value = mock_service
        
        # Test knowledge graph building
        result = legal_knowledge_graph(
            case_number="24NNCV06082",
            include_relationships=True
        )
        
        # Verify service call
        mock_service.build_relationship_graph.assert_called_once_with(
            "24NNCV06082",
            include_relationships=True
        )
        
        assert "Legal Knowledge Graph" in result


class TestMCPErrorHandling:
    """Test MCP error handling for invalid parameters."""

    def test_search_entities_missing_parameters(self):
        """Test search_entities with missing required parameters."""
        from infrastructure.mcp_servers.search_intelligence_mcp import search_entities
        
        # Should handle missing both document_id and text
        result = search_entities()
        assert "Either document_id or text must be provided" in result

    @patch('infrastructure.mcp_servers.search_intelligence_mcp.get_search_intelligence_service')
    def test_search_entities_service_error_handling(self, mock_get_service):
        """Test search_entities error handling when service fails."""
        from infrastructure.mcp_servers.search_intelligence_mcp import search_entities
        
        # Mock service to raise exception
        mock_service = Mock()
        mock_service.extract_and_cache_entities.side_effect = Exception("Service error")
        mock_get_service.return_value = mock_service
        
        result = search_entities(document_id="test")
        
        # Should return error message, not raise exception
        assert "Error extracting entities" in result
        assert "Service error" in result

    def test_search_process_all_invalid_operation(self):
        """Test search_process_all with invalid operation."""
        from infrastructure.mcp_servers.search_intelligence_mcp import search_process_all
        
        result = search_process_all(operation="invalid_operation")
        
        assert "Unknown operation" in result
        assert "invalid_operation" in result