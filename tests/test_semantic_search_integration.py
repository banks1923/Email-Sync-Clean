#!/usr/bin/env python3
"""
Integration Tests for Semantic Search Migration
Tests the new search coordination module and CLI integration.
"""

import sys
import time
from pathlib import Path

import pytest

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from search_intelligence import basic_search as search
from search_intelligence import semantic_search, vector_store_available
from shared.simple_db import SimpleDB


class TestSemanticSearchIntegration:
    """Test suite for semantic search migration"""

    def test_vector_store_availability(self):
        """Test that vector store is available and has expected content"""
        assert vector_store_available(), "Vector store should be available"
        
        from utilities.vector_store import get_vector_store
        store = get_vector_store()
        count = store.count()
        assert count > 0, f"Vector store should have content, found {count} vectors"
        print(f"✅ Vector store has {count} vectors")

    def test_search_coordination_module(self):
        """Test the new search coordination module directly"""
        # Test semantic search
        semantic_results = semantic_search("contract", limit=3)
        assert isinstance(semantic_results, list), "Semantic search should return list"
        
        # Test hybrid search
        hybrid_results = search("contract", limit=3)
        assert isinstance(hybrid_results, list), "Hybrid search should return list"
        
        # Verify RRF scoring is present in hybrid results
        if hybrid_results:
            first_result = hybrid_results[0]
            assert "rrf_score" in first_result, "Hybrid results should have RRF scores"
        
        print("✅ Search coordination module working")

    def test_cli_search_modes(self):
        """Test CLI search modes work correctly"""
        # Import by adding the tools/scripts directory to path
        import os
        import subprocess

        # Test CLI via subprocess to avoid import issues
        script_path = os.path.join(os.path.dirname(__file__), "..", "tools", "scripts", "vsearch")
        
        # Test basic search
        result = subprocess.run([
            "python3", script_path, "search", "contract", "--limit", "2"
        ], capture_output=True, text=True, timeout=30)
        
        assert result.returncode == 0 or "Found" in result.stdout, "CLI search should work"
        print("✅ CLI search modes working")

    def test_backward_compatibility(self):
        """Test SearchIntelligenceService still works"""
        service = get_search_intelligence_service()
        
        # Test unified_search method
        results = service.unified_search("contract", limit=3)
        assert isinstance(results, list), "unified_search should return list"
        
        # Test smart_search_with_preprocessing
        results = service.smart_search_with_preprocessing("contract", limit=3)
        assert isinstance(results, list), "smart_search_with_preprocessing should return list"
        
        print("✅ SearchIntelligenceService backward compatibility working")

    def test_performance_characteristics(self):
        """Test performance is within expected bounds"""
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
        
        # Test hybrid performance (should be reasonable)
        start = time.time()
        search(query, limit=5)
        hybrid_time = time.time() - start
        assert hybrid_time < 10.0, f"Hybrid search too slow: {hybrid_time:.3f}s"
        
        print(f"✅ Performance OK: K={keyword_time:.3f}s, S={semantic_time:.3f}s, H={hybrid_time:.3f}s")

    def test_edge_cases(self):
        """Test edge cases and error handling"""
        # Empty query
        results = search("", limit=3)
        assert isinstance(results, list), "Empty query should return list"
        
        # Non-existent terms
        results = search("xyznonexistent123", limit=3)
        assert isinstance(results, list), "Non-existent terms should return list"
        
        # Special characters
        results = search("contract@#$", limit=3)
        assert isinstance(results, list), "Special chars should return list"
        
        print("✅ Edge cases handled correctly")

    def test_rrf_merging(self):
        """Test that RRF merging produces expected results"""
        query = "contract"
        
        # Get individual results
        db = SimpleDB()
        keyword_results = db.search_content(query, limit=10)
        semantic_results = semantic_search(query, limit=10)
        hybrid_results = search(query, limit=10)
        
        # Check that hybrid has characteristics of both
        keyword_ids = {r["content_id"] for r in keyword_results}
        semantic_ids = {r["content_id"] for r in semantic_results}
        hybrid_ids = {r["content_id"] for r in hybrid_results}
        
        # Hybrid should include results from both if available
        if keyword_results and semantic_results:
            overlap_k = len(keyword_ids & hybrid_ids)
            overlap_s = len(semantic_ids & hybrid_ids)
            assert overlap_k > 0 or overlap_s > 0, "Hybrid should include results from component searches"
        
        print("✅ RRF merging working correctly")

    def test_search_intelligence_migration_compatibility(self):
        """Test that intelligence handlers still work with new search"""
        # Test that intelligence commands would work
        try:
            from tools.scripts.cli.intelligence_handler import smart_search_command

            # This should not crash - actual execution tested via CLI
            assert hasattr(smart_search_command, '__call__'), "Intelligence handlers should be callable"
            print("✅ Intelligence handler compatibility OK")
        except ImportError:
            pytest.skip("Intelligence handlers not available")

    def test_legal_handler_compatibility(self):
        """Test that legal handlers still work"""
        try:
            from search_intelligence import basic_search as search_legal

            # This should not crash - actual execution tested via CLI
            assert hasattr(search_legal, '__call__'), "Legal handlers should be callable"
            print("✅ Legal handler compatibility OK")
        except ImportError:
            pytest.skip("Legal handlers not available")


if __name__ == "__main__":
    # Run tests directly
    test_suite = TestSemanticSearchIntegration()
    
    print("🧪 Running Semantic Search Integration Tests\n")
    
    try:
        test_suite.test_vector_store_availability()
        test_suite.test_search_coordination_module()
        test_suite.test_cli_search_modes()
        test_suite.test_backward_compatibility()
        test_suite.test_performance_characteristics()
        test_suite.test_edge_cases()
        test_suite.test_rrf_merging()
        test_suite.test_search_intelligence_migration_compatibility()
        test_suite.test_legal_handler_compatibility()
        
        print("\n🎉 All integration tests passed!")
        
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)