#!/usr/bin/env python3
"""
Search Handler - Modular CLI component for search operations
Handles: search, multi-search commands
"""

import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from lib.exceptions import (
    EnrichmentError,
    SearchError,
    ValidationError,
    VectorStoreError,
)

# Import service locator
from tools.scripts.cli.service_locator import get_locator


def search_emails(query, limit=5, hybrid=True, mode="semantic"):
    """Semantic Search: Searches across all content using Legal BERT embeddings

    Args:
        query: Search query string
        limit: Maximum number of results
        hybrid: DEPRECATED - will be removed in v3.0 (ignored - always uses semantic)
        mode: DEPRECATED - will be removed in v3.0 (ignored - always semantic)
    """
    # Add deprecation warnings for legacy parameters
    if hybrid is not True:
        import warnings
        warnings.warn(
            "hybrid parameter is deprecated and will be removed in v3.0. Semantic search is always used.",
            DeprecationWarning,
            stacklevel=2
        )
    
    if mode != "semantic":
        import warnings
        warnings.warn(
            "mode parameter is deprecated and will be removed in v3.0. Semantic search is always used.",
            DeprecationWarning,
            stacklevel=2
        )
    
    print(f"🧠 Semantic Search for: '{query}'")
    get_locator()
    
    try:
        # Import the new semantic search directly
        from lib.search import search, vector_store_available

        # Check if vector store is available
        if not vector_store_available():
            print("❌ Vector store not available - please ensure Qdrant is running")
            return False

        print("🔍 Running semantic vector search...")

        # Perform semantic search
        results = search(query=query, limit=limit)

        if results:
            print(f"✅ Found {len(results)} semantic matches")
            display_semantic_results(results, "🧠 Semantic Search Results", limit)
            return True
        else:
            print("❌ No results found")
            return False

    except ValidationError as e:
        print(f"❌ Invalid query: {e}")
        return False
    except VectorStoreError as e:
        print(f"💥 Vector store error: {e}")
        print("ℹ️  Start Qdrant or run 'tools/scripts/vsearch admin health --deep'.")
        return False
    except EnrichmentError as e:
        print(f"❌ Result enrichment failed: {e}")
        return False
    except SearchError as e:
        print(f"❌ Search failed: {e}")
        return False


def find_literal_pattern(pattern, limit=50):
    """Find documents with exact pattern matches.

    Perfect for finding BATES IDs, section codes, email addresses, etc.
    """
    print(f"🔤 Searching for exact pattern: '{pattern}'")
    
    try:
        from lib.search import find_literal

        print("🔍 Scanning for exact matches...")

        # Perform literal search
        results = find_literal(pattern=pattern, limit=limit)

        if results:
            print(f"✅ Found {len(results)} documents with exact matches")
            display_literal_results(results, "🔤 Literal Pattern Matches", limit)
            return True
        else:
            print(f"❌ No documents found containing '{pattern}'")
            return False

    except EnrichmentError as e:
        print(f"❌ Literal search enrichment failed: {e}")
        return False
    except ValidationError as e:
        print(f"❌ Invalid pattern: {e}")
        return False
    except SearchError as e:
        print(f"❌ Literal search failed: {e}")
        return False


def display_literal_results(results, search_type, limit=None):
    """
    Display literal search results.
    """
    print(f"\n{search_type}:")
    print("-" * 50)
    
    # Limit results if specified
    if limit:
        results = results[:limit]
    
    for i, result in enumerate(results, 1):
        title = result.get("title", "Untitled")
        source_type = result.get("source_type", "unknown")
        content = result.get("content", "")
        
        # Truncate content for display
        if len(content) > 200:
            content = content[:197] + "..."
        
        print(f"\n{i}. [{source_type}] {title}")
        print(f"   Preview: {content}")
    
    print("\n" + "-" * 50)


def hybrid_search_command(query: str, limit: int = 10, why: bool = False, 
                         semantic_weight: float = 0.7, keyword_weight: float = 0.3):
    """Run true hybrid search with RRF.

    Uses Reciprocal Rank Fusion to combine semantic and keyword search.
    Fails fast (non-zero exit) if vector store is unavailable.
    """
    print(f"🔎 Hybrid Search (RRF) for: '{query}'")
    print(f"   Weights: semantic={semantic_weight:.1f}, keyword={keyword_weight:.1f}")
    try:
        from lib.search import hybrid_search

        results = hybrid_search(
            query=query, 
            limit=limit, 
            semantic_weight=semantic_weight,
            keyword_weight=keyword_weight
        )
        if not results:
            print("❌ No results found")
            return False

        print(f"✅ Found {len(results)} results")
        display_hybrid_results(results, "🔎 Hybrid Search Results", limit=limit, why=why)
        return True

    except VectorStoreError as e:
        print(f"💥 Vector store unavailable: {e}")
        print("ℹ️  Run 'tools/scripts/vsearch admin health --deep' to diagnose.")
        return False
    except ValidationError as e:
        print(f"❌ Invalid query: {e}")
        return False
    except EnrichmentError as e:
        print(f"❌ Result enrichment failed: {e}")
        return False
    except SearchError as e:
        print(f"❌ Hybrid search failed: {e}")
        return False


