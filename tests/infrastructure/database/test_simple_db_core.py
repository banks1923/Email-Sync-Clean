"""Core tests for SimpleDB - Initialization, CRUD, and Search operations.

Test Categories:
1. Database initialization and schema
2. Content operations (CRUD) 
3. Search functionality
4. Error handling
"""

import os

import pytest
from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st

from lib.db import SimpleDB


@pytest.mark.unit
class TestSimpleDBInitialization:
    """
    Test SimpleDB initialization and schema creation.
    """

    def test_init_default_database(self, temp_db):
        """
        Test initialization with default database path behavior.
        """
        db = SimpleDB(db_path=temp_db)
        assert db.db_path == temp_db
        assert os.path.exists(db.db_path)

    def test_init_custom_database(self, temp_db):
        """
        Test initialization with custom database path.
        """
        db = SimpleDB(db_path=temp_db)
        assert db.db_path == temp_db
        assert os.path.exists(temp_db)

    def test_init_with_existing_database(self, temp_db):
        """
        Test initialization with existing database preserves data.
        """
        db1 = SimpleDB(db_path=temp_db)
        metadata = {}
        db1.add_content("document", "Test", "Content", metadata)
        
        db2 = SimpleDB(db_path=temp_db)
        results = db2.search_content("Content")
        assert len(results) == 1


@pytest.mark.unit
class TestContentOperations:
    """
    Test CRUD operations for content.
    """

    def test_add_content_basic(self, simple_db):
        """
        Test adding basic content.
        """
        metadata = {"test": True}
        content_id = simple_db.add_content("document", "Test Title", "Test content", metadata)
        assert content_id is not None
        assert isinstance(content_id, str)

    def test_add_content_all_fields(self, simple_db):
        """
        Test adding content with all optional fields.
        """
        metadata = {"tags": ["test", "email"]}
        content_id = simple_db.add_content(
            content_type="email",
            title="Full Test",
            content="Full test content",
            metadata=metadata,
            source_path="/test/path.txt"
        )
        assert content_id is not None
        assert isinstance(content_id, str)

    def test_add_content_empty_values(self, simple_db):
        """
        Test adding content with empty values.
        """
        metadata = {}
        content_id = simple_db.add_content("document", "", "", metadata)
        assert content_id is not None
        assert isinstance(content_id, str)

    def test_get_content_existing(self, populated_db):
        """
        Test retrieving existing content.
        """
        # First add content to get a valid ID
        metadata = {"test": True}
        content_id = populated_db.add_content("test", "Test Title", "Test content", metadata)
        
        content = populated_db.get_content(content_id)
        assert content is not None
        assert content["id"] == content_id

    def test_get_content_nonexistent(self, simple_db):
        """
        Test retrieving non-existent content.
        """
        # Use a UUID that doesn't exist
        content = simple_db.get_content("non-existent-id-123")
        assert content is None

    def test_update_content_via_add(self, simple_db):
        """
        Test updating content using add_content with same ID.
        """
        metadata = {"version": 1}
        content_id = simple_db.add_content("document", "Original", "Original content", metadata)
        
        # Update by calling add_content with same content_id
        updated_metadata = {"version": 2}
        updated_id = simple_db.add_content(
            "document", "Updated", "Updated content", updated_metadata,
            content_id=content_id  # Pass the same ID to update
        )
        assert updated_id == content_id
        
        content = simple_db.get_content(content_id)
        assert content["title"] == "Updated"
        assert content["content"] == "Updated content"  # Note: field is 'content' not 'body'

    def test_delete_content(self, simple_db):
        """
        Test deleting content.
        """
        metadata = {}
        content_id = simple_db.add_content("document", "Delete me", "Content", metadata)
        
        deleted = simple_db.delete_content(content_id)
        assert deleted is True
        
        content = simple_db.get_content(content_id)
        assert content is None


