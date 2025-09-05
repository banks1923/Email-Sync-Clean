#!/usr/bin/env python3
"""
Clean up ALL orphaned vectors and fix data alignment.
Nuclear option - removes all vectors without database records.
"""

import sys
import os
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from loguru import logger
from lib.db import SimpleDB
from config.settings import settings
from qdrant_client import QdrantClient

# Configure logging
logger.remove()
logger.add(
    sys.stderr,
    level="INFO",
    format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | <level>{message}</level>",
    colorize=True
)

def nuclear_cleanup():
    """Remove ALL orphaned vectors - complete cleanup."""
    logger.info("=" * 60)
    logger.info("NUCLEAR CLEANUP - REMOVING ALL ORPHANED VECTORS")
    logger.info("=" * 60)
    
    client = QdrantClient(host="localhost", port=6333)
    db = SimpleDB(settings.database.emails_db_path)
    
    # Get ALL vectors
    logger.info("Fetching all vectors from Qdrant...")
    all_points = []
    offset = None
    
    while True:
        batch = client.scroll(
            collection_name='vectors_v2',
            limit=100,
            offset=offset,
            with_payload=True,
            with_vectors=False
        )
        
        points = batch[0]
        if not points:
            break
            
        all_points.extend(points)
        offset = batch[1]
        
        if offset is None:
            break
            
    logger.info(f"Found {len(all_points)} total vectors")
    
    # Check each vector
    orphaned_ids = []
    valid_count = 0
    
    for point in all_points:
        content_id = point.payload.get('content_id')
        
        if not content_id:
            orphaned_ids.append(point.id)
            logger.warning(f"Vector {point.id} has no content_id")
            continue
            
        # Check if content exists in database
        try:
            exists = db.fetch_one(
                "SELECT 1 FROM content_unified WHERE id = ?",
                (int(content_id),)
            )
            
            if not exists:
                orphaned_ids.append(point.id)
                logger.warning(f"Vector {point.id} orphaned - content_id {content_id} not in database")
            else:
                valid_count += 1
                
        except Exception as e:
            orphaned_ids.append(point.id)
            logger.error(f"Error checking vector {point.id}: {e}")
            
    logger.info(f"\nFound {len(orphaned_ids)} orphaned vectors")
    logger.info(f"Found {valid_count} valid vectors")
    
    if orphaned_ids:
        logger.warning(f"DELETING {len(orphaned_ids)} orphaned vectors...")
        
        # Delete in batches
        batch_size = 100
        for i in range(0, len(orphaned_ids), batch_size):
            batch = orphaned_ids[i:i+batch_size]
            
            client.delete(
                collection_name='vectors_v2',
                points_selector=batch  # Just pass the list directly
            )
            
            logger.info(f"Deleted batch {i//batch_size + 1} ({len(batch)} vectors)")
            
        logger.success(f"✅ Deleted {len(orphaned_ids)} orphaned vectors")
        
    # Verify cleanup
    remaining = client.scroll(
        collection_name='vectors_v2',
        limit=1,
        with_payload=False
    )
    
    final_count = len(remaining[0]) if remaining[0] else 0
    
    # Get actual count
    info = client.get_collection('vectors_v2')
    
    logger.success(f"\n✅ CLEANUP COMPLETE")
    logger.info(f"Remaining vectors: {info.points_count}")
    logger.info(f"Valid vectors: {valid_count}")
    
    # Quick validation - check if remaining vectors are all valid
    if info.points_count > 0:
        sample = client.scroll(
            collection_name='vectors_v2',
            limit=5,
            with_payload=True
        )[0]
        
        logger.info("\nSample of remaining vectors:")
        for point in sample:
            content_id = point.payload.get('content_id')
            exists = db.fetch_one(
                "SELECT title FROM content_unified WHERE id = ?",
                (int(content_id),)
            ) if content_id else None
            
            if exists:
                logger.success(f"  ✅ Vector {point.id} -> Content {content_id}: {exists['title'][:50]}")
            else:
                logger.error(f"  ❌ Vector {point.id} -> Content {content_id}: NOT FOUND")
                
    return len(orphaned_ids)


def verify_system():
    """Quick system verification after cleanup."""
    logger.info("\n" + "=" * 60)
    logger.info("VERIFYING SYSTEM AFTER CLEANUP")
    logger.info("=" * 60)
    
    try:
        from lib.search import hybrid_search
        
        # Test search
        results = hybrid_search("test", limit=1)
        logger.success(f"✅ Search works - returned {len(results)} results")
        
        # Check database
        db = SimpleDB(settings.database.emails_db_path)
        content_count = db.fetch_one("SELECT COUNT(*) as count FROM content_unified")['count']
        
        # Check vectors
        client = QdrantClient(host="localhost", port=6333)
        info = client.get_collection('vectors_v2')
        
        logger.info(f"\nFinal stats:")
        logger.info(f"  Database content: {content_count}")
        logger.info(f"  Vector points: {info.points_count}")
        
        if content_count == 0 and info.points_count == 0:
            logger.warning("⚠️  System is empty - no content or vectors")
            logger.info("This is expected if starting fresh. Run ingestion to add content.")
        elif info.points_count > content_count:
            logger.error(f"❌ Still have more vectors ({info.points_count}) than content ({content_count})")
        else:
            logger.success(f"✅ System aligned - vectors <= content")
            
    except Exception as e:
        logger.error(f"Verification failed: {e}")


def main():
    """Run nuclear cleanup."""
    deleted = nuclear_cleanup()
    verify_system()
    
    logger.info("\n" + "=" * 60)
    if deleted > 0:
        logger.success(f"🧹 CLEANED {deleted} ORPHANED VECTORS")
    else:
        logger.success("✅ NO ORPHANED VECTORS FOUND")
    logger.info("Run diagnostics again to confirm: python3 tools/diagnostics/system_diagnostics.py")
    

if __name__ == "__main__":
    main()