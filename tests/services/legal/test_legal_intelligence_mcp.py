"""
Tests for Legal Intelligence MCP Server

Tests the unified legal intelligence MCP server including all 6 tools:
- legal_extract_entities
- legal_timeline_events
- legal_knowledge_graph
- legal_document_analysis
- legal_case_tracking
- legal_relationship_discovery
"""

import os
import sys
from unittest.mock import MagicMock, patch

import pytest

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import the MCP server functions
from infrastructure.mcp_servers.legal_intelligence_mcp import (
    SERVICES_AVAILABLE,
    LegalIntelligenceServer,
    legal_case_tracking,
    legal_document_analysis,
    legal_extract_entities,
    legal_knowledge_graph,
    legal_relationship_discovery,
    legal_timeline_events,
)


class TestLegalExtractEntities:
    """Test legal entity extraction functionality"""

    def test_extract_entities_basic(self):
        """Test basic entity extraction"""
        if not SERVICES_AVAILABLE:
            pytest.skip("Legal intelligence services not available")

        content = (
            "John Doe, attorney for plaintiff, filed motion in case 24NNCV00555 before Judge Smith."
        )

        with patch("mcp_servers.legal_intelligence_mcp.EntityService") as mock_entity:
            mock_entity_instance = MagicMock()
            mock_entity.return_value = mock_entity_instance

            mock_entity_instance.extract_email_entities.return_value = {
                "success": True,
                "entities": [
                    {"text": "John Doe", "label": "PERSON", "confidence": 0.95},
                    {"text": "Judge Smith", "label": "JUDGE", "confidence": 0.92},
                    {"text": "24NNCV00555", "label": "CASE_NUMBER", "confidence": 0.98},
                ],
                "relationships": [
                    {"source": "John Doe", "target": "24NNCV00555", "type": "attorney_in_case"}
                ],
            }

            result = legal_extract_entities(content, "test_case")

            assert "🧠 Legal Entity Analysis" in result
            assert "John Doe" in result
            assert "Judge Smith" in result
            assert "24NNCV00555" in result
            assert "PERSON" in result
            assert "JUDGE" in result
            assert "Total entities: 3" in result

    def test_extract_entities_error_handling(self):
        """Test entity extraction error handling"""
        if not SERVICES_AVAILABLE:
            pytest.skip("Legal intelligence services not available")

        with patch("mcp_servers.legal_intelligence_mcp.EntityService") as mock_entity:
            mock_entity_instance = MagicMock()
            mock_entity.return_value = mock_entity_instance

            mock_entity_instance.extract_email_entities.return_value = {
                "success": False,
                "error": "Entity extraction failed",
            }

            result = legal_extract_entities("test content")

            assert "❌ Entity extraction failed" in result
            assert "Entity extraction failed" in result

    def test_extract_entities_no_services(self):
        """Test behavior when services are not available"""
        with patch("mcp_servers.legal_intelligence_mcp.SERVICES_AVAILABLE", False):
            result = legal_extract_entities("test content")
            assert "Legal intelligence services not available" in result


