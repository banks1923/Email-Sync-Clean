#!/usr/bin/env python3
"""
Unified Embedding Management Script
Consolidates: rebuild_embeddings.py, generate_email_message_embeddings.py, sync_email_message_vectors.py
"""

import sys
from pathlib import Path
from typing import Optional

# Add project root to path
sys.path.append(str(Path(__file__).parent.parent))

from loguru import logger
from shared.simple_db import SimpleDB
from utilities.embeddings.service import EmbeddingService
from utilities.vector_store.service import VectorStoreService


def rebuild_missing_embeddings(limit: Optional[int] = None) -> int:
    """Generate embeddings for content_unified entries that lack embeddings."""
    logger.info("🔄 Rebuilding missing embeddings...")
    
    db = SimpleDB()
    embedding_service = EmbeddingService()
    
    # Find content without embeddings
    query = """
        SELECT cu.id, cu.title, cu.body, cu.source_type
        FROM content_unified cu
        LEFT JOIN embeddings e ON cu.id = e.content_id
        WHERE e.id IS NULL AND cu.body IS NOT NULL AND cu.body != ''
    """
    if limit:
        query += f" LIMIT {limit}"
    
    missing = db.fetch(query)
    logger.info(f"Found {len(missing)} records missing embeddings")
    
    count = 0
    for record in missing:
        try:
            # Generate embedding
            embedding = embedding_service.embed_text(record['body'])
            
            # Store in database
            db.execute("""
                INSERT INTO embeddings (content_id, embedding_data, model_version)
                VALUES (?, ?, ?)
            """, (record['id'], embedding.tobytes(), 'legal-bert-base'))
            
            count += 1
            if count % 10 == 0:
                logger.info(f"Processed {count}/{len(missing)} embeddings")
                
        except Exception as e:
            logger.error(f"Failed to create embedding for {record['id']}: {e}")
    
    logger.success(f"✅ Created {count} new embeddings")
    return count


def sync_to_vector_store() -> int:
    """Sync all embeddings to vector store."""
    logger.info("🔄 Syncing embeddings to vector store...")
    
    db = SimpleDB()
    vector_service = VectorStoreService()
    
    # Get all embeddings
    embeddings = db.fetch("""
        SELECT e.id, e.content_id, e.embedding_data, cu.title, cu.body, cu.source_type
        FROM embeddings e
        JOIN content_unified cu ON e.content_id = cu.id
    """)
    
    logger.info(f"Syncing {len(embeddings)} embeddings to vector store")
    
    count = 0
    for record in embeddings:
        try:
            vector_service.add_document(
                doc_id=record['content_id'],
                content=record['body'],
                metadata={
                    'title': record['title'],
                    'source_type': record['source_type']
                },
                embedding=record['embedding_data']
            )
            count += 1
            
        except Exception as e:
            logger.error(f"Failed to sync {record['content_id']}: {e}")
    
    logger.success(f"✅ Synced {count} embeddings to vector store")
    return count


def main():
    """Main execution."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Manage embeddings')
    parser.add_argument('--rebuild', action='store_true', help='Rebuild missing embeddings')
    parser.add_argument('--sync', action='store_true', help='Sync to vector store')
    parser.add_argument('--limit', type=int, help='Limit number of records to process')
    parser.add_argument('--all', action='store_true', help='Do both rebuild and sync')
    
    args = parser.parse_args()
    
    if args.all or (args.rebuild and args.sync):
        rebuild_missing_embeddings(args.limit)
        sync_to_vector_store()
    elif args.rebuild:
        rebuild_missing_embeddings(args.limit)
    elif args.sync:
        sync_to_vector_store()
    else:
        # Default: show status
        db = SimpleDB()
        stats = db.fetch("""
            SELECT 
                (SELECT COUNT(*) FROM content_unified) as total_content,
                (SELECT COUNT(*) FROM embeddings) as total_embeddings,
                (SELECT COUNT(*) FROM content_unified WHERE id NOT IN 
                    (SELECT content_id FROM embeddings)) as missing_embeddings
        """)[0]
        
        logger.info("📊 Embedding Status:")
        logger.info(f"  Total content: {stats['total_content']}")
        logger.info(f"  With embeddings: {stats['total_embeddings']}")
        logger.info(f"  Missing embeddings: {stats['missing_embeddings']}")
        
        if stats['missing_embeddings'] > 0:
            logger.warning(f"⚠️  Run with --rebuild to create {stats['missing_embeddings']} missing embeddings")


if __name__ == "__main__":
    main()