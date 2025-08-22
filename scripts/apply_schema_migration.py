#!/usr/bin/env python3
"""Apply schema migration with proper error handling"""

import sqlite3
from pathlib import Path


def apply_migration():
    db_path = Path("data/emails.db")
    if not db_path.exists():
        print(f"❌ Database not found: {db_path}")
        return False
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Check existing columns
    cursor.execute("PRAGMA table_info(documents)")
    existing_columns = {row[1] for row in cursor.fetchall()}
    
    migrations = [
        # Add missing columns (only if not exists)
        ("char_count", "ALTER TABLE documents ADD COLUMN char_count INTEGER DEFAULT 0"),
        ("word_count", "ALTER TABLE documents ADD COLUMN word_count INTEGER DEFAULT 0"),
        ("pages", "ALTER TABLE documents ADD COLUMN pages INTEGER DEFAULT 0"),
        ("sha256", "ALTER TABLE documents ADD COLUMN sha256 TEXT"),
        ("ocr_applied", "ALTER TABLE documents ADD COLUMN ocr_applied INTEGER DEFAULT 0"),
        ("text_path", "ALTER TABLE documents ADD COLUMN text_path TEXT"),
        ("meta_json_path", "ALTER TABLE documents ADD COLUMN meta_json_path TEXT"),
        ("status", "ALTER TABLE documents ADD COLUMN status TEXT DEFAULT 'processed'"),
        ("error_message", "ALTER TABLE documents ADD COLUMN error_message TEXT"),
        ("processed_at", "ALTER TABLE documents ADD COLUMN processed_at TEXT"),
        ("attempt_count", "ALTER TABLE documents ADD COLUMN attempt_count INTEGER DEFAULT 0"),
        ("next_retry_at", "ALTER TABLE documents ADD COLUMN next_retry_at TEXT"),
    ]
    
    for column_name, sql in migrations:
        if column_name not in existing_columns:
            try:
                cursor.execute(sql)
                print(f"✅ Added column: {column_name}")
            except sqlite3.OperationalError as e:
                print(f"⚠️  Column {column_name}: {e}")
        else:
            print(f"✓ Column exists: {column_name}")
    
    # Create schema_version table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS schema_version (
            version INTEGER PRIMARY KEY,
            applied_at TEXT DEFAULT CURRENT_TIMESTAMP,
            description TEXT
        )
    """)
    
    # Record migration
    cursor.execute("""
        INSERT OR IGNORE INTO schema_version (version, description) 
        VALUES (1, 'Add missing PDF pipeline columns')
    """)
    
    # Create unified content table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS content_unified (
            id INTEGER PRIMARY KEY,
            source_type TEXT NOT NULL,
            source_id INTEGER NOT NULL,
            title TEXT,
            body TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            ready_for_embedding INTEGER DEFAULT 0,
            UNIQUE(source_type, source_id)
        )
    """)
    
    # Ensure embeddings table exists
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS embeddings (
            id INTEGER PRIMARY KEY,
            content_id INTEGER NOT NULL,
            vector BLOB,
            dim INTEGER NOT NULL DEFAULT 1024,
            model TEXT NOT NULL DEFAULT 'legal-bert',
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(content_id, model)
        )
    """)
    
    # Create indexes
    try:
        cursor.execute("CREATE INDEX idx_documents_sha256 ON documents(sha256)")
        print("✅ Created sha256 index")
    except sqlite3.OperationalError:
        print("✓ sha256 index exists")
    
    conn.commit()
    conn.close()
    
    print("\n✅ Schema migration complete")
    return True

if __name__ == "__main__":
    apply_migration()