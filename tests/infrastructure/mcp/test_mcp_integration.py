#!/usr/bin/env python3
"""
Integration tests for MCP servers
Tests the Legal Intelligence and Search Intelligence MCP servers
"""

import json
import sys
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Import MCP server functions
from infrastructure.mcp_servers.legal_intelligence_mcp import (
    legal_case_tracking,
    legal_document_analysis,
    legal_extract_entities,
    legal_knowledge_graph,
    legal_relationship_discovery,
    legal_timeline_events,
)


class TestLegalIntelligenceMCP:
    """Test Legal Intelligence MCP Server functions"""

    @pytest.fixture
    def mock_legal_service(self):
        """Mock LegalIntelligenceService"""
        with patch("mcp_servers.legal_intelligence_mcp.LegalIntelligenceService") as mock:
            service = Mock()
            mock.return_value = service
            yield service

    @pytest.fixture
    def mock_entity_service(self):
        """Mock EntityService"""
        with patch("mcp_servers.legal_intelligence_mcp.EntityService") as mock:
            service = Mock()
            mock.return_value = service
            yield service

    @pytest.fixture
    def mock_simple_db(self):
        """Mock SimpleDB"""
        with patch("mcp_servers.legal_intelligence_mcp.SimpleDB") as mock:
            db = Mock()
            mock.return_value = db
            yield db

    def test_legal_extract_entities_success(self, mock_entity_service):
        """Test successful entity extraction"""
        # Setup mock response
        mock_entity_service.extract_email_entities.return_value = {
            "success": True,
            "entities": [
                {"text": "John Doe", "label": "PERSON", "confidence": 0.95},
                {"text": "ABC Corp", "label": "ORG", "confidence": 0.88},
            ],
            "relationships": [{"source": "John Doe", "target": "ABC Corp", "type": "represents"}],
        }

        # Call function
        result = legal_extract_entities("John Doe represents ABC Corp in case 24NNCV")

        # Verify result contains expected elements
        assert "Legal Entity Analysis" in result
        assert "John Doe" in result
        assert "ABC Corp" in result
        assert "Statistics" in result

    def test_legal_timeline_events_success(self, mock_legal_service):
        """Test timeline generation"""
        # Setup mock response
        mock_legal_service._get_case_documents.return_value = [
            {"content_id": "1", "title": "Complaint", "datetime_utc": "2024-01-01"}
        ]
        mock_legal_service.generate_case_timeline.return_value = {
            "success": True,
            "events": [
                {
                    "date": "2024-01-01",
                    "type": "filing_date",
                    "description": "Initial complaint filed",
                    "document_title": "Complaint",
                }
            ],
            "gaps": [],
            "milestones": [],
            "date_range": {"start": "2024-01-01", "end": "2024-01-01"},
        }

        # Call function
        result = legal_timeline_events("24NNCV00555")

        # Verify result
        assert "Legal Case Timeline" in result
        assert "24NNCV00555" in result
        assert "Chronological Events" in result

    def test_legal_knowledge_graph_success(self, mock_legal_service):
        """Test knowledge graph building"""
        # Setup mock response
        mock_legal_service._get_case_documents.return_value = [
            {"content_id": "1", "title": "Doc1"},
            {"content_id": "2", "title": "Doc2"},
        ]
        mock_legal_service.build_relationship_graph.return_value = {
            "success": True,
            "nodes": [
                {"id": "1", "title": "Doc1", "type": "document"},
                {"id": "2", "title": "Doc2", "type": "document"},
            ],
            "edges": [{"source": "1", "target": "2", "type": "similar_to", "strength": 0.75}],
            "node_count": 2,
            "edge_count": 1,
            "graph_density": 0.5,
        }

        # Call function
        result = legal_knowledge_graph("24NNCV00555")

        # Verify result
        assert "Legal Knowledge Graph" in result
        assert "Graph Statistics" in result
        assert "Document Nodes" in result

    def test_legal_document_analysis_comprehensive(self, mock_legal_service):
        """Test comprehensive document analysis"""
        # Setup mock response
        mock_legal_service._get_case_documents.return_value = [
            {"content_id": "1", "title": "Complaint", "content": "Legal complaint text"}
        ]
        mock_legal_service.process_case.return_value = {
            "success": True,
            "case_number": "24NNCV00555",
            "document_count": 1,
            "entities": {
                "total_entities": 10,
                "unique_entities": 5,
                "by_type": {"PERSON": ["John Doe"], "ORG": ["ABC Corp"]},
                "key_parties": [
                    {"text": "John Doe", "label": "PERSON"},
                    {"text": "ABC Corp", "label": "ORG"},
                ],
            },
            "timeline": {
                "success": True,
                "events": [{"date": "2024-01-01", "type": "filing"}],
                "date_range": {"start": "2024-01-01", "end": "2024-01-01"},
                "gaps": [],
            },
            "missing_documents": {"success": True, "predicted_missing": []},
            "analysis_timestamp": "2025-08-16T12:00:00",
        }

        # Call function
        result = legal_document_analysis("24NNCV00555", "comprehensive")

        # Verify result
        assert "Legal Document Analysis" in result
        assert "Case Summary" in result
        assert "Entity Analysis" in result
        assert "Timeline Summary" in result

    def test_legal_case_tracking_status(self, mock_legal_service):
        """Test case status tracking"""
        # Setup mock response
        mock_legal_service._get_case_documents.return_value = [
            {
                "content_id": "1",
                "title": "Complaint",
                "content": "Initial complaint",
                "datetime_utc": "2024-01-01",
            }
        ]
        mock_legal_service._identify_document_types.return_value = {"complaint"}
        mock_legal_service._determine_case_type.return_value = "civil_litigation"

        # Call function
        result = legal_case_tracking("24NNCV00555", "status")

        # Verify result
        assert "Legal Case Tracking" in result
        assert "Case Status" in result
        assert "Recent Activity" in result

    def test_legal_relationship_discovery(self, mock_legal_service, mock_simple_db):
        """Test relationship discovery"""
        # Setup mock response
        mock_legal_service._get_case_documents.return_value = [
            {"content_id": "1", "title": "Doc1", "content": "Content 1"}
        ]
        mock_legal_service._build_case_relationships.return_value = {
            "success": True,
            "edges": [{"source": "1", "target": "2", "strength": 0.8}],
            "nodes": [{"id": "1", "title": "Doc1"}],
        }
        mock_legal_service._extract_case_entities.return_value = {
            "relationships": [
                {
                    "source": "John Doe",
                    "target": "ABC Corp",
                    "type": "represents",
                    "confidence": 0.9,
                }
            ],
            "by_type": {"PERSON": ["John Doe"], "ORG": ["ABC Corp"]},
        }
        mock_simple_db.search_content.return_value = []

        # Call function
        result = legal_relationship_discovery("24NNCV00555")

        # Verify result
        assert "Legal Relationship Discovery" in result
        assert "Entity Relationships" in result
        assert "Document Relationships" in result

    def test_error_handling_no_services(self):
        """Test error handling when services unavailable"""
        with patch("mcp_servers.legal_intelligence_mcp.SERVICES_AVAILABLE", False):
            result = legal_extract_entities("test content")
            assert "not available" in result.lower()


