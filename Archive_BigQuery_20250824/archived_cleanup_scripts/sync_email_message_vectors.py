#!/usr/bin/env python3
"""
Sync individual email message embeddings to vector store.
"""

import pickle
import sys
from pathlib import Path

# Add project root to Python path (scripts/ is one level down)
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from shared.simple_db import SimpleDB
from utilities.vector_store import get_vector_store


def sync_email_message_vectors():
    """Sync individual email message embeddings to vector store."""
    
    print("🔄 Syncing Individual Email Message Vectors to Qdrant")
    print("=" * 60)
    
    # Initialize services
    db = SimpleDB("data/emails.db")
    vector_store = get_vector_store()
    
    # Get embeddings for individual email messages
    print("🔍 Finding individual message embeddings to sync...")
    email_message_embeddings = db.fetch("""
        SELECT e.id as embedding_id, e.content_id, e.vector, e.model,
               c.title, c.body, c.source_id, c.created_at
        FROM embeddings e
        JOIN content_unified c ON e.content_id = c.id
        WHERE c.source_type = 'email_message'
        ORDER BY e.id
    """)
    
    if not email_message_embeddings:
        print("❌ No individual message embeddings found")
        return False
    
    print(f"📧 Found {len(email_message_embeddings)} individual message embeddings to sync")
    print()
    
    successful = 0
    failed = 0
    
    print("🚀 Syncing to vector store...")
    for i, embedding_record in enumerate(email_message_embeddings, 1):
        try:
            embedding_id = embedding_record['embedding_id']
            content_id = embedding_record['content_id']
            vector_blob = embedding_record['vector']
            title = embedding_record['title'] or ""
            embedding_record['body'] or ""
            
            # Deserialize the embedding vector
            vector = pickle.loads(vector_blob)
            
            # Create metadata for the vector
            metadata = {
                "content_id": content_id,
                "source_type": "email_message",
                "title": title[:200],  # Limit title length
                "source_id": embedding_record['source_id'] or "",
                "created_at": embedding_record['created_at'] or "",
                "model": embedding_record['model']
            }
            
            # Store in vector store with content_id as integer (proper type)
            vector_store.upsert(
                vector=vector,
                payload=metadata,
                id=int(content_id)
            )
            
            successful += 1
            
            # Progress update every 100 vectors
            if i % 100 == 0 or i == len(email_message_embeddings):
                print(f"   📈 Progress: {i}/{len(email_message_embeddings)} ({successful} successful, {failed} failed)")
            
        except Exception as e:
            failed += 1
            print(f"   ❌ Failed to sync embedding {embedding_id}: {e}")
            continue
    
    print()
    print("✅ Vector sync completed!")
    print(f"   📈 Successful: {successful}")
    print(f"   ❌ Failed: {failed}")
    print(f"   📊 Success rate: {(successful/(successful+failed)*100):.1f}%")
    
    # Test a search to verify
    print()
    print("🔍 Testing search with individual messages...")
    try:
        # Get the embedding service to create a query vector
        from utilities.embeddings import get_embedding_service
        embedding_service = get_embedding_service()
        query_vector = embedding_service.get_embedding("stoneman harassment")
        
        search_results = vector_store.search(query_vector, limit=5)
        print(f"   🎯 Found {len(search_results)} results for harassment search")
        
        for i, result in enumerate(search_results[:3], 1):
            title = result.get('payload', {}).get('title', 'No title')[:50]
            score = result.get('score', 0.0)
            print(f"   📄 Result {i}: {title}... (score: {score:.3f})")
        
    except Exception as e:
        print(f"   ⚠️  Search test failed: {e}")
    
    return failed == 0

if __name__ == "__main__":
    success = sync_email_message_vectors()
    
    if success:
        print("\n🎉 Individual email message vectors synced successfully!")
        print("Vector store now contains individual messages for advanced search")
    else:
        print("\n⚠️ Some vectors failed to sync - check logs above")
        sys.exit(1)