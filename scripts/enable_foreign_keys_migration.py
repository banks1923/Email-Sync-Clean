#!/usr/bin/env python3
"""Migration script to properly enable foreign key constraints in the database.

IMPORTANT: This migration adds actual FOREIGN KEY constraints to the database schema.
Simply enabling PRAGMA foreign_keys=ON only enforces constraints that exist - it doesn't
create them. This script:

1. Checks for and cleans up orphaned records
2. Creates a new table with proper FK constraints
3. Migrates existing data
4. Validates the migration

Run with --dry-run first to see what would happen without making changes.
"""

import argparse
import sqlite3
import sys
import time
from pathlib import Path
from datetime import datetime

from loguru import logger
from shared.simple_db import SimpleDB


def check_orphaned_records(db: SimpleDB) -> tuple[int, list]:
    """Check for orphaned records that would violate FK constraints."""
    
    # Check content_unified for orphaned email_message references
    orphans_query = """
    SELECT id, source_id, title 
    FROM content_unified 
    WHERE source_type = 'email_message' 
    AND source_id NOT IN (
        SELECT message_hash FROM individual_messages
    )
    """
    
    orphans = db.fetch(orphans_query, [])
    
    # Also check message_occurrences
    occurrences_orphans_query = """
    SELECT COUNT(*) as count
    FROM message_occurrences 
    WHERE message_hash NOT IN (
        SELECT message_hash FROM individual_messages
    )
    """
    
    occ_result = db.fetch(occurrences_orphans_query, [])
    occ_orphans = occ_result[0]["count"] if occ_result else 0
    
    return len(orphans), orphans, occ_orphans


def clean_orphaned_records(db: SimpleDB, dry_run: bool = False) -> int:
    """Clean up orphaned records before migration."""
    
    if dry_run:
        print("   [DRY RUN] Would delete orphaned records")
        return 0
    
    conn = db.get_connection()
    try:
        # Delete orphaned content_unified records
        conn.execute("""
            DELETE FROM content_unified 
            WHERE source_type = 'email_message' 
            AND source_id NOT IN (
                SELECT message_hash FROM individual_messages
            )
        """)
        content_deleted = conn.total_changes
        
        # Delete orphaned message_occurrences
        conn.execute("""
            DELETE FROM message_occurrences 
            WHERE message_hash NOT IN (
                SELECT message_hash FROM individual_messages
            )
        """)
        occ_deleted = conn.total_changes - content_deleted
        
        conn.commit()
        return content_deleted + occ_deleted
    finally:
        conn.close()