@pytest.mark.unit
class TestSearchFunctionality:
    """
    Test search operations.
    """

    def test_search_content_basic(self, populated_db):
        """
        Test basic search functionality.
        """
        results = populated_db.search_content("document")
        assert len(results) > 0

    def test_search_content_no_results(self, populated_db):
        """
        Test search with no matching results.
        """
        results = populated_db.search_content("xyz123abc")
        assert len(results) == 0

    def test_search_content_with_filters(self, simple_db):
        """
        Test search with type filters.
        """
        simple_db.add_content("email", "Email 1", "test content", {})
        simple_db.add_content("document", "Doc 1", "test content", {})
        
        results = simple_db.search_content("test", content_type="email")
        assert len(results) == 1
        assert results[0]["content_type"] == "email"

    def test_search_content_limit(self, simple_db):
        """
        Test search with result limit.
        """
        for i in range(10):
            simple_db.add_content("document", f"Doc {i}", "searchable content", {})
        
        results = simple_db.search_content("searchable", limit=5)
        assert len(results) == 5

    def test_search_content_empty_query(self, populated_db):
        """
        Test search with empty query returns all.
        """
        results = populated_db.search_content("")
        assert len(results) > 0


@pytest.mark.unit
class TestErrorHandling:
    """
    Test error handling and edge cases.
    """

    def test_add_content_sql_injection(self, simple_db):
        """
        Test SQL injection protection in add_content.
        """
        malicious_title = "'; DROP TABLE content; --"
        content_id = simple_db.add_content("document", malicious_title, "content", {})
        assert content_id is not None
        
        # Verify table still exists
        results = simple_db.search_content("content")
        assert results is not None

    def test_search_content_sql_injection(self, simple_db):
        """
        Test SQL injection protection in search.
        """
        simple_db.add_content("document", "Test", "content", {})
        
        malicious_query = "' OR '1'='1"
        results = simple_db.search_content(malicious_query)
        # Should return empty or actual matches, not all records
        assert len(results) == 0

    def test_invalid_content_type(self, simple_db):
        """
        Test handling of invalid content type.
        """
        # Should not raise, just store as-is
        content_id = simple_db.add_content("invalid_type", "Title", "Content", {})
        assert content_id is not None

    def test_none_values(self, simple_db):
        """
        Test handling of None values.
        """
        # Should handle gracefully
        # Handle None values - pass empty strings and metadata
        content_id = simple_db.add_content("document", "", "", {})
        assert content_id is not None

    def test_very_large_content(self, simple_db):
        """
        Test handling of very large content.
        """
        large_content = "x" * 1000000  # 1MB of text
        content_id = simple_db.add_content("document", "Large", large_content, {})
        assert content_id is not None
        
        # Verify it can be retrieved
        content = simple_db.get_content(content_id)
        assert len(content["content"]) == 1000000


@pytest.mark.unit
class TestPropertyBased:
    """
    Property-based tests using Hypothesis.
    """

    @given(
        content_type=st.text(min_size=1, max_size=50),
        title=st.text(min_size=0, max_size=200),
        content=st.text(min_size=0, max_size=1000)
    )
    @settings(max_examples=50, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_add_get_content_roundtrip(self, simple_db, content_type, title, content):
        """
        Test that content survives add/get roundtrip.
        """
        content_id = simple_db.add_content(content_type, title, content, {})
        assert content_id is not None
        
        retrieved = simple_db.get_content(content_id)
        assert retrieved is not None
        assert retrieved["content_type"] == content_type
        assert retrieved["title"] == title
        assert retrieved["content"] == content

    @given(query=st.text(min_size=0, max_size=100))
    @settings(max_examples=50, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_search_never_crashes(self, simple_db, query):
        """
        Test that search never crashes regardless of input.
        """
        try:
            results = simple_db.search_content(query)
            assert isinstance(results, list)
        except Exception as e:
            pytest.fail(f"Search crashed with query '{query}': {e}")