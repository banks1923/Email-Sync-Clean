#!/usr/bin/env python3
"""
Rebuild vector store from database content.
Ensures vector IDs match database IDs to prevent enrichment failures.
"""

import sys
import time
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from lib.vector_store import get_vector_store
from lib.embeddings import get_embedding_service
from lib.db import SimpleDB


def main():
    print("=" * 60)
    print("VECTOR STORE REBUILD")
    print("=" * 60)
    
    # Initialize services
    print("\n1. Initializing services...")
    store = get_vector_store('vectors_v2')
    embedding_service = get_embedding_service()
    db = SimpleDB()
    
    # Get all content from database
    print("\n2. Loading content from database...")
    content = db.fetch_all("""
        SELECT id, source_id, source_type, title, body, substantive_text 
        FROM content_unified 
        WHERE body IS NOT NULL OR substantive_text IS NOT NULL
        ORDER BY id
    """)
    
    total_items = len(content)
    print(f"   Found {total_items} items to index")
    
    # Index in batches
    print("\n3. Generating embeddings and indexing...")
    batch_size = 10
    indexed = 0
    failed = 0
    start_time = time.time()
    
    for i in range(0, total_items, batch_size):
        batch = content[i:i + batch_size]
        batch_end = min(i + batch_size, total_items)
        
        print(f"\n   Batch {i//batch_size + 1}: Items {i+1}-{batch_end}")
        
        for item in batch:
            try:
                # Get text content (prefer substantive_text)
                text = item['substantive_text'] or item['body']
                if not text or len(text) < 10:
                    continue
                
                # Generate embedding (limit text length for performance)
                max_text_length = 5000  # Reasonable limit for embedding
                embedding_text = text[:max_text_length]
                vector = embedding_service.encode(embedding_text)
                
                # Add to vector store with matching ID
                store.add_vector(
                    vector=vector,
                    metadata={
                        'content_id': str(item['id']),
                        'source_id': item['source_id'],
                        'source_type': item['source_type'],
                        'title': item['title'] or 'No title',
                    },
                    point_id=item['id']  # Critical: Use DB ID as vector ID
                )
                
                indexed += 1
                
                # Progress indicator
                if indexed % 10 == 0:
                    elapsed = time.time() - start_time
                    rate = indexed / elapsed if elapsed > 0 else 0
                    eta = (total_items - indexed) / rate if rate > 0 else 0
                    print(f"      Indexed {indexed}/{total_items} ({indexed*100//total_items}%) - "
                          f"Rate: {rate:.1f} items/sec - ETA: {eta:.0f}s")
                
            except Exception as e:
                failed += 1
                print(f"      ERROR indexing ID {item['id']}: {e}")
    
    # Final statistics
    elapsed_total = time.time() - start_time
    print("\n" + "=" * 60)
    print("REBUILD COMPLETE")
    print("=" * 60)
    print(f"Successfully indexed: {indexed} items")
    print(f"Failed: {failed} items")
    print(f"Total time: {elapsed_total:.1f} seconds")
    print(f"Average rate: {indexed/elapsed_total:.1f} items/second")
    
    # Verify the index
    print("\n4. Verifying index...")
    test_query = "stoneman"
    test_vector = embedding_service.encode(test_query)
    results = store.search(test_vector, limit=3)
    
    if results:
        print(f"   ✅ Test search for '{test_query}' returned {len(results)} results")
        for r in results[:3]:
            payload = r.get('payload', {})
            print(f"      - ID {r['id']}: {payload.get('title', 'No title')[:50]}")
    else:
        print(f"   ⚠️  Test search returned no results")
    
    print("\n✨ Done! The vector store has been rebuilt.")
    print("   Run 'vsearch search semantic <query>' to test.")


if __name__ == "__main__":
    main()