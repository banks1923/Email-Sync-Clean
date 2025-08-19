#!/usr/bin/env python3
"""
Search Intelligence CLI Command Handlers
Implements all intelligence commands for the vsearch CLI
"""

import json
import sys
from pathlib import Path
from typing import Any

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

try:
    from search_intelligence import get_search_intelligence_service

    INTELLIGENCE_AVAILABLE = True
except ImportError as e:
    INTELLIGENCE_AVAILABLE = False
    print(f"⚠️ Search Intelligence not available: {e}")


def smart_search_command(
    query: str, limit: int = 10, use_expansion: bool = True, json_output: bool = False
):
    """Execute intelligent search with preprocessing and expansion"""
    if not INTELLIGENCE_AVAILABLE:
        print("❌ Search Intelligence service not available")
        return False

    try:
        print(f"🧠 Smart Search for: '{query}'")
        if use_expansion:
            print("📈 Query expansion enabled")

        intelligence = get_search_intelligence_service()
        results = intelligence.smart_search_with_preprocessing(
            query, limit=limit, use_expansion=use_expansion
        )

        if json_output:
            print(json.dumps(results, indent=2, default=str))
        else:
            _display_search_results(results, "🧠 Smart Search")

        return True

    except Exception as e:
        print(f"❌ Smart search failed: {e}")
        return False


def similarity_command(
    doc_id: str, limit: int = 10, threshold: float = 0.7, json_output: bool = False
):
    """Find documents similar to the specified document"""
    if not INTELLIGENCE_AVAILABLE:
        print("❌ Search Intelligence service not available")
        return False

    try:
        print(f"🔍 Finding documents similar to: {doc_id}")
        print(f"📊 Threshold: {threshold}, Limit: {limit}")

        intelligence = get_search_intelligence_service()
        results = intelligence.analyze_document_similarity(doc_id, threshold=threshold, limit=limit)

        if json_output:
            print(json.dumps(results, indent=2, default=str))
        else:
            _display_similarity_results(results, doc_id)

        return True

    except Exception as e:
        print(f"❌ Similarity analysis failed: {e}")
        return False


def cluster_command(
    threshold: float = 0.7,
    content_type: str | None = None,
    limit: int = 100,
    min_samples: int = 2,
    json_output: bool = False,
):
    """Cluster similar content using DBSCAN"""
    if not INTELLIGENCE_AVAILABLE:
        print("❌ Search Intelligence service not available")
        return False

    try:
        print(f"🎯 Clustering content with threshold: {threshold}")
        if content_type:
            print(f"📄 Content type filter: {content_type}")
        print(f"📊 Processing up to {limit} documents, min cluster size: {min_samples}")

        intelligence = get_search_intelligence_service()

        # Note: content_type filtering not yet supported in cluster_similar_content
        # TODO: Add content type filtering to the core method
        results = intelligence.cluster_similar_content(
            threshold=threshold, limit=limit, min_samples=min_samples
        )

        if json_output:
            print(json.dumps(results, indent=2, default=str))
        else:
            _display_cluster_results(results)

        return True

    except Exception as e:
        print(f"❌ Clustering failed: {e}")
        return False


def duplicates_command(
    content_type: str | None = None, threshold: float = 0.95, json_output: bool = False
):
    """Detect duplicate documents using hash and semantic similarity"""
    if not INTELLIGENCE_AVAILABLE:
        print("❌ Search Intelligence service not available")
        return False

    try:
        print(f"🔍 Detecting duplicates with similarity threshold: {threshold}")
        if content_type:
            print(f"📄 Content type filter: {content_type}")

        intelligence = get_search_intelligence_service()

        # Note: content_type filtering not yet supported in detect_duplicates
        # TODO: Add content type filtering to the core method
        results = intelligence.detect_duplicates(similarity_threshold=threshold)

        if json_output:
            print(json.dumps(results, indent=2, default=str))
        else:
            _display_duplicate_results(results)

        return True

    except Exception as e:
        print(f"❌ Duplicate detection failed: {e}")
        return False


