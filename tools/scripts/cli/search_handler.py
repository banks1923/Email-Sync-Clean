#!/usr/bin/env python3
"""
Search Handler - Modular CLI component for search operations
Handles: search, multi-search commands
"""

import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

# Import service locator
from tools.scripts.cli.service_locator import get_locator


def search_emails(query, limit=5, hybrid=True, mode="semantic"):
    """Semantic Search: Searches across all content using Legal BERT embeddings

    Args:
        query: Search query string
        limit: Maximum number of results
        hybrid: Legacy parameter (ignored - always uses semantic)
        mode: Legacy parameter (ignored - always semantic)
    """
    print(f"🧠 Semantic Search for: '{query}'")
    get_locator()
    
    try:
        # Import the new semantic search directly
        from search_intelligence import search, vector_store_available
        
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
            
    except Exception as e:
        print(f"❌ Search error: {e}")
        return False


def find_literal_pattern(pattern, limit=50):
    """Find documents with exact pattern matches.
    
    Perfect for finding BATES IDs, section codes, email addresses, etc.
    """
    print(f"🔤 Searching for exact pattern: '{pattern}'")
    
    try:
        from search_intelligence import find_literal
        
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
            
    except Exception as e:
        print(f"❌ Literal search error: {e}")
        return False


def display_literal_results(results, search_type, limit=None):
    """Display literal search results."""
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
    """Display semantic search results in a clean format."""
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