def migrate_to_fk_schema(db: SimpleDB, dry_run: bool = False) -> bool:
    """Migrate to schema with proper foreign key constraints.
    
    SQLite doesn't support ALTER TABLE ADD CONSTRAINT for foreign keys,
    so we need to recreate the table with constraints.
    """
    
    print("\n3. Migrating to FK-enabled schema...")
    
    if dry_run:
        print("   [DRY RUN] Would recreate tables with FK constraints")
        return True
    
    conn = db.get_connection()
    cursor = conn.cursor()
    
    try:
        # Begin transaction
        cursor.execute("BEGIN EXCLUSIVE")
        
        # Create backup of current data
        print("   Creating backup tables...")
        cursor.execute("""
            CREATE TABLE content_unified_backup AS 
            SELECT * FROM content_unified
        """)
        
        cursor.execute("""
            CREATE TABLE message_occurrences_backup AS 
            SELECT * FROM message_occurrences
        """)
        
        # Drop the old tables
        print("   Dropping old tables...")
        cursor.execute("DROP TABLE content_unified")
        cursor.execute("DROP TABLE message_occurrences")
        
        # Recreate with FK constraints
        print("   Creating new tables with FK constraints...")
        
        # content_unified with FK to individual_messages
        cursor.execute("""
        CREATE TABLE content_unified (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            source_type TEXT NOT NULL CHECK(source_type IN ('email', 'email_message', 'document', 'document_chunk')),
            source_id TEXT NOT NULL,
            title TEXT,
            body TEXT NOT NULL,
            sha256 TEXT UNIQUE,
            validation_status TEXT DEFAULT 'pending' CHECK(validation_status IN ('pending', 'validated', 'failed')),
            ready_for_embedding BOOLEAN DEFAULT 1,
            embedding_generated BOOLEAN DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            embedding_generated_at TIMESTAMP,
            UNIQUE(source_type, source_id),
            FOREIGN KEY (source_id) REFERENCES individual_messages(message_hash) 
                ON DELETE CASCADE 
                ON UPDATE CASCADE
                DEFERRABLE INITIALLY DEFERRED
        )
        """)
        
        # message_occurrences with FK
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
        
        # Restore data (only non-orphaned records)
        print("   Restoring valid data...")
        
        # Restore content_unified - only email_message types need FK validation
        cursor.execute("""
            INSERT INTO content_unified 
            SELECT * FROM content_unified_backup
            WHERE source_type != 'email_message'
            OR source_id IN (SELECT message_hash FROM individual_messages)
        """)
        content_restored = cursor.rowcount
        
        # Restore message_occurrences
        cursor.execute("""
            INSERT INTO message_occurrences
            SELECT * FROM message_occurrences_backup
            WHERE message_hash IN (SELECT message_hash FROM individual_messages)
        """)
        occ_restored = cursor.rowcount
        
        # Recreate indexes
        print("   Recreating indexes...")
        cursor.execute("""
            CREATE INDEX idx_content_unified_source 
            ON content_unified(source_type, source_id)
        """)
        
        cursor.execute("""
            CREATE INDEX idx_content_unified_embedding 
            ON content_unified(ready_for_embedding, embedding_generated)
        """)
        
        cursor.execute("""
            CREATE INDEX idx_message_occurrences_hash 
            ON message_occurrences(message_hash)
        """)
        
        cursor.execute("""
            CREATE INDEX idx_message_occurrences_email 
            ON message_occurrences(email_id)
        """)
        
        print(f"   Restored {content_restored} content_unified records")
        print(f"   Restored {occ_restored} message_occurrences records")
        
        # Commit the migration
        conn.commit()
        print("   ✅ Migration completed successfully")
        
        # Drop backup tables
        print("   Cleaning up backup tables...")
        cursor.execute("DROP TABLE content_unified_backup")
        cursor.execute("DROP TABLE message_occurrences_backup")
        conn.commit()
        
        return True
        
    except Exception as e:
        logger.error(f"Migration failed: {e}")
        print(f"   ❌ Migration failed: {e}")
        
        # Rollback
        conn.rollback()
        
        # Try to restore from backup
        try:
            print("   Attempting to restore from backup...")
            cursor.execute("DROP TABLE IF EXISTS content_unified")
            cursor.execute("DROP TABLE IF EXISTS message_occurrences")
            cursor.execute("ALTER TABLE content_unified_backup RENAME TO content_unified")
            cursor.execute("ALTER TABLE message_occurrences_backup RENAME TO message_occurrences")
            conn.commit()
            print("   ✅ Restored from backup")
        except Exception as restore_error:
            print(f"   ❌ Restore failed: {restore_error}")
            print("   CRITICAL: Database may be in inconsistent state!")
        
        return False
        
    finally:
        conn.close()


def validate_migration(db: SimpleDB) -> bool:
    """Validate that FK constraints are working."""
    
    print("\n4. Validating FK constraints...")
    
    conn = db.get_connection()
    
    try:
        # Test 1: Check FK pragma is enabled
        fk_status = conn.execute("PRAGMA foreign_keys").fetchone()[0]
        if not fk_status:
            print("   ❌ Foreign keys not enabled")
            return False
        print("   ✅ Foreign keys enabled")
        
        # Test 2: Try to violate constraint (should fail)
        try:
            conn.execute("""
                INSERT INTO content_unified (
                    source_type, source_id, title, body, sha256
                ) VALUES (?, ?, ?, ?, ?)
            """, ("email_message", "fake_hash_test", "Test", "Test", "test_sha"))
            conn.commit()
            print("   ❌ FK constraint not enforced - invalid insert succeeded")
            return False
        except sqlite3.IntegrityError as e:
            if "FOREIGN KEY constraint failed" in str(e):
                print("   ✅ FK constraint properly enforced")
            else:
                print(f"   ⚠️  Different error: {e}")
                return False
        
        # Test 3: Check CASCADE works
        print("   Testing CASCADE delete...")
        
        # Create test data
        test_hash = f"test_cascade_{int(time.time())}"
        
        # Insert test message
        conn.execute("""
            INSERT INTO individual_messages (
                message_hash, content, subject, sender_email, date_sent, message_id
            ) VALUES (?, ?, ?, ?, ?, ?)
        """, (test_hash, "Test", "Test", "test@example.com", datetime.now(), f"test_{time.time()}"))
        
        # Insert related content
        conn.execute("""
            INSERT INTO content_unified (
                source_type, source_id, title, body, sha256
            ) VALUES (?, ?, ?, ?, ?)
        """, ("email_message", test_hash, "Test", "Test", f"sha_{test_hash}"))
        
        conn.commit()
        
        # Verify both exist
        content_exists = conn.execute(
            "SELECT COUNT(*) FROM content_unified WHERE source_id = ?", 
            (test_hash,)
        ).fetchone()[0]
        
        if content_exists != 1:
            print("   ❌ Test data not created properly")
            return False
        
        # Delete the message (should cascade)
        conn.execute("DELETE FROM individual_messages WHERE message_hash = ?", (test_hash,))
        conn.commit()
        
        # Check if content was deleted
        content_after = conn.execute(
            "SELECT COUNT(*) FROM content_unified WHERE source_id = ?",
            (test_hash,)
        ).fetchone()[0]
        
        if content_after == 0:
            print("   ✅ CASCADE delete works")
        else:
            print("   ❌ CASCADE delete not working")
            return False
        
        print("\n   ✅ All validation tests passed!")
        return True
        
    finally:
        conn.close()


