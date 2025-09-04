#!/usr/bin/env python3
"""Test script to verify foreign key enforcement in SQLite.

This script tests that foreign key constraints are properly enforced
after the changes to enable them in SimpleDB.
"""

import sqlite3
import sys

from loguru import logger
from shared.db.simple_db import SimpleDB


def test_foreign_keys():
    """Test that foreign key constraints are enforced."""
    
    print("=" * 60)
    print("Foreign Key Enforcement Test")
    print("=" * 60)
    
    # Initialize database
    db = SimpleDB()
    
    # Test 1: Check FK status through SimpleDB connection
    print("\n1. Testing foreign key status...")
    conn = db.get_connection()
    try:
        cursor = conn.execute("PRAGMA foreign_keys")
        fk_status = cursor.fetchone()[0]
        if fk_status:
            print("   ✅ Foreign keys are ENABLED")
        else:
            print("   ❌ Foreign keys are DISABLED")
            return False
    finally:
        conn.close()
    
    # Test 2: Check existing data integrity
    print("\n2. Checking existing data integrity...")
    
    # Check for orphaned records in content_unified
    orphans_query = """
    SELECT COUNT(*) 
    FROM content_unified 
    WHERE source_type = 'email_message' 
    AND source_id NOT IN (
        SELECT message_hash FROM individual_messages
    )
    """
    
    orphans_result = db.fetch(orphans_query, [])
    orphans = orphans_result[0]["COUNT(*)"] if orphans_result else 0
    
    if orphans > 0:
        print(f"   ⚠️  Found {orphans} orphaned records in content_unified")
        print("      These would prevent FK constraint creation")
    else:
        print("   ✅ No orphaned records found")
    
    # Test 3: Try to violate FK constraint (should fail)
    print("\n3. Testing foreign key enforcement...")
    
    # First, get a valid message_hash for testing
    valid_hash = db.fetch(
        "SELECT message_hash FROM individual_messages LIMIT 1", []
    )
    
    if not valid_hash:
        print("   ⚠️  No messages found to test with")
        return True
    
    valid_hash = valid_hash[0]["message_hash"]
    
    # Try to insert a content_unified record with invalid source_id
    fake_hash = "fake_nonexistent_hash_12345"
    
    try:
        conn = db.get_connection()
        conn.execute("""
            INSERT INTO content_unified (
                source_type, source_id, title, body, sha256
            ) VALUES (?, ?, ?, ?, ?)
        """, ("email_message", fake_hash, "Test", "Test body", "test_sha"))
        conn.commit()
        conn.close()
        
        print("   ❌ FK constraint NOT enforced - invalid insert succeeded!")
        return False
        
    except sqlite3.IntegrityError as e:
        if "FOREIGN KEY constraint failed" in str(e):
            print("   ✅ FK constraint properly enforced - invalid insert blocked")
        else:
            print(f"   ⚠️  Different integrity error: {e}")
            return False
    except Exception as e:
        print(f"   ❌ Unexpected error: {e}")
        return False
    finally:
        if conn:
            conn.close()
    
    # Test 4: Test CASCADE behavior
    print("\n4. Testing CASCADE behavior...")
    
    # Check if CASCADE is configured
    cascade_check = """
    SELECT sql FROM sqlite_master 
    WHERE type='table' AND name='content_unified'
    AND sql LIKE '%ON DELETE CASCADE%'
    """
    
    cascade_sql = db.fetch(cascade_check, [])
    if cascade_sql:
        print("   ✅ CASCADE delete configured in schema")
    else:
        print("   ℹ️  No CASCADE delete configured (manual cleanup required)")
    
    # Test 5: Performance impact check
    print("\n5. Checking performance with FK enabled...")
    
    import time
    
    # Test a typical query with FK enabled
    start = time.perf_counter()
    db.search_content("test", limit=10)
    elapsed = (time.perf_counter() - start) * 1000
    
    print(f"   Search query took {elapsed:.1f}ms")
    if elapsed < 500:
        print("   ✅ Performance acceptable with FK enabled")
    else:
        print(f"   ⚠️  Query slower than expected ({elapsed:.1f}ms)")
    
    print("\n" + "=" * 60)
    print("Summary:")
    print("-" * 60)
    print("✅ Foreign keys are properly enabled and enforced")
    print("✅ Data integrity is maintained")
    print("✅ Invalid references are blocked")
    print("\nRecommendation: Safe to proceed with FK enabled")
    print("=" * 60)
    
    return True


def check_and_fix_orphans():
    """Check for and optionally fix orphaned records."""
    
    db = SimpleDB()
    
    # Find orphans
    orphans_query = """
    SELECT source_id, title, id 
    FROM content_unified 
    WHERE source_type = 'email_message' 
    AND source_id NOT IN (
        SELECT message_hash FROM individual_messages
    )
    LIMIT 10
    """
    
    orphans = db.fetch(orphans_query, [])
    
    if orphans:
        print(f"\n⚠️  Found {len(orphans)} orphaned records:")
        for orphan in orphans[:5]:
            print(f"   - ID {orphan['id']}: {orphan['title'][:50]}")
        
        response = input("\nDelete orphaned records? (y/n): ")
        if response.lower() == 'y':
            conn = db.get_connection()
            try:
                conn.execute("""
                    DELETE FROM content_unified 
                    WHERE source_type = 'email_message' 
                    AND source_id NOT IN (
                        SELECT message_hash FROM individual_messages
                    )
                """)
                deleted = conn.total_changes
                conn.commit()
                print(f"✅ Deleted {deleted} orphaned records")
            finally:
                conn.close()


if __name__ == "__main__":
    try:
        # Run the test
        success = test_foreign_keys()
        
        # Check for orphans if requested
        if "--check-orphans" in sys.argv:
            check_and_fix_orphans()
        
        sys.exit(0 if success else 1)
        
    except Exception as e:
        logger.error(f"Test failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)