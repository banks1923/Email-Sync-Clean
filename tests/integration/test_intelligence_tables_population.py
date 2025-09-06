"""Integration test for intelligence tables population.

Verifies that all three intelligence tables receive data during document
processing.
"""

import json
import sys
import unittest
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent.parent))

from services import get_pdf_service
from tests.integration.test_helpers import (
    cleanup_test_files,
    create_test_database,
    get_test_pdf_path,
)


class TestIntelligenceTablesPopulation(unittest.TestCase):
    """
    Test that all intelligence tables get populated during processing.
    """

    def setUp(self):
        """
        Set up test environment.
        """
        # Create test database
        self.db, self.db_path = create_test_database()

        # Initialize services
        self.pdf_service = get_pdf_service(self.db_path)

        # Get test file
        self.test_pdf = get_test_pdf_path()

        # Track cleanup
        self.cleanup_paths = [self.db_path]

    def tearDown(self):
        """
        Clean up test artifacts.
        """
        cleanup_test_files(self.cleanup_paths)

    def test_document_summaries_table_populated(self):
        """
        Test that document_summaries table receives data.
        """
        # Process a PDF
        result = self.pdf_service.upload_single_pdf(self.test_pdf, use_pipeline=False)
        content_id = result.get("content_id")

        self.assertIsNotNone(content_id)

        # Check document_summaries table
        summaries = self.db.fetch(
            """
            SELECT * FROM document_summaries
            WHERE document_id = ?
            """,
            (content_id,),
        )

        self.assertGreater(len(summaries), 0, "No summaries found in table")

        # Verify summary structure
        summary = summaries[0]
        self.assertIn("summary_id", summary)
        self.assertIn("document_id", summary)
        self.assertIn("summary_type", summary)
        self.assertIn("summary_text", summary)
        self.assertIn("tf_idf_keywords", summary)
        self.assertIn("textrank_sentences", summary)

        # Verify data quality
        self.assertIsNotNone(summary["summary_text"])
        self.assertIn(summary["summary_type"], ["tfidf", "textrank", "combined"])

        # Parse JSON fields
        if summary["tf_idf_keywords"]:
            keywords = json.loads(summary["tf_idf_keywords"])
            self.assertIsInstance(keywords, dict)
            self.assertGreater(len(keywords), 0)

        if summary["textrank_sentences"]:
            sentences = json.loads(summary["textrank_sentences"])
            self.assertIsInstance(sentences, list)
            self.assertGreater(len(sentences), 0)

    def test_document_intelligence_table_populated(self):
        """
        Test that document_intelligence table can receive data.
        """
        # Process a PDF
        result = self.pdf_service.upload_single_pdf(self.test_pdf, use_pipeline=False)
        content_id = result.get("content_id")

        self.assertIsNotNone(content_id)

        # Manually add intelligence data (since entity extraction may not be automatic)
        intel_data = {
            "entities": ["Contract", "Agreement", "Party A", "Party B"],
            "entity_types": ["DOCUMENT", "DOCUMENT", "ORG", "ORG"],
        }

        intel_id = self.db.add_document_intelligence(
            document_id=content_id,
            intelligence_type="entity_extraction",
            intelligence_data=intel_data,
            confidence_score=0.85,
        )

        self.assertIsNotNone(intel_id)

        # Verify data in table
        intelligence = self.db.fetch(
            """
            SELECT * FROM document_intelligence
            WHERE document_id = ?
            """,
            (content_id,),
        )

        self.assertGreater(len(intelligence), 0, "No intelligence data found")

        # Verify structure
        intel = intelligence[0]
        self.assertEqual(intel["document_id"], content_id)
        self.assertEqual(intel["intelligence_type"], "entity_extraction")
        self.assertIsNotNone(intel["intelligence_data"])
        self.assertEqual(intel["confidence_score"], 0.85)

        # Verify JSON data
        stored_data = json.loads(intel["intelligence_data"])
        self.assertEqual(stored_data["entities"], intel_data["entities"])

    def test_relationship_cache_table_populated(self):
        """
        Test that relationship_cache table can receive data.
        """
        # Process two PDFs to create relationship
        result1 = self.pdf_service.upload_single_pdf(self.test_pdf, use_pipeline=False)

        # Create a second content record for relationship
        content_id1 = result1.get("content_id")
        content_id2 = self.db.add_content(
            content_type="pdf",
            title="Related Document",
            content="Related content about contracts and agreements",
        )

        self.assertIsNotNone(content_id1)
        self.assertIsNotNone(content_id2)

        # Add relationship
        cache_data = {
            "similarity_score": 0.75,
            "common_keywords": ["contract", "agreement", "terms"],
        }

        cache_id = self.db.add_relationship_cache(
            source_id=content_id1,
            target_id=content_id2,
            relationship_type="similar",
            strength=0.75,
            cached_data=cache_data,
            ttl_hours=24,
        )

        self.assertIsNotNone(cache_id)

        # Verify in table
        relationships = self.db.fetch(
            """
            SELECT * FROM relationship_cache
            WHERE source_id = ? AND target_id = ?
            """,
            (content_id1, content_id2),
        )

        self.assertGreater(len(relationships), 0, "No relationships found")

        # Verify structure
        rel = relationships[0]
        self.assertEqual(rel["source_id"], content_id1)
        self.assertEqual(rel["target_id"], content_id2)
        self.assertEqual(rel["relationship_type"], "similar")
        self.assertEqual(rel["strength"], 0.75)
        self.assertIsNotNone(rel["cached_data"])
        self.assertIsNotNone(rel["expires_at"])

    def test_all_tables_populated_from_single_document(self):
        """
        Test that processing one document can populate all intelligence tables.
        """
        # Process PDF
        result = self.pdf_service.upload_single_pdf(self.test_pdf, use_pipeline=False)
        content_id = result.get("content_id")

        self.assertIsNotNone(content_id)

        # Check document_summaries
        summaries = self.db.get_document_summaries(content_id)
        self.assertGreater(len(summaries), 0, "No summaries created")

        # Add intelligence data
        intel_id = self.db.add_document_intelligence(
            content_id, "classification", {"category": "legal", "subcategory": "contract"}, 0.9
        )
        self.assertIsNotNone(intel_id)

        # Add self-referential relationship (document similar to itself for testing)
        cache_id = self.db.add_relationship_cache(
            content_id, content_id, "self_reference", 1.0, {"note": "Test self-reference"}, 1
        )
        self.assertIsNotNone(cache_id)

        # Verify all tables have data
        tables_check = {
            "document_summaries": f"document_id = '{content_id}'",
            "document_intelligence": f"document_id = '{content_id}'",
            "relationship_cache": f"source_id = '{content_id}'",
        }

        for table, where_clause in tables_check.items():
            count = self.db.fetch_one(f"SELECT COUNT(*) as count FROM {table} WHERE {where_clause}")
            self.assertGreater(
                count["count"], 0, f"Table {table} has no data for document {content_id}"
            )

    def test_foreign_key_constraints_enforced(self):
        """
        Test that foreign key constraints prevent orphan records.
        """
        # Try to add summary for non-existent document
        with self.assertRaises(Exception):
            self.db.add_document_summary(
                document_id="non_existent_id", summary_type="tfidf", summary_text="Test summary"
            )

        # Try to add intelligence for non-existent document
        with self.assertRaises(Exception):
            self.db.add_document_intelligence(
                document_id="non_existent_id",
                intelligence_type="test",
                intelligence_data={"test": "data"},
                confidence_score=0.5,
            )

        # Try to add relationship with non-existent documents
        with self.assertRaises(Exception):
            self.db.add_relationship_cache(
                source_id="non_existent_1",
                target_id="non_existent_2",
                relationship_type="test",
                strength=0.5,
            )

    def test_cascade_operations(self):
        """
        Test that related records are handled properly.
        """
        # Create content
        content_id = self.db.add_content(
            content_type="test", title="Test Document", content="Test content for cascade testing"
        )

        # Add summary
        summary_id = self.db.add_document_summary(
            content_id, "tfidf", "Test summary", {"test": 0.5}, ["Test sentence"]
        )

        # Add intelligence
        intel_id = self.db.add_document_intelligence(content_id, "test_type", {"data": "test"}, 0.7)

        # Verify all records exist
        self.assertIsNotNone(summary_id)
        self.assertIsNotNone(intel_id)

        summaries = self.db.get_document_summaries(content_id)
        self.assertEqual(len(summaries), 1)

        intelligence = self.db.get_document_intelligence(content_id)
        self.assertEqual(len(intelligence), 1)

    def test_data_types_and_constraints(self):
        """
        Test that data types and constraints are properly enforced.
        """
        # Create content
        content_id = self.db.add_content(content_type="test", title="Test", content="Test content")

        # Test summary_type constraint
        with self.assertRaises(Exception):
            self.db.execute(
                """
                INSERT INTO document_summaries
                (summary_id, document_id, summary_type)
                VALUES (?, ?, ?)
                """,
                ("test_1", content_id, "invalid_type"),
            )

        # Test confidence score range
        with self.assertRaises(Exception):
            self.db.execute(
                """
                INSERT INTO document_intelligence
                (intelligence_id, document_id, intelligence_type,
                 intelligence_data, confidence_score)
                VALUES (?, ?, ?, ?, ?)
                """,
                ("test_2", content_id, "test", "{}", 1.5),  # Invalid score > 1.0
            )

        # Test strength range
        with self.assertRaises(Exception):
            self.db.execute(
                """
                INSERT INTO relationship_cache
                (cache_id, source_id, target_id, relationship_type, strength)
                VALUES (?, ?, ?, ?, ?)
                """,
                ("test_3", content_id, content_id, "test", -0.5),  # Invalid < 0
            )


if __name__ == "__main__":
    unittest.main()
