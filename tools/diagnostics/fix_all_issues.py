#!/usr/bin/env python3
"""
Fix ALL System Issues - One-Shot Solution
Addresses all 9 errors found by diagnostics.
"""

import sys
import os
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from loguru import logger
from lib.db import SimpleDB
from config.settings import settings
import sqlite3

# Configure logging
logger.remove()
logger.add(
    sys.stderr,
    level="INFO",
    format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | <level>{message}</level>",
    colorize=True
)

def fix_database_schema():
    """Fix all database schema issues."""
    logger.info("=" * 60)
    logger.info("FIXING DATABASE SCHEMA ISSUES")
    logger.info("=" * 60)
    
    db = SimpleDB(settings.database.emails_db_path)
    
    # 1. Add missing substantive_text column if not exists
    logger.info("Checking substantive_text column...")
    try:
        # Check if column exists
        columns = db.fetch_all("""
            PRAGMA table_info(content_unified)
        """)
        column_names = [c['name'] for c in columns]
        
        if 'substantive_text' not in column_names:
            logger.warning("Adding missing substantive_text column...")
            db.execute("""
                ALTER TABLE content_unified 
                ADD COLUMN substantive_text TEXT
            """)
            
            # Populate with body content as default
            db.execute("""
                UPDATE content_unified 
                SET substantive_text = body 
                WHERE substantive_text IS NULL
            """)
            logger.success("✅ Added substantive_text column")
        else:
            logger.info("✅ substantive_text column already exists")
            
    except Exception as e:
        logger.error(f"Failed to add substantive_text: {e}")
        
    # 2. Create missing tables
    missing_tables = [
        ("individual_messages", """
            CREATE TABLE IF NOT EXISTS individual_messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                message_id TEXT UNIQUE NOT NULL,
                thread_id TEXT,
                subject TEXT,
                sender TEXT,
                recipients TEXT,
                date TEXT,
                body TEXT,
                has_attachments BOOLEAN DEFAULT 0,
                labels TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """),
        ("message_occurrences", """
            CREATE TABLE IF NOT EXISTS message_occurrences (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                message_id TEXT NOT NULL,
                folder TEXT,
                seen_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (message_id) REFERENCES individual_messages(message_id)
            )
        """),
        ("entities", """
            CREATE TABLE IF NOT EXISTS entities (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                content_id INTEGER,
                entity_type TEXT,
                entity_value TEXT,
                confidence REAL,
                start_pos INTEGER,
                end_pos INTEGER,
                context TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (content_id) REFERENCES content_unified(id)
            )
        """)
    ]
    
    for table_name, create_sql in missing_tables:
        logger.info(f"Creating table: {table_name}...")
        try:
            db.execute(create_sql)
            
            # Create indexes
            if table_name == "individual_messages":
                db.execute("""
                    CREATE INDEX IF NOT EXISTS idx_messages_date 
                    ON individual_messages(date)
                """)
                db.execute("""
                    CREATE INDEX IF NOT EXISTS idx_messages_sender 
                    ON individual_messages(sender)
                """)
                
            elif table_name == "entities":
                db.execute("""
                    CREATE INDEX IF NOT EXISTS idx_entities_content 
                    ON entities(content_id)
                """)
                db.execute("""
                    CREATE INDEX IF NOT EXISTS idx_entities_type_value 
                    ON entities(entity_type, entity_value)
                """)
                
            logger.success(f"✅ Created table: {table_name}")
            
        except Exception as e:
            logger.error(f"Failed to create {table_name}: {e}")
            
    # 3. Verify all tables exist
    tables = db.fetch_all("""
        SELECT name FROM sqlite_master 
        WHERE type='table' 
        ORDER BY name
    """)
    table_names = [t['name'] for t in tables]
    
    logger.info("\nFinal table list:")
    for table in table_names:
        logger.info(f"  - {table}")
        
    return True


def fix_vector_alignment():
    """Fix vector-database alignment issues."""
    logger.info("=" * 60)
    logger.info("FIXING VECTOR-DATABASE ALIGNMENT")
    logger.info("=" * 60)
    
    try:
        from qdrant_client import QdrantClient
        from lib.embeddings import get_embedding_service
        
        client = QdrantClient(host="localhost", port=6333)
        db = SimpleDB(settings.database.emails_db_path)
        embedding_service = get_embedding_service(use_mock=False)
        
        # Check for content without vectors
        content_without_vectors = db.fetch_all("""
            SELECT id, title, body 
            FROM content_unified 
            WHERE body IS NOT NULL 
            AND LENGTH(body) > 100
            ORDER BY id DESC 
            LIMIT 10
        """)
        
        logger.info(f"Checking {len(content_without_vectors)} recent content items...")
        
        fixed_count = 0
        for content in content_without_vectors:
            try:
                # Check if vector exists
                try:
                    existing = client.retrieve(
                        collection_name='vectors_v2',
                        ids=[content['id']]  # Use integer ID directly
                    )
                    if existing:
                        logger.debug(f"Vector exists for content {content['id']}")
                        continue
                except:
                    pass  # Vector doesn't exist
                    
                # Generate and add missing vector
                logger.info(f"Generating vector for content {content['id']}: {content['title'][:50]}...")
                
                text = content['body'][:5000]  # Limit text length
                vector = embedding_service.encode(text)
                
                # Add to Qdrant using integer ID
                client.upsert(
                    collection_name='vectors_v2',
                    points=[{
                        'id': content['id'],  # Use integer ID directly
                        'vector': vector.tolist(),
                        'payload': {
                            'content_id': str(content['id']),
                            'title': content['title'],
                            'source_type': 'content_unified'
                        }
                    }]
                )
                
                fixed_count += 1
                logger.success(f"✅ Added vector for content {content['id']}")
                
            except Exception as e:
                logger.error(f"Failed to fix vector for content {content['id']}: {e}")
                
        logger.info(f"\n✅ Fixed {fixed_count} missing vectors")
        
        # Clean up orphaned vectors
        logger.info("\nChecking for orphaned vectors...")
        
        # Get sample of vectors
        vectors = client.scroll(
            collection_name='vectors_v2',
            limit=100,
            with_payload=True,
            with_vectors=False
        )[0]
        
        orphaned_count = 0
        for point in vectors:
            content_id = point.payload.get('content_id')
            if content_id:
                try:
                    exists = db.fetch_one(
                        "SELECT 1 FROM content_unified WHERE id = ?",
                        (int(content_id),)
                    )
                    if not exists:
                        # Delete orphaned vector
                        client.delete(
                            collection_name='vectors_v2',
                            points_selector={'points': [point.id]}
                        )
                        orphaned_count += 1
                        logger.warning(f"Deleted orphaned vector: {point.id}")
                except Exception as e:
                    logger.debug(f"Error checking vector {point.id}: {e}")
                    
        if orphaned_count > 0:
            logger.success(f"✅ Cleaned up {orphaned_count} orphaned vectors")
        else:
            logger.info("✅ No orphaned vectors found")
            
    except ImportError:
        logger.error("Qdrant client not available - skipping vector fixes")
    except Exception as e:
        logger.error(f"Vector alignment fix failed: {e}")
        
    return True


def verify_fixes():
    """Quick verification that fixes worked."""
    logger.info("=" * 60)
    logger.info("VERIFYING FIXES")
    logger.info("=" * 60)
    
    db = SimpleDB(settings.database.emails_db_path)
    
    # Check tables
    tables = db.fetch_all("""
        SELECT name FROM sqlite_master 
        WHERE type='table' 
        ORDER BY name
    """)
    table_names = [t['name'] for t in tables]
    
    required_tables = [
        'content_unified',
        'individual_messages',
        'message_occurrences', 
        'entities',
        'document_summaries'
    ]
    
    all_good = True
    for table in required_tables:
        if table in table_names:
            logger.success(f"✅ Table exists: {table}")
        else:
            logger.error(f"❌ Missing table: {table}")
            all_good = False
            
    # Check substantive_text column
    columns = db.fetch_all("""
        PRAGMA table_info(content_unified)
    """)
    column_names = [c['name'] for c in columns]
    
    if 'substantive_text' in column_names:
        logger.success("✅ substantive_text column exists")
    else:
        logger.error("❌ substantive_text column missing")
        all_good = False
        
    # Quick search test
    try:
        from lib.search import hybrid_search
        results = hybrid_search("test", limit=1)
        logger.success(f"✅ Search works - returned {len(results)} results")
    except Exception as e:
        logger.error(f"❌ Search failed: {e}")
        all_good = False
        
    if all_good:
        logger.success("\n🎉 ALL FIXES VERIFIED SUCCESSFULLY!")
    else:
        logger.error("\n⚠️  Some issues remain - check logs above")
        
    return all_good


def main():
    """Run all fixes."""
    logger.info("=" * 60)
    logger.info("STARTING ONE-SHOT FIX FOR ALL ISSUES")
    logger.info("=" * 60)
    
    # Run fixes
    fix_database_schema()
    fix_vector_alignment()
    
    # Verify
    success = verify_fixes()
    
    if success:
        logger.success("\n✅ SYSTEM FIXED! Run diagnostics again to confirm.")
        logger.info("python3 tools/diagnostics/system_diagnostics.py")
    else:
        logger.error("\n❌ Some issues remain. Check logs and run diagnostics.")
        
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()