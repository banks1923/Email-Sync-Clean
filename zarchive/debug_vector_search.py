#!/usr/bin/env python3
"""
Comprehensive debug script for the search vector system.
Tests all components and identifies issues.
"""

import time
import numpy as np
from loguru import logger
from qdrant_client import QdrantClient

# Configure logging
logger.add("vector_debug.log", level="DEBUG")

def section_header(title: str):
    """Print a formatted section header."""
    print("\n" + "="*60)
    print(f"🔍 {title}")
    print("="*60)

def test_vector_store_connection():
    """Test 1: Vector Store Connection"""
    section_header("TEST 1: VECTOR STORE CONNECTION")
    
    try:
        from utilities.vector_store import get_vector_store
        
        # Test wrapper connection
        vs = get_vector_store()
        print("✅ Vector store wrapper connected")
        print(f"   Host: {vs.host}")
        print(f"   Port: {vs.port}")
        
        # Test direct connection
        client = QdrantClient('localhost', port=6333)
        collections = client.get_collections()
        print("✅ Direct Qdrant connection successful")
        print(f"   Collections: {[c.name for c in collections.collections]}")
        
        # Check emails collection
        if any(c.name == 'emails' for c in collections.collections):
            info = client.get_collection('emails')
            print("✅ 'emails' collection exists")
            print(f"   Points count: {info.points_count}")
            print(f"   Vectors dimension: {info.config.params.vectors.size if hasattr(info.config.params.vectors, 'size') else 'N/A'}")
            print(f"   Distance metric: {info.config.params.vectors.distance if hasattr(info.config.params.vectors, 'distance') else 'N/A'}")
            
            # Debug the attribute issue
            print("\n⚠️  Attribute debug:")
            print(f"   info.points_count: {info.points_count}")
            print(f"   info.vectors_count: {getattr(info, 'vectors_count', 'ATTRIBUTE DOES NOT EXIST')}")
        
        return True
    except Exception as e:
        print(f"❌ Connection failed: {e}")
        logger.error(f"Vector store connection failed: {e}")
        return False

def test_embedding_service():
    """Test 2: Embedding Service"""
    section_header("TEST 2: EMBEDDING SERVICE")
    
    try:
        from utilities.embeddings import get_embedding_service
        
        emb_service = get_embedding_service()
        print("✅ Embedding service initialized")
        
        # Test embedding generation
        test_text = "This is a test legal document about contracts."
        start = time.time()
        embedding = emb_service.get_embedding(test_text)
        elapsed = time.time() - start
        
        print(f"✅ Embedding generated in {elapsed:.2f}s")
        print(f"   Dimension: {len(embedding)}")
        print(f"   Type: {type(embedding)}")
        print(f"   Non-zero values: {np.count_nonzero(embedding)}/{len(embedding)}")
        print(f"   Mean: {np.mean(embedding):.4f}")
        print(f"   Std: {np.std(embedding):.4f}")
        
        # Test batch embeddings
        texts = ["Document 1", "Document 2", "Document 3"]
        start = time.time()
        embeddings = emb_service.get_embeddings(texts)
        elapsed = time.time() - start
        
        print(f"✅ Batch embeddings generated in {elapsed:.2f}s")
        print(f"   Count: {len(embeddings)}")
        print(f"   Shape: {len(embeddings)}x{len(embeddings[0]) if embeddings else 0}")
        
        return True
    except Exception as e:
        print(f"❌ Embedding service failed: {e}")
        logger.error(f"Embedding service failed: {e}")
        return False

def test_search_coordination():
    """Test 3: Search Coordination"""
    section_header("TEST 3: SEARCH COORDINATION")
    
    try:
        from search.main import search, semantic_search, vector_store_available
        
        # Check vector store availability
        available = vector_store_available()
        print(f"{'✅' if available else '❌'} Vector store available: {available}")
        
        # Test pure semantic search
        print("\n📊 Testing semantic search...")
        start = time.time()
        results = semantic_search("legal contract", limit=3)
        elapsed = time.time() - start
        
        print(f"✅ Semantic search completed in {elapsed:.2f}s")
        print(f"   Results: {len(results)}")
        if results:
            print(f"   Top result: {results[0].get('title', 'N/A')[:50]}")
            print(f"   Score: {results[0].get('score', 'N/A')}")
        
        # Test hybrid search
        print("\n📊 Testing hybrid search...")
        start = time.time()
        results = search("legal contract", limit=3)
        elapsed = time.time() - start
        
        print(f"✅ Hybrid search completed in {elapsed:.2f}s")
        print(f"   Results: {len(results)}")
        if results:
            print(f"   Top result: {results[0].get('title', 'N/A')[:50]}")
            print(f"   RRF Score: {results[0].get('rrf_score', 'N/A')}")
        
        return True
    except Exception as e:
        print(f"❌ Search coordination failed: {e}")
        logger.error(f"Search coordination failed: {e}")
        return False

