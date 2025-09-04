#!/usr/bin/env python3
"""
Integration Tests for Semantic Search Migration Tests the new search
coordination module and CLI integration.
"""

import sys
import time
from pathlib import Path

import pytest

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from search_intelligence import search as semantic_search
from search_intelligence import vector_store_available
from shared.db.simple_db import SimpleDB


class TestSemanticSearchIntegration:
    """
    Test suite for semantic search migration.
    """

    def test_vector_store_availability(self):
        """
        Test that vector store is available and has expected content.
        """
        assert vector_store_available(), "Vector store should be available"

        from utilities.vector_store import get_vector_store

        store = get_vector_store()
        count = store.count()
        assert count > 0, f"Vector store should have content, found {count} vectors"
        print(f"✅ Vector store has {count} vectors")

    def test_semantic_search_module(self):
        """
        Test the semantic search function directly.
        """
        results = semantic_search("contract", limit=3)
        assert isinstance(results, list), "Semantic search should return list"
        print("✅ Semantic search function working")

    def test_cli_search_modes(self):
        """
        Test CLI search modes work correctly.
        """
        # Import by adding the tools/scripts directory to path
        import os
        import subprocess

        # Test CLI via subprocess to avoid import issues
        script_path = os.path.join(os.path.dirname(__file__), "..", "tools", "scripts", "vsearch")

        # Test basic search
        result = subprocess.run(
            ["python3", script_path, "search", "contract", "--limit", "2"],
            capture_output=True,
            text=True,
            timeout=30,
        )

        assert result.returncode == 0 or "Found" in result.stdout, "CLI search should work"
        print("✅ CLI search modes working")

    # Removed backward compatibility test for deprecated service

    def test_performance_characteristics(self):
        """
        Test performance is within expected bounds.
        """
        query = "contract agreement"

        # Test keyword performance (should be very fast)
        start = time.time()
        db = SimpleDB()
        db.search_content(query, limit=5)
        keyword_time = time.time() - start
        assert keyword_time < 1.0, f"Keyword search too slow: {keyword_time:.3f}s"

        # Test semantic performance (should complete within 10s after model load)
        start = time.time()
        semantic_search(query, limit=5)
        semantic_time = time.time() - start
        assert semantic_time < 10.0, f"Semantic search too slow: {semantic_time:.3f}s"
        print(
            f"✅ Performance OK: K={keyword_time:.3f}s, S={semantic_time:.3f}s"
        )

    def test_edge_cases(self):
        """
        Test edge cases and error handling.
        """
        # Empty query
        results = semantic_search("", limit=3)
        assert isinstance(results, list), "Empty query should return list"

        # Non-existent terms
        results = semantic_search("xyznonexistent123", limit=3)
        assert isinstance(results, list), "Non-existent terms should return list"

        # Special characters
        results = semantic_search("contract@#$", limit=3)
        assert isinstance(results, list), "Special chars should return list"

        print("✅ Edge cases handled correctly")

    # Removed RRF merging tests (hybrid mode retired)

    # Removed legacy intelligence handler compatibility test

    # Removed legal handler compatibility test (out of scope)


if __name__ == "__main__":
    # Run tests directly
    test_suite = TestSemanticSearchIntegration()

    print("🧪 Running Semantic Search Integration Tests\n")

    try:
        test_suite.test_vector_store_availability()
        test_suite.test_semantic_search_module()
        test_suite.test_cli_search_modes()
        test_suite.test_performance_characteristics()
        test_suite.test_edge_cases()
        # Removed retired tests

        print("\n🎉 All integration tests passed!")

    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)
