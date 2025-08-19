#!/usr/bin/env python3
"""Verify vector database synchronization status."""

from shared.simple_db import SimpleDB
from utilities.vector_store import get_vector_store
from utilities.embeddings import get_embedding_service
import sys


def verify_sync():
    """Verify database and vector store are synchronized."""
    
    # Initialize services
    db = SimpleDB()
    vector_store = get_vector_store()
    embedding_service = get_embedding_service()
    
    # Get counts
    db_docs = db.search_content('')  # Get all content from database
    valid_docs = [d for d in db_docs if d.get("content_id") and d.get("content")]
    
    stats = vector_store.get_collection_stats()
    vector_count = stats.get("points_count", 0)
    
    print("\n" + "="*60)
    print("🔍 VECTOR SYNC VERIFICATION REPORT")
    print("="*60)
    
    print("\n📊 Database:")
    print(f"  Total documents: {len(db_docs)}")
    print(f"  Valid documents: {len(valid_docs)}")
    
    print("\n🧠 Vector Store:")
    print(f"  Total vectors: {vector_count}")
    print("  Collection: emails")
    print("  Dimensions: 1024")
    
    print("\n✅ Sync Status:")
    if len(valid_docs) == vector_count:
        print(f"  ✅ SYNCHRONIZED: {len(valid_docs)} documents = {vector_count} vectors")
    else:
        print(f"  ⚠️ OUT OF SYNC: {len(valid_docs)} documents ≠ {vector_count} vectors")
        print(f"  Missing vectors: {len(valid_docs) - vector_count}")
    
    # Test batch embedding method
    print("\n🧪 Testing Batch Methods:")
    try:
        # Test get_embeddings alias
        test_texts = ["test one", "test two"]
        embeddings = embedding_service.get_embeddings(test_texts)
        print(f"  ✅ get_embeddings() works: {len(embeddings)} embeddings generated")
    except Exception as e:
        print(f"  ❌ get_embeddings() failed: {e}")
    
    # Test search functionality
    print("\n🔍 Testing Search:")
    try:
        from search.main import search
        results = search("test", limit=1)
        if results:
            print(f"  ✅ Search works: Found {len(results)} results")
        else:
            print("  ⚠️ Search returned no results (may be normal)")
    except Exception as e:
        print(f"  ❌ Search failed: {e}")
    
    print("\n" + "="*60)
    
    return len(valid_docs) == vector_count


if __name__ == "__main__":
    success = verify_sync()
    sys.exit(0 if success else 1)