class TestLegalTimelineEvents:
    """Test legal timeline generation functionality"""

    def test_timeline_events_basic(self):
        """Test basic timeline generation"""
        if not SERVICES_AVAILABLE:
            pytest.skip("Legal intelligence services not available")

        case_number = "24NNCV00555"

        with patch("mcp_servers.legal_intelligence_mcp.LegalIntelligenceService") as mock_legal:
            mock_legal_instance = MagicMock()
            mock_legal.return_value = mock_legal_instance

            mock_legal_instance.generate_case_timeline.return_value = {
                "success": True,
                "events": [
                    {
                        "date": "2024-01-15",
                        "type": "filing_date",
                        "description": "Complaint filed",
                        "document_title": "Initial Complaint",
                    },
                    {
                        "date": "2024-02-01",
                        "type": "service_date",
                        "description": "Defendant served",
                        "document_title": "Proof of Service",
                    },
                ],
                "gaps": [
                    {
                        "start": "2024-02-01",
                        "end": "2024-03-15",
                        "duration_days": 43,
                        "significance": "medium",
                    }
                ],
                "milestones": [
                    {"date": "2024-01-15", "type": "filing_date", "description": "Case initiated"}
                ],
                "date_range": {"start": "2024-01-15", "end": "2024-02-01"},
            }

            result = legal_timeline_events(case_number)

            assert f"📅 Legal Case Timeline: {case_number}" in result
            assert "Complaint filed" in result
            assert "Defendant served" in result
            assert "Timeline Gaps Detected" in result
            assert "Key Milestones" in result
            assert "2024-01-15" in result

    def test_timeline_events_with_date_filter(self):
        """Test timeline generation with date filtering"""
        if not SERVICES_AVAILABLE:
            pytest.skip("Legal intelligence services not available")

        with patch("mcp_servers.legal_intelligence_mcp.LegalIntelligenceService") as mock_legal:
            mock_legal_instance = MagicMock()
            mock_legal.return_value = mock_legal_instance

            mock_legal_instance.generate_case_timeline.return_value = {
                "success": True,
                "events": [
                    {"date": "2024-01-15", "type": "filing", "description": "Early event"},
                    {"date": "2024-03-15", "type": "motion", "description": "Later event"},
                ],
                "gaps": [],
                "milestones": [],
                "date_range": {"start": "2024-01-15", "end": "2024-03-15"},
            }

            result = legal_timeline_events("24NNCV00555", "2024-02-01", "2024-04-01")

            assert "Filtered by: 2024-02-01 to 2024-04-01" in result
            assert "Later event" in result

    def test_timeline_events_error(self):
        """Test timeline generation error handling"""
        if not SERVICES_AVAILABLE:
            pytest.skip("Legal intelligence services not available")

        with patch("mcp_servers.legal_intelligence_mcp.LegalIntelligenceService") as mock_legal:
            mock_legal_instance = MagicMock()
            mock_legal.return_value = mock_legal_instance

            mock_legal_instance.generate_case_timeline.return_value = {
                "success": False,
                "error": "No timeline data found",
            }

            result = legal_timeline_events("INVALID_CASE")

            assert "❌ Timeline generation failed" in result


class TestLegalKnowledgeGraph:
    """Test legal knowledge graph functionality"""

    def test_knowledge_graph_basic(self):
        """Test basic knowledge graph generation"""
        if not SERVICES_AVAILABLE:
            pytest.skip("Legal intelligence services not available")

        case_number = "24NNCV00555"

        with patch("mcp_servers.legal_intelligence_mcp.LegalIntelligenceService") as mock_legal:
            mock_legal_instance = MagicMock()
            mock_legal.return_value = mock_legal_instance

            mock_legal_instance.build_relationship_graph.return_value = {
                "success": True,
                "nodes": [
                    {
                        "id": "doc1",
                        "title": "Complaint",
                        "metadata": {"content_type": "legal_document"},
                    },
                    {
                        "id": "doc2",
                        "title": "Answer",
                        "metadata": {"content_type": "legal_document"},
                    },
                ],
                "edges": [
                    {"source": "doc1", "target": "doc2", "type": "similar_to", "strength": 0.75}
                ],
                "node_count": 2,
                "edge_count": 1,
                "graph_density": 0.5,
            }

            result = legal_knowledge_graph(case_number)

            assert f"🕸️ Legal Knowledge Graph: {case_number}" in result
            assert "Nodes (documents): 2" in result
            assert "Edges (relationships): 1" in result
            assert "Graph density: 0.500" in result
            assert "Complaint" in result
            assert "Answer" in result

    def test_knowledge_graph_without_relationships(self):
        """Test knowledge graph without relationship details"""
        if not SERVICES_AVAILABLE:
            pytest.skip("Legal intelligence services not available")

        with patch("mcp_servers.legal_intelligence_mcp.LegalIntelligenceService") as mock_legal:
            mock_legal_instance = MagicMock()
            mock_legal.return_value = mock_legal_instance

            mock_legal_instance.build_relationship_graph.return_value = {
                "success": True,
                "nodes": [{"id": "doc1", "title": "Test Doc", "metadata": {}}],
                "edges": [],
                "node_count": 1,
                "edge_count": 0,
                "graph_density": 0.0,
            }

            result = legal_knowledge_graph("24NNCV00555", include_relationships=False)

            assert "🕸️ Legal Knowledge Graph" in result
            assert "Test Doc" in result