class TestSearchIntelligenceMCPIntegration:
    """Test Search Intelligence MCP integration"""

    @pytest.fixture
    def mock_search_intelligence(self):
        """Mock SearchIntelligenceService"""
        with patch("search_intelligence.main.SearchIntelligenceService") as mock:
            service = Mock()
            mock.return_value = service
            yield service

    def test_smart_search_integration(self, mock_search_intelligence):
        """Test smart search with preprocessing"""
        # Setup mock
        mock_search_intelligence.smart_search_with_preprocessing.return_value = [
            {
                "content_id": "1",
                "title": "Test Document",
                "content": "Test content",
                "score": 0.95,
                "recency_score": 0.8,
                "combined_score": 0.88,
            }
        ]

        # Would call through CLI handler
        from tools.scripts.cli.intelligence_handler import smart_search_command

        # Execute command
        result = smart_search_command("test query", limit=5, use_expansion=True)

        # Verify success
        assert result is True

    def test_similarity_analysis_integration(self, mock_search_intelligence):
        """Test document similarity analysis"""
        # Setup mock
        mock_search_intelligence.analyze_document_similarity.return_value = [
            {"content_id": "2", "title": "Similar Doc", "similarity_score": 0.85}
        ]

        from tools.scripts.cli.intelligence_handler import similarity_command

        # Execute command
        result = similarity_command("doc_1", threshold=0.7)

        # Verify success
        assert result is True

    def test_clustering_integration(self, mock_search_intelligence):
        """Test content clustering"""
        # Setup mock
        mock_search_intelligence.cluster_similar_content.return_value = [
            {
                "cluster_id": 0,
                "size": 3,
                "documents": [
                    {"content_id": "1", "title": "Doc1"},
                    {"content_id": "2", "title": "Doc2"},
                    {"content_id": "3", "title": "Doc3"},
                ],
            }
        ]

        from tools.scripts.cli.intelligence_handler import cluster_command

        # Execute command
        result = cluster_command(threshold=0.7, limit=100)

        # Verify success
        assert result is True


class TestMCPServerIntegration:
    """Test MCP server configuration and initialization"""

    def test_mcp_config_exists(self):
        """Test that .mcp.json exists and is valid"""
        mcp_config_path = Path(__file__).parent.parent / ".mcp.json"
        assert mcp_config_path.exists(), ".mcp.json configuration file not found"

        # Load and validate JSON
        with open(mcp_config_path) as f:
            config = json.load(f)

        # Check for expected servers
        assert "mcpServers" in config
        servers = config["mcpServers"]

        # Verify Legal Intelligence server configured
        assert "legal-intelligence" in servers
        legal_config = servers["legal-intelligence"]
        assert legal_config["type"] == "stdio"
        assert "legal_intelligence_mcp.py" in legal_config["args"][-1]

    def test_mcp_server_files_exist(self):
        """Test that MCP server files exist"""
        mcp_dir = Path(__file__).parent.parent / "mcp_servers"

        # Check critical MCP server files
        required_files = ["legal_intelligence_mcp.py", "__init__.py"]

        for filename in required_files:
            filepath = mcp_dir / filename
            assert filepath.exists(), f"MCP server file {filename} not found"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
