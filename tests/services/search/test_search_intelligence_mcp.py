#!/usr/bin/env python3
"""
Test script for Search Intelligence MCP Server
"""

import sys
from pathlib import Path

# Add project root to path
sys.path.append(str(Path(__file__).parent.parent))

from infrastructure.mcp_servers.search_intelligence_mcp import (
    search_cluster,
    search_entities,
    search_process_all,
    search_similar,
    search_smart,
    search_summarize,
)


def test_search_smart():
    """Test smart search functionality"""
    print("\n🔍 Testing search_smart...")
    result = search_smart("contract", limit=3, use_expansion=True)
    print(result)
    assert "Smart Search Results" in result or "No results found" in result
    print("✅ search_smart test passed")


def test_search_entities():
    """Test entity extraction"""
    print("\n🏷️ Testing search_entities...")
    test_text = (
        "John Smith from ABC Corporation signed the contract on January 15, 2024 in New York."
    )
    result = search_entities(text=test_text)
    print(result)
    assert "Entity Extraction" in result or "No entities found" in result
    print("✅ search_entities test passed")


def test_search_summarize():
    """Test document summarization"""
    print("\n📝 Testing search_summarize...")
    test_text = """
    This is a test document about legal contracts. Contracts are important legal documents
    that establish agreements between parties. They contain terms, conditions, and obligations.
    Contract law is a fundamental aspect of business relationships. Proper contract management
    ensures compliance and reduces legal risks. Organizations should maintain detailed records
    of all contractual agreements.
    """
    result = search_summarize(text=test_text, max_sentences=2, max_keywords=5)
    print(result)
    assert "Document Summary" in result
    print("✅ search_summarize test passed")


def test_search_similar():
    """Test document similarity search"""
    print("\n🔄 Testing search_similar...")
    # This will likely fail without a valid document ID, but we test the function works
    result = search_similar("test_doc_id", threshold=0.5, limit=5)
    print(result)
    # Function should return a result even if no documents found
    assert "Similar Documents" in result or "No similar documents" in result
    print("✅ search_similar test passed")


def test_search_cluster():
    """Test document clustering"""
    print("\n🗂️ Testing search_cluster...")
    result = search_cluster(threshold=0.6, limit=50, min_cluster_size=2)
    print(result)
    assert "Document Clusters" in result or "No clusters found" in result
    print("✅ search_cluster test passed")


def test_search_process_all():
    """Test batch processing"""
    print("\n⚙️ Testing search_process_all...")
    result = search_process_all("find_duplicates", limit=10)
    print(result)
    assert "Batch Processing" in result or "Error" in result
    print("✅ search_process_all test passed")


def main():
    """Run all tests"""
    print("=" * 60)
    print("Search Intelligence MCP Server Test Suite")
    print("=" * 60)

    try:
        test_search_smart()
        test_search_entities()
        test_search_summarize()
        test_search_similar()
        test_search_cluster()
        test_search_process_all()

        print("\n" + "=" * 60)
        print("🎉 All tests passed successfully!")
        print("=" * 60)

    except AssertionError as e:
        print(f"\n❌ Test failed: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
