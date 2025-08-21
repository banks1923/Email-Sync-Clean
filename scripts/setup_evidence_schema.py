#!/usr/bin/env python3
"""Setup legal evidence tracking schema in emails database."""

import sqlite3
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))



def setup_evidence_schema(db_path="emails.db"):
    """Add evidence tracking columns to emails table."""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Check if columns exist
    cursor.execute("PRAGMA table_info(emails)")
    columns = [col[1] for col in cursor.fetchall()]
    
    # Add eid column if it doesn't exist
    if 'eid' not in columns:
        print("Adding eid column...")
        cursor.execute("ALTER TABLE emails ADD COLUMN eid TEXT")
        print("✅ Added eid column")
        
        # Create unique index for eid
        cursor.execute("CREATE UNIQUE INDEX idx_eid ON emails(eid)")
        print("✅ Created unique index on eid")
    else:
        print("ℹ️  eid column already exists")
        
    # Add thread_id column if it doesn't exist
    if 'thread_id' not in columns:
        print("Adding thread_id column...")
        cursor.execute("ALTER TABLE emails ADD COLUMN thread_id TEXT")
        print("✅ Added thread_id column")
    else:
        print("ℹ️  thread_id column already exists")
        
    # Create index for thread_id if it doesn't exist
    cursor.execute("""
        SELECT name FROM sqlite_master 
        WHERE type='index' AND name='idx_thread_id'
    """)
    
    if not cursor.fetchone():
        print("Creating thread_id index...")
        cursor.execute("CREATE INDEX idx_thread_id ON emails(thread_id)")
        print("✅ Created thread_id index")
    else:
        print("ℹ️  thread_id index already exists")
        
    conn.commit()
    conn.close()
    
    print("\n✅ Evidence tracking schema setup complete!")
    

if __name__ == "__main__":
    setup_evidence_schema()
    
    # Show current schema
    print("\n📊 Current emails table schema:")
    conn = sqlite3.connect("emails.db")
    cursor = conn.cursor()
    cursor.execute("PRAGMA table_info(emails)")
    
    for col in cursor.fetchall():
        print(f"  {col[1]:<20} {col[2]:<15} {'NOT NULL' if col[3] else 'NULL':<10} {'PRIMARY KEY' if col[5] else ''}")
        
    conn.close()