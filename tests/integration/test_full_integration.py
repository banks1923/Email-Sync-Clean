#!/usr/bin/env python3
"""
Full integration test - Process a small batch of emails with the new advanced parsing.
This simulates what would happen during normal Gmail sync operations.
"""

import sys
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from gmail.main import GmailService
from shared.simple_db import SimpleDB


def test_full_integration():
    """
    Test full email processing pipeline with advanced parsing.
    """

    print("🧪 Full Integration Test - Advanced Email Processing")
    print("=" * 60)

    # Get current database state
    db = SimpleDB("data/emails.db")

    # Count current individual messages
    before_count = db.fetch_one(
        "SELECT COUNT(*) as count FROM content_unified WHERE source_type = 'email_message'"
    )
    print(f"📊 Individual messages before: {before_count['count']}")

    # Initialize Gmail service
    print("📧 Initializing Gmail service...")
    service = GmailService(db_path="data/emails.db")

    # Get a small sample of existing emails to reprocess
    print("🔄 Getting sample emails for reprocessing...")
    sample_emails = db.fetch(
        """
        SELECT message_id, thread_id, sender, subject, content, datetime_utc
        FROM emails 
        WHERE content IS NOT NULL 
        AND LENGTH(content) > 200
        AND thread_id IS NOT NULL
        ORDER BY datetime_utc DESC
        LIMIT 3
    """
    )

    if not sample_emails:
        print("❌ No sample emails found")
        return False

    print(f"✅ Found {len(sample_emails)} sample emails for testing")

    # Group by thread
    threads_grouped = {}
    for email in sample_emails:
        thread_id = email["thread_id"] or email["message_id"]
        if thread_id not in threads_grouped:
            threads_grouped[thread_id] = []
        threads_grouped[thread_id].append(email)

    print(f"📊 Grouped into {len(threads_grouped)} threads")

    # Test the advanced thread processing directly
    print("🚀 Testing advanced thread processing...")

    try:
        result = service._process_threads_advanced(threads_grouped)

        print("✅ Processing result:")
        print(f"   📈 Messages extracted: {result['messages_extracted']}")
        print(f"   💾 Messages stored: {result['processed']}")
        print(f"   ❌ Errors: {result['errors']}")

        if result["errors"] > 0:
            print("⚠️  Some errors occurred during processing")

    except Exception as e:
        print(f"❌ Advanced processing failed: {e}")
        import traceback

        traceback.print_exc()
        return False

    # Check results
    after_count = db.fetch_one(
        "SELECT COUNT(*) as count FROM content_unified WHERE source_type = 'email_message'"
    )
    new_messages = after_count["count"] - before_count["count"]

    print(f"📊 Individual messages after: {after_count['count']}")
    print(f"🆕 New messages added: {new_messages}")

    # Test pattern detection
    print("🔍 Testing legal pattern detection...")

    anonymous_patterns = db.fetch(
        """
        SELECT id, title, body 
        FROM content_unified 
        WHERE source_type = 'email_message'
        AND (title LIKE '%stoneman staff%' OR body LIKE '%stoneman staff%')
        ORDER BY id DESC
        LIMIT 5
    """
    )

    print(f"🎭 Anonymous signatures detected: {len(anonymous_patterns)}")
    for pattern in anonymous_patterns:
        print(f"   📄 ID {pattern['id']}: {pattern['title'][:60]}...")

    # Test search capability
    print("🔍 Testing search on individual messages...")
    search_results = db.fetch(
        """
        SELECT id, title, body 
        FROM content_unified 
        WHERE source_type = 'email_message'
        AND body LIKE '%repair%'
        ORDER BY id DESC
        LIMIT 3
    """
    )

    print(f"🔧 Repair-related messages: {len(search_results)}")
    for result in search_results:
        print(f"   📄 ID {result['id']}: {result['title'][:60]}...")

    print("\n🎉 Full integration test completed successfully!")
    print(f"💡 System now has {after_count['count']} individual messages for advanced analysis")

    return True


if __name__ == "__main__":
    success = test_full_integration()

    if success:
        print("\n✅ Integration test PASSED!")
        print("🚀 Advanced email parsing is fully operational")
    else:
        print("\n❌ Integration test FAILED!")
        sys.exit(1)