class TestLegalDocumentAnalysis:
    """Test legal document analysis functionality"""

    def test_document_analysis_comprehensive(self):
        """Test comprehensive document analysis"""
        if not SERVICES_AVAILABLE:
            pytest.skip("Legal intelligence services not available")

        case_number = "24NNCV00555"

        with patch("mcp_servers.legal_intelligence_mcp.LegalIntelligenceService") as mock_legal:
            mock_legal_instance = MagicMock()
            mock_legal.return_value = mock_legal_instance

            mock_legal_instance.process_case.return_value = {
                "success": True,
                "document_count": 5,
                "analysis_timestamp": "2024-01-15T10:30:00",
                "entities": {
                    "total_entities": 15,
                    "unique_entities": 12,
                    "by_type": {"PERSON": ["John Doe", "Jane Smith"], "ORG": ["ABC Corp"]},
                    "key_parties": [
                        {"text": "John Doe", "label": "PERSON"},
                        {"text": "ABC Corp", "label": "ORG"},
                    ],
                },
                "timeline": {
                    "success": True,
                    "events": [{"date": "2024-01-15", "type": "filing"}],
                    "date_range": {"start": "2024-01-15", "end": "2024-02-15"},
                    "gaps": [{"start": "2024-01-20", "end": "2024-02-10"}],
                },
                "missing_documents": {
                    "success": True,
                    "predicted_missing": [
                        {
                            "document_type": "answer",
                            "confidence": 0.8,
                            "reason": "Expected response not found",
                        }
                    ],
                },
            }

            result = legal_document_analysis(case_number, "comprehensive")

            assert f"📊 Legal Document Analysis: {case_number}" in result
            assert "Total documents: 5" in result
            assert "Total entities: 15" in result
            assert "John Doe" in result
            assert "ABC Corp" in result
            assert "Timeline Summary" in result
            assert "Predicted Missing Documents" in result
            assert "Answer: 80% confidence" in result

    def test_document_analysis_patterns(self):
        """Test pattern-specific document analysis"""
        if not SERVICES_AVAILABLE:
            pytest.skip("Legal intelligence services not available")

        with patch("mcp_servers.legal_intelligence_mcp.LegalIntelligenceService") as mock_legal:
            mock_legal_instance = MagicMock()
            mock_legal.return_value = mock_legal_instance

            mock_legal_instance.analyze_document_patterns.return_value = {
                "success": True,
                "document_types": {"complaint", "motion", "order"},
                "themes": [{"theme": "procedural", "prevalence": 0.8, "document_count": 4}],
                "anomalies": [{"type": "potential_duplicate", "confidence": 0.95}],
                "document_flow": {
                    "total_documents": 5,
                    "date_range": {"start": "2024-01-15", "end": "2024-02-15"},
                },
            }

            result = legal_document_analysis("24NNCV00555", "patterns")

            assert "📋 Document Pattern Analysis" in result
            assert "complaint, motion, order" in result
            assert "Procedural: 80% prevalence" in result
            assert "Potential Duplicate: 95% confidence" in result


class TestLegalCaseTracking:
    """Test legal case tracking functionality"""

    def test_case_tracking_status(self):
        """Test case status tracking"""
        if not SERVICES_AVAILABLE:
            pytest.skip("Legal intelligence services not available")

        case_number = "24NNCV00555"

        with patch("mcp_servers.legal_intelligence_mcp.LegalIntelligenceService") as mock_legal:
            mock_legal_instance = MagicMock()
            mock_legal.return_value = mock_legal_instance

            # Mock case documents
            mock_documents = [
                {"title": "Initial Complaint", "datetime_utc": "2024-01-15T10:00:00"},
                {"title": "Defendant's Answer", "datetime_utc": "2024-02-01T14:30:00"},
            ]

            mock_legal_instance._get_case_documents.return_value = mock_documents
            mock_legal_instance._identify_document_types.return_value = {"complaint", "answer"}
            mock_legal_instance._determine_case_type.return_value = "civil_litigation"

            result = legal_case_tracking(case_number, "status")

            assert f"📋 Legal Case Tracking: {case_number}" in result
            assert "Case type: Civil Litigation" in result
            assert "Documents filed: 2" in result
            assert "Current stage: Responsive pleadings" in result
            assert "Initial Complaint" in result

    def test_case_tracking_missing(self):
        """Test missing document tracking"""
        if not SERVICES_AVAILABLE:
            pytest.skip("Legal intelligence services not available")

        with patch("mcp_servers.legal_intelligence_mcp.LegalIntelligenceService") as mock_legal:
            mock_legal_instance = MagicMock()
            mock_legal.return_value = mock_legal_instance

            mock_legal_instance._get_case_documents.return_value = [
                {"title": "Complaint", "content": "test content"}
            ]

            mock_legal_instance.predict_missing_documents.return_value = {
                "success": True,
                "case_type": "civil_litigation",
                "existing_documents": ["complaint"],
                "predicted_missing": [
                    {
                        "document_type": "answer",
                        "confidence": 0.8,
                        "reason": "Expected response not found",
                    }
                ],
            }

            result = legal_case_tracking("24NNCV00555", "missing")

            assert "🔍 Missing Document Analysis" in result
            assert "Answer: 80% confidence" in result
            assert "Expected response not found" in result

    def test_case_tracking_deadlines(self):
        """Test deadline tracking"""
        if not SERVICES_AVAILABLE:
            pytest.skip("Legal intelligence services not available")

        with patch("mcp_servers.legal_intelligence_mcp.LegalIntelligenceService") as mock_legal:
            mock_legal_instance = MagicMock()
            mock_legal.return_value = mock_legal_instance

            mock_documents = [
                {
                    "title": "Motion Notice",
                    "content": "Response due by 02/15/2024 to the court motion filed...",
                }
            ]

            mock_legal_instance._get_case_documents.return_value = mock_documents

            result = legal_case_tracking("24NNCV00555", "deadlines")

            assert "⏰ Deadline Tracking" in result
            assert "02/15/2024" in result or "potential deadlines" in result


class TestLegalRelationshipDiscovery:
    """Test legal relationship discovery functionality"""

    def test_relationship_discovery_basic(self):
        """Test basic relationship discovery"""
        if not SERVICES_AVAILABLE:
            pytest.skip("Legal intelligence services not available")

        case_number = "24NNCV00555"

        with patch("mcp_servers.legal_intelligence_mcp.LegalIntelligenceService") as mock_legal:
            with patch("mcp_servers.legal_intelligence_mcp.get_knowledge_graph_service"):
                mock_legal_instance = MagicMock()
                mock_legal.return_value = mock_legal_instance

                mock_documents = [
                    {"content_id": "doc1", "title": "Complaint", "content": "test content"}
                ]

                mock_legal_instance._get_case_documents.return_value = mock_documents

                mock_legal_instance._build_case_relationships.return_value = {
                    "success": True,
                    "nodes": [{"id": "doc1", "title": "Complaint"}],
                    "edges": [{"source": "doc1", "target": "doc2", "strength": 0.85}],
                }

                mock_legal_instance._extract_case_entities.return_value = {
                    "relationships": [
                        {
                            "source": "John Doe",
                            "target": "ABC Corp",
                            "type": "attorney_for",
                            "confidence": 0.9,
                        }
                    ],
                    "by_type": {"PERSON": ["John Doe"], "ORG": ["ABC Corp"]},
                }

                result = legal_relationship_discovery(case_number)

                assert f"🔗 Legal Relationship Discovery: {case_number}" in result
                assert "Entity Relationships" in result
                assert "Document Relationships" in result
                assert "John Doe" in result
                assert "ABC Corp" in result

    def test_relationship_discovery_with_focus(self):
        """Test relationship discovery with entity focus"""
        if not SERVICES_AVAILABLE:
            pytest.skip("Legal intelligence services not available")

        with patch("mcp_servers.legal_intelligence_mcp.LegalIntelligenceService") as mock_legal:
            with patch("mcp_servers.legal_intelligence_mcp.get_knowledge_graph_service"):
                mock_legal_instance = MagicMock()
                mock_legal.return_value = mock_legal_instance

                mock_legal_instance._get_case_documents.return_value = [
                    {"content_id": "doc1", "title": "Test Doc"}
                ]

                mock_legal_instance._build_case_relationships.return_value = {
                    "success": True,
                    "nodes": [],
                    "edges": [],
                }

                mock_legal_instance._extract_case_entities.return_value = {
                    "relationships": [
                        {"source": "John Doe", "target": "ABC Corp", "type": "attorney_for"},
                        {"source": "Jane Smith", "target": "XYZ Corp", "type": "attorney_for"},
                    ],
                    "by_type": {"PERSON": ["John Doe", "Jane Smith"]},
                }

                result = legal_relationship_discovery("24NNCV00555", "John Doe")

                assert "Filtered by 'John Doe'" in result


class TestLegalIntelligenceServer:
    """Test the MCP server class"""

    @pytest.mark.asyncio
    async def test_server_initialization(self):
        """Test server initializes correctly"""
        server = LegalIntelligenceServer()
        assert server.server is not None
        assert server.server.name == "legal-intelligence-server"

    @pytest.mark.asyncio
    async def test_list_tools(self):
        """Test tool registration"""
        server = LegalIntelligenceServer()

        # Get the list_tools handler
        list_tools_handler = None
        for handler in server.server._tool_list_handlers:
            list_tools_handler = handler
            break

        assert list_tools_handler is not None

        tools = await list_tools_handler()

        assert len(tools) == 6
        tool_names = [tool.name for tool in tools]

        expected_tools = [
            "legal_extract_entities",
            "legal_timeline_events",
            "legal_knowledge_graph",
            "legal_document_analysis",
            "legal_case_tracking",
            "legal_relationship_discovery",
        ]

        for expected_tool in expected_tools:
            assert expected_tool in tool_names

    @pytest.mark.asyncio
    async def test_call_tool_unknown(self):
        """Test calling unknown tool"""
        server = LegalIntelligenceServer()

        # Get the call_tool handler
        call_tool_handler = None
        for handler in server.server._tool_call_handlers:
            call_tool_handler = handler
            break

        assert call_tool_handler is not None

        result = await call_tool_handler("unknown_tool", {})

        assert len(result) == 1
        assert "Unknown tool: unknown_tool" in result[0].text

    @pytest.mark.asyncio
    async def test_call_tool_with_error(self):
        """Test tool call error handling"""
        server = LegalIntelligenceServer()

        # Get the call_tool handler
        call_tool_handler = None
        for handler in server.server._tool_call_handlers:
            call_tool_handler = handler
            break

        # Test with missing required argument
        result = await call_tool_handler("legal_extract_entities", {})

        assert len(result) == 1
        assert "Error executing" in result[0].text


class TestIntegration:
    """Integration tests for the legal intelligence MCP server"""

    def test_end_to_end_entity_extraction(self):
        """Test complete entity extraction workflow"""
        if not SERVICES_AVAILABLE:
            pytest.skip("Legal intelligence services not available")

        content = """
        Case 24NNCV00555: John Doe, Esq. representing plaintiff ABC Corporation
        in breach of contract action against defendant XYZ Inc.
        Motion filed before Judge Smith on January 15, 2024.
        """

        with patch("mcp_servers.legal_intelligence_mcp.LegalIntelligenceService"):
            with patch("mcp_servers.legal_intelligence_mcp.EntityService") as mock_entity:
                mock_entity_instance = MagicMock()
                mock_entity.return_value = mock_entity_instance

                mock_entity_instance.extract_email_entities.return_value = {
                    "success": True,
                    "entities": [
                        {"text": "24NNCV00555", "label": "CASE_NUMBER", "confidence": 0.98},
                        {"text": "John Doe", "label": "ATTORNEY", "confidence": 0.95},
                        {"text": "ABC Corporation", "label": "ORG", "confidence": 0.92},
                        {"text": "XYZ Inc", "label": "ORG", "confidence": 0.90},
                        {"text": "Judge Smith", "label": "JUDGE", "confidence": 0.88},
                    ],
                    "relationships": [],
                }

                result = legal_extract_entities(content, "24NNCV00555")

                # Verify comprehensive output
                assert "🧠 Legal Entity Analysis" in result
                assert "CASE_NUMBER" in result
                assert "ATTORNEY" in result
                assert "JUDGE" in result
                assert "ORG" in result
                assert "24NNCV00555" in result
                assert "John Doe" in result
                assert "Judge Smith" in result
                assert "Total entities: 5" in result

    def test_services_not_available_graceful_degradation(self):
        """Test graceful degradation when services are not available"""
        with patch("mcp_servers.legal_intelligence_mcp.SERVICES_AVAILABLE", False):
            # Test all functions handle service unavailability gracefully
            functions_to_test = [
                (legal_extract_entities, ("test content",)),
                (legal_timeline_events, ("24NNCV00555",)),
                (legal_knowledge_graph, ("24NNCV00555",)),
                (legal_document_analysis, ("24NNCV00555",)),
                (legal_case_tracking, ("24NNCV00555",)),
                (legal_relationship_discovery, ("24NNCV00555",)),
            ]

            for func, args in functions_to_test:
                result = func(*args)
                assert "not available" in result.lower()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