def display_hybrid_results(results, title: str, limit: int = None, why: bool = False):
    print(f"\n{title}:")
    print("-" * 50)
    if limit:
        results = results[:limit]

    for i, r in enumerate(results, 1):
        print(f"\n{i}. [{r.get('source_type','unknown')}] {r.get('title','Untitled')}")
        
        # Show RRF hybrid score and match sources
        hybrid_score = r.get("hybrid_score", 0.0)
        match_sources = r.get("match_sources", [])
        print(f"   RRF Score: {hybrid_score:.4f} | Sources: {', '.join(match_sources)}")
        
        # Show individual ranks if available
        if "semantic_rank" in r:
            print(f"   Semantic rank: #{r['semantic_rank']}, score: {r.get('semantic_score', 0.0):.3f}")
        if "keyword_rank" in r:
            print(f"   Keyword rank: #{r['keyword_rank']}")
            
        if why and r.get("reasons"):
            print("   Why: " + "; ".join(str(x) for x in r["reasons"]))
        
        content = r.get("content", "")
        if len(content) > 200:
            content = content[:197] + "..."
        print(f"   Preview: {content}")
    print("\n" + "-" * 50)


def search_multi_content(query, limit=5):
    """
    Search across PDFs and transcriptions only (excluding emails)
    """
    print(f"🤖 Multi-Content Search for: '{query}'")
    print("🔍 Searching PDFs and transcriptions...")
    locator = get_locator()

    try:
        vector_service = locator.get_vector_service()

        if hasattr(vector_service, "validation_result") and vector_service.validation_result.get(
            "success"
        ):
            # Generate embedding for query
            embedding_result = vector_service.embedder.generate_embedding_dict(query)
            if embedding_result["success"]:
                # Search only PDF and transcription collections
                search_result = vector_service.qdrant.search_similar_multi_collection(
                    embedding_result["embedding"],
                    collections=["pdf_documents", "transcriptions"],
                    limit=limit,
                    score_threshold=0.1,
                )

                if search_result["success"] and search_result.get("matches"):
                    # Enhance results
                    enhanced_results = []
                    for match in search_result["matches"]:
                        enhanced = vector_service._enhance_search_result(match)
                        if enhanced:
                            enhanced_results.append(enhanced)

                    if enhanced_results:
                        print(f"✅ Found {len(enhanced_results)} multi-content matches")
                        display_unified_results(enhanced_results, "📚 Multi-Content Search", limit)
                        return True
                    else:
                        print("❌ No valid results found")
                        return False
                else:
                    print("❌ No results found")
                    return False
            else:
                print(
                    f"❌ Failed to generate embedding: {embedding_result.get('error', 'Unknown error')}"
                )
                return False
        else:
            print("⚠️  Vector service not ready")
            return False
    except Exception as e:
        print(f"❌ Multi-content search error: {e}")
        return False


def display_semantic_results(results, search_type, limit=None):
    """
    Display semantic search results in a clean format.
    """
    print(f"\n{search_type}:")
    print("-" * 50)
    
    # Limit results if specified
    if limit:
        results = results[:limit]
    
    for i, result in enumerate(results, 1):
        title = result.get("title", "Untitled")
        source_type = result.get("source_type", "unknown")
        score = result.get("semantic_score", 0.0)
        content = result.get("content", "")
        
        # Truncate content for display
        if len(content) > 200:
            content = content[:197] + "..."
        
        print(f"\n{i}. [{source_type}] {title}")
        print(f"   Score: {score:.3f}")
        print(f"   Preview: {content}")
    
    print("\n" + "-" * 50)


def display_unified_results(results, search_type, limit=None):
    """
    Display unified search results with content type indicators.
    """
    if limit:
        results = results[:limit]

    print(f"\n=== {search_type} Results ===")

    for i, result in enumerate(results, 1):
        _display_single_unified_result(result, i)

        if i >= 5:  # Limit display to top 5 results
            remaining = len(results) - i
            if remaining > 0:
                print(f"\n... and {remaining} more results")
            break


