#!/usr/bin/env python3
"""
Search Intelligence CLI Command Handlers - Simplified direct function calls.
"""

import json
import sys
from pathlib import Path
from typing import Any

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

try:
    from lib.search import find_literal, search
    INTELLIGENCE_AVAILABLE = True
except ImportError as e:
    INTELLIGENCE_AVAILABLE = False
    print(f"⚠️ Search library not available: {e}")


def smart_search_command(
    query: str, limit: int = 10, use_expansion: bool = True, json_output: bool = False
):
    """
    Execute semantic search (expansion flag ignored - always semantic).
    """
    if not INTELLIGENCE_AVAILABLE:
        print("❌ Search Intelligence service not available")
        return False

    try:
        print(f"🧠 Semantic Search for: '{query}'")
        
        # Direct semantic search - expansion flag ignored
        results = search(query, limit=limit)

        if json_output:
            print(json.dumps(results, indent=2, default=str))
        else:
            _display_search_results(results, "🧠 Semantic Search")

        return True

    except Exception as e:
        print(f"❌ Search failed: {e}")
        return False


def literal_search_command(
    pattern: str, limit: int = 50, json_output: bool = False
):
    """
    Find documents with exact pattern matches.
    """
    if not INTELLIGENCE_AVAILABLE:
        print("❌ Search Intelligence service not available")
        return False

    try:
        print(f"🔍 Literal search for: '{pattern}'")
        
        results = find_literal(pattern, limit=limit)

        if json_output:
            print(json.dumps(results, indent=2, default=str))
        else:
            _display_search_results(results, "🔍 Literal Search")

        return True

    except Exception as e:
        print(f"❌ Literal search failed: {e}")
        return False


def _display_search_results(results: list[dict[str, Any]], title: str):
    """
    Display search results in readable format.
    """
    print(f"\n{title} Results: {len(results)} found")
    print("=" * 60)
    
    for i, result in enumerate(results, 1):
        print(f"\n--- Result {i} ---")
        print(f"ID: {result.get('content_id', 'Unknown')}")
        print(f"Type: {result.get('source_type', 'Unknown')}")
        print(f"Title: {result.get('title', 'No title')}")
        
        if 'semantic_score' in result:
            print(f"Score: {result['semantic_score']:.3f}")
        elif 'match_type' in result:
            print(f"Match: {result['match_type']}")
            
        content = result.get('content', '')
        if content:
            preview = content[:200] + "..." if len(content) > 200 else content
            print(f"Content: {preview}")
        
        print("-" * 40)


# Removed functions that don't exist in new API:
# - similarity_command (not available)
# - cluster_command (not available) 
# - duplicate_command (not available)
# - process_batch_command (not available)

def add_intelligence_commands(subparsers):
    """
    Add intelligence commands to vsearch CLI.
    """
    # Smart search (semantic)
    smart_parser = subparsers.add_parser("smart-search", help="Semantic search")
    smart_parser.add_argument("query", help="Search query")
    smart_parser.add_argument("--limit", type=int, default=10, help="Maximum results")
    smart_parser.add_argument("--json", action="store_true", help="JSON output")
    
    # Literal search  
    literal_parser = subparsers.add_parser("literal-search", help="Exact pattern search")
    literal_parser.add_argument("pattern", help="Pattern to search for")
    literal_parser.add_argument("--limit", type=int, default=50, help="Maximum results")
    literal_parser.add_argument("--json", action="store_true", help="JSON output")


def handle_intelligence_command(args):
    """
    Route intelligence commands to appropriate handlers.
    """
    command = getattr(args, "command", None)
    
    if command == "smart-search":
        return smart_search_command(
            args.query, 
            limit=args.limit,
            json_output=args.json
        )
    elif command == "literal-search":
        return literal_search_command(
            args.pattern,
            limit=args.limit,
            json_output=args.json
        )
    else:
        print(f"❌ Unknown intelligence command: {command}")
        return False
