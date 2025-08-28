#!/usr/bin/env python3
"""
Clean slate reset for embeddings and email data.
Clears all embeddings and prepares for fresh processing.
"""

import sqlite3
from pathlib import Path
from loguru import logger
from shared.simple_db import SimpleDB

def reset_embeddings_and_flags():
    """Clear embeddings table and reset all processing flags."""
    db = SimpleDB()
    conn = db.get_connection()
    cursor = conn.cursor()
    
    try:
        # Clear embeddings table
        cursor.execute("DELETE FROM embeddings")
        embeddings_deleted = cursor.rowcount
        logger.info(f"Deleted {embeddings_deleted} embeddings")
        
        # Reset all embedding flags in content_unified
        cursor.execute("""
            UPDATE content_unified 
            SET ready_for_embedding = 1,
                validation_status = 'pending'
            WHERE source_type IN ('email_message', 'email_summary', 'document', 'document_chunk')
        """)
        content_reset = cursor.rowcount
        logger.info(f"Reset {content_reset} content items for reprocessing")
        
        # Clear any vector-related metadata
        cursor.execute("""
            UPDATE content_unified 
            SET metadata = json_remove(metadata, '$.vector_id', '$.embedding_id', '$.processed_at')
            WHERE metadata IS NOT NULL
        """)
        metadata_cleaned = cursor.rowcount
        logger.info(f"Cleaned metadata for {metadata_cleaned} items")
        
        conn.commit()
        
        # Get current statistics
        cursor.execute("""
            SELECT source_type, COUNT(*) as count 
            FROM content_unified 
            GROUP BY source_type
        """)
        stats = cursor.fetchall()
        
        logger.info("Current content statistics:")
        for source_type, count in stats:
            logger.info(f"  {source_type}: {count}")
            
        return embeddings_deleted, content_reset
        
    except Exception as e:
        conn.rollback()
        logger.error(f"Error during reset: {e}")
        raise
    finally:
        conn.close()

def clean_email_data():
    """Remove all email data for fresh Gmail sync."""
    db = SimpleDB()
    conn = db.get_connection()
    cursor = conn.cursor()
    
    try:
        # Delete email-related content
        cursor.execute("""
            DELETE FROM content_unified 
            WHERE source_type IN ('email_message', 'email_summary')
        """)
        emails_deleted = cursor.rowcount
        
        # Delete individual messages
        cursor.execute("DELETE FROM individual_messages")
        messages_deleted = cursor.rowcount
        
        # Delete message occurrences
        cursor.execute("DELETE FROM message_occurrences")
        occurrences_deleted = cursor.rowcount
        
        # Delete Gmail metadata (if table exists)
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='gmail_metadata'")
        if cursor.fetchone():
            cursor.execute("DELETE FROM gmail_metadata")
            metadata_deleted = cursor.rowcount
        else:
            metadata_deleted = 0
        
        conn.commit()
        
        logger.info(f"Cleaned email data:")
        logger.info(f"  Content unified: {emails_deleted} records")
        logger.info(f"  Individual messages: {messages_deleted}")
        logger.info(f"  Message occurrences: {occurrences_deleted}")
        logger.info(f"  Gmail metadata: {metadata_deleted}")
        
        return emails_deleted, messages_deleted
        
    except Exception as e:
        conn.rollback()
        logger.error(f"Error cleaning email data: {e}")
        raise
    finally:
        conn.close()

def main():
    """Run the clean slate reset."""
    logger.info("=" * 60)
    logger.info("CLEAN SLATE RESET - Clearing embeddings and email data")
    logger.info("=" * 60)
    
    # Step 1: Clear embeddings and reset flags
    logger.info("\nStep 1: Clearing embeddings...")
    embeddings_deleted, content_reset = reset_embeddings_and_flags()
    
    # Step 2: Clean email data
    logger.info("\nStep 2: Cleaning email data...")
    emails_deleted, messages_deleted = clean_email_data()
    
    logger.info("\n" + "=" * 60)
    logger.info("RESET COMPLETE")
    logger.info(f"  Embeddings cleared: {embeddings_deleted}")
    logger.info(f"  Content reset for processing: {content_reset}")
    logger.info(f"  Emails removed: {emails_deleted}")
    logger.info(f"  Messages removed: {messages_deleted}")
    logger.info("\nNext steps:")
    logger.info("  1. Start Qdrant: docker-compose up -d")
    logger.info("  2. Sync Gmail: python3 -m gmail.main")
    logger.info("  3. Generate embeddings: tools/scripts/vsearch ingest --emails")
    logger.info("=" * 60)

if __name__ == "__main__":
    main()