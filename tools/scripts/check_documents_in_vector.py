#!/usr/bin/env python3
"""
Check document vectors using the vector service.
"""

import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from search_intelligence import get_search_intelligence_service as get_search_service


def check_document_vectors():
    """
    Check document vectors in the system.
    """

    print("Checking document vectors...")
    print("-" * 60)

    service = get_search_service()

    # Get collection info
    info = service.get_collection_info()
    if info["success"]:
        print("✅ Vector collection info:")
        print(f"   Total vectors: {info.get('vector_count', 0)}")
        print(f"   Provider: {info.get('provider', 'unknown')}")
        print(f"   Dimensions: {info.get('dimensions', 'unknown')}")

    # Search for specific document-related terms
    document_queries = [
        "This is a legal contract",  # Text from legal_contract.pdf
        "chunk_id",  # Document metadata field
        "file_name pdf",  # Document terms
    ]

    for query in document_queries:
        print(f"\n🔍 Searching for: '{query}'")
        results = service.search_similar(query, limit=5)

        if results["success"] and results.get("data"):
            print(f"   Found {len(results['data'])} results")

            doc_results = 0
            email_results = 0

            for result in results["data"]:
                if result.get("source") == "document" or "chunk_id" in result:
                    doc_results += 1
                elif "message_id" in result:
                    email_results += 1

            print(f"   - Documents: {doc_results}")
            print(f"   - Emails: {email_results}")

            # Show first document result if any
            for result in results["data"]:
                if result.get("source") == "document" or "chunk_id" in result:
                    print("\n   📄 Sample document result:")
                    print(f"      File: {result.get('file_name', 'Unknown')}")
                    print(f"      Score: {result.get('score', 0):.3f}")
                    print(f"      Text: {result.get('text_snippet', '')[:100]}...")
                    if result.get("legal_metadata"):
                        print("      ✅ Has legal metadata")
                    break
        else:
            print("   No results found")

    service.cleanup()


if __name__ == "__main__":
    check_document_vectors()