def _display_single_unified_result(result, index):
    """
    Display a single unified search result.
    """
    content_type = result.get("type", "unknown")
    score = result.get("score", 1.0)
    title = result.get("title", "No title")
    content = result.get("content", "No content")

    # Content type icons
    type_icons = {"email": "📧", "pdf": "📄", "transcription": "🎙️"}
    icon = type_icons.get(content_type, "📄")

    print(f"\n--- {icon} Result {index} [{content_type.upper()}] (Score: {score:.3f}) ---")
    print(f"Title: {title}")

    # Show metadata based on content type
    metadata = result.get("metadata", {})
    if content_type == "email":
        print(f"From: {metadata.get('sender', 'Unknown')}")
        print(f"Date: {metadata.get('date', 'Unknown')}")
    elif content_type == "pdf":
        print(f"File: {metadata.get('file_name', 'Unknown')}")
        print(f"Chunk: {metadata.get('chunk_index', 0)}")
    elif content_type == "transcription":
        print(f"Source: {metadata.get('source_path', 'Unknown')}")
        print(f"Words: {metadata.get('word_count', 0)}")

    print(f"Preview: {content[:150]}...")


def display_unified_search_results(results, search_type, limit=None):
    """
    Display unified search results from search intelligence service.
    """
    if limit:
        results = results[:limit]

    print(f"\n=== {search_type} Results ===")

    for i, result in enumerate(results, 1):
        score = result.get("score", 0.0)
        source = result.get("search_source", "unknown")

        print(f"\n--- Result {i} (Score: {score:.3f}, Source: {source}) ---")
        print(f"Title: {result.get('title', 'Untitled')}")

        # Show type-specific fields
        content_type = result.get("content_type", "document")
        if content_type == "email":
            print(f"From: {result.get('sender', 'Unknown')}")
            print(f"To: {result.get('recipient', 'Unknown')}")

        print(f"Date: {result.get('created_time', 'Unknown')}")

        # Show file path for analog results
        if result.get("file_path"):
            print(f"File: {result.get('file_path')}")

        # Show content preview
        content = result.get("content", "")
        if content:
            print(f"Preview: {content[:150]}...")

        if i >= 5:  # Limit display to top 5 results
            remaining = len(results) - i
            if remaining > 0:
                print(f"\n... and {remaining} more results")
            break


def display_results(emails, search_type, limit=None):
    """
    Display search results with consistent formatting.
    """
    if limit:
        emails = emails[:limit]

    print(f"\n=== {search_type} Results ===")

    for i, email in enumerate(emails, 1):
        score = email.get("score", email.get("similarity_score", 1.0))
        print(f"\n--- Result {i} (Score: {score:.3f}) ---")
        print(f"Subject: {email['subject']}")
        print(f"From: {email['sender']}")
        print(f"Date: {email.get('datetime_utc', 'Unknown')}")
        print(f"Preview: {email['content'][:150]}...")

        if i >= 5:  # Limit display to top 5 results
            remaining = len(emails) - i
            if remaining > 0:
                print(f"\n... and {remaining} more results")
            break


def main(argv=None):
    """CLI entry for search subcommand.

    Returns exit code: 0 on success, 2 on failure.
    """
    import argparse

    parser = argparse.ArgumentParser(description="Search operations")
    sub = parser.add_subparsers(dest="mode")

    p_hyb = sub.add_parser("hybrid", help="Hybrid search with RRF: semantic + keyword")
    p_hyb.add_argument("query", nargs="?", help="Query text")
    p_hyb.add_argument("--limit", type=int, default=10)
    p_hyb.add_argument("--why", action="store_true", help="Explain match reasons")
    p_hyb.add_argument("--semantic-weight", type=float, default=0.7, help="Weight for semantic (default: 0.7)")
    p_hyb.add_argument("--keyword-weight", type=float, default=0.3, help="Weight for keyword (default: 0.3)")

    p_sem = sub.add_parser("semantic", help="Semantic-only search")
    p_sem.add_argument("query", nargs="?", help="Query text")
    p_sem.add_argument("--limit", type=int, default=5)

    p_lit = sub.add_parser("literal", help="Literal pattern search")
    p_lit.add_argument("pattern", help="Exact pattern (e.g., BATES ID)")
    p_lit.add_argument("--limit", type=int, default=50)

    # If no explicit subcommand, assume hybrid
    args, rest = parser.parse_known_args(argv)

    if args.mode is None:
        # Default to hybrid
        args = parser.parse_args(["hybrid"] + (argv or []))
        ok = hybrid_search_command(args.query or "", limit=args.limit, why=args.why, 
                                  semantic_weight=args.semantic_weight, keyword_weight=args.keyword_weight)
        return 0 if ok else 2

    if args.mode == "hybrid":
        if not getattr(args, "query", None):
            parser.print_help()
            return 2
        ok = hybrid_search_command(args.query, limit=args.limit, why=args.why,
                                  semantic_weight=args.semantic_weight, keyword_weight=args.keyword_weight)
        return 0 if ok else 2

    if args.mode == "semantic":
        if not getattr(args, "query", None):
            parser.print_help()
            return 2
        ok = search_emails(args.query, limit=args.limit)
        return 0 if ok else 2

    if args.mode == "literal":
        ok = find_literal_pattern(args.pattern, limit=args.limit)
        return 0 if ok else 2

    parser.print_help()
    return 2