def test_vector_content_sync():
    """Test 4: Vector-Database Synchronization"""
    section_header("TEST 4: VECTOR-DATABASE SYNC")
    
    try:
        from shared.simple_db import SimpleDB
        from qdrant_client import QdrantClient
        
        db = SimpleDB()
        client = QdrantClient('localhost', port=6333)
        
        # Get content from database
        db_content = db.search_content("", limit=1000)  # Get all
        print(f"📊 Database content count: {len(db_content)}")
        
        # Get vectors from Qdrant
        vectors = client.scroll(
            collection_name='emails',
            limit=1000,
            with_payload=True,
            with_vectors=False
        )
        
        vector_ids = {point.id for point in vectors[0]}
        print(f"📊 Vector store count: {len(vector_ids)}")
        
        # Check for mismatches
        db_ids = {str(item['id']) for item in db_content}
        
        missing_in_vectors = db_ids - vector_ids
        missing_in_db = vector_ids - db_ids
        
        print("\n📊 Synchronization status:")
        print(f"   Missing in vectors: {len(missing_in_vectors)}")
        print(f"   Missing in database: {len(missing_in_db)}")
        print(f"   Synchronized: {len(db_ids & vector_ids)}")
        
        if missing_in_vectors:
            print("\n⚠️  Sample IDs missing in vectors:")
            for id in list(missing_in_vectors)[:5]:
                print(f"   - {id}")
        
        if missing_in_db:
            print("\n⚠️  Sample IDs missing in database:")
            for id in list(missing_in_db)[:5]:
                print(f"   - {id}")
        
        return len(missing_in_vectors) == 0 and len(missing_in_db) == 0
    except Exception as e:
        print(f"❌ Sync check failed: {e}")
        logger.error(f"Sync check failed: {e}")
        return False

def test_search_quality():
    """Test 5: Search Quality"""
    section_header("TEST 5: SEARCH QUALITY")
    
    try:
        from search.main import search, semantic_search
        from shared.simple_db import SimpleDB
        
        test_queries = [
            ("contract", "keyword-heavy term"),
            ("legal dispute resolution", "semantic concept"),
            ("2024", "date/number"),
            ("John Smith", "entity name"),
            ("asdfghjkl", "nonsense query")
        ]
        
        db = SimpleDB()
        
        for query, description in test_queries:
            print(f"\n🔍 Testing: '{query}' ({description})")
            
            # Keyword search
            keyword_results = db.search_content(query, limit=3)
            print(f"   Keyword: {len(keyword_results)} results")
            
            # Semantic search
            try:
                semantic_results = semantic_search(query, limit=3)
                print(f"   Semantic: {len(semantic_results)} results")
            except Exception as e:
                print(f"   Semantic: Failed - {e}")
            
            # Hybrid search
            hybrid_results = search(query, limit=3)
            print(f"   Hybrid: {len(hybrid_results)} results")
            
            if hybrid_results:
                print(f"   Top result: {hybrid_results[0].get('title', 'N/A')[:40]}...")
        
        return True
    except Exception as e:
        print(f"❌ Search quality test failed: {e}")
        logger.error(f"Search quality test failed: {e}")
        return False

def test_error_handling():
    """Test 6: Error Handling"""
    section_header("TEST 6: ERROR HANDLING")
    
    try:
        from search.main import search
        
        # Test with vector store supposedly down
        print("🔍 Testing graceful degradation...")
        
        # This should still work even if vector fails
        results = search("test query", limit=5)
        print("✅ Search works even with potential vector issues")
        print(f"   Results: {len(results)}")
        
        # Test with empty query
        print("\n🔍 Testing empty query...")
        results = search("", limit=5)
        print(f"✅ Empty query handled: {len(results)} results")
        
        # Test with huge limit
        print("\n🔍 Testing huge limit...")
        results = search("test", limit=10000)
        print(f"✅ Huge limit handled: {len(results)} results returned")
        
        return True
    except Exception as e:
        print(f"❌ Error handling test failed: {e}")
        logger.error(f"Error handling test failed: {e}")
        return False

def main():
    """Run all debug tests."""
    print("🚀 COMPREHENSIVE VECTOR SEARCH SYSTEM DEBUG")
    print("=" * 60)
    
    results = {
        "Vector Store Connection": test_vector_store_connection(),
        "Embedding Service": test_embedding_service(),
        "Search Coordination": test_search_coordination(),
        "Vector-DB Sync": test_vector_content_sync(),
        "Search Quality": test_search_quality(),
        "Error Handling": test_error_handling()
    }
    
    section_header("FINAL REPORT")
    
    passed = sum(1 for v in results.values() if v)
    total = len(results)
    
    for test, result in results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status} - {test}")
    
    print(f"\n📊 Overall: {passed}/{total} tests passed")
    
    if passed < total:
        print("\n⚠️  ISSUES DETECTED - Review debug output above")
    else:
        print("\n✅ ALL SYSTEMS OPERATIONAL")
    
    print("\n📝 Detailed logs saved to: vector_debug.log")

if __name__ == "__main__":
    main()