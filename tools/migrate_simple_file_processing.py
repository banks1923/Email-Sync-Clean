#!/usr/bin/env python3
"""
Migration: Clean up complex file management database tables.

Removes tables that were used by OriginalFileManager and EnhancedArchiveManager:
- file_hashes (file deduplication tracking)
- file_links (hard/soft link tracking)  
- space_savings (space optimization metrics)

These are no longer needed with the simple file processing approach.
"""

from loguru import logger

from shared.simple_db import SimpleDB


def cleanup_database_tables():
    """
    Remove unused database tables from complex file management system.
    """
    logger.info("Starting database cleanup for simple file processing migration")
    
    db = SimpleDB()
    
    # Tables to remove (used by OriginalFileManager and EnhancedArchiveManager)
    tables_to_drop = [
        "file_hashes",      # SHA-256 deduplication tracking
        "file_links",       # Hard/soft link tracking  
        "space_savings"     # Space optimization metrics
    ]
    
    for table_name in tables_to_drop:
        try:
            # Check if table exists
            result = db.fetch_one(
                "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
                (table_name,)
            )
            
            if result:
                # Get row count before dropping
                count_result = db.fetch_one(f"SELECT COUNT(*) as count FROM {table_name}")
                row_count = count_result['count'] if count_result else 0
                
                # Drop the table
                db.execute(f"DROP TABLE {table_name}")
                logger.info(f"Dropped table '{table_name}' (had {row_count} rows)")
            else:
                logger.info(f"Table '{table_name}' does not exist (already cleaned up)")
                
        except Exception as e:
            logger.warning(f"Error processing table '{table_name}': {e}")
    
    # Vacuum database to reclaim space
    try:
        db.execute("VACUUM")
        logger.info("Database vacuumed to reclaim space")
    except Exception as e:
        logger.warning(f"Database vacuum failed: {e}")
    
    logger.info("Database cleanup completed")


def main():
    """
    Main entry point.
    """
    cleanup_database_tables()
    print("✅ Database migration completed - complex file management tables removed")


if __name__ == "__main__":
    main()