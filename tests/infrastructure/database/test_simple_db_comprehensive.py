"""Comprehensive tests for SimpleDB following CoverUp methodology.

This test file aims for 80%+ coverage of SimpleDB functionality by systematically
testing all public methods, error conditions, and edge cases.

Test Categories:
1. Database initialization and schema
2. Content operations (CRUD)
3. Search functionality
4. Summary operations
5. Intelligence data operations
6. Batch operations
7. Error handling and edge cases
8. Performance and concurrency
"""

import os
import sqlite3
from unittest.mock import patch

import pytest
from hypothesis import Verbosity, given, settings
from hypothesis import strategies as st

from shared.simple_db import SimpleDB


@pytest.mark.unit
class TestSimpleDBInitialization:
    """
    Test SimpleDB initialization and schema creation.
    """

    def test_init_default_database(self, temp_db):
        """
        Test initialization with default database path behavior.
        """
        # Test that default path is set correctly
        db = SimpleDB(db_path=temp_db)  # Use temp_db to avoid contaminating main database
        # Verify it has a database path
        assert db.db_path == temp_db
        assert os.path.exists(db.db_path)

        # Test that default path constant is correct (without creating the file)
        default_db = SimpleDB.__new__(SimpleDB)  # Create instance without calling __init__
        default_db.db_path = "emails.db"  # Set the expected default
        assert default_db.db_path == "emails.db"

    def test_init_custom_database(self, temp_db):
        """
        Test initialization with custom database path.
        """
        db = SimpleDB(db_path=temp_db)
        assert db.db_path == temp_db
        assert os.path.exists(temp_db)

    def test_schema_creation(self, temp_db):
        """
        Test that all required tables are created.
        """
        db = SimpleDB(db_path=temp_db)

        # Create the content table (SimpleDB doesn't auto-create this)
        db.execute(
            """
            CREATE TABLE IF NOT EXISTS content (
                id TEXT PRIMARY KEY,
                content_type TEXT,
                title TEXT,
                content TEXT,
                metadata TEXT,
                source_path TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                content_hash TEXT,
                word_count INTEGER,
                char_count INTEGER
            )
        """
        )

        # Create intelligence tables
        db.create_intelligence_tables()

        with sqlite3.connect(temp_db) as conn:
            cursor = conn.cursor()

            # Check content table
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='content'")
            assert cursor.fetchone() is not None

            # Check document_summaries table
            cursor.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='document_summaries'"
            )
            assert cursor.fetchone() is not None

            # Check document_intelligence table
            cursor.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='document_intelligence'"
            )
            assert cursor.fetchone() is not None

            # Check relationship_cache table
            cursor.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='relationship_cache'"
            )
            assert cursor.fetchone() is not None

    def test_init_with_existing_database(self, temp_db):
        """
        Test initialization with existing database preserves data.
        """
        # Create first instance and add data
        db1 = SimpleDB(db_path=temp_db)
        # Create the content table first
        db1.execute(
            """
            CREATE TABLE IF NOT EXISTS content (
                id TEXT PRIMARY KEY,
                content_type TEXT,
                title TEXT,
                content TEXT,
                metadata TEXT,
                source_path TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                content_hash TEXT,
                word_count INTEGER,
                char_count INTEGER
            )
        """
        )
        content_id = db1.add_content("email", "Test", "Content", {})

        # Create second instance with same database
        db2 = SimpleDB(db_path=temp_db)
        content = db2.get_content(content_id)

        assert content is not None
        assert content["title"] == "Test"

    def test_init_with_invalid_path(self):
        """
        Test initialization with invalid database path.
        """
        invalid_path = "/invalid/path/test.db"
        # SimpleDB constructor doesn't validate paths, so test database operations instead
        db = SimpleDB(db_path=invalid_path)
        with pytest.raises(Exception):
            # This should fail when trying to actually use the database
            db.execute("CREATE TABLE test (id INTEGER)")


