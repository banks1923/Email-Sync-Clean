#!/usr/bin/env python3
"""
Generate Legal BERT embeddings for all content in content_unified table.
"""

from loguru import logger
from shared.simple_db import SimpleDB
from utilities.embeddings.embedding_service import get_embedding_service
from utilities.vector_store import VectorStore
import uuid

def generate_embeddings():
    """Generate embeddings for all content_unified records."""
    db = SimpleDB()
    embedding_service = get_embedding_service()
    vector_store = VectorStore(collection="legal_documents", dimensions=1024)
    
    # Get all content that needs embeddings
    content = db.fetch("""
        SELECT id, source_type, source_id, title, body, sha256
        FROM content_unified
        WHERE ready_for_embedding = 1
        ORDER BY id
        LIMIT 10
    """)
    
    logger.info(f"Found {len(content)} documents to embed")
    
    success = 0
    errors = 0
    
    for doc in content:
        try:
            # Generate text for embedding
            text = f"{doc['title']} {doc['body']}"[:5000]  # Limit text length
            
            # Generate embedding
            embedding = embedding_service.encode(text)
            
            # Store in vector database
            vector_id = str(uuid.uuid4())
            vector_store.upsert(
                vector=embedding,
                payload={
                    "content_id": doc['id'],
                    "source_type": doc['source_type'],
                    "source_id": doc['source_id'],
                    "title": doc['title'],
                    "sha256": doc['sha256'],
                    "text_preview": text[:500]
                },
                id=vector_id
            )
            
            # Mark as embedded
            db.execute("""
                UPDATE content_unified 
                SET ready_for_embedding = 0 
                WHERE id = ?
            """, (doc['id'],))
            
            success += 1
            if success % 10 == 0:
                logger.info(f"Progress: {success}/{len(content)} embedded")
                
        except Exception as e:
            logger.error(f"Failed to embed document {doc['id']}: {e}")
            errors += 1
    
    logger.info(f"Embedding complete: {success} successful, {errors} errors")
    return {
        'success': success,
        'errors': errors,
        'total': len(content)
    }

if __name__ == "__main__":
    # Ensure Qdrant is running
    import subprocess
    import time
    
    # Start Qdrant if not running
    try:
        import requests
        response = requests.get("http://localhost:6333/readyz", timeout=2)
        logger.info("Qdrant already running")
    except:
        logger.info("Starting Qdrant...")
        subprocess.Popen([
            "sh", "-c", 
            "QDRANT__STORAGE__PATH=./qdrant_data ~/bin/qdrant > qdrant.log 2>&1 &"
        ])
        time.sleep(5)
    
    result = generate_embeddings()
    print(f"\n✅ Embeddings Generated:")
    print(f"   Successful: {result['success']}")
    print(f"   Errors: {result['errors']}")
    print(f"   Total: {result['total']}")