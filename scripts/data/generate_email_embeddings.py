#!/usr/bin/env python3
"""
Generate embeddings for all emails in the database.
Direct and simple - no complex chunking, just email content to vectors.
"""

import sys
import uuid
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from loguru import logger
from utilities.embeddings import get_embedding_service
from utilities.vector_store import get_vector_store
from shared.db.simple_db import SimpleDB


def generate_email_embeddings(batch_size=50, limit=None):
    """Generate embeddings for all emails in the database."""
    db = SimpleDB()
    emb = get_embedding_service()
    vs = get_vector_store('emails')
    
    # Get total count
    cursor = db.execute(
        "SELECT COUNT(*) FROM content_unified WHERE source_type='email_message' AND body IS NOT NULL"
    )
    total = cursor.fetchone()[0]
    
    if limit:
        total = min(total, limit)
    
    logger.info(f"Processing {total} emails in batches of {batch_size}")
    
    # Process in batches
    offset = 0
    processed = 0
    skipped = 0
    errors = 0
    
    while offset < total:
        # Get batch
        query = """
            SELECT id, source_id, body, title
            FROM content_unified 
            WHERE source_type='email_message' AND body IS NOT NULL
            ORDER BY id
            LIMIT ? OFFSET ?
        """
        cursor = db.execute(query, (batch_size, offset))
        rows = cursor.fetchall()
        
        if not rows:
            break
        
        for id, source_id, text, title in rows:
            try:
                # Use substantive_text if available, otherwise body
                cursor2 = db.execute(
                    "SELECT substantive_text FROM content_unified WHERE id=?", (id,)
                )
                result = cursor2.fetchone()
                if result and result[0]:
                    text = result[0]
                
                # Generate embedding
                embedding = emb.encode(text)
                
                # Create UUID from source_id for Qdrant
                point_id = str(uuid.uuid5(uuid.NAMESPACE_DNS, source_id))
                
                # Store in vector DB
                vs.upsert(
                    vector=embedding,
                    payload={
                        'db_id': id,
                        'source_id': source_id,
                        'source_type': 'email_message',
                        'title': title or 'No subject',
                        'text_preview': text[:500]
                    },
                    id=point_id
                )
                
                processed += 1
                
            except Exception as e:
                logger.error(f"Error processing email {id}: {e}")
                errors += 1
        
        offset += batch_size
        logger.info(f"Progress: {processed}/{total} processed, {errors} errors")
    
    logger.info(f"Complete: {processed} embeddings generated, {errors} errors")
    
    # Test search
    if processed > 0:
        logger.info("Testing search functionality...")
        test_query = "lease agreement"
        test_embedding = emb.encode(test_query)
        results = vs.search(test_embedding, limit=3)
        logger.info(f"Test search for '{test_query}' found {len(results)} results")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Generate embeddings for emails")
    parser.add_argument("--batch-size", type=int, default=50, help="Batch size")
    parser.add_argument("--limit", type=int, help="Limit number of emails to process")
    
    args = parser.parse_args()
    generate_email_embeddings(batch_size=args.batch_size, limit=args.limit)