def entities_command(doc_id: str, force_refresh: bool = False, json_output: bool = False):
    """Extract and cache entities from a document"""
    if not INTELLIGENCE_AVAILABLE:
        print("❌ Search Intelligence service not available")
        return False

    try:
        print(f"🏷️ Extracting entities from: {doc_id}")
        if force_refresh:
            print("🔄 Force refresh enabled - ignoring cache")

        intelligence = get_search_intelligence_service()
        results = intelligence.extract_and_cache_entities(doc_id, force_refresh=force_refresh)

        if json_output:
            print(json.dumps(results, indent=2, default=str))
        else:
            _display_entity_results(results, doc_id)

        return True

    except Exception as e:
        print(f"❌ Entity extraction failed: {e}")
        return False


def intel_summarize_command(
    doc_id: str,
    sentences: int = 3,
    keywords: int = 10,
    use_cache: bool = True,
    json_output: bool = False,
):
    """Auto-summarize a document with intelligence features"""
    if not INTELLIGENCE_AVAILABLE:
        print("❌ Search Intelligence service not available")
        return False

    try:
        print(f"📝 Summarizing document: {doc_id}")
        print(f"📊 Target: {sentences} sentences, {keywords} keywords")
        if not use_cache:
            print("🚫 Cache disabled")

        intelligence = get_search_intelligence_service()
        results = intelligence.auto_summarize_document(
            doc_id, max_sentences=sentences, max_keywords=keywords, use_cache=use_cache
        )

        if json_output:
            print(json.dumps(results, indent=2, default=str))
        else:
            _display_summary_results(results, doc_id)

        return True

    except Exception as e:
        print(f"❌ Document summarization failed: {e}")
        return False


# Display helper functions
def _display_search_results(results: list[dict[str, Any]], title: str):
    """Display search results in a formatted way"""
    print(f"\n=== {title} Results ===")

    if not results:
        print("❌ No results found")
        return

    print(f"✅ Found {len(results)} results")

    for i, result in enumerate(results, 1):
        score = result.get("score", result.get("similarity_score", 1.0))
        content = result.get("content", {})
        metadata = result.get("metadata", {})

        # Determine content type
        content_type = metadata.get("content_type", result.get("content_type", "unknown"))
        type_icons = {"email": "📧", "pdf": "📄", "transcript": "🎙️", "document": "📄", "note": "📝"}
        icon = type_icons.get(content_type, "📄")

        print(f"\n--- {icon} Result {i} (Score: {score:.3f}) ---")
        print(f"ID: {result.get('id', result.get('content_id', 'Unknown'))}")
        print(f"Title: {content.get('title', result.get('title', 'No title'))}")
        print(f"Type: {content_type}")

        # Show snippet
        content_text = content.get("content", result.get("content", ""))
        if isinstance(content_text, str) and content_text:
            snippet = content_text[:200].replace("\n", " ")
            print(f"Content: {snippet}...")


def _display_similarity_results(results: list[dict[str, Any]], source_doc_id: str):
    """Display similarity analysis results"""
    print(f"\n=== Similar Documents to {source_doc_id} ===")

    if not results:
        print("❌ No similar documents found")
        return

    print(f"✅ Found {len(results)} similar documents")

    for i, result in enumerate(results, 1):
        similarity = result.get("similarity_score", result.get("score", 0.0))
        doc_id = result.get("content_id", result.get("id", "Unknown"))
        title = result.get("title", "No title")
        content_type = result.get("content_type", "unknown")

        type_icons = {"email": "📧", "pdf": "📄", "transcript": "🎙️", "document": "📄", "note": "📝"}
        icon = type_icons.get(content_type, "📄")

        print(f"\n{icon} {i}. {title}")
        print(f"   ID: {doc_id}")
        print(f"   Similarity: {similarity:.3f}")
        print(f"   Type: {content_type}")


def _display_cluster_results(results: list[dict[str, Any]]):
    """Display clustering results"""
    print("\n=== Content Clustering Results ===")

    if not results:
        print("❌ No clusters found")
        return

    total_docs = sum(cluster.get("size", 0) for cluster in results)
    print(f"📊 Documents clustered: {total_docs}")
    print(f"🎯 Clusters found: {len(results)}")

    for i, cluster in enumerate(results):
        cluster_id = cluster.get("cluster_id", i)
        size = cluster.get("size", 0)
        documents = cluster.get("documents", [])

        print(f"\n--- 🎯 Cluster {cluster_id} ({size} documents) ---")

        for j, doc in enumerate(documents[:5]):  # Show first 5 docs
            doc_id = doc.get("content_id", doc.get("id", "Unknown"))
            title = doc.get("title", "No title")[:50]
            content_type = doc.get("content_type", "unknown")

            type_icons = {
                "email": "📧",
                "pdf": "📄",
                "transcript": "🎙️",
                "document": "📄",
                "note": "📝",
            }
            icon = type_icons.get(content_type, "📄")

            print(f"  {icon} {doc_id}: {title}...")

        if len(documents) > 5:
            print(f"  ... and {len(documents) - 5} more documents")


