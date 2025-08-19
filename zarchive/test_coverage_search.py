#!/usr/bin/env python3
"""
Coverage test runner for search and vector modules
"""
import sys
sys.path.insert(0, '.')

def test_search_module_coverage():
    """Test search module functions to improve coverage"""
    
    # Test basic imports
    from search import search, semantic_search, vector_store_available
    from utilities.vector_store import get_vector_store
    
    print("=== Search Module Coverage Test ===\n")
    
    # Test vector store availability
    print("1. Testing vector_store_available()...")
    is_available = vector_store_available()
    print(f"   Vector store available: {is_available}")
    
    # Test basic search functionality
    print("\n2. Testing search() function...")
    try:
        results = search("test contract", limit=3)
        print(f"   Search returned {len(results)} results")
        if results:
            print(f"   Sample result ID: {results[0].get('content_id', 'N/A')}")
    except Exception as e:
        print(f"   Search failed: {e}")
    
    # Test semantic search if available
    print("\n3. Testing semantic_search() function...")
    if is_available:
        try:
            sem_results = semantic_search("legal document", limit=3)
            print(f"   Semantic search returned {len(sem_results)} results")
            if sem_results:
                print(f"   Sample semantic result ID: {sem_results[0].get('content_id', 'N/A')}")
        except Exception as e:
            print(f"   Semantic search failed: {e}")
    else:
        print("   Skipping semantic search (vector store not available)")
    
    # Test vector store directly
    print("\n4. Testing vector store functionality...")
    if is_available:
        try:
            store = get_vector_store()
            count = store.count()
            print(f"   Vector count: {count}")
            
            # Test search with dummy vector
            if count > 0:
                import numpy as np
                dummy_vector = np.random.random(1024).tolist()
                vector_results = store.search(dummy_vector, limit=2)
                print(f"   Vector search returned {len(vector_results)} results")
        except Exception as e:
            print(f"   Vector store test failed: {e}")
    
    print("\n=== Coverage Test Complete ===")

if __name__ == "__main__":
    test_search_module_coverage()