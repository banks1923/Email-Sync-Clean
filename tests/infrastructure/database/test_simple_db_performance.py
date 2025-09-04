"""Performance and batch operation tests for SimpleDB.

Test Categories:
1. Batch operations
2. Performance benchmarks
3. Concurrent access
4. Health checks and metrics
"""

import threading
import time

import pytest


@pytest.mark.unit
class TestBatchOperations:
    """
    Test batch operations for efficiency.
    """

    def test_batch_add_content(self, simple_db):
        """
        Test batch adding multiple content items.
        """
        contents = [
            ("document", f"Title {i}", f"Content {i}", {})
            for i in range(100)
        ]
        
        start_time = time.time()
        ids = []
        for content_type, title, content, metadata in contents:
            content_id = simple_db.add_content(content_type, title, content, metadata)
            ids.append(content_id)
        elapsed = time.time() - start_time
        
        assert len(ids) == 100
        assert all(id is not None for id in ids)
        # Should complete within reasonable time
        assert elapsed < 5.0  # 5 seconds for 100 items

    def test_batch_search(self, simple_db):
        """
        Test batch searching performance.
        """
        # Add test data
        for i in range(50):
            simple_db.add_content(
                "document",
                f"Document {i}",
                f"Content with searchable text {i}",
                {}
            )
        
        queries = ["searchable", "text", "document", "content", "with"]
        
        start_time = time.time()
        results = []
        for query in queries:
            result = simple_db.search_content(query)
            results.append(result)
        elapsed = time.time() - start_time
        
        assert len(results) == 5
        assert all(len(r) > 0 for r in results)
        assert elapsed < 2.0  # 2 seconds for 5 searches

    def test_batch_update_via_add(self, simple_db):
        """
        Test batch updating content using add_content with same IDs.
        """
        # Create content
        ids = []
        for i in range(20):
            content_id = simple_db.add_content(
                "document",
                f"Original {i}",
                f"Original content {i}",
                {"version": 1}
            )
            ids.append(content_id)
        
        # Batch update using add_content with same IDs
        start_time = time.time()
        for idx, content_id in enumerate(ids):
            simple_db.add_content(
                "document",
                f"Updated {idx}",
                f"Updated content {idx}",
                {"version": 2},
                content_id=content_id  # Pass same ID to update
            )
        elapsed = time.time() - start_time
        
        # Verify updates
        for idx, content_id in enumerate(ids):
            content = simple_db.get_content(content_id)
            assert "Updated" in content["title"]
            assert content["metadata"]["version"] == 2
        
        assert elapsed < 3.0  # 3 seconds for 20 updates

    def test_batch_delete(self, simple_db):
        """
        Test batch deletion performance.
        """
        # Create content
        ids = []
        for i in range(30):
            content_id = simple_db.add_content(
                "document",
                f"Delete {i}",
                f"Content {i}",
                {}
            )
            ids.append(content_id)
        
        # Batch delete
        start_time = time.time()
        for content_id in ids:
            simple_db.delete_content(content_id)
        elapsed = time.time() - start_time
        
        # Verify deletions
        for content_id in ids:
            content = simple_db.get_content(content_id)
            assert content is None
        
        assert elapsed < 2.0  # 2 seconds for 30 deletions


@pytest.mark.unit
class TestContentCounting:
    """
    Test content counting and basic statistics.
    """

    def test_get_content_count_empty(self, simple_db):
        """
        Test counting content in empty database.
        """
        count = simple_db.get_content_count()
        assert count == 0

    def test_get_content_count_by_type(self, simple_db):
        """
        Test counting content by type.
        """
        # Add various content types
        simple_db.add_content("email", "Email 1", "Content", {})
        simple_db.add_content("email", "Email 2", "Content", {})
        simple_db.add_content("document", "Doc 1", "Content", {})
        simple_db.add_content("document", "Doc 2", "Content", {})
        simple_db.add_content("document", "Doc 3", "Content", {})
        
        # Test counts
        total_count = simple_db.get_content_count()
        email_count = simple_db.get_content_count(content_type="email")
        doc_count = simple_db.get_content_count(content_type="document")
        
        assert total_count == 5
        assert email_count == 2
        assert doc_count == 3

    def test_get_all_content_ids(self, simple_db):
        """
        Test getting all content IDs.
        """
        # Add content
        expected_ids = []
        for i in range(10):
            content_id = simple_db.add_content(
                "document" if i % 2 == 0 else "email",
                f"Title {i}",
                f"Content {i}",
                {}
            )
            expected_ids.append(content_id)
        
        # Get all IDs
        all_ids = simple_db.get_all_content_ids()
        
        assert len(all_ids) == 10
        assert set(all_ids) == set(expected_ids)

    def test_get_all_content_ids_by_type(self, simple_db):
        """
        Test getting content IDs filtered by type.
        """
        # Add mixed content
        email_ids = []
        doc_ids = []
        
        for i in range(6):
            if i % 2 == 0:
                content_id = simple_db.add_content("email", f"Email {i}", "Content", {})
                email_ids.append(content_id)
            else:
                content_id = simple_db.add_content("document", f"Doc {i}", "Content", {})
                doc_ids.append(content_id)
        
        # Get IDs by type
        retrieved_email_ids = simple_db.get_all_content_ids(content_type="email")
        retrieved_doc_ids = simple_db.get_all_content_ids(content_type="document")
        
        assert set(retrieved_email_ids) == set(email_ids)
        assert set(retrieved_doc_ids) == set(doc_ids)


@pytest.mark.unit
class TestHealthCheck:
    """
    Test database health check functionality.
    """

    def test_health_check_empty(self, simple_db):
        """
        Test health check on empty database.
        """
        health = simple_db.health_check()
        
        assert health is not None
        assert health["status"] == "healthy"
        assert health["content_count"] == 0
        assert "tables" in health
        assert "db_size_bytes" in health
        assert "db_size_mb" in health

    def test_health_check_with_content(self, simple_db):
        """
        Test health check with content.
        """
        # Add some content
        for i in range(5):
            simple_db.add_content("document", f"Doc {i}", "Content", {})
        
        health = simple_db.health_check()
        
        assert health["status"] == "healthy"
        assert health["content_count"] == 5
        assert health["db_size_bytes"] > 0
        assert "metrics" in health

    def test_health_check_metrics(self, simple_db):
        """
        Test that health check includes metrics.
        """
        # Perform some operations to generate metrics
        simple_db.add_content("doc", "Title", "Content", {})
        simple_db.search_content("test")
        simple_db.get_content_count()
        
        health = simple_db.health_check()
        
        assert "metrics" in health
        assert health["metrics"]["queries"] > 0
        assert health["metrics"]["writes"] > 0


@pytest.mark.unit
class TestConcurrentAccess:
    """
    Test concurrent database access.
    """

    def test_concurrent_reads(self, simple_db):
        """
        Test concurrent read operations.
        """
        # Add test content
        content_id = simple_db.add_content("document", "Test", "Content", {})
        
        results = []
        errors = []
        
        def read_content():
            try:
                result = simple_db.get_content(content_id)
                results.append(result)
            except Exception as e:
                errors.append(e)
        
        # Create multiple threads
        threads = []
        for _ in range(10):
            thread = threading.Thread(target=read_content)
            threads.append(thread)
            thread.start()
        
        # Wait for all threads
        for thread in threads:
            thread.join()
        
        # Check results
        assert len(errors) == 0
        assert len(results) == 10
        assert all(r is not None for r in results)
        assert all(r["id"] == content_id for r in results)

    def test_concurrent_writes(self, simple_db):
        """
        Test concurrent write operations.
        """
        ids = []
        errors = []
        lock = threading.Lock()
        
        def write_content(index):
            try:
                content_id = simple_db.add_content(
                    "document",
                    f"Doc {index}",
                    f"Content {index}",
                    {"thread": index}
                )
                with lock:
                    ids.append(content_id)
            except Exception as e:
                with lock:
                    errors.append(e)
        
        # Create multiple threads
        threads = []
        for i in range(10):
            thread = threading.Thread(target=write_content, args=(i,))
            threads.append(thread)
            thread.start()
        
        # Wait for all threads
        for thread in threads:
            thread.join()
        
        # Check results
        assert len(errors) == 0
        assert len(ids) == 10
        assert len(set(ids)) == 10  # All IDs should be unique

    def test_concurrent_mixed_operations(self, simple_db):
        """
        Test mixed concurrent operations.
        """
        # Add initial content
        base_id = simple_db.add_content("document", "Base", "Base content", {})
        
        results = {"reads": [], "writes": [], "searches": [], "errors": []}
        lock = threading.Lock()
        
        def mixed_operations(index):
            try:
                # Perform different operations based on index
                if index % 3 == 0:
                    # Read operation
                    result = simple_db.get_content(base_id)
                    with lock:
                        results["reads"].append(result)
                elif index % 3 == 1:
                    # Write operation
                    content_id = simple_db.add_content(
                        "document",
                        f"Concurrent {index}",
                        f"Content {index}",
                        {}
                    )
                    with lock:
                        results["writes"].append(content_id)
                else:
                    # Search operation
                    result = simple_db.search_content("content", limit=5)
                    with lock:
                        results["searches"].append(result)
            except Exception as e:
                with lock:
                    results["errors"].append(e)
        
        # Create multiple threads
        threads = []
        for i in range(15):
            thread = threading.Thread(target=mixed_operations, args=(i,))
            threads.append(thread)
            thread.start()
        
        # Wait for all threads
        for thread in threads:
            thread.join()
        
        # Check results
        assert len(results["errors"]) == 0
        assert len(results["reads"]) == 5
        assert len(results["writes"]) == 5
        assert len(results["searches"]) == 5


@pytest.mark.unit
class TestPerformanceBenchmarks:
    """
    Test performance benchmarks.
    """

    def test_insert_performance(self, simple_db):
        """
        Benchmark insert performance.
        """
        start_time = time.time()
        
        for i in range(100):
            simple_db.add_content(
                "document",
                f"Perf test {i}",
                f"Content for performance testing {i}",
                {"index": i}
            )
        
        elapsed = time.time() - start_time
        inserts_per_second = 100 / elapsed
        
        # Should handle at least 20 inserts per second
        assert inserts_per_second > 20
        print(f"Insert performance: {inserts_per_second:.1f} inserts/second")

    def test_search_performance(self, simple_db):
        """
        Benchmark search performance.
        """
        # Populate with data
        for i in range(200):
            simple_db.add_content(
                "document",
                f"Search test {i}",
                f"Searchable content with term{i % 10}",
                {}
            )
        
        # Benchmark searches
        start_time = time.time()
        
        for i in range(50):
            simple_db.search_content(f"term{i % 10}", limit=10)
        
        elapsed = time.time() - start_time
        searches_per_second = 50 / elapsed
        
        # Should handle at least 10 searches per second
        assert searches_per_second > 10
        print(f"Search performance: {searches_per_second:.1f} searches/second")

    def test_large_content_handling(self, simple_db):
        """
        Test handling of large content.
        """
        # Create large content (1MB)
        large_content = "x" * (1024 * 1024)
        
        start_time = time.time()
        content_id = simple_db.add_content(
            "document",
            "Large document",
            large_content,
            {"size_mb": 1}
        )
        insert_time = time.time() - start_time
        
        # Should insert within 1 second
        assert insert_time < 1.0
        
        # Test retrieval
        start_time = time.time()
        content = simple_db.get_content(content_id)
        retrieve_time = time.time() - start_time
        
        assert content is not None
        assert len(content["content"]) == len(large_content)
        # Should retrieve within 1 second
        assert retrieve_time < 1.0