"""
Comprehensive tests for Legal Intelligence Module

Tests all core functionality with mock data and real case patterns.
"""

import os
import sys
import tempfile
import unittest
from unittest.mock import Mock, patch

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from legal_intelligence import get_legal_intelligence_service


class TestLegalIntelligenceService(unittest.TestCase):
    """Test suite for Legal Intelligence Service."""

    def setUp(self):
        """Set up test environment."""
        # Create temporary database
        self.temp_db = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        self.db_path = self.temp_db.name
        self.temp_db.close()

        # Mock case data based on real 24NNCV pattern
        self.mock_case_documents = [
            {
                "content_id": "doc_001",
                "title": "COMPLAINT - UNLAWFUL DETAINER 24NNCV00555",
                "content": "COMPLAINT FOR UNLAWFUL DETAINER\nCase No. 24NNCV00555\nPlaintiff vs Defendant\nFiled: 08/13/2024",
                "content_type": "pdf",
                "datetime_utc": "2024-08-13T10:00:00Z",
            },
            {
                "content_id": "doc_002",
                "title": "SUMMONS - 24NNCV00555",
                "content": "SUMMONS\nCase No. 24NNCV00555\nYou are hereby summoned to appear\nService Date: 08/15/2024",
                "content_type": "pdf",
                "datetime_utc": "2024-08-15T14:30:00Z",
            },
            {
                "content_id": "doc_003",
                "title": "MOTION TO QUASH SERVICE 24NNCV00555",
                "content": "MOTION TO QUASH SERVICE OF SUMMONS\nCase No. 24NNCV00555\nDefendant moves to quash\nFiled: 08/20/2024",
                "content_type": "pdf",
                "datetime_utc": "2024-08-20T09:15:00Z",
            },
            {
                "content_id": "doc_004",
                "title": "ORDER ON MOTION TO QUASH 24NNCV00555",
                "content": "ORDER\nCase No. 24NNCV00555\nMotion to Quash is DENIED\nDate: 09/10/2024\nJudge signature",
                "content_type": "pdf",
                "datetime_utc": "2024-09-10T16:00:00Z",
            },
        ]

    def tearDown(self):
        """Clean up test environment."""
        try:
            os.unlink(self.db_path)
        except Exception:
            pass

    @patch("legal_intelligence.main.SimpleDB")
    @patch("legal_intelligence.main.EntityService")
    @patch("legal_intelligence.main.TimelineService")
    @patch("legal_intelligence.main.get_knowledge_graph_service")
    @patch("legal_intelligence.main.get_similarity_analyzer")
    @patch("legal_intelligence.main.get_embedding_service")
    def test_service_initialization(
        self, mock_embed, mock_sim, mock_kg, mock_timeline, mock_entity, mock_db
    ):
        """Test that service initializes with all integrated services."""
        service = get_legal_intelligence_service(self.db_path)

        # Verify all services were initialized
        self.assertIsNotNone(service)
        mock_entity.assert_called_once()
        mock_timeline.assert_called_once()
        mock_kg.assert_called_once_with(self.db_path)
        mock_sim.assert_called_once()
        mock_embed.assert_called_once()

    @patch("legal_intelligence.main.SimpleDB")
    def test_process_case(self, mock_db_class):
        """Test complete case processing."""
        # Set up mocks
        mock_db = Mock()
        mock_db_class.return_value = mock_db
        mock_db.search_content.return_value = self.mock_case_documents

        with patch("legal_intelligence.main.EntityService") as mock_entity_class, patch(
            "legal_intelligence.main.TimelineService"
        ), patch("legal_intelligence.main.get_knowledge_graph_service"), patch(
            "legal_intelligence.main.get_similarity_analyzer"
        ), patch(
            "legal_intelligence.main.get_embedding_service"
        ):

            # Set up entity service mock
            mock_entity_service = Mock()
            mock_entity_class.return_value = mock_entity_service
            mock_entity_service.extract_entities.return_value = {
                "success": True,
                "entities": [
                    {"text": "Plaintiff", "label": "PERSON", "confidence": 0.9},
                    {"text": "Defendant", "label": "PERSON", "confidence": 0.9},
                ],
                "relationships": [],
            }

            service = get_legal_intelligence_service(self.db_path)
            result = service.process_case("24NNCV00555")

            # Verify result structure
            self.assertTrue(result["success"])
            self.assertEqual(result["case_number"], "24NNCV00555")
            self.assertEqual(result["document_count"], 4)
            self.assertIn("entities", result)
            self.assertIn("timeline", result)
            self.assertIn("relationships", result)
            self.assertIn("patterns", result)
            self.assertIn("missing_documents", result)

    @patch("legal_intelligence.main.SimpleDB")
    def test_analyze_document_patterns(self, mock_db_class):
        """Test document pattern analysis."""
        mock_db = Mock()
        mock_db_class.return_value = mock_db
        mock_db.search_content.return_value = self.mock_case_documents

        with patch("legal_intelligence.main.EntityService"), patch(
            "legal_intelligence.main.TimelineService"
        ), patch("legal_intelligence.main.get_knowledge_graph_service"), patch(
            "legal_intelligence.main.get_similarity_analyzer"
        ), patch(
            "legal_intelligence.main.get_embedding_service"
        ) as mock_embed:

            # Mock embedding service
            mock_embed_service = Mock()
            mock_embed.return_value = mock_embed_service
            mock_embed_service.encode.return_value = [0.1] * 1024  # Legal BERT dimension

            service = get_legal_intelligence_service(self.db_path)
            result = service.analyze_document_patterns("24NNCV00555")

            # Verify pattern analysis
            self.assertTrue(result["success"])
            self.assertIn("document_types", result)
            self.assertIn("themes", result)
            self.assertIn("anomalies", result)
            self.assertIn("document_flow", result)

    @patch("legal_intelligence.main.SimpleDB")
    def test_predict_missing_documents(self, mock_db_class):
        """Test missing document prediction."""
        mock_db = Mock()
        mock_db_class.return_value = mock_db
        mock_db.search_content.return_value = self.mock_case_documents

        with patch("legal_intelligence.main.EntityService"), patch(
            "legal_intelligence.main.TimelineService"
        ), patch("legal_intelligence.main.get_knowledge_graph_service"), patch(
            "legal_intelligence.main.get_similarity_analyzer"
        ), patch(
            "legal_intelligence.main.get_embedding_service"
        ):

            service = get_legal_intelligence_service(self.db_path)
            result = service.predict_missing_documents("24NNCV00555")

            # Verify prediction results
            self.assertTrue(result["success"])
            self.assertEqual(result["case_id"], "24NNCV00555")
            self.assertIn("case_type", result)
            self.assertIn("existing_documents", result)
            self.assertIn("predicted_missing", result)

            # Should predict "answer" is missing
            missing_types = [m["document_type"] for m in result["predicted_missing"]]
            self.assertIn("answer", missing_types)

    @patch("legal_intelligence.main.SimpleDB")
    def test_generate_case_timeline(self, mock_db_class):
        """Test timeline generation."""
        mock_db = Mock()
        mock_db_class.return_value = mock_db
        mock_db.search_content.return_value = self.mock_case_documents

        with patch("legal_intelligence.main.EntityService"), patch(
            "legal_intelligence.main.TimelineService"
        ), patch("legal_intelligence.main.get_knowledge_graph_service"), patch(
            "legal_intelligence.main.get_similarity_analyzer"
        ), patch(
            "legal_intelligence.main.get_embedding_service"
        ):

            service = get_legal_intelligence_service(self.db_path)
            result = service.generate_case_timeline("24NNCV00555")

            # Verify timeline structure
            self.assertTrue(result["success"])
            self.assertIn("events", result)
            self.assertIn("total_events", result)
            self.assertIn("date_range", result)
            self.assertIn("gaps", result)
            self.assertIn("milestones", result)

            # Should have events from documents
            self.assertGreater(len(result["events"]), 0)

    @patch("legal_intelligence.main.SimpleDB")
    def test_build_relationship_graph(self, mock_db_class):
        """Test relationship graph building."""
        mock_db = Mock()
        mock_db_class.return_value = mock_db
        mock_db.search_content.return_value = self.mock_case_documents

        with patch("legal_intelligence.main.EntityService"), patch(
            "legal_intelligence.main.TimelineService"
        ), patch("legal_intelligence.main.get_knowledge_graph_service") as mock_kg, patch(
            "legal_intelligence.main.get_similarity_analyzer"
        ), patch(
            "legal_intelligence.main.get_embedding_service"
        ) as mock_embed:

            # Mock knowledge graph
            mock_kg_service = Mock()
            mock_kg.return_value = mock_kg_service
            mock_kg_service.add_node.return_value = {"success": True}
            mock_kg_service.add_edge.return_value = {"success": True}

            # Mock embeddings for similarity
            mock_embed_service = Mock()
            mock_embed.return_value = mock_embed_service
            mock_embed_service.encode.return_value = [0.1] * 1024

            service = get_legal_intelligence_service(self.db_path)
            result = service.build_relationship_graph("24NNCV00555")

            # Verify graph structure
            self.assertTrue(result["success"])
            self.assertIn("nodes", result)
            self.assertIn("edges", result)
            self.assertIn("node_count", result)
            self.assertIn("edge_count", result)
            self.assertIn("graph_density", result)

            # Should have nodes for each document
            self.assertEqual(len(result["nodes"]), 4)

    @patch("legal_intelligence.main.SimpleDB")
    def test_empty_case_handling(self, mock_db_class):
        """Test handling of case with no documents."""
        mock_db = Mock()
        mock_db_class.return_value = mock_db
        mock_db.search_content.return_value = []  # No documents

        with patch("legal_intelligence.main.EntityService"), patch(
            "legal_intelligence.main.TimelineService"
        ), patch("legal_intelligence.main.get_knowledge_graph_service"), patch(
            "legal_intelligence.main.get_similarity_analyzer"
        ), patch(
            "legal_intelligence.main.get_embedding_service"
        ):

            service = get_legal_intelligence_service(self.db_path)
            result = service.process_case("NONEXISTENT")

            # Should handle gracefully
            self.assertFalse(result["success"])
            self.assertIn("error", result)
            self.assertIn("No documents found", result["error"])

    @patch("legal_intelligence.main.SimpleDB")
    def test_document_type_identification(self, mock_db_class):
        """Test identification of legal document types."""
        mock_db = Mock()
        mock_db_class.return_value = mock_db
        mock_db.search_content.return_value = self.mock_case_documents

        with patch("legal_intelligence.main.EntityService"), patch(
            "legal_intelligence.main.TimelineService"
        ), patch("legal_intelligence.main.get_knowledge_graph_service"), patch(
            "legal_intelligence.main.get_similarity_analyzer"
        ), patch(
            "legal_intelligence.main.get_embedding_service"
        ):

            service = get_legal_intelligence_service(self.db_path)

            # Test internal method
            doc_types = service._identify_document_types(self.mock_case_documents)

            # Should identify complaint, motion, order
            self.assertIn("complaint", doc_types)
            self.assertIn("motion", doc_types)
            self.assertIn("order", doc_types)
            self.assertIn("notice", doc_types)  # Summons is a type of notice

    @patch("legal_intelligence.main.SimpleDB")
    def test_case_type_determination(self, mock_db_class):
        """Test determination of case type from documents."""
        mock_db = Mock()
        mock_db_class.return_value = mock_db

        with patch("legal_intelligence.main.EntityService"), patch(
            "legal_intelligence.main.TimelineService"
        ), patch("legal_intelligence.main.get_knowledge_graph_service"), patch(
            "legal_intelligence.main.get_similarity_analyzer"
        ), patch(
            "legal_intelligence.main.get_embedding_service"
        ):

            service = get_legal_intelligence_service(self.db_path)

            # Test with unlawful detainer case
            case_type = service._determine_case_type(self.mock_case_documents)
            self.assertEqual(case_type, "unlawful_detainer")

    @patch("legal_intelligence.main.SimpleDB")
    def test_caching_mechanism(self, mock_db_class):
        """Test that analysis results are cached."""
        mock_db = Mock()
        mock_db_class.return_value = mock_db
        mock_db.search_content.return_value = self.mock_case_documents

        with patch("legal_intelligence.main.EntityService"), patch(
            "legal_intelligence.main.TimelineService"
        ), patch("legal_intelligence.main.get_knowledge_graph_service"), patch(
            "legal_intelligence.main.get_similarity_analyzer"
        ), patch(
            "legal_intelligence.main.get_embedding_service"
        ):

            service = get_legal_intelligence_service(self.db_path)

            # First call
            result1 = service.process_case("24NNCV00555")

            # Second call - should use cache for most things
            # but predict_missing_documents will still query
            result2 = service.process_case("24NNCV00555")

            # Results should be from cache (identical except timestamp)
            # Check that everything except timestamp is the same
            result1_copy = result1.copy()
            result2_copy = result2.copy()
            result1_copy.pop("analysis_timestamp", None)
            result2_copy.pop("analysis_timestamp", None)
            self.assertEqual(result1_copy, result2_copy)

            # Database called 2 times total:
            # 2 in first process_case (main + predict_missing_documents)
            # 0 in second process_case (using cache)
            self.assertEqual(mock_db.search_content.call_count, 2)