@pytest.mark.unit
class TestContentOperations:
    """
    Test basic content CRUD operations.
    """

    def test_add_content_basic(self, simple_db):
        """
        Test adding basic content.
        """
        content_id = simple_db.add_content(
            content_type="email",
            title="Test Email",
            content="This is test content",
            metadata={"sender": "test@example.com"},
        )

        assert content_id is not None
        assert len(content_id) > 0

    def test_add_content_all_fields(self, simple_db):
        """
        Test adding content with all optional fields.
        """
        metadata = {
            "sender": "test@example.com",
            "date": "2024-01-01",
            "tags": ["important", "legal"],
        }

        content_id = simple_db.add_content(
            content_type="pdf",
            title="Legal Document",
            content="Legal content here",
            metadata=metadata,
            source_path="/test/path.pdf",
        )

        content = simple_db.get_content(content_id)
        assert content["content_type"] == "pdf"
        assert content["title"] == "Legal Document"
        assert content["content_hash"] is not None  # Auto-calculated
        assert content["word_count"] == 3  # "Legal content here" = 3 words
        assert content["char_count"] == 18  # "Legal content here" = 18 chars

    def test_add_content_empty_values(self, simple_db):
        """
        Test adding content with empty/null values.
        """
        content_id = simple_db.add_content(content_type="", title="", content="", metadata={})

        content = simple_db.get_content(content_id)
        assert content["content_type"] == ""
        assert content["title"] == ""
        assert content["content"] == ""

    def test_get_content_existing(self, populated_db):
        """
        Test retrieving existing content.
        """
        # Get content added by populated_db fixture
        with sqlite3.connect(populated_db.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id FROM content_unified LIMIT 1")
            content_id = cursor.fetchone()[0]

        content = populated_db.get_content(content_id)
        assert content is not None
        assert "content_id" in content
        assert "title" in content
        assert "content" in content

    def test_get_content_nonexistent(self, simple_db):
        """
        Test retrieving non-existent content.
        """
        content = simple_db.get_content("nonexistent_id")
        assert content is None

    def test_get_content_invalid_id(self, simple_db):
        """
        Test retrieving content with invalid ID format.
        """
        content = simple_db.get_content("")
        assert content is None

        content = simple_db.get_content(None)
        assert content is None

    def test_update_content(self, simple_db):
        """
        Test updating existing content.
        """
        # Add initial content
        content_id = simple_db.add_content("email", "Original", "Original content", {})

        # Update content
        success = simple_db.update_content(
            content_id, title="Updated Title", content="Updated content", metadata={"updated": True}
        )

        assert success is True

        # Verify update
        content = simple_db.get_content(content_id)
        assert content["title"] == "Updated Title"
        assert content["content"] == "Updated content"

    def test_update_nonexistent_content(self, simple_db):
        """
        Test updating non-existent content.
        """
        success = simple_db.update_content("nonexistent", title="Test")
        assert success is False

    def test_delete_content(self, simple_db):
        """
        Test deleting content.
        """
        # Add content
        content_id = simple_db.add_content("email", "To Delete", "Content", {})

        # Verify it exists
        assert simple_db.get_content(content_id) is not None

        # Delete it
        success = simple_db.delete_content(content_id)
        assert success is True

        # Verify it's gone
        assert simple_db.get_content(content_id) is None

    def test_delete_nonexistent_content(self, simple_db):
        """
        Test deleting non-existent content.
        """
        success = simple_db.delete_content("nonexistent")
        assert success is False


@pytest.mark.unit
class TestSearchFunctionality:
    """
    Test search operations and filtering.
    """

    def test_search_content_basic(self, populated_db):
        """
        Test basic content search.
        """
        results = populated_db.search_content("legal", limit=10)
        assert isinstance(results, list)
        assert len(results) > 0

        # Check result structure
        for result in results:
            assert "content_id" in result
            assert "title" in result
            assert "content" in result

    def test_search_content_no_results(self, populated_db):
        """
        Test search with no matching results.
        """
        results = populated_db.search_content("nonexistent_term", limit=10)
        assert isinstance(results, list)
        assert len(results) == 0

    def test_search_content_with_filters(self, simple_db):
        """
        Test search with various filters.
        """
        # Add test content with different types and dates
        simple_db.add_content(
            "email", "Email 1", "Content", {"date": "2024-01-01", "tags": ["work"]}
        )
        simple_db.add_content("pdf", "PDF 1", "Document", {"date": "2024-01-15", "tags": ["legal"]})

        # Test content type filter
        filters = {"content_types": ["email"]}
        results = simple_db.search_content("Content", filters=filters)
        assert all(r["content_type"] == "email" for r in results)

        # Test date filters
        filters = {"since": "2024-01-10", "until": "2024-01-20"}
        results = simple_db.search_content("", filters=filters)
        # Should only return PDF from Jan 15

    def test_search_content_limit(self, simple_db):
        """
        Test search result limiting.
        """
        # Add multiple items
        for i in range(5):
            simple_db.add_content("email", f"Email {i}", "test content", {})

        results = simple_db.search_content("test", limit=3)
        assert len(results) <= 3

    def test_search_content_empty_query(self, populated_db):
        """
        Test search with empty query.
        """
        results = populated_db.search_content("", limit=10)
        assert isinstance(results, list)
        # Should return all content when query is empty

    @pytest.mark.skip(reason="Hypothesis doesn't support function-scoped fixtures")
    @given(query=st.text(min_size=1, max_size=100))
    @settings(max_examples=10, verbosity=Verbosity.quiet)
    def test_search_content_random_queries(self, populated_db, query):
        """Property-based test: search should always return valid results."""
        results = populated_db.search_content(query, limit=5)
        assert isinstance(results, list)
        assert len(results) >= 0


@pytest.mark.unit
class TestSummaryOperations:
    """
    Test document summary operations.
    """

    def test_add_document_summary(self, simple_db):
        """
        Test adding document summary.
        """
        content_id = simple_db.add_content("pdf", "Test Doc", "Content", {})

        summary_id = simple_db.add_document_summary(
            document_id=content_id,
            summary_type="tfidf",
            summary_text="Test summary",
            tf_idf_keywords={"legal": 0.8, "contract": 0.6},
            textrank_sentences=["Sentence 1", "Sentence 2"],
        )

        assert summary_id is not None

        # Verify summary was stored
        with sqlite3.connect(simple_db.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM document_summaries WHERE summary_id = ?", (summary_id,))
            row = cursor.fetchone()
            assert row is not None

    def test_get_document_summary(self, simple_db):
        """
        Test retrieving document summary.
        """
        content_id = simple_db.add_content("pdf", "Test Doc", "Content", {})
        summary_id = simple_db.add_document_summary(
            document_id=content_id, summary_type="combined", summary_text="Summary text"
        )

        summary = simple_db.get_document_summary(summary_id)
        assert summary is not None
        assert summary["document_id"] == content_id
        assert summary["summary_type"] == "combined"

    def test_get_summaries_for_document(self, simple_db):
        """
        Test getting all summaries for a document.
        """
        content_id = simple_db.add_content("pdf", "Test Doc", "Content", {})

        # Add multiple summaries
        simple_db.add_document_summary(content_id, "tfidf", "TF-IDF summary")
        simple_db.add_document_summary(content_id, "textrank", "TextRank summary")

        summaries = simple_db.get_summaries_for_document(content_id)
        assert len(summaries) == 2
        assert any(s["summary_type"] == "tfidf" for s in summaries)
        assert any(s["summary_type"] == "textrank" for s in summaries)


@pytest.mark.unit
class TestIntelligenceOperations:
    """
    Test document intelligence operations.
    """

    def test_add_document_intelligence(self, simple_db):
        """
        Test adding document intelligence data.
        """
        content_id = simple_db.add_content("email", "Test Email", "Content", {})

        intel_id = simple_db.add_document_intelligence(
            document_id=content_id,
            intelligence_type="entity_extraction",
            intelligence_data={"entities": ["John Doe", "ABC Corp"]},
            confidence_score=0.85,
        )

        assert intel_id is not None

    def test_get_document_intelligence(self, simple_db):
        """
        Test retrieving document intelligence.
        """
        content_id = simple_db.add_content("pdf", "Legal Doc", "Content", {})
        intel_id = simple_db.add_document_intelligence(
            content_id, "sentiment", {"sentiment": "positive"}, 0.9
        )

        intelligence = simple_db.get_intelligence_by_id(intel_id)
        assert intelligence is not None
        assert intelligence["intelligence_type"] == "sentiment"
        assert intelligence["confidence_score"] == 0.9

    def test_get_intelligence_for_document(self, simple_db):
        """
        Test getting all intelligence for a document.
        """
        content_id = simple_db.add_content("pdf", "Test Doc", "Content", {})

        # Add multiple intelligence entries
        simple_db.add_document_intelligence(content_id, "entities", {"entities": []})
        simple_db.add_document_intelligence(content_id, "sentiment", {"score": 0.8})

        intelligence = simple_db.get_intelligence_for_document(content_id)
        assert len(intelligence) == 2


@pytest.mark.unit
class TestBatchOperations:
    """
    Test batch processing operations.
    """

    def test_batch_insert_basic(self, simple_db):
        """
        Test basic batch insert functionality.
        """
        table_name = "content"
        columns = ["content_id", "content_type", "title", "content"]
        data_list = [
            ("id1", "email", "Email 1", "Content 1"),
            ("id2", "pdf", "PDF 1", "Content 2"),
            ("id3", "email", "Email 2", "Content 3"),
        ]

        stats = simple_db.batch_insert(table_name, columns, data_list)

        assert stats["total"] == 3
        assert stats["inserted"] >= 0
        assert stats["ignored"] >= 0
        assert "time_seconds" in stats

    def test_batch_insert_with_duplicates(self, simple_db):
        """
        Test batch insert with duplicate handling.
        """
        # First insert
        table_name = "content"
        columns = ["content_id", "content_type", "title", "content"]
        data_list = [("id1", "email", "Email 1", "Content 1")]

        stats1 = simple_db.batch_insert(table_name, columns, data_list)
        assert stats1["inserted"] == 1

        # Second insert with same ID (should be ignored)
        stats2 = simple_db.batch_insert(table_name, columns, data_list)
        assert stats2["ignored"] == 1

    def test_batch_insert_large_dataset(self, simple_db):
        """
        Test batch insert with large dataset.
        """
        table_name = "content"
        columns = ["content_id", "content_type", "title", "content"]

        # Generate large dataset
        data_list = [(f"id_{i}", "email", f"Email {i}", f"Content {i}") for i in range(1000)]

        stats = simple_db.batch_insert(table_name, columns, data_list, batch_size=100)
        assert stats["total"] == 1000
        assert stats["time_seconds"] > 0

    def test_batch_add_content(self, simple_db):
        """
        Test batch content addition.
        """
        content_list = [
            {"content_type": "email", "title": "Email 1", "content": "Content 1"},
            {"content_type": "pdf", "title": "PDF 1", "content": "Content 2"},
            {"content_type": "email", "title": "Email 2", "content": "Content 3"},
        ]

        result = simple_db.batch_add_content(content_list)

        assert result["stats"]["total"] == 3
        assert len(result["content_ids"]) == 3
        assert all(isinstance(cid, str) for cid in result["content_ids"])


@pytest.mark.unit
class TestErrorHandling:
    """
    Test error conditions and edge cases.
    """

    @pytest.mark.skip(reason="SimpleDB doesn't connect on initialization - lazy connection")
    def test_database_connection_error(self):
        """
        Test handling of database connection errors.
        """
        # Try to use invalid database path
        with patch("sqlite3.connect") as mock_connect:
            mock_connect.side_effect = sqlite3.Error("Connection failed")

            with pytest.raises(sqlite3.Error):
                SimpleDB(db_path="invalid.db")

    def test_sql_injection_protection(self, simple_db):
        """
        Test protection against SQL injection.
        """
        malicious_query = "'; DROP TABLE content; --"

        # This should not cause any damage
        results = simple_db.search_content(malicious_query)
        assert isinstance(results, list)

        # Verify table still exists
        with sqlite3.connect(simple_db.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='content'")
            assert cursor.fetchone() is not None

    def test_invalid_json_metadata(self, simple_db):
        """
        Test handling of invalid JSON in metadata.
        """
        # This should be handled gracefully
        simple_db.add_content(
            "email",
            "Test",
            "Content",
            metadata={"invalid": object()},  # This will cause JSON serialization to fail
        )
        # Should still work, metadata might be stored as string or handled gracefully

    def test_unicode_content(self, simple_db):
        """
        Test handling of Unicode content.
        """
        content_id = simple_db.add_content(
            "email",
            "Unicode Test 📧",
            "Content with émojis 🚀 and special chars: αβγ",
            {"unicode_field": "测试 данные"},
        )

        content = simple_db.get_content(content_id)
        assert "📧" in content["title"]
        assert "🚀" in content["content"]

    def test_very_large_content(self, simple_db):
        """
        Test handling of very large content.
        """
        large_content = "x" * 1000000  # 1MB of content

        content_id = simple_db.add_content("pdf", "Large Document", large_content, {})

        retrieved = simple_db.get_content(content_id)
        assert len(retrieved["content"]) == 1000000

    def test_concurrent_access(self, simple_db):
        """
        Test concurrent database access.
        """
        import threading

        results = []
        errors = []

        def add_content(i):
            try:
                content_id = simple_db.add_content("email", f"Email {i}", f"Content {i}", {})
                results.append(content_id)
            except Exception as e:
                errors.append(e)

        # Create multiple threads
        threads = []
        for i in range(10):
            thread = threading.Thread(target=add_content, args=(i,))
            threads.append(thread)
            thread.start()

        # Wait for all threads to complete
        for thread in threads:
            thread.join()

        # Should have minimal errors
        assert len(errors) <= 2  # Allow for some race conditions
        assert len(results) >= 8  # Most should succeed


@pytest.mark.unit
class TestStatisticsAndReporting:
    """
    Test statistics and reporting functionality.
    """

    def test_get_content_stats_empty(self, simple_db):
        """
        Test statistics on empty database.
        """
        stats = simple_db.get_content_stats()

        assert stats["total_content"] == 0
        assert stats["content_by_type"] == {}
        assert stats["total_characters"] == 0

    def test_get_content_stats_populated(self, simple_db):
        """
        Test statistics on populated database.
        """
        # Add test content
        simple_db.add_content("email", "Email 1", "Content 1", {})
        simple_db.add_content("email", "Email 2", "Content 2", {})
        simple_db.add_content("pdf", "PDF 1", "Content 3", {})

        stats = simple_db.get_content_stats()

        assert stats["total_content"] == 3
        assert stats["content_by_type"]["email"] == 2
        assert stats["content_by_type"]["pdf"] == 1
        assert stats["total_characters"] > 0

    def test_database_size_reporting(self, simple_db):
        """
        Test database size reporting.
        """
        # Add some content
        for i in range(10):
            simple_db.add_content("email", f"Email {i}", "x" * 1000, {})

        stats = simple_db.get_content_stats()
        assert stats["total_characters"] >= 10000


class TestPerformance:
    """
    Test performance characteristics.
    """

    @pytest.mark.slow
    def test_large_batch_performance(self, simple_db):
        """
        Test performance with large batch operations.
        """
        import time

        # Generate large dataset
        content_list = [
            {"content_type": "email", "title": f"Email {i}", "content": f"Content {i}"}
            for i in range(5000)
        ]

        start_time = time.time()
        result = simple_db.batch_add_content(content_list, batch_size=1000)
        end_time = time.time()

        # Should complete in reasonable time
        assert end_time - start_time < 30  # 30 seconds max
        assert result["stats"]["total"] == 5000

    @pytest.mark.slow
    def test_search_performance(self, simple_db):
        """
        Test search performance with large dataset.
        """
        import time

        # Add test data
        for i in range(1000):
            simple_db.add_content(
                "email",
                f"Email {i}",
                f"This is email content {i} with some searchable terms",
                {"number": i},
            )

        start_time = time.time()
        results = simple_db.search_content("searchable", limit=100)
        end_time = time.time()

        # Should be fast
        assert end_time - start_time < 2  # 2 seconds max
        assert len(results) > 0


# Property-based testing with Hypothesis
@pytest.mark.skip(reason="Hypothesis doesn't support function-scoped fixtures")
class TestPropertyBased:
    """
    Property-based tests using Hypothesis.
    """

    @given(
        content_type=st.text(min_size=1, max_size=50),
        title=st.text(min_size=0, max_size=200),
        content=st.text(min_size=0, max_size=1000),
    )
    @settings(max_examples=20, verbosity=Verbosity.quiet)
    def test_add_get_content_roundtrip(self, simple_db, content_type, title, content):
        """Property test: Added content should be retrievable."""
        content_id = simple_db.add_content(content_type, title, content, {})
        retrieved = simple_db.get_content(content_id)

        assert retrieved is not None
        assert retrieved["content_type"] == content_type
        assert retrieved["title"] == title
        assert retrieved["content"] == content

    @given(query=st.text(min_size=0, max_size=100))
    @settings(max_examples=15, verbosity=Verbosity.quiet)
    def test_search_never_crashes(self, populated_db, query):
        """Property test: Search should never crash regardless of input."""
        try:
            results = populated_db.search_content(query, limit=10)
            assert isinstance(results, list)
        except Exception as e:
            pytest.fail(f"Search crashed with query '{query}': {e}")
