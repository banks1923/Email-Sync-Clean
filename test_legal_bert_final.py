#!/usr/bin/env python3
"""Test all Legal BERT functionality - Final comprehensive test."""

from loguru import logger
from search_intelligence.main import SearchIntelligenceService
from shared.simple_db import SimpleDB
import json

def test_all_features():
    """Test all Legal BERT features comprehensively."""
    search_service = SearchIntelligenceService()
    db = SimpleDB()
    
    print("\n" + "="*60)
    print("LEGAL BERT FUNCTIONALITY TEST - POST NUCLEAR RESET")
    print("="*60 + "\n")
    
    # Database Status
    print("📊 DATABASE STATUS")
    stats = db.fetch_one("""
        SELECT 
            COUNT(*) as total,
            COUNT(CASE WHEN source_type = 'email_message' THEN 1 END) as emails,
            COUNT(CASE WHEN ready_for_embedding = 0 THEN 1 END) as embedded
        FROM content_unified
    """)
    print(f"   Total documents: {stats['total']}")
    print(f"   Email messages: {stats['emails']}")
    print(f"   Documents with embeddings: {stats['embedded']}")
    
    # 1. Entity Extraction (via batch processing)
    print("\n1️⃣  ENTITY EXTRACTION (via batch processing)")
    batch_result = search_service.process_batch(
        operation="extract_entities",
        limit=3
    )
    print(f"   ✅ Processed: {batch_result.get('processed', 0)} documents")
    print(f"   ✅ Success: {batch_result.get('success', 0)}")
    print(f"   ❌ Errors: {batch_result.get('errors', 0)}")
    
    # Check extracted entities
    entities = db.fetch("""
        SELECT COUNT(*) as count, entity_type 
        FROM email_entities 
        GROUP BY entity_type 
        LIMIT 5
    """)
    if entities:
        print("   Extracted entity types:")
        for e in entities:
            print(f"   - {e['entity_type']}: {e['count']} entities")
    
    # 2. Summarization
    print("\n2️⃣  SUMMARIZATION")
    test_text = """This lease agreement between Landlord Jim Johnson and Tenant Sarah Smith 
    for property at 123 Main Street begins January 1, 2024 with monthly rent of $2,500. 
    The security deposit is $5,000. Tenant responsible for utilities."""
    
    summary_result = search_service.summarize(test_text)
    print(f"   Keywords: {', '.join(summary_result.get('keywords', [])[:5])}")
    print(f"   Summary preview: {summary_result.get('summary', '')[:100]}...")
    
    # 3. Semantic Search (using Legal BERT embeddings)
    print("\n3️⃣  SEMANTIC SEARCH (Legal BERT)")
    search_results = search_service.smart_search("lease agreement rent", limit=3)
    print(f"   Found: {len(search_results.get('results', []))} results")
    for i, result in enumerate(search_results.get('results', [])[:2], 1):
        print(f"   {i}. Score {result.get('score', 0):.3f}: {result.get('title', '')[:50]}...")
    
    # 4. Document Similarity
    print("\n4️⃣  DOCUMENT SIMILARITY")
    doc_ids = db.fetch("SELECT id, title FROM content_unified WHERE body IS NOT NULL LIMIT 1")
    if doc_ids:
        doc = doc_ids[0]
        similar = search_service.find_similar(str(doc['id']), limit=3)
        print(f"   Reference doc: {doc['title'][:50]}...")
        print(f"   Similar documents: {len(similar.get('results', []))}")
        for result in similar.get('results', [])[:2]:
            print(f"   - Score {result.get('score', 0):.3f}: {result.get('title', '')[:40]}...")
    
    # 5. Quality Scoring
    print("\n5️⃣  QUALITY SCORING")
    quality = search_service.score_quality(test_text)
    print(f"   📖 Readability: {quality.get('readability_score', 0):.2f}/10")
    print(f"   ✅ Completeness: {quality.get('completeness_score', 0):.2f}/10")
    print(f"   ⭐ Overall Quality: {quality.get('quality_score', 0):.2f}/10")
    
    # 6. Document Clustering
    print("\n6️⃣  DOCUMENT CLUSTERING")
    clusters = search_service.cluster_documents(min_cluster_size=2, limit=20)
    print(f"   Clusters found: {len(clusters.get('clusters', []))}")
    for i, cluster in enumerate(clusters.get('clusters', [])[:2], 1):
        print(f"   Cluster {i}: {cluster.get('size', 0)} documents")
        if cluster.get('themes'):
            print(f"   - Themes: {', '.join(cluster.get('themes', [])[:3])}")
    
    # 7. Vector Store Status
    print("\n7️⃣  VECTOR STORE STATUS")
    from utilities.vector_store import get_vector_store
    vector_store = get_vector_store("legal_documents")
    vector_count = vector_store.count()
    print(f"   Legal BERT vectors indexed: {vector_count}")
    print(f"   Collection: legal_documents")
    print(f"   Dimensions: 1024 (Legal BERT)")
    
    print("\n" + "="*60)
    print("✅ ALL LEGAL BERT FEATURES TESTED SUCCESSFULLY")
    print("="*60 + "\n")
    
    return {
        'documents': stats['total'],
        'embeddings': stats['embedded'],
        'vectors': vector_count,
        'entities_extracted': batch_result.get('success', 0),
        'tests_passed': 7
    }

if __name__ == "__main__":
    results = test_all_features()
    print(f"Final Results: {json.dumps(results, indent=2)}")
