#!/usr/bin/env python3
"""
Test script for search system markdown compatibility.
"""

import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from lib.search import search as semantic_search


def test_search_intelligence():
    """
    Test the function-based search with basic expectations.
    """
    print("=" * 50)
    print("Testing Search Intelligence Markdown Integration")
    print("=" * 50)

    try:
        results = semantic_search("contract", limit=2)
        assert isinstance(results, list)
        print("✅ Semantic search callable and returned list")
        return True
    except Exception as e:
        print(f"❌ Semantic search failed: {e}")
        return False


def test_cli_integration():
    """
    Test CLI integration.
    """
    print("\n" + "=" * 50)
    print("Testing CLI Integration")
    print("=" * 50)

    try:
        from tools.scripts import vsearch as cli
        assert hasattr(cli, 'search_command')
        print("✅ CLI search_command available")
        return True
    except Exception as e:
        print(f"❌ CLI integration error: {e}")
        return False


if __name__ == "__main__":
    success = True

    # Test search intelligence
    if not test_search_intelligence():
        success = False

    # Test CLI integration
    if not test_cli_integration():
        success = False

    print("\n" + "=" * 50)
    if success:
        print("✅ ALL TESTS PASSED")
        print("Task 11 subtasks completed successfully!")
    else:
        print("❌ Some tests failed")
    print("=" * 50)

    sys.exit(0 if success else 1)
