#!/usr/bin/env python3
"""
Generate missing embeddings for all content marked as ready.
This fixes the broken embedding pipeline that only processed 58 out of 1003 items.
"""

import sys
import time
from typing import List, Tuple
from loguru import logger
from shared.simple_db import SimpleDB
from utilities.embeddings import get_embedding_service
from utilities.vector_store import get_vector_store
import numpy as np

def get_missing_content(db: SimpleDB, batch_size: int = 50) -> List[Tuple[int, str]]:
    """Get content that needs embeddings."""
    query = """
        SELECT 
            c.id,
            c.body
        FROM content_unified c
        LEFT JOIN embeddings e ON c.id = e.content_id
        WHERE e.id IS NULL
          AND c.ready_for_embedding = 1
          AND c.body IS NOT NULL
          AND LENGTH(c.body) > 0
        ORDER BY c.id
        LIMIT ?
    """
    results = db.execute(query, (batch_size,)).fetchall()
    return [(row[0], row[1]) for row in results]

def process_embeddings(dry_run: bool = False):
    """Generate embeddings for all missing content."""
    
    logger.info("Starting embedding generation process")
    
    # Initialize services
    db = SimpleDB()
    emb_service = get_embedding_service()
    vector_store = get_vector_store()
    
    # Get initial counts
    total_content = db.execute(
        "SELECT COUNT(*) FROM content_unified WHERE ready_for_embedding = 1"
    ).fetchone()[0]
    
    existing_embeddings = db.execute(
        "SELECT COUNT(*) FROM embeddings"
    ).fetchone()[0]
    
    logger.info(f"Total content ready: {total_content}")
    logger.info(f"Existing embeddings: {existing_embeddings}")
    logger.info(f"Need to generate: {total_content - existing_embeddings}")
    
    if dry_run:
        logger.info("DRY RUN - not saving embeddings")
    
    processed = 0
    errors = 0
    batch_num = 0
    
    while True:
        batch_num += 1
        
        # Get next batch of content needing embeddings
        batch = get_missing_content(db, batch_size=50)
        
        if not batch:
            logger.info("No more content to process")
            break
            
        logger.info(f"Processing batch {batch_num} with {len(batch)} items")
        
        for content_id, body in batch:
            try:
                # Truncate to 8000 chars if needed (BERT limit)
                text = body[:8000] if len(body) > 8000 else body
                
                # Generate embedding
                embedding = emb_service.get_embedding(text)
                
                if not dry_run:
                    # Save to database
                    db.execute("""
                        INSERT INTO embeddings (content_id, vector, dim, model, created_at)
                        VALUES (?, ?, ?, ?, datetime('now'))
                    """, (
                        content_id,
                        np.array(embedding).tobytes(),
                        len(embedding),
                        'pile-of-law/legalbert-large-1.7M-2'
                    ))
                    
                    # Save to Qdrant
                    vector_store.upsert(
                        vector=embedding,
                        id=str(content_id),
                        payload={"content_id": content_id, "type": "content"}
                    )
                
                processed += 1
                
                if processed % 10 == 0:
                    logger.info(f"Progress: {processed} embeddings generated")
                    
            except Exception as e:
                errors += 1
                logger.error(f"Failed to process content_id {content_id}: {e}")
                continue
        
        # Small delay to avoid overwhelming the system
        time.sleep(0.1)
    
    logger.info("=" * 50)
    logger.info(f"Embedding generation complete!")
    logger.info(f"Processed: {processed}")
    logger.info(f"Errors: {errors}")
    
    # Final verification
    final_count = db.execute("SELECT COUNT(*) FROM embeddings").fetchone()[0]
    logger.info(f"Total embeddings in database: {final_count}")
    
    # Check Qdrant
    collection_info = vector_store.client.get_collection('emails')
    logger.info(f"Total vectors in Qdrant: {collection_info.points_count}")

if __name__ == "__main__":
    # Check for dry-run flag
    dry_run = "--dry-run" in sys.argv
    
    logger.info("=" * 50)
    logger.info("MISSING EMBEDDINGS GENERATOR")
    logger.info("=" * 50)
    
    if dry_run:
        logger.info("Running in DRY RUN mode - no changes will be saved")
    else:
        logger.info("Running in LIVE mode - embeddings will be saved")
        logger.info("Starting in 3 seconds... (Ctrl+C to cancel)")
    
    try:
        process_embeddings(dry_run=dry_run)
    except KeyboardInterrupt:
        logger.info("\nInterrupted by user")
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        sys.exit(1)