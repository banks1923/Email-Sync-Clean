#!/usr/bin/env python3
"""
Fix duplicate content entries and prevent future duplicates.
This addresses the core issue: missing deduplication logic.
"""

from loguru import logger
from shared.simple_db import SimpleDB

def fix_duplicates():
    """Remove duplicate content entries and add prevention."""
    
    db = SimpleDB()
    logger.info("Starting duplicate fix...")
    
    # Step 1: Find all duplicates
    logger.info("Step 1: Finding duplicates...")
    duplicates = db.execute("""
        SELECT sha256, chunk_index, COUNT(*) as count, GROUP_CONCAT(id) as ids
        FROM content_unified
        WHERE sha256 IS NOT NULL
        GROUP BY sha256, chunk_index
        HAVING COUNT(*) > 1
    """).fetchall()
    
    if not duplicates:
        logger.info("✅ No duplicates found!")
        return
    
    logger.info(f"Found {len(duplicates)} sets of duplicates")
    
    # Step 2: Keep only the first entry of each duplicate set
    total_removed = 0
    for sha256, chunk_index, count, ids_str in duplicates:
        ids = [int(id) for id in ids_str.split(',')]
        keep_id = min(ids)  # Keep the earliest entry
        remove_ids = [id for id in ids if id != keep_id]
        
        logger.info(f"SHA {sha256[:16]}... chunk {chunk_index}: Keeping ID {keep_id}, removing {remove_ids}")
        
        # Remove duplicates
        for remove_id in remove_ids:
            # First remove any embeddings for this content
            db.execute("DELETE FROM embeddings WHERE content_id = ?", (remove_id,))
            # Then remove the content
            db.execute("DELETE FROM content_unified WHERE id = ?", (remove_id,))
            total_removed += 1
    
    logger.info(f"✅ Removed {total_removed} duplicate entries")
    
    # Step 3: Add UNIQUE constraint to prevent future duplicates
    logger.info("Step 3: Adding UNIQUE constraint...")
    try:
        # SQLite doesn't support adding constraints to existing tables
        # So we need to recreate the table with the constraint
        
        # Create new table with UNIQUE constraint
        db.execute("""
            CREATE TABLE IF NOT EXISTS content_unified_new (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                source_type TEXT NOT NULL,
                source_id INTEGER,
                title TEXT,
                body TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                ready_for_embedding INTEGER DEFAULT 1,
                sha256 TEXT,
                chunk_index INTEGER DEFAULT 0,
                UNIQUE(sha256, chunk_index)
            )
        """)
        
        # Copy data to new table
        db.execute("""
            INSERT INTO content_unified_new 
            SELECT * FROM content_unified
        """)
        
        # Drop old table and rename new one
        db.execute("DROP TABLE content_unified")
        db.execute("ALTER TABLE content_unified_new RENAME TO content_unified")
        
        # Recreate indexes
        db.execute("CREATE INDEX idx_content_unified_sha256 ON content_unified(sha256)")
        db.execute("CREATE INDEX idx_content_unified_sha256_chunk ON content_unified(sha256, chunk_index)")
        
        logger.info("✅ Added UNIQUE constraint on (sha256, chunk_index)")
        
    except Exception as e:
        logger.warning(f"Could not add UNIQUE constraint: {e}")
        logger.info("Alternative: Modify insert code to check for duplicates")
    
    # Step 4: Show the fix for the code
    logger.info("\n" + "="*60)
    logger.info("CODE FIX NEEDED:")
    logger.info("="*60)
    logger.info("""
In your document processing code, change FROM:

    # Old way (allows duplicates)
    db.execute(
        "INSERT INTO content_unified (sha256, body, ...) VALUES (?, ?, ...)",
        (sha256, body, ...)
    )

TO:

    # New way (prevents duplicates)
    existing = db.execute(
        "SELECT id FROM content_unified WHERE sha256 = ? AND chunk_index = ?",
        (sha256, chunk_index)
    ).fetchone()
    
    if not existing:
        db.execute(
            "INSERT INTO content_unified (sha256, body, ...) VALUES (?, ?, ...)",
            (sha256, body, ...)
        )
    else:
        logger.debug(f"Skipping duplicate: {sha256[:16]}...")
    """)
    
    # Step 5: Verify the fix
    logger.info("\n" + "="*60)
    logger.info("VERIFICATION:")
    remaining_dupes = db.execute("""
        SELECT COUNT(*) FROM (
            SELECT sha256, chunk_index, COUNT(*) as count
            FROM content_unified
            WHERE sha256 IS NOT NULL
            GROUP BY sha256, chunk_index
            HAVING COUNT(*) > 1
        )
    """).fetchone()[0]
    
    if remaining_dupes == 0:
        logger.info("✅ All duplicates removed successfully!")
    else:
        logger.error(f"❌ Still have {remaining_dupes} duplicate sets")
    
    # Final stats
    total_content = db.execute("SELECT COUNT(*) FROM content_unified").fetchone()[0]
    unique_hashes = db.execute("SELECT COUNT(DISTINCT sha256) FROM content_unified WHERE sha256 IS NOT NULL").fetchone()[0]
    
    logger.info(f"\nFinal stats:")
    logger.info(f"  Total content entries: {total_content}")
    logger.info(f"  Unique document hashes: {unique_hashes}")

if __name__ == "__main__":
    fix_duplicates()