def _display_duplicate_results(results: list[dict[str, Any]]):
    """Display duplicate detection results"""
    print("\n=== Duplicate Detection Results ===")

    if not results:
        print("✅ No duplicates found")
        return

    # Separate by type
    exact_duplicates = [r for r in results if r.get("type") == "hash"]
    near_duplicates = [r for r in results if r.get("type") == "semantic"]

    total_docs = sum(group.get("count", 0) for group in results)
    print(f"📊 Total duplicate documents: {total_docs}")
    print(f"🔍 Exact duplicate groups: {len(exact_duplicates)}")
    print(f"🔍 Near duplicate groups: {len(near_duplicates)}")

    # Display exact duplicates
    if exact_duplicates:
        print("\n--- 🎯 Exact Duplicates (Hash-based) ---")
        for i, group in enumerate(exact_duplicates):
            docs = group.get("documents", [])
            print(f"\nGroup {i + 1} ({len(docs)} documents):")
            for doc in docs:
                doc_id = doc.get("content_id", doc.get("id", "Unknown"))
                title = doc.get("title", "No title")[:50]
                print(f"  📄 {doc_id}: {title}...")

    # Display near duplicates
    if near_duplicates:
        print("\n--- 🔍 Near Duplicates (Semantic similarity) ---")
        for i, group in enumerate(near_duplicates):
            docs = group.get("documents", [])
            similarity = group.get("similarity", 0.0)
            print(f"\nGroup {i + 1} ({len(docs)} documents, similarity: {similarity:.3f}):")
            for doc in docs:
                doc_id = doc.get("content_id", doc.get("id", "Unknown"))
                title = doc.get("title", "No title")[:50]
                print(f"  📄 {doc_id}: {title}...")


def _display_entity_results(results: dict[str, Any], doc_id: str):
    """Display entity extraction results"""
    print(f"\n=== Entity Extraction for {doc_id} ===")

    entities = results.get("entities", {})
    cached = results.get("cached", False)

    if cached:
        print("📋 Results from cache")
    else:
        print("🔄 Freshly extracted")

    if not entities:
        print("❌ No entities found")
        return

    for entity_type, entity_list in entities.items():
        if entity_list:
            print(f"\n🏷️ {entity_type.upper()} ({len(entity_list)} found):")
            for entity in entity_list[:10]:  # Show first 10
                confidence = ""
                if isinstance(entity, dict):
                    text = entity.get("text", entity.get("name", str(entity)))
                    conf = entity.get("confidence", entity.get("score"))
                    if conf:
                        confidence = f" (confidence: {conf:.2f})"
                else:
                    text = str(entity)

                print(f"  • {text}{confidence}")

            if len(entity_list) > 10:
                print(f"  ... and {len(entity_list) - 10} more")


def _display_summary_results(results: dict[str, Any], doc_id: str):
    """Display document summary results"""
    print(f"\n=== Document Summary for {doc_id} ===")

    summary_text = results.get("summary_text", "")
    keywords = results.get("tf_idf_keywords", {})
    sentences = results.get("textrank_sentences", [])
    cached = results.get("cached", False)

    if cached:
        print("📋 Results from cache")
    else:
        print("🔄 Freshly generated")

    # Display summary
    if summary_text:
        print(f"\n📝 Summary:\n{summary_text}")

    # Display keywords
    if keywords:
        print("\n🔑 Top Keywords:")
        sorted_keywords = sorted(keywords.items(), key=lambda x: x[1], reverse=True)
        for keyword, score in sorted_keywords[:10]:
            print(f"  • {keyword} (score: {score:.3f})")

    # Display key sentences
    if sentences:
        print("\n📄 Key Sentences:")
        for i, sentence in enumerate(sentences[:5], 1):
            if isinstance(sentence, dict):
                text = sentence.get("text", sentence.get("sentence", str(sentence)))
                score = sentence.get("score", "")
                score_text = f" (score: {score:.3f})" if score else ""
            else:
                text = str(sentence)
                score_text = ""

            print(f"  {i}. {text[:200]}...{score_text}")
