#!/usr/bin/env python3
"""Integration tests for email deduplication system.

Tests the complete flow from raw emails to deduplicated storage.
"""

import sys
import tempfile
import unittest
from datetime import datetime
from pathlib import Path

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))

from email_parsing.message_deduplicator import MessageDeduplicator
from scripts.parse_messages import EmailBatchProcessor
from shared.simple_db import SimpleDB


class TestEmailDeduplicationIntegration(unittest.TestCase):
    """
    Integration tests for email deduplication workflow.
    """

    def setUp(self):
        """
        Create temporary database and test data.
        """
        self.temp_db = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        self.db = SimpleDB(self.temp_db.name)
        self.deduplicator = MessageDeduplicator()

        # Apply the v2.0 schema for testing
        schema_file = Path(__file__).parent.parent / "NEW_SCHEMA_CLEAN.sql"
        if schema_file.exists():
            with open(schema_file) as f:
                schema_sql = f.read()
            # Apply schema
            import sqlite3

            conn = sqlite3.connect(self.temp_db.name)
            conn.executescript(schema_sql)
            conn.close()

        # Create test email directory
        self.temp_dir = tempfile.TemporaryDirectory()
        self.email_dir = Path(self.temp_dir.name)

    def tearDown(self):
        """
        Clean up temporary files.
        """
        Path(self.temp_db.name).unlink(missing_ok=True)
        self.temp_dir.cleanup()

    def test_end_to_end_deduplication(self):
        """
        Test complete workflow from email files to deduplicated database.
        """

        # Create test emails with duplicate content
        email1 = """From: john@example.com
To: alice@example.com
Subject: Project Update
Date: Mon, 15 Jan 2024 10:30:00

Hi Alice,

This is the project update for January.

Best regards,
John"""

        email2 = """From: alice@example.com
To: bob@example.com
Subject: FW: Project Update
Date: Mon, 15 Jan 2024 11:00:00

FYI - forwarding John's update

-------- Forwarded message --------
From: john@example.com
Subject: Project Update
Date: Mon, 15 Jan 2024 10:30:00

Hi Alice,

This is the project update for January.

Best regards,
John"""

        email3 = """From: bob@example.com
To: carol@example.com
Subject: RE: FW: Project Update
Date: Mon, 15 Jan 2024 14:00:00

Thanks for sharing!

> From: alice@example.com
> Date: Mon, 15 Jan 2024 11:00:00
> 
> FYI - forwarding John's update
> 
> -------- Forwarded message --------
> From: john@example.com
> Subject: Project Update
> 
> Hi Alice,
> 
> This is the project update for January.
> 
> Best regards,
> John"""

        # Save test emails
        (self.email_dir / "email_001.txt").write_text(email1)
        (self.email_dir / "email_002.txt").write_text(email2)
        (self.email_dir / "email_003.txt").write_text(email3)

        # Process emails
        processor = EmailBatchProcessor(self.db, str(self.email_dir))
        stats = processor.process_all(resume=False)

        # Verify results
        self.assertEqual(stats["processed_files"], 3, "Should process 3 files")

        # Check unique messages
        unique_count = self.db.fetch_one("SELECT COUNT(*) as count FROM individual_messages")
        self.assertIsNotNone(unique_count)
        # We expect fewer unique messages than total due to deduplication
        self.assertLess(unique_count["count"], 6, "Should have deduplication")

        # Check occurrences tracking
        occurrences = self.db.fetch_one("SELECT COUNT(*) as count FROM message_occurrences")
        self.assertIsNotNone(occurrences)
        self.assertGreaterEqual(occurrences["count"], 3, "Should track all occurrences")

        # Verify content_unified integration
        content_count = self.db.fetch_one(
            "SELECT COUNT(*) as count FROM content_unified WHERE source_type='email_message'"
        )
        self.assertIsNotNone(content_count)
        self.assertEqual(
            content_count["count"],
            unique_count["count"],
            "content_unified should match unique messages",
        )

    def test_duplicate_detection_accuracy(self):
        """
        Test that duplicate detection correctly identifies same content.
        """

        # Create identical messages
        msg1 = "This is a test message with some content."
        msg2 = "This is a test message with some content."
        msg3 = "This is a different message."

        # Generate hashes
        hash1 = self.deduplicator.create_message_hash(msg1, "Test")
        hash2 = self.deduplicator.create_message_hash(msg2, "Test")
        hash3 = self.deduplicator.create_message_hash(msg3, "Test")

        # Verify deduplication logic
        self.assertEqual(hash1, hash2, "Identical messages should have same hash")
        self.assertNotEqual(hash1, hash3, "Different messages should have different hash")

        # Store messages
        self.db.add_individual_message(
            message_hash=hash1, content=msg1, subject="Test", sender_email="test@example.com"
        )

        # Try to add duplicate - should return False
        result = self.db.add_individual_message(
            message_hash=hash2, content=msg2, subject="Test", sender_email="test@example.com"
        )
        self.assertFalse(result, "Duplicate message should not be added")

        # Add different message - should succeed
        result = self.db.add_individual_message(
            message_hash=hash3, content=msg3, subject="Test", sender_email="test@example.com"
        )
        self.assertTrue(result, "Different message should be added")

    def test_thread_reconstruction(self):
        """
        Test that we can reconstruct email threads from deduplicated messages.
        """

        # Create a thread of messages
        thread_id = "thread_test_123"

        # Original message
        self.db.add_individual_message(
            message_hash="hash1",
            content="Original message",
            subject="Test Thread",
            sender_email="john@example.com",
            date_sent=datetime(2024, 1, 15, 10, 0),
            thread_id=thread_id,
            content_type="original",
        )

        # Reply
        self.db.add_individual_message(
            message_hash="hash2",
            content="Reply to original",
            subject="Re: Test Thread",
            sender_email="alice@example.com",
            date_sent=datetime(2024, 1, 15, 11, 0),
            thread_id=thread_id,
            content_type="reply",
        )

        # Forward
        self.db.add_individual_message(
            message_hash="hash3",
            content="Forwarding this thread",
            subject="Fwd: Test Thread",
            sender_email="bob@example.com",
            date_sent=datetime(2024, 1, 15, 12, 0),
            thread_id=thread_id,
            content_type="forward",
        )

        # Retrieve thread
        thread_messages = self.db.get_thread_messages(thread_id)

        self.assertEqual(len(thread_messages), 3, "Should retrieve all thread messages")
        # Verify chronological order
        self.assertEqual(thread_messages[0]["content"], "Original message")
        self.assertEqual(thread_messages[1]["content"], "Reply to original")
        self.assertEqual(thread_messages[2]["content"], "Forwarding this thread")

    def test_foreign_key_integrity(self):
        """
        Test that foreign key constraints maintain data integrity.
        """

        # Add a message
        self.db.add_individual_message(
            message_hash="test_integrity", content="Test message", subject="Test"
        )

        # Add occurrence
        self.db.add_message_occurrence(
            message_hash="test_integrity", email_id="email_001", position_in_email=0
        )

        # Try to add occurrence for non-existent message (should fail)
        with self.assertRaises(Exception):
            self.db.execute("PRAGMA foreign_keys=ON")
            self.db.add_message_occurrence(
                message_hash="non_existent", email_id="email_002", position_in_email=0
            )

        # Delete message (should cascade delete occurrences)
        self.db.execute("DELETE FROM individual_messages WHERE message_hash=?", ("test_integrity",))

        # Verify cascade deletion
        occurrences = self.db.fetch_one(
            "SELECT COUNT(*) as count FROM message_occurrences WHERE message_hash=?",
            ("test_integrity",),
        )
        self.assertEqual(occurrences["count"], 0, "Occurrences should be cascade deleted")


if __name__ == "__main__":
    unittest.main()
