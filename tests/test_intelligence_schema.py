"""Unit tests for document intelligence database schema and operations.

Tests schema creation, migration, CRUD operations, and data integrity.
"""

import os
import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent))

from shared.db.simple_db import SimpleDB


class TestIntelligenceSchema(unittest.TestCase):
    """
    Test suite for intelligence database schema and operations.
    """

    def setUp(self):
        """
        Create a temporary database for testing.
        """
        self.temp_db = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        self.db_path = self.temp_db.name
        self.temp_db.close()

        self.db = SimpleDB(self.db_path)

        # Create base content table for foreign key constraints
        self.db.execute(
            """
            CREATE TABLE IF NOT EXISTS content (
                id TEXT PRIMARY KEY,
                content_type TEXT,
                title TEXT,
                content TEXT,
                created_time TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """
        )

        # Add test content
        self.test_content_id = "test-doc-001"
        self.test_content_id2 = "test-doc-002"
        self.db.execute(
            """
            INSERT INTO content_unified (source_id, source_type, title, body)
            VALUES (?, 'document', 'Test Document', 'Test content')
        """,
            (self.test_content_id,),
        )
        self.db.execute(
            """
            INSERT INTO content_unified (source_id, source_type, title, body)
            VALUES (?, 'document', 'Test Document 2', 'Test content 2')
        """,
            (self.test_content_id2,),
        )

    def tearDown(self):
        """
        Clean up temporary database.
        """
        try:
            os.unlink(self.db_path)
        except Exception:
            pass

    def test_create_intelligence_tables(self):
        """
        Test creation of intelligence tables.
        """
        result = self.db.create_intelligence_tables()

        self.assertTrue(result["success"])
        self.assertEqual(len(result["tables_created"]), 3)
        self.assertIn("document_summaries", result["tables_created"])
        self.assertIn("document_intelligence", result["tables_created"])
        self.assertIn("relationship_cache", result["tables_created"])

        # Verify tables exist
        tables = self.db.fetch(
            """
            SELECT name FROM sqlite_master
            WHERE type='table' AND name IN ('document_summaries', 'document_intelligence', 'relationship_cache')
        """
        )
        self.assertEqual(len(tables), 3)

    def test_schema_migration(self):
        """
        Test schema migration functionality.
        """
        # Initial version should be 0
        version = self.db.get_schema_version()
        self.assertEqual(version, 0)

        # Run migration
        result = self.db.migrate_schema()
        self.assertTrue(result["success"])
        self.assertEqual(result["current_version"], 1)

        # Verify version was updated
        version = self.db.get_schema_version()
        self.assertEqual(version, 1)

        # Running migration again should not change version
        result = self.db.migrate_schema()
        self.assertTrue(result["success"])
        self.assertEqual(result["current_version"], 1)

    def test_add_document_summary(self):
        """
        Test adding document summaries.
        """
        self.db.create_intelligence_tables()

        # Add summary with all fields
        keywords = {"legal": 0.8, "contract": 0.6, "agreement": 0.5}
        sentences = ["This is a legal contract.", "Agreement between parties."]

        summary_id = self.db.add_document_summary(
            document_id=self.test_content_id,
            summary_type="combined",
            summary_text="Legal contract agreement summary",
            tf_idf_keywords=keywords,
            textrank_sentences=sentences,
        )

        self.assertIsNotNone(summary_id)

        # Retrieve and verify
        summaries = self.db.get_document_summaries(self.test_content_id)
        self.assertEqual(len(summaries), 1)
        self.assertEqual(summaries[0]["summary_type"], "combined")
        self.assertEqual(summaries[0]["summary_text"], "Legal contract agreement summary")
        self.assertEqual(summaries[0]["tf_idf_keywords"], keywords)
        self.assertEqual(summaries[0]["textrank_sentences"], sentences)

    def test_add_document_intelligence(self):
        """
        Test adding document intelligence data.
        """
        self.db.create_intelligence_tables()

        # Add intelligence data
        intel_data = {
            "entities": ["John Doe", "ABC Corp"],
            "sentiment": "neutral",
            "categories": ["legal", "business"],
        }

        intel_id = self.db.add_document_intelligence(
            document_id=self.test_content_id,
            intelligence_type="entity_extraction",
            intelligence_data=intel_data,
            confidence_score=0.85,
        )

        self.assertIsNotNone(intel_id)

        # Retrieve and verify
        intelligence = self.db.get_document_intelligence(self.test_content_id)
        self.assertEqual(len(intelligence), 1)
        self.assertEqual(intelligence[0]["intelligence_type"], "entity_extraction")
        self.assertEqual(intelligence[0]["intelligence_data"], intel_data)
        self.assertEqual(intelligence[0]["confidence_score"], 0.85)

    def test_add_relationship_cache(self):
        """
        Test adding cached relationships.
        """
        self.db.create_intelligence_tables()

        # Add relationship
        cache_data = {"similarity_score": 0.92, "common_entities": ["contract"]}

        cache_id = self.db.add_relationship_cache(
            source_id=self.test_content_id,
            target_id=self.test_content_id2,
            relationship_type="similar",
            strength=0.92,
            cached_data=cache_data,
            ttl_hours=24,
        )

        self.assertIsNotNone(cache_id)

        # Retrieve and verify
        relationships = self.db.get_relationship_cache(source_id=self.test_content_id)
        self.assertEqual(len(relationships), 1)
        self.assertEqual(relationships[0]["relationship_type"], "similar")
        self.assertEqual(relationships[0]["strength"], 0.92)
        self.assertEqual(relationships[0]["cached_data"], cache_data)

    def test_relationship_unique_constraint(self):
        """
        Test that relationship unique constraint works.
        """
        self.db.create_intelligence_tables()

        # Add first relationship
        self.db.add_relationship_cache(
            source_id=self.test_content_id,
            target_id=self.test_content_id2,
            relationship_type="similar",
            strength=0.8,
        )

        # Add same relationship (should replace)
        self.db.add_relationship_cache(
            source_id=self.test_content_id,
            target_id=self.test_content_id2,
            relationship_type="similar",
            strength=0.9,
        )

        # Should only have one relationship
        relationships = self.db.get_relationship_cache(
            source_id=self.test_content_id,
            target_id=self.test_content_id2,
            relationship_type="similar",
        )
        self.assertEqual(len(relationships), 1)
        self.assertEqual(relationships[0]["strength"], 0.9)  # Updated value

    def test_foreign_key_constraints(self):
        """
        Test that foreign key constraints are enforced.
        """
        self.db.create_intelligence_tables()

        # Try to add summary for non-existent document
        with self.assertRaises(sqlite3.IntegrityError):
            self.db.add_document_summary(
                document_id="non-existent-doc", summary_type="tfidf", summary_text="Test"
            )

        # Try to add relationship for non-existent documents
        with self.assertRaises(sqlite3.IntegrityError):
            self.db.add_relationship_cache(
                source_id="non-existent-1", target_id="non-existent-2", relationship_type="similar"
            )

    def test_batch_add_summaries(self):
        """
        Test batch adding summaries.
        """
        self.db.create_intelligence_tables()

        # Create batch data
        summaries = [
            {
                "document_id": self.test_content_id,
                "summary_type": "tfidf",
                "summary_text": "Summary 1",
                "tf_idf_keywords": {"key1": 0.5},
            },
            {
                "document_id": self.test_content_id2,
                "summary_type": "textrank",
                "summary_text": "Summary 2",
                "textrank_sentences": ["Sentence 1", "Sentence 2"],
            },
        ]

        result = self.db.batch_add_summaries(summaries)
        self.assertEqual(result["total"], 2)
        self.assertEqual(result["inserted"], 2)

        # Verify both were added
        summaries1 = self.db.get_document_summaries(self.test_content_id)
        summaries2 = self.db.get_document_summaries(self.test_content_id2)
        self.assertEqual(len(summaries1), 1)
        self.assertEqual(len(summaries2), 1)

    def test_get_document_intelligence_by_type(self):
        """
        Test filtering intelligence by type.
        """
        self.db.create_intelligence_tables()

        # Add multiple intelligence types
        self.db.add_document_intelligence(
            self.test_content_id, "entities", {"entities": ["A", "B"]}, 0.9
        )
        self.db.add_document_intelligence(
            self.test_content_id, "sentiment", {"sentiment": "positive"}, 0.8
        )
        self.db.add_document_intelligence(
            self.test_content_id, "entities", {"entities": ["C", "D"]}, 0.85
        )

        # Get all intelligence
        all_intel = self.db.get_document_intelligence(self.test_content_id)
        self.assertEqual(len(all_intel), 3)

        # Get only entity intelligence
        entity_intel = self.db.get_document_intelligence(self.test_content_id, "entities")
        self.assertEqual(len(entity_intel), 2)
        for intel in entity_intel:
            self.assertEqual(intel["intelligence_type"], "entities")

    def test_clean_expired_cache(self):
        """
        Test cleaning expired cache entries.
        """
        self.db.create_intelligence_tables()

        # Add relationship with very short TTL
        self.db.execute(
            """
            INSERT INTO relationship_cache
            (cache_id, source_id, target_id, relationship_type, expires_at)
            VALUES (?, ?, ?, ?, datetime('now', '-1 hour'))
        """,
            ("expired-1", self.test_content_id, self.test_content_id2, "old"),
        )

        # Add non-expired relationship
        self.db.add_relationship_cache(
            self.test_content_id, self.test_content_id2, "current", ttl_hours=24
        )

        # Clean expired
        deleted = self.db.clean_expired_cache()
        self.assertEqual(deleted, 1)

        # Verify only current relationship remains
        relationships = self.db.get_relationship_cache()
        self.assertEqual(len(relationships), 1)
        self.assertEqual(relationships[0]["relationship_type"], "current")

    def test_check_constraint_validation(self):
        """
        Test CHECK constraints are working.
        """
        self.db.create_intelligence_tables()

        # Test invalid summary_type
        with self.assertRaises(sqlite3.IntegrityError):
            self.db.execute(
                """
                INSERT INTO document_summaries
                (summary_id, document_id, summary_type)
                VALUES (?, ?, ?)
            """,
                ("test-1", self.test_content_id, "invalid_type"),
            )

        # Test invalid confidence score
        with self.assertRaises(sqlite3.IntegrityError):
            self.db.execute(
                """
                INSERT INTO document_intelligence
                (intelligence_id, document_id, intelligence_type, intelligence_data, confidence_score)
                VALUES (?, ?, ?, ?, ?)
            """,
                ("test-1", self.test_content_id, "test", "{}", 1.5),
            )

        # Test invalid strength
        with self.assertRaises(sqlite3.IntegrityError):
            self.db.execute(
                """
                INSERT INTO relationship_cache
                (cache_id, source_id, target_id, relationship_type, strength)
                VALUES (?, ?, ?, ?, ?)
            """,
                ("test-1", self.test_content_id, self.test_content_id2, "test", -0.1),
            )

    def test_json_field_handling(self):
        """
        Test proper JSON serialization/deserialization.
        """
        self.db.create_intelligence_tables()

        # Complex nested JSON data
        complex_data = {
            "nested": {"list": [1, 2, 3], "dict": {"a": 1, "b": 2}},
            "unicode": "テスト",
            "special": 'quote\'s & "quotes"',
        }

        self.db.add_document_intelligence(self.test_content_id, "complex", complex_data, 0.5)

        # Retrieve and verify JSON was properly handled
        intelligence = self.db.get_document_intelligence(self.test_content_id)
        self.assertEqual(intelligence[0]["intelligence_data"], complex_data)


if __name__ == "__main__":
    unittest.main()
