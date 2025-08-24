#!/usr/bin/env python3
"""
Execute Email Cleanup
Removes duplicate email thread records while preserving individual messages.
SAFE: Keeps 426 email_message records, removes 416 email thread records.
"""

import sqlite3
from pathlib import Path
import sys
import time

# Add project root to path
sys.path.append(str(Path(__file__).parent.parent))

from shared.simple_db import SimpleDB
from loguru import logger

def execute_cleanup():
    """Execute the email cleanup operation."""
    db = SimpleDB()
    
    print("🧹 Starting Email Cleanup Operation")
    print("=" * 50)
    
    # First, verify current state
    before_counts = db.fetch_one("""
        SELECT 
            (SELECT COUNT(*) FROM content_unified WHERE source_type = 'email') as email_threads,
            (SELECT COUNT(*) FROM content_unified WHERE source_type = 'email_message') as email_messages,
            (SELECT COUNT(*) FROM embeddings e JOIN content_unified c ON e.content_id = c.id WHERE c.source_type = 'email') as email_embeddings
    """)
    
    print(f"📊 Before cleanup:")
    print(f"  - Email threads: {before_counts['email_threads']}")
    print(f"  - Email messages: {before_counts['email_messages']}")  
    print(f"  - Thread embeddings: {before_counts['email_embeddings']}")
    
    # Get IDs of records that will be deleted (for logging)
    email_ids = db.fetch("SELECT id FROM content_unified WHERE source_type = 'email' LIMIT 5")
    print(f"📝 Sample email thread IDs to be removed: {[row['id'] for row in email_ids]}")
    
    try:
        start_time = time.time()
        
        # Step 1: Delete embeddings for email threads (foreign key will cascade, but be explicit)
        print("\n🔗 Step 1: Removing embeddings for email threads...")
        embedding_delete_result = db.execute("""
            DELETE FROM embeddings 
            WHERE content_id IN (
                SELECT id FROM content_unified WHERE source_type = 'email'
            )
        """)
        embeddings_deleted = embedding_delete_result.rowcount
        print(f"   ✅ Removed {embeddings_deleted} embeddings")
        
        # Step 2: Delete email thread records  
        print("\n📧 Step 2: Removing email thread records...")
        email_delete_result = db.execute("""
            DELETE FROM content_unified WHERE source_type = 'email'
        """)
        emails_deleted = email_delete_result.rowcount
        print(f"   ✅ Removed {emails_deleted} email thread records")
        
        # Verify final state
        after_counts = db.fetch_one("""
            SELECT 
                (SELECT COUNT(*) FROM content_unified WHERE source_type = 'email') as email_threads,
                (SELECT COUNT(*) FROM content_unified WHERE source_type = 'email_message') as email_messages,
                (SELECT COUNT(*) FROM embeddings e JOIN content_unified c ON e.content_id = c.id WHERE c.source_type = 'email_message') as message_embeddings,
                (SELECT COUNT(*) FROM content_unified WHERE source_type IN ('email', 'email_message')) as total_email_records
        """)
        
        end_time = time.time()
        duration = end_time - start_time
        
        print(f"\n📊 After cleanup:")
        print(f"  - Email threads: {after_counts['email_threads']} (should be 0)")
        print(f"  - Email messages: {after_counts['email_messages']} (preserved)")
        print(f"  - Message embeddings: {after_counts['message_embeddings']}")
        print(f"  - Total email records: {after_counts['total_email_records']}")
        
        print(f"\n✅ Cleanup completed in {duration:.1f} seconds")
        print(f"   - Removed: {emails_deleted} email threads + {embeddings_deleted} embeddings")
        print(f"   - Preserved: {after_counts['email_messages']} individual messages + embeddings")
        
        # Calculate space savings
        if emails_deleted > 0:
            reduction_pct = (emails_deleted / (emails_deleted + after_counts['email_messages'])) * 100
            print(f"   - Storage reduction: {reduction_pct:.1f}%")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Cleanup failed: {e}")
        print(f"\n❌ CLEANUP FAILED: {e}")
        
        # Show current state for debugging
        current_counts = db.fetch_one("""
            SELECT 
                (SELECT COUNT(*) FROM content_unified WHERE source_type = 'email') as email_threads,
                (SELECT COUNT(*) FROM content_unified WHERE source_type = 'email_message') as email_messages
        """)
        print(f"Current state: {current_counts['email_threads']} threads, {current_counts['email_messages']} messages")
        
        return False

def verify_cleanup_success():
    """Verify the cleanup was successful."""
    db = SimpleDB()
    
    print("\n🔍 Verification:")
    print("=" * 30)
    
    # Check no email threads remain
    remaining_threads = db.fetch_one("SELECT COUNT(*) as count FROM content_unified WHERE source_type = 'email'")['count']
    
    # Check email messages are preserved
    preserved_messages = db.fetch_one("SELECT COUNT(*) as count FROM content_unified WHERE source_type = 'email_message'")['count']
    
    # Check embeddings
    message_embeddings = db.fetch_one("""
        SELECT COUNT(*) as count FROM embeddings e 
        JOIN content_unified c ON e.content_id = c.id 
        WHERE c.source_type = 'email_message'
    """)['count']
    
    orphan_embeddings = db.fetch_one("""
        SELECT COUNT(*) as count FROM embeddings e 
        WHERE NOT EXISTS (SELECT 1 FROM content_unified c WHERE c.id = e.content_id)
    """)['count']
    
    success = (
        remaining_threads == 0 and 
        preserved_messages > 0 and 
        orphan_embeddings == 0
    )
    
    status = "✅" if success else "❌"
    print(f"{status} Email threads remaining: {remaining_threads} (should be 0)")
    print(f"✅ Email messages preserved: {preserved_messages}")
    print(f"✅ Message embeddings: {message_embeddings}")
    print(f"{'✅' if orphan_embeddings == 0 else '❌'} Orphan embeddings: {orphan_embeddings} (should be 0)")
    
    if success:
        print(f"\n🎉 CLEANUP SUCCESSFUL!")
        print(f"   Database now contains {preserved_messages} clean email messages")
        print(f"   No duplicate thread content remaining")
    else:
        print(f"\n❌ CLEANUP VERIFICATION FAILED!")
    
    return success

def main():
    """Execute cleanup with verification."""
    print("🚀 Email Database Cleanup")
    print("Removing duplicate email threads, preserving individual messages")
    print("=" * 60)
    
    # Execute cleanup
    cleanup_success = execute_cleanup()
    
    if cleanup_success:
        # Verify results
        verify_success = verify_cleanup_success()
        return verify_success
    else:
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)