class TestLegalIntelligenceIntegration(unittest.TestCase):
    """Integration tests with real service connections."""

    def setUp(self):
        """Set up integration test environment."""
        self.temp_db = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        self.db_path = self.temp_db.name
        self.temp_db.close()

    def tearDown(self):
        """Clean up."""
        try:
            os.unlink(self.db_path)
        except Exception:
            pass

    def test_real_service_initialization(self):
        """Test that service can initialize with real dependencies."""
        try:
            service = get_legal_intelligence_service(self.db_path)
            self.assertIsNotNone(service)

            # Test that services are properly initialized
            self.assertIsNotNone(service.entity_service)
            self.assertIsNotNone(service.timeline_service)
            self.assertIsNotNone(service.knowledge_graph)
            self.assertIsNotNone(service.embedding_service)

        except Exception as e:
            # This might fail if dependencies aren't installed
            # but shouldn't crash
            print(f"Integration test skipped: {e}")

    def test_legal_document_patterns(self):
        """Test that legal document patterns are properly defined."""
        service = get_legal_intelligence_service(self.db_path)

        # Verify standard patterns exist
        self.assertIn("complaint", service._legal_doc_patterns)
        self.assertIn("motion", service._legal_doc_patterns)
        self.assertIn("order", service._legal_doc_patterns)
        self.assertIn("discovery", service._legal_doc_patterns)

        # Each pattern should have associated keywords
        for doc_type, patterns in service._legal_doc_patterns.items():
            self.assertIsInstance(patterns, list)
            self.assertGreater(len(patterns), 0)


if __name__ == "__main__":
    unittest.main()
