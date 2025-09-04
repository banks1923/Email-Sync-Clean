#!/usr/bin/env python3
"""Test all Legal BERT functionality."""

from search_intelligence.main import SearchIntelligenceService
from shared.simple_db import SimpleDB

def test_all_features():
    """Test all Legal BERT features."""
    search_service = SearchIntelligenceService()
    db = SimpleDB()
    
    print("\n=== Testing Legal BERT Features ===\n")
    
    # 1. Entity Extraction
    print("1. ENTITY EXTRACTION")
    text = "On January 15, 2023, Jim Johnson filed a complaint with Judge Smith in Santa Clara County regarding a $50,000 breach of contract claim."
    entities = search_service.extract_entities(text)
    print(f"   Extracted: {len(entities.get('entities', []))} entities")
    for entity in entities.get('entities', [])[:3]:
        print(f"   - {entity['type']}: {entity['text']}")
    
    # 2. Summarization
    print("\n2. SUMMARIZATION")
    summary_result = search_service.summarize(text)
    print(f"   Keywords: {', '.join(summary_result.get('keywords', [])[:5])}")
    print(f"   Summary: {summary_result.get('summary', '')[:100]}...")
    
    # 3. Semantic Search (with embeddings)
    print("\n3. SEMANTIC SEARCH")
    search_results = search_service.smart_search("lease agreement", limit=3)
    print(f"   Results: {len(search_results.get('results', []))}")
    for result in search_results.get('results', [])[:2]:
        print(f"   - Score {result.get('score', 0):.3f}: {result.get('title', '')[:50]}...")
    
    # 4. Similarity Search
    print("\n4. SIMILARITY SEARCH")
    # Get a document ID
    doc_ids = db.fetch("SELECT id FROM content_unified WHERE body IS NOT NULL LIMIT 1")
    if doc_ids:
        similar = search_service.find_similar(str(doc_ids[0]['id']), limit=3)
        print(f"   Similar to doc {doc_ids[0]['id']}: {len(similar.get('results', []))} found")
        for result in similar.get('results', [])[:2]:
            print(f"   - Score {result.get('score', 0):.3f}: {result.get('title', '')[:50]}...")
    
    # 5. Quality Scoring
    print("\n5. QUALITY SCORING")
    quality = search_service.score_quality(text)
    print(f"   Readability: {quality.get('readability_score', 0):.2f}")
    print(f"   Completeness: {quality.get('completeness_score', 0):.2f}")
    print(f"   Overall: {quality.get('quality_score', 0):.2f}")
    
    # 6. Document Clustering
    print("\n6. DOCUMENT CLUSTERING")
    clusters = search_service.cluster_documents(min_cluster_size=2, limit=20)
    print(f"   Clusters: {len(clusters.get('clusters', []))}")
    for i, cluster in enumerate(clusters.get('clusters', [])[:2]):
        print(f"   - Cluster {i+1}: {cluster.get('size', 0)} documents")
        print(f"     Theme: {', '.join(cluster.get('themes', [])[:3])}")
    
    # 7. Batch Processing
    print("\n7. BATCH PROCESSING")
    batch_result = search_service.process_batch(
        operation="extract_entities",
        limit=5
    )
    print(f"   Processed: {batch_result.get('processed', 0)} documents")
    print(f"   Success: {batch_result.get('success', 0)}")
    print(f"   Errors: {batch_result.get('errors', 0)}")
    
    # 8. Database Stats
    print("\n8. DATABASE STATS")
    stats = db.fetch_one("""
        SELECT 
            COUNT(*) as total,
            COUNT(CASE WHEN source_type = 'email_message' THEN 1 END) as emails,
            COUNT(CASE WHEN ready_for_embedding = 0 THEN 1 END) as embedded
        FROM content_unified
    """)
    print(f"   Total documents: {stats['total']}")
    print(f"   Email messages: {stats['emails']}")
    print(f"   With embeddings: {stats['embedded']}")
    
    print("\n=== All Tests Complete ===")

if __name__ == "__main__":
    test_all_features()
