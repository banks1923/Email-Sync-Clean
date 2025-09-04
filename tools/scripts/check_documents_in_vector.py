#!/usr/bin/env python3
"""
Check document vectors using the vector service.
"""

import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from lib.search import search
from lib.vector_store import get_vector_store


def check_document_vectors():
    """
    Check document vectors in the system.
    """

    print("Checking document vectors...")
    print("-" * 60)

    store = get_vector_store()

    # Get collection info
    try:
        health = store.health_check(deep=True)
        details = health.get("details", {})
        print("✅ Vector collection info:")
        print(f"   Connected: {details.get('connected', False)}")
        print(f"   Collection: {details.get('collection_name', 'unknown')}")
        print(f"   Dimensions: {details.get('vector_size', 'unknown')}")
        print(f"   Total vectors: {details.get('point_count', 0)}")
    except Exception:
        print("⚠️ Unable to fetch vector collection info (using mock?)")

    # Search for specific document-related terms
    document_queries = [
        "This is a legal contract",  # Text from legal_contract.pdf
        "chunk_id",  # Document metadata field
        "file_name pdf",  # Document terms
    ]

    for query in document_queries:
        print(f"\n🔍 Searching for: '{query}'")
        try:
            results = search(query, limit=5)
        except Exception as e:
            print(f"   Search failed: {e}")
            results = []

        if results:
            print(f"   Found {len(results)} results")

            doc_results = 0
            email_results = 0

            for result in results:
                if result.get("source_type") == "document" or "chunk_id" in result:
                    doc_results += 1
                elif result.get("source_type") == "email_message" or "message_id" in result:
                    email_results += 1

            print(f"   - Documents: {doc_results}")
            print(f"   - Emails: {email_results}")

            # Show first document result if any
            for result in results:
                if result.get("source_type") == "document" or "chunk_id" in result:
                    print("\n   📄 Sample document result:")
                    print(f"      File: {result.get('file_name', 'Unknown')}")
                    if 'semantic_score' in result:
                        print(f"      Score: {result.get('semantic_score', 0):.3f}")
                    snippet = result.get('content', '') or result.get('text_snippet', '')
                    print(f"      Text: {snippet[:100]}...")
                    if result.get("legal_metadata"):
                        print("      ✅ Has legal metadata")
                    break
        else:
            print("   No results found")


if __name__ == "__main__":
    check_document_vectors()