def main():
    parser = argparse.ArgumentParser(description="Enable foreign key constraints in the database")
    parser.add_argument("--dry-run", action="store_true", help="Show what would happen without making changes")
    parser.add_argument("--skip-backup", action="store_true", help="Skip creating backup (not recommended)")
    parser.add_argument("--force", action="store_true", help="Force migration even with orphaned records")
    args = parser.parse_args()
    
    print("=" * 70)
    print("Foreign Key Migration Script")
    print("=" * 70)
    
    if args.dry_run:
        print("🔍 DRY RUN MODE - No changes will be made")
    
    # Initialize database
    db = SimpleDB()
    
    # Step 1: Check for orphaned records
    print("\n1. Checking for orphaned records...")
    orphan_count, orphans, occ_orphans = check_orphaned_records(db)
    
    if orphan_count > 0 or occ_orphans > 0:
        print(f"   ⚠️  Found {orphan_count} orphaned content_unified records")
        print(f"   ⚠️  Found {occ_orphans} orphaned message_occurrences records")
        
        if orphans and len(orphans) > 0:
            print("\n   Sample orphaned records:")
            for orphan in orphans[:3]:
                title = orphan['title'][:50] if orphan['title'] else "No title"
                print(f"      - ID {orphan['id']}: {title}")
        
        if not args.force and not args.dry_run:
            response = input("\n   Clean up orphaned records? (y/n): ")
            if response.lower() != 'y':
                print("   ❌ Migration cancelled - orphaned records must be handled")
                return 1
    else:
        print("   ✅ No orphaned records found")
    
    # Step 2: Clean up orphans if needed
    if (orphan_count > 0 or occ_orphans > 0) and not args.dry_run:
        print("\n2. Cleaning orphaned records...")
        deleted = clean_orphaned_records(db, args.dry_run)
        print(f"   ✅ Deleted {deleted} orphaned records")
    elif orphan_count == 0:
        print("\n2. No cleanup needed")
    
    # Step 3: Backup database
    if not args.skip_backup and not args.dry_run:
        print("\n   Creating database backup...")
        backup_path = Path(db.db_path).with_suffix(f".backup_{int(time.time())}.db")
        
        import shutil
        shutil.copy2(db.db_path, backup_path)
        print(f"   ✅ Backup created: {backup_path}")
    
    # Step 4: Migrate schema
    success = migrate_to_fk_schema(db, args.dry_run)
    
    if not success and not args.dry_run:
        print("\n❌ Migration failed!")
        return 1
    
    # Step 5: Validate if not dry run
    if not args.dry_run:
        if not validate_migration(db):
            print("\n❌ Validation failed!")
            return 1
    
    print("\n" + "=" * 70)
    
    if args.dry_run:
        print("DRY RUN COMPLETE - No changes were made")
        print("Run without --dry-run to apply changes")
    else:
        print("✅ MIGRATION SUCCESSFUL!")
        print("\nForeign key constraints are now active:")
        print("  • Invalid references will be blocked")
        print("  • Deleting messages will cascade to content_unified")
        print("  • Data integrity is enforced")
    
    print("=" * 70)
    
    return 0


if __name__ == "__main__":
    sys.exit(main())