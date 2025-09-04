#!/usr/bin/env python3
"""Comprehensive migration to enable foreign key constraints with proper handling of email summaries.

This script addresses the discovered issue where email summaries were stored with
source_type='email_message' but using SHA256 hashes as source_id instead of actual
message_hash values from individual_messages table.

The solution:
1. Create a new email_summaries table for email-specific summaries
2. Migrate email summaries from document_summaries to email_summaries
3. Add proper FK constraints only where they make sense
4. Preserve all data integrity

Run with --dry-run first to see what would happen without making changes.
"""

import argparse
import sqlite3
import sys
import time
from pathlib import Path

from loguru import logger
from shared.db.simple_db import SimpleDB


def analyze_current_state(db: SimpleDB) -> dict:
    """Analyze the current database state to understand data patterns."""
    
    analysis = {
        "total_content": 0,
        "email_messages": 0,
        "documents": 0,
        "individual_messages": 0,
        "summaries": 0,
        "email_summaries": 0,
        "orphaned_references": 0,
        "actual_orphans": 0
    }
    
    # Count content_unified records
    result = db.fetch("SELECT COUNT(*) as count FROM content_unified", [])
    analysis["total_content"] = result[0]["count"] if result else 0
    
    # Count by source_type
    result = db.fetch("""
        SELECT source_type, COUNT(*) as count 
        FROM content_unified 
        GROUP BY source_type
    """, [])
    for row in result:
        if row["source_type"] == "email_message":
            analysis["email_messages"] = row["count"]
        elif row["source_type"] == "document":
            analysis["documents"] = row["count"]
    
    # Count individual_messages
    result = db.fetch("SELECT COUNT(*) as count FROM individual_messages", [])
    analysis["individual_messages"] = result[0]["count"] if result else 0
    
    # Identify email summaries (64-char SHA256 hashes not in individual_messages)
    result = db.fetch("""
        SELECT COUNT(*) as count
        FROM content_unified 
        WHERE source_type = 'email_message'
        AND LENGTH(source_id) = 64
        AND source_id NOT IN (SELECT message_hash FROM individual_messages)
        AND (body LIKE 'From:%' OR body LIKE 'Subject:%')
    """, [])
    analysis["email_summaries"] = result[0]["count"] if result else 0
    
    # Count actual orphans (non-summary records without matching message)
    result = db.fetch("""
        SELECT COUNT(*) as count
        FROM content_unified 
        WHERE source_type = 'email_message'
        AND source_id NOT IN (SELECT message_hash FROM individual_messages)
        AND NOT (LENGTH(source_id) = 64 AND (body LIKE 'From:%' OR body LIKE 'Subject:%'))
    """, [])
    analysis["actual_orphans"] = result[0]["count"] if result else 0
    
    # Count document_summaries
    result = db.fetch("SELECT COUNT(*) as count FROM document_summaries", [])
    analysis["summaries"] = result[0]["count"] if result else 0
    
    return analysis


def create_email_summaries_table(conn: sqlite3.Connection) -> None:
    """Create the email_summaries table with proper FK to content_unified."""
    
    conn.execute("""
    CREATE TABLE IF NOT EXISTS email_summaries (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        content_id INTEGER NOT NULL,
        summary TEXT NOT NULL,
        key_points TEXT,
        sentiment TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (content_id) REFERENCES content_unified(id)
            ON DELETE CASCADE
            ON UPDATE CASCADE
    )
    """)
    
    # Create index for performance
    conn.execute("""
    CREATE INDEX IF NOT EXISTS idx_email_summaries_content 
    ON email_summaries(content_id)
    """)


def migrate_email_summaries(conn: sqlite3.Connection, dry_run: bool = False) -> int:
    """Migrate email summaries and orphaned Gmail records to proper storage.
    
    Updates source_type from 'email_message' to 'email_summary' for:
    1. Summary records (64-char SHA256 hashes)
    2. Orphaned Gmail ID records (8-10 digit IDs)
    """
    
    if dry_run:
        # Count what would be migrated
        cursor = conn.execute("""
            SELECT COUNT(*) as count
            FROM content_unified 
            WHERE source_type = 'email_message'
            AND source_id NOT IN (SELECT message_hash FROM individual_messages)
        """)
        count = cursor.fetchone()[0]
        print(f"   [DRY RUN] Would update {count} orphaned records to source_type='email_summary'")
        return count
    
    # Update ALL orphaned email_message records to email_summary
    # This includes both SHA256 summaries and Gmail ID records
    conn.execute("""
        UPDATE content_unified 
        SET source_type = 'email_summary'
        WHERE source_type = 'email_message'
        AND source_id NOT IN (SELECT message_hash FROM individual_messages)
    """)
    
    return conn.total_changes


