#!/usr/bin/env python3
"""
Search Intelligence Module Demo

Demonstrates the key features of the search intelligence module.
Run this script to see the module in action.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from search_intelligence import get_search_intelligence_service


def demo_smart_search():
    """Demonstrate smart search with query expansion."""
    print("\n" + "=" * 60)
    print("SMART SEARCH DEMO")
    print("=" * 60)

    intelligence = get_search_intelligence_service()

    # Example queries that will be expanded
    queries = ["LLC attorney meeting Q1", "contract vs agreement", "payment invoice deadline"]

    for query in queries:
        print(f"\nOriginal Query: '{query}'")
        print("-" * 40)

        # Show preprocessing
        processed = intelligence._preprocess_query(query)
        print(f"After Preprocessing: '{processed}'")

        # Show expansion
        expanded = intelligence._expand_query(processed)
        if expanded:
            print(f"Expanded Terms: {expanded}")

        print("\nPerforming search...")
        # Note: This will fail without actual data, but shows the API
        try:
            results = intelligence.smart_search_with_preprocessing(
                query, limit=3, use_expansion=True
            )
            print(f"Found {len(results)} results")
        except Exception as e:
            print(f"Search failed (expected without data): {e}")


def demo_similarity_analysis():
    """Demonstrate document similarity analysis."""
    print("\n" + "=" * 60)
    print("DOCUMENT SIMILARITY DEMO")
    print("=" * 60)

    intelligence = get_search_intelligence_service()

    print("\nAnalyzing document similarity...")
    print("(This requires actual documents in the database)")

    # Example: Find similar documents
    try:
        similar_docs = intelligence.analyze_document_similarity(
            doc_id="sample_doc_123", limit=5, threshold=0.7
        )

        if similar_docs:
            print(f"\nFound {len(similar_docs)} similar documents:")
            for doc in similar_docs:
                print(f"  - {doc['id']}: {doc['similarity_score']:.2f}")
        else:
            print("No similar documents found")

    except Exception as e:
        print(f"Similarity analysis failed (expected without data): {e}")


def demo_duplicate_detection():
    """Demonstrate duplicate detection."""
    print("\n" + "=" * 60)
    print("DUPLICATE DETECTION DEMO")
    print("=" * 60)

    intelligence = get_search_intelligence_service()

    print("\nDetecting duplicates...")
    print("Settings: similarity_threshold=0.95")

    try:
        duplicates = intelligence.detect_duplicates(content_type="email", similarity_threshold=0.95)

        print("\nResults:")
        print(f"  Total documents: {duplicates['total_documents']}")
        print(f"  Exact duplicates: {len(duplicates['exact_duplicates'])} groups")
        print(f"  Near duplicates: {len(duplicates['near_duplicates'])} groups")
        print(f"  Duplicate rate: {duplicates['duplicate_percentage']:.1f}%")

    except Exception as e:
        print(f"Duplicate detection failed (expected without data): {e}")


def demo_clustering():
    """Demonstrate content clustering."""
    print("\n" + "=" * 60)
    print("CONTENT CLUSTERING DEMO")
    print("=" * 60)

    intelligence = get_search_intelligence_service()

    print("\nClustering similar content...")
    print("Settings: threshold=0.7, min_samples=2")

    try:
        clusters = intelligence.cluster_similar_content(
            threshold=0.7, content_type="email", limit=50, min_samples=2
        )

        if clusters:
            print(f"\nFound {len(clusters)} clusters:")
            for cluster in clusters[:3]:  # Show first 3
                print(f"\n  Cluster {cluster['cluster_id']}:")
                print(f"    Size: {cluster['size']} documents")
                if "sample_title" in cluster:
                    print(f"    Sample: {cluster['sample_title']}")
        else:
            print("No clusters found")

    except Exception as e:
        print(f"Clustering failed (expected without data): {e}")


def demo_entity_extraction():
    """Demonstrate entity extraction with caching."""
    print("\n" + "=" * 60)
    print("ENTITY EXTRACTION DEMO")
    print("=" * 60)

    intelligence = get_search_intelligence_service()

    print("\nExtracting entities from document...")

    try:
        # Mock document for demo
        result = intelligence.extract_and_cache_entities(
            doc_id="sample_doc_456", force_refresh=False
        )

        if result.get("success"):
            print(f"\nExtracted {result['total_entities']} entities:")
            for entity_type, entities in result["entities_by_type"].items():
                print(f"  {entity_type}: {len(entities)} found")
                for entity in entities[:2]:  # Show first 2
                    print(f"    - {entity['text']}")
        else:
            print(f"Extraction failed: {result.get('error')}")

    except Exception as e:
        print(f"Entity extraction failed (expected without data): {e}")


def demo_auto_summarization():
    """Demonstrate automatic summarization."""
    print("\n" + "=" * 60)
    print("AUTO-SUMMARIZATION DEMO")
    print("=" * 60)

    intelligence = get_search_intelligence_service()

    # Sample text for demonstration
    sample_text = """
    This is a sample legal document discussing the terms of a contract
    between ABC Corporation and XYZ Limited. The agreement covers the
    delivery of professional services starting from January 1st, 2024.
    The total value of the contract is $500,000 with quarterly payments
    due on the first business day of each quarter. Both parties agree
    to confidentiality terms and dispute resolution through arbitration.
    """

    print("\nSummarizing document...")

    try:
        summary = intelligence.auto_summarize_document(
            doc_id="demo_doc",
            text=sample_text,
            max_sentences=2,
            max_keywords=5,
            cache=False,  # Don't cache demo
        )

        if summary.get("success"):
            print(f"\nSummary: {summary['summary']}")
            print("\nTop Keywords:")
            for keyword, score in list(summary["keywords"].items())[:5]:
                print(f"  - {keyword}: {score:.2f}")
        else:
            print(f"Summarization failed: {summary.get('error')}")

    except Exception as e:
        print(f"Summarization failed: {e}")


def show_service_stats():
    """Show service statistics."""
    print("\n" + "=" * 60)
    print("SERVICE STATISTICS")
    print("=" * 60)

    intelligence = get_search_intelligence_service()
    stats = intelligence.get_stats()

    print("\nSearch Intelligence Service Stats:")
    print(f"  Collection: {stats['collection']}")
    print(
        f"  Entity Service: {'Available' if stats['entity_service_available'] else 'Not Available'}"
    )
    print(f"  Cached Items: {stats['cached_items']}")
    print(f"  Synonym Groups: {stats['synonym_groups']}")
    print(f"  Abbreviations: {stats['abbreviations']}")

    if "search_service" in stats:
        print("\nSearch Service Stats:")
        for key, value in stats["search_service"].items():
            print(f"  {key}: {value}")


def main():
    """Run all demos."""
    print("\n" + "=" * 60)
    print("SEARCH INTELLIGENCE MODULE DEMONSTRATION")
    print("=" * 60)
    print("\nThis demo shows the key features of the search intelligence module.")
    print("Note: Some features require actual data in the database to work.")

    # Run demos
    demo_smart_search()
    demo_similarity_analysis()
    demo_duplicate_detection()
    demo_clustering()
    demo_entity_extraction()
    demo_auto_summarization()
    show_service_stats()

    print("\n" + "=" * 60)
    print("DEMO COMPLETE")
    print("=" * 60)
    print("\nFor more information, see search_intelligence/README.md")


if __name__ == "__main__":
    main()
