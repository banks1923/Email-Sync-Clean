#!/usr/bin/env python3
"""
Add FTS5 full-text search to content_unified table.

This migration:
1. Creates FTS5 virtual table for full-text search
2. Populates it with existing content
3. Creates triggers to keep it synchronized
4. Adds query_logs table for search analytics
"""

import sqlite3
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from lib.db import SimpleDB


def create_fts5_table(db: SimpleDB) -> None:
    """Create FTS5 virtual table for content_unified."""
    print("Creating FTS5 virtual table...")
    
    # Create FTS5 table with porter tokenizer for better stemming
    # Include key searchable fields
    db.execute("""
        CREATE VIRTUAL TABLE IF NOT EXISTS content_unified_fts USING fts5(
            content_id UNINDEXED,  -- Store but don't index the ID
            title,
            body,
            substantive_text,
            tokenize='porter unicode61'  -- Porter stemmer + Unicode support
        )
    """)
    print("✓ FTS5 table created")


def populate_fts5_table(db: SimpleDB) -> None:
    """Populate FTS5 table with existing content."""
    print("Populating FTS5 table from existing content...")
    
    # Count existing content
    count_result = db.fetch_one("SELECT COUNT(*) as count FROM content_unified")
    total = count_result["count"] if count_result else 0
    
    if total == 0:
        print("  No existing content to migrate")
        return
    
    print(f"  Migrating {total} documents...")
    
    # Batch insert for better performance
    db.execute("""
        INSERT INTO content_unified_fts (content_id, title, body, substantive_text)
        SELECT id, title, body, substantive_text
        FROM content_unified
        WHERE title IS NOT NULL OR body IS NOT NULL OR substantive_text IS NOT NULL
    """)
    
    # Verify migration
    fts_count = db.fetch_one("SELECT COUNT(*) as count FROM content_unified_fts")
    migrated = fts_count["count"] if fts_count else 0
    print(f"✓ Migrated {migrated} documents to FTS5")


def create_synchronization_triggers(db: SimpleDB) -> None:
    """Create triggers to keep FTS5 synchronized with content_unified."""
    print("Creating synchronization triggers...")
    
    # INSERT trigger
    db.execute("""
        CREATE TRIGGER IF NOT EXISTS content_unified_fts_insert
        AFTER INSERT ON content_unified
        BEGIN
            INSERT INTO content_unified_fts (content_id, title, body, substantive_text)
            VALUES (NEW.id, NEW.title, NEW.body, NEW.substantive_text);
        END
    """)
    
    # UPDATE trigger
    db.execute("""
        CREATE TRIGGER IF NOT EXISTS content_unified_fts_update
        AFTER UPDATE ON content_unified
        BEGIN
            UPDATE content_unified_fts
            SET title = NEW.title,
                body = NEW.body,
                substantive_text = NEW.substantive_text
            WHERE content_id = NEW.id;
        END
    """)
    
    # DELETE trigger
    db.execute("""
        CREATE TRIGGER IF NOT EXISTS content_unified_fts_delete
        AFTER DELETE ON content_unified
        BEGIN
            DELETE FROM content_unified_fts WHERE content_id = OLD.id;
        END
    """)
    
    print("✓ Created INSERT, UPDATE, and DELETE triggers")


def create_query_logs_table(db: SimpleDB) -> None:
    """Create table for query logging and analytics."""
    print("Creating query_logs table...")
    
    db.execute("""
        CREATE TABLE IF NOT EXISTS query_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            query TEXT NOT NULL,
            search_mode TEXT NOT NULL,  -- 'keyword', 'semantic', 'hybrid'
            result_count INTEGER,
            execution_time_ms REAL,
            filters TEXT,  -- JSON
            timestamp TEXT DEFAULT CURRENT_TIMESTAMP,
            user_session TEXT,  -- Optional session identifier
            clicked_results TEXT  -- JSON array of clicked result IDs
        )
    """)
    
    # Index for analytics
    db.execute("""
        CREATE INDEX IF NOT EXISTS idx_query_logs_timestamp 
        ON query_logs(timestamp DESC)
    """)
    
    db.execute("""
        CREATE INDEX IF NOT EXISTS idx_query_logs_mode 
        ON query_logs(search_mode)
    """)
    
    print("✓ Created query_logs table with indexes")


def verify_fts5_functionality(db: SimpleDB) -> None:
    """Verify FTS5 is working correctly."""
    print("\nVerifying FTS5 functionality...")
    
    # Check if FTS5 table exists
    result = db.fetch_one("""
        SELECT name FROM sqlite_master 
        WHERE type='table' AND name='content_unified_fts'
    """)
    
    if not result:
        raise RuntimeError("FTS5 table was not created")
    
    # Test a simple MATCH query
    try:
        db.fetch_all("""
            SELECT content_id 
            FROM content_unified_fts 
            WHERE content_unified_fts MATCH 'test' 
            LIMIT 1
        """)
        print("✓ FTS5 MATCH queries working")
    except sqlite3.Error as e:
        print(f"⚠ FTS5 query test failed: {e}")
    
    # Check triggers exist
    triggers = db.fetch_all("""
        SELECT name FROM sqlite_master 
        WHERE type='trigger' AND name LIKE 'content_unified_fts_%'
    """)
    
    if len(triggers) == 3:
        print(f"✓ All 3 synchronization triggers exist")
    else:
        print(f"⚠ Only {len(triggers)} triggers found (expected 3)")


def main():
    """Run the migration."""
    print("FTS5 Search Migration")
    print("=" * 50)
    
    # Use the main database
    db_path = Path(__file__).parent.parent.parent / "data" / "system_data" / "emails.db"
    
    if not db_path.exists():
        print(f"Database not found at {db_path}")
        sys.exit(1)
    
    db = SimpleDB(str(db_path))
    
    try:
        # Run migration steps
        create_fts5_table(db)
        populate_fts5_table(db)
        create_synchronization_triggers(db)
        create_query_logs_table(db)
        verify_fts5_functionality(db)
        
        print("\n" + "=" * 50)
        print("✓ FTS5 migration completed successfully!")
        print("\nNext steps:")
        print("1. Test keyword search performance improvement")
        print("2. Verify hybrid search uses FTS5")
        print("3. Monitor query_logs for search patterns")
        
    except Exception as e:
        print(f"\n✗ Migration failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()