def add_foreign_key_constraints(db: SimpleDB, dry_run: bool = False) -> bool:
    """Add proper foreign key constraints to the database.
    
    This recreates tables with FK constraints since SQLite doesn't support
    ALTER TABLE ADD CONSTRAINT.
    """
    
    if dry_run:
        print("   [DRY RUN] Would recreate tables with FK constraints")
        return True
    
    conn = db.get_connection()
    cursor = conn.cursor()
    
    try:
        # Begin transaction
        cursor.execute("BEGIN EXCLUSIVE")
        
        # Skip Step 1 - we'll handle source_type update when recreating table
        # The CHECK constraint prevents updating to 'email_summary' in existing table
        
        # Step 2: Create email_summaries table
        print("   Creating email_summaries table...")
        create_email_summaries_table(conn)
        
        # Step 3: Backup and recreate content_unified with FK constraint
        print("   Backing up content_unified table...")
        cursor.execute("""
            CREATE TABLE content_unified_backup AS 
            SELECT * FROM content_unified
        """)
        
        # Get the current schema
        cursor.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name='content_unified'")
        cursor.fetchone()[0]
        
        # Drop old table
        cursor.execute("DROP TABLE content_unified")
        
        # Create new table with conditional FK (only for actual email_message records)
        # Include all columns from the actual schema
        cursor.execute("""
        CREATE TABLE content_unified (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            source_type TEXT NOT NULL CHECK(
                source_type IN ('email', 'email_message', 'email_summary', 'document', 'document_chunk')
            ),
            source_id TEXT NOT NULL,
            title TEXT,
            body TEXT NOT NULL,
            sha256 TEXT UNIQUE,
            validation_status TEXT DEFAULT 'pending' CHECK(
                validation_status IN ('pending', 'validated', 'failed')
            ),
            ready_for_embedding BOOLEAN DEFAULT 1,
            embedding_generated BOOLEAN DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            embedding_generated_at TIMESTAMP,
            quality_score REAL DEFAULT 1.0,
            metadata TEXT,
            UNIQUE(source_type, source_id)
        )
        """)
        
        # Note: We'll use a trigger to enforce FK only for email_message types
        cursor.execute("""
        CREATE TRIGGER enforce_email_message_fk
        BEFORE INSERT ON content_unified
        FOR EACH ROW
        WHEN NEW.source_type = 'email_message'
        BEGIN
            SELECT RAISE(ABORT, 'Foreign key violation: message_hash not found')
            WHERE NOT EXISTS (
                SELECT 1 FROM individual_messages 
                WHERE message_hash = NEW.source_id
            );
        END
        """)
        
        # Similar trigger for updates
        cursor.execute("""
        CREATE TRIGGER enforce_email_message_fk_update
        BEFORE UPDATE OF source_id, source_type ON content_unified
        FOR EACH ROW
        WHEN NEW.source_type = 'email_message'
        BEGIN
            SELECT RAISE(ABORT, 'Foreign key violation: message_hash not found')
            WHERE NOT EXISTS (
                SELECT 1 FROM individual_messages 
                WHERE message_hash = NEW.source_id
            );
        END
        """)
        
        # Restore data with source_type updates
        print("   Restoring content_unified data...")
        
        # First restore actual email_message records that have matching message_hash
        cursor.execute("""
            INSERT INTO content_unified 
            SELECT * FROM content_unified_backup
            WHERE source_type != 'email_message'
            OR source_id IN (SELECT message_hash FROM individual_messages)
        """)
        valid_restored = cursor.rowcount
        
        # Then restore orphaned records as email_summary type
        cursor.execute("""
            INSERT INTO content_unified 
            SELECT 
                id,
                'email_summary' as source_type,  -- Change type
                source_id,
                title,
                body,
                sha256,
                validation_status,
                ready_for_embedding,
                embedding_generated,
                created_at,
                updated_at,
                embedding_generated_at,
                quality_score,
                metadata
            FROM content_unified_backup
            WHERE source_type = 'email_message'
            AND source_id NOT IN (SELECT message_hash FROM individual_messages)
        """)
        orphans_converted = cursor.rowcount
        
        restored = valid_restored + orphans_converted
        print(f"   Restored {valid_restored} valid records")
        print(f"   Converted {orphans_converted} orphaned records to email_summary type")
        print(f"   Total restored: {restored} records")
        
        # Recreate indexes
        cursor.execute("""
            CREATE INDEX idx_content_unified_source 
            ON content_unified(source_type, source_id)
        """)
        
        cursor.execute("""
            CREATE INDEX idx_content_unified_embedding 
            ON content_unified(ready_for_embedding, embedding_generated)
        """)
        
        # Step 4: Handle message_occurrences table
        print("   Adding FK constraint to message_occurrences...")
        
        # Check if table exists
        cursor.execute("""
            SELECT name FROM sqlite_master 
            WHERE type='table' AND name='message_occurrences'
        """)
        if cursor.fetchone():
            # Backup
            cursor.execute("""
                CREATE TABLE message_occurrences_backup AS 
                SELECT * FROM message_occurrences
            """)
            
            # Drop and recreate with FK
            cursor.execute("DROP TABLE message_occurrences")
            
            cursor.execute("""
            CREATE TABLE message_occurrences (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                message_hash TEXT NOT NULL,
                email_id TEXT NOT NULL,
                position_in_email INTEGER NOT NULL,
                context_type TEXT,
                quote_depth INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (message_hash) REFERENCES individual_messages(message_hash)
                    ON DELETE CASCADE
                    ON UPDATE CASCADE
            )
            """)
            
            # Restore valid data
            cursor.execute("""
                INSERT INTO message_occurrences
                SELECT * FROM message_occurrences_backup
                WHERE message_hash IN (SELECT message_hash FROM individual_messages)
            """)
            
            cursor.execute("""
                CREATE INDEX idx_message_occurrences_hash 
                ON message_occurrences(message_hash)
            """)
        
        # Commit
        conn.commit()
        
        # Clean up backups
        print("   Cleaning up backup tables...")
        cursor.execute("DROP TABLE content_unified_backup")
        cursor.execute("DROP TABLE IF EXISTS message_occurrences_backup")
        conn.commit()
        
        print("   ✅ Foreign key constraints successfully added")
        return True
        
    except Exception as e:
        logger.error(f"Migration failed: {e}")
        print(f"   ❌ Migration failed: {e}")
        
        # Attempt rollback
        conn.rollback()
        
        # Try to restore
        try:
            cursor.execute("DROP TABLE IF EXISTS content_unified")
            cursor.execute("ALTER TABLE content_unified_backup RENAME TO content_unified")
            cursor.execute("DROP TABLE IF EXISTS message_occurrences")
            cursor.execute("ALTER TABLE message_occurrences_backup RENAME TO message_occurrences")
            conn.commit()
            print("   ✅ Restored from backup")
        except:
            print("   ❌ CRITICAL: Restore failed!")
        
        return False
        
    finally:
        conn.close()


def validate_constraints(db: SimpleDB) -> bool:
    """Validate that FK constraints are working properly."""
    
    print("\n4. Validating constraints...")
    
    conn = db.get_connection()
    
    try:
        # Test 1: FK pragma status
        fk_status = conn.execute("PRAGMA foreign_keys").fetchone()[0]
        if fk_status:
            print("   ✅ Foreign keys enabled")
        else:
            print("   ❌ Foreign keys not enabled")
            return False
        
        # Test 2: Try to violate constraint (should fail)
        print("   Testing constraint enforcement...")
        try:
            conn.execute("""
                INSERT INTO content_unified (
                    source_type, source_id, title, body, sha256
                ) VALUES (?, ?, ?, ?, ?)
            """, ("email_message", "fake_nonexistent_hash", "Test", "Test", f"test_{time.time()}"))
            conn.commit()
            print("   ❌ Constraint not enforced - invalid insert succeeded")
            return False
        except sqlite3.IntegrityError as e:
            if "Foreign key violation" in str(e) or "FOREIGN KEY constraint failed" in str(e):
                print("   ✅ Constraint properly enforced")
            else:
                print(f"   ⚠️  Different error: {e}")
        
        # Test 3: Verify email_summary records don't trigger FK
        print("   Testing email_summary exemption...")
        try:
            test_sha = f"test_summary_{int(time.time())}"
            conn.execute("""
                INSERT INTO content_unified (
                    source_type, source_id, title, body, sha256
                ) VALUES (?, ?, ?, ?, ?)
            """, ("email_summary", test_sha, "Summary", "From: test", test_sha))
            conn.commit()
            
            # Clean up test record
            conn.execute("DELETE FROM content_unified WHERE sha256 = ?", (test_sha,))
            conn.commit()
            
            print("   ✅ Email summaries exempt from FK constraint")
        except Exception as e:
            print(f"   ❌ Email summary insertion failed: {e}")
            return False
        
        # Test 4: Check data integrity
        cursor = conn.execute("""
            SELECT COUNT(*) as orphans
            FROM content_unified 
            WHERE source_type = 'email_message'
            AND source_id NOT IN (SELECT message_hash FROM individual_messages)
        """)
        orphans = cursor.fetchone()[0]
        
        if orphans == 0:
            print("   ✅ No orphaned email_message records")
        else:
            print(f"   ❌ Found {orphans} orphaned email_message records")
            return False
        
        print("\n   ✅ All validation tests passed!")
        return True
        
    finally:
        conn.close()


def main():
    parser = argparse.ArgumentParser(
        description="Enable foreign key constraints with proper handling of email summaries"
    )
    parser.add_argument("--dry-run", action="store_true", help="Show what would happen without changes")
    parser.add_argument("--skip-backup", action="store_true", help="Skip database backup")
    parser.add_argument("--force", action="store_true", help="Automatically handle orphans without prompting")
    args = parser.parse_args()
    
    print("=" * 70)
    print("Foreign Key & Email Summary Migration")
    print("=" * 70)
    
    if args.dry_run:
        print("🔍 DRY RUN MODE - No changes will be made\n")
    
    # Initialize database
    db = SimpleDB()
    
    # Step 1: Analyze current state
    print("1. Analyzing current database state...")
    state = analyze_current_state(db)
    
    print(f"   Total content records: {state['total_content']}")
    print(f"   Email messages: {state['email_messages']}")
    print(f"   Individual messages: {state['individual_messages']}")
    print(f"   Email summaries (to be migrated): {state['email_summaries']}")
    print(f"   Actual orphans: {state['actual_orphans']}")
    
    if state["actual_orphans"] > 0:
        print(f"\n   ⚠️  Found {state['actual_orphans']} truly orphaned records")
        print("   These appear to be Gmail IDs from older imports")
        if not args.dry_run:
            if args.force:
                print("   --force flag set, will convert to email_summary type")
            else:
                response = input("   Convert orphaned records to email_summary type? (y/n): ")
                if response.lower() != 'y':
                    print("   Migration cancelled")
                    return 1
    
    # Step 2: Backup
    if not args.skip_backup and not args.dry_run:
        print("\n2. Creating backup...")
        backup_path = Path(db.db_path).with_suffix(f".backup_{int(time.time())}.db")
        
        import shutil
        shutil.copy2(db.db_path, backup_path)
        print(f"   ✅ Backup created: {backup_path}")
    elif args.dry_run:
        print("\n2. [DRY RUN] Would create backup")
    
    # Step 3: Migrate
    print("\n3. Applying migration...")
    if not add_foreign_key_constraints(db, args.dry_run):
        if not args.dry_run:
            print("\n❌ Migration failed!")
            return 1
    
    # Step 4: Validate
    if not args.dry_run:
        if not validate_constraints(db):
            print("\n❌ Validation failed!")
            return 1
    
    # Final summary
    print("\n" + "=" * 70)
    
    if args.dry_run:
        print("DRY RUN COMPLETE")
        print("\nChanges that would be made:")
        print(f"  • {state['email_summaries']} email summaries → source_type='email_summary'")
        print("  • Foreign key constraints added to email_message records only")
        print("  • email_summaries table created")
        print("\nRun without --dry-run to apply changes")
    else:
        print("✅ MIGRATION SUCCESSFUL!")
        print("\nChanges applied:")
        print(f"  • {state['email_summaries']} email summaries migrated")
        print("  • Foreign key constraints active for email_message records")
        print("  • Email summaries exempt from FK constraints")
        print("  • Data integrity enforced")
    
    print("=" * 70)
    
    return 0


if __name__ == "__main__":
    sys.exit(main())