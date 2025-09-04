"""Intelligence and summary tests for SimpleDB.

Test Categories:
1. Document summaries
2. Intelligence table creation
3. JSON metadata handling
"""

import json

import pytest


@pytest.mark.unit
class TestIntelligenceTables:
    """
    Test intelligence table operations.
    """

    def test_create_intelligence_tables(self, simple_db):
        """
        Test creation of intelligence tables.
        """
        # create_intelligence_tables doesn't return anything, just creates tables
        simple_db.create_intelligence_tables()
        
        # Verify tables were created by checking sqlite_master
        with simple_db._get_connection() as conn:
            cursor = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
            )
            tables = [row[0] for row in cursor]
        
        assert "document_summaries" in tables
        assert "document_intelligence" in tables
        assert "relationship_cache" in tables


@pytest.mark.unit
class TestSummaryOperations:
    """
    Test document summary operations.
    """

    def test_add_summary_basic(self, simple_db):
        """
        Test adding a basic summary.
        """
        # Add test document
        metadata = {"source": "test"}
        content_id = simple_db.add_content("document", "Test Doc", "Test content", metadata)
        simple_db.create_intelligence_tables()
        
        # Add summary
        summary_id = simple_db.add_summary(
            content_id=content_id,
            summary="This is a test summary",
            summary_type="default"
        )
        
        assert summary_id is not None
        assert isinstance(summary_id, str)

    def test_add_summary_with_keywords(self, simple_db):
        """
        Test adding summary with keywords.
        """
        metadata = {}
        content_id = simple_db.add_content("document", "Test", "Content", metadata)
        simple_db.create_intelligence_tables()
        
        keywords = ["legal", "contract", "agreement"]
        summary_id = simple_db.add_summary(
            content_id=content_id,
            summary="Summary with keywords",
            summary_type="extractive",
            keywords=keywords
        )
        
        assert summary_id is not None

    def test_add_summary_with_metadata(self, simple_db):
        """
        Test adding summary with metadata.
        """
        metadata = {}
        content_id = simple_db.add_content("document", "Test", "Content", metadata)
        simple_db.create_intelligence_tables()
        
        summary_metadata = {
            "method": "tf-idf",
            "confidence": 0.85,
            "processing_time": 1.23
        }
        
        summary_id = simple_db.add_summary(
            content_id=content_id,
            summary="Summary with metadata",
            summary_type="abstractive",
            metadata=summary_metadata
        )
        
        assert summary_id is not None

    def test_get_summary_default_type(self, simple_db):
        """
        Test retrieving summary with default type.
        """
        metadata = {}
        content_id = simple_db.add_content("document", "Test", "Content", metadata)
        simple_db.create_intelligence_tables()
        
        # Add summary
        simple_db.add_summary(
            content_id=content_id,
            summary="Default summary text"
        )
        
        # Get summary
        summary = simple_db.get_summary(content_id)
        assert summary is not None
        assert summary["summary"] == "Default summary text"
        assert summary["summary_type"] == "default"

    def test_get_summary_specific_type(self, simple_db):
        """
        Test retrieving summary with specific type.
        """
        metadata = {}
        content_id = simple_db.add_content("document", "Test", "Content", metadata)
        simple_db.create_intelligence_tables()
        
        # Add multiple summaries with different types
        simple_db.add_summary(
            content_id=content_id,
            summary="Default summary",
            summary_type="default"
        )
        simple_db.add_summary(
            content_id=content_id,
            summary="Extractive summary",
            summary_type="extractive"
        )
        
        # Get specific type
        summary = simple_db.get_summary(content_id, summary_type="extractive")
        assert summary is not None
        assert summary["summary"] == "Extractive summary"
        assert summary["summary_type"] == "extractive"

    def test_get_summary_nonexistent(self, simple_db):
        """
        Test retrieving non-existent summary.
        """
        simple_db.create_intelligence_tables()
        
        summary = simple_db.get_summary("non-existent-id")
        assert summary is None

    def test_summary_with_keywords_roundtrip(self, simple_db):
        """
        Test that keywords survive storage and retrieval.
        """
        metadata = {}
        content_id = simple_db.add_content("document", "Test", "Content", metadata)
        simple_db.create_intelligence_tables()
        
        keywords = ["legal", "contract", "binding"]
        simple_db.add_summary(
            content_id=content_id,
            summary="Summary text",
            keywords=keywords
        )
        
        summary = simple_db.get_summary(content_id)
        assert summary is not None
        assert summary["keywords"] == keywords

    def test_summary_with_metadata_roundtrip(self, simple_db):
        """
        Test that metadata survives storage and retrieval.
        """
        metadata = {}
        content_id = simple_db.add_content("document", "Test", "Content", metadata)
        simple_db.create_intelligence_tables()
        
        summary_metadata = {
            "algorithm": "BERT",
            "confidence": 0.92,
            "tokens": 512
        }
        simple_db.add_summary(
            content_id=content_id,
            summary="Summary text",
            metadata=summary_metadata
        )
        
        summary = simple_db.get_summary(content_id)
        assert summary is not None
        assert summary["metadata"] == summary_metadata


@pytest.mark.unit
class TestDirectTableAccess:
    """
    Test direct table operations for intelligence features.
    """

    def test_insert_into_document_intelligence(self, simple_db):
        """
        Test direct insertion into document_intelligence table.
        """
        metadata = {}
        content_id = simple_db.add_content("document", "Test", "Content", metadata)
        simple_db.create_intelligence_tables()
        
        # Direct insert into document_intelligence
        intelligence_data = {
            "entities": ["Person A", "Company B"],
            "sentiment": "neutral",
            "topics": ["legal", "contract"]
        }
        
        with simple_db._get_connection() as conn:
            conn.execute("""
                INSERT INTO document_intelligence 
                (id, content_id, intelligence_type, intelligence_data, confidence_score)
                VALUES (?, ?, ?, ?, ?)
            """, ("intel-1", content_id, "entity_extraction", 
                  json.dumps(intelligence_data), 0.88))
        
        # Verify insertion
        result = simple_db.fetch_one(
            "SELECT * FROM document_intelligence WHERE content_id = ?",
            (content_id,)
        )
        assert result is not None
        assert result["intelligence_type"] == "entity_extraction"
        assert result["confidence_score"] == 0.88

    def test_insert_into_relationship_cache(self, simple_db):
        """
        Test direct insertion into relationship_cache table.
        """
        simple_db.create_intelligence_tables()
        
        # Add two documents to relate
        metadata = {}
        doc1 = simple_db.add_content("document", "Doc1", "Content1", metadata)
        doc2 = simple_db.add_content("document", "Doc2", "Content2", metadata)
        
        # Direct insert into relationship_cache
        with simple_db._get_connection() as conn:
            conn.execute("""
                INSERT INTO relationship_cache
                (id, source_id, target_id, relationship_type, confidence_score)
                VALUES (?, ?, ?, ?, ?)
            """, ("rel-1", doc1, doc2, "cites", 0.95))
        
        # Verify insertion
        result = simple_db.fetch_one(
            "SELECT * FROM relationship_cache WHERE source_id = ?",
            (doc1,)
        )
        assert result is not None
        assert result["target_id"] == doc2
        assert result["relationship_type"] == "cites"
        assert result["confidence_score"] == 0.95


@pytest.mark.unit 
class TestJSONHandling:
    """
    Test JSON serialization and deserialization.
    """

    def test_metadata_json_handling(self, simple_db):
        """
        Test that complex metadata is properly handled.
        """
        complex_metadata = {
            "nested": {
                "level1": {
                    "level2": ["item1", "item2"]
                }
            },
            "numbers": [1, 2.5, 3],
            "boolean": True,
            "null_value": None
        }
        
        content_id = simple_db.add_content(
            "document", "Test", "Content", complex_metadata
        )
        
        content = simple_db.get_content(content_id)
        assert content is not None
        assert content["metadata"] == complex_metadata
        assert content["metadata"]["nested"]["level1"]["level2"] == ["item1", "item2"]

    def test_empty_metadata_handling(self, simple_db):
        """
        Test that empty metadata is handled correctly.
        """
        content_id = simple_db.add_content("document", "Test", "Content", {})
        
        content = simple_db.get_content(content_id)
        assert content is not None
        # Empty metadata may be stored as None or {} depending on implementation
        assert content["metadata"] in (None, {})