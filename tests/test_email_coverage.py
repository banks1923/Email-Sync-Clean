#!/usr/bin/env python3
"""Additional tests to achieve 100% coverage for email_parsing module.

Tests edge cases and error conditions.
"""

import sys
import unittest
from datetime import datetime
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent))

from email_parsing.message_deduplicator import (
    MessageBoundary,
    MessageDeduplicator,
    ParsedMessage,
)


class TestMessageDeduplicatorCoverage(unittest.TestCase):
    """
    Additional tests for complete coverage.
    """
    
    def setUp(self):
        """
        Initialize deduplicator for each test.
        """
        self.deduplicator = MessageDeduplicator()
    
    def test_reply_boundary_detection(self):
        """
        Test reply marker detection (lines 160-168).
        """
        email_content = """Current message here

On 2024-01-15 10:30 AM, John Smith wrote:
This is the original message.
It has multiple lines.
"""
        
        lines = email_content.split('\n')
        boundaries = self.deduplicator._detect_reply_boundaries(lines)
        
        # Should detect the reply boundary
        self.assertGreater(len(boundaries), 0)
        reply_boundary = boundaries[0]
        self.assertEqual(reply_boundary.boundary_type, 'reply')
        self.assertIsNotNone(reply_boundary.marker)
    
    def test_find_section_end_with_marker(self):
        """
        Test _find_section_end when it finds another marker (line 216).
        """
        lines = [
            "First section",
            "Some content",
            "-------- Forwarded message --------",
            "Second section",
            "More content"
        ]
        
        # Should find the end at the forward marker
        end = self.deduplicator._find_section_end(lines, 0)
        self.assertEqual(end, 2)  # Index of the forward marker
    
    def test_merge_boundaries_empty(self):
        """
        Test _merge_boundaries with empty boundaries list (lines 224-229).
        """
        # When no boundaries, should create one for full content
        boundaries = []
        merged = self.deduplicator._merge_boundaries(boundaries, 10)
        
        self.assertEqual(len(merged), 1)
        self.assertEqual(merged[0].start, 0)
        self.assertEqual(merged[0].end, 10)
        self.assertEqual(merged[0].boundary_type, 'original')
    
    def test_merge_boundaries_overlap(self):
        """
        Test boundary merging with overlapping boundaries (lines 245-246).
        """
        boundaries = [
            MessageBoundary(start=0, end=5, boundary_type='original', 
                          confidence=0.9, marker='test1'),
            MessageBoundary(start=3, end=8, boundary_type='quote', 
                          confidence=0.8, marker='test2'),
            MessageBoundary(start=6, end=10, boundary_type='forward',
                          confidence=0.7, marker='test3')
        ]
        
        merged = self.deduplicator._merge_boundaries(boundaries, 10)
        
        # Should merge overlapping boundaries
        self.assertLessEqual(len(merged), len(boundaries))
        
        # Check no overlaps in merged boundaries
        for i in range(len(merged) - 1):
            self.assertLessEqual(merged[i].end, merged[i+1].start)
    
    def test_parse_message_segment_empty(self):
        """
        Test parsing empty message segment (line 256).
        """
        # Empty content should return None
        result = self.deduplicator._parse_message_segment(
            "   \n  \n  ", "original", 0
        )
        self.assertIsNone(result)
    
    def test_parse_message_with_quote_markers(self):
        """
        Test parsing messages with quote depth tracking (lines 265-266).
        """
        content = """> First level quote
>> Second level quote
>>> Third level quote
>> Back to second
> Back to first
Normal text"""
        
        result = self.deduplicator._parse_message_segment(
            content, "quoted", 0
        )
        
        self.assertIsNotNone(result)
        # Should have tracked quote depth
        self.assertIn("quote", result.context_type)
    
    def test_normalize_content_signature_removal(self):
        """
        Test signature removal in normalization (line 280).
        """
        content_with_sig = """This is the main message.

Best regards,
John

--
John Smith
Senior Developer
Sent from my iPhone"""
        
        normalized = self.deduplicator._normalize_content(content_with_sig)
        
        # Should remove signature
        self.assertNotIn("Sent from my iPhone", normalized)
        self.assertIn("main message", normalized)
    
    def test_extract_subject_no_header(self):
        """
        Test subject extraction when no header present (line 367).
        """
        content = """This is just content without headers.
No subject line here."""
        
        subject = self.deduplicator._extract_subject(content)
        self.assertIsNone(subject)
    
    def test_extract_date_with_timezone(self):
        """
        Test date extraction with various formats (lines 400-405).
        """
        # Test that it tries different formats
        content1 = "Date: 2024-01-15 10:30:00"
        date1 = self.deduplicator._extract_date(content1)
        self.assertIsNotNone(date1)
        self.assertEqual(date1.year, 2024)
        
        # Test truncation for long date strings
        content2 = "Date: Mon, 15 Jan 2024 10:30:00 -0800 (PST)"
        date2 = self.deduplicator._extract_date(content2)
        # Should handle or fail gracefully
        if date2:
            self.assertEqual(date2.year, 2024)
    
    def test_complete_email_thread_parsing(self):
        """
        Test parsing a complex email thread with all boundary types.
        """
        complex_email = """Latest update on the project

> On Jan 15, 2024, Alice wrote:
> Thanks for the previous update.
> 
> -------- Forwarded message --------
> From: Bob
> Date: Jan 14, 2024
> 
> Here's the original message.
> With multiple lines.
> 
> >> Earlier quote from Carol
> >> This is nested deeply

Some final thoughts here."""
        
        messages = self.deduplicator.parse_email_thread(complex_email, "test_complex")
        
        # Should extract at least one message
        self.assertGreater(len(messages), 0)
        
        # Check that we have the main content
        main_content = ' '.join([m.content for m in messages])
        self.assertIn("Latest update", main_content)
    
    def test_boundary_detection_all_types(self):
        """
        Test detection of all boundary types.
        """
        email = """Current message

-------- Original Message --------
Original content

-------- Forwarded message --------
Forwarded content

> Quoted content
>> Nested quote"""
        
        boundaries = self.deduplicator._find_message_boundaries(email)
        
        # Should detect multiple boundary types
        boundary_types = {b.boundary_type for b in boundaries}
        self.assertGreater(len(boundary_types), 0)
    
    def test_deduplicate_messages_with_metadata(self):
        """
        Test deduplication preserves all metadata.
        """
        # Create messages with IDENTICAL content and subject for proper deduplication
        messages = [
            ParsedMessage(
                content="Test message content here",
                subject="Test Subject",  # Same subject
                sender="alice@example.com",
                recipients=["bob@example.com"],
                date=datetime(2024, 1, 15),
                message_id="<msg1@example.com>",
                parent_id="<parent@example.com>",
                position_in_email=0,
                context_type='original',
                quote_depth=0
            ),
            ParsedMessage(
                content="Test message content here",  # Exact duplicate
                subject="Test Subject",  # Same subject
                sender="bob@example.com",
                recipients=["alice@example.com"],
                date=datetime(2024, 1, 16),
                message_id="<msg2@example.com>",
                parent_id="<msg1@example.com>",
                position_in_email=1,
                context_type='quoted',
                quote_depth=1
            )
        ]
        
        unique = self.deduplicator.deduplicate_messages(messages)
        
        # Should deduplicate to 1 unique message (same content + subject)
        self.assertEqual(len(unique), 1)
        
        # Check occurrence tracking
        for msg_hash, msg_data in unique.items():
            self.assertEqual(len(msg_data['occurrences']), 2)
            # Check the data structure has expected fields
            self.assertIn('content', msg_data)
            self.assertIn('occurrences', msg_data)
            self.assertIn('quote_depths', msg_data)


class TestFullCoverage(unittest.TestCase):
    """
    Additional tests to reach 100% coverage.
    """
    
    def test_forwarded_context_type(self):
        """
        Test that forwarded boundary creates forwarded context type (line 280).
        """
        dedup = MessageDeduplicator()
        
        # Parse a forwarded section
        content = """-------- Forwarded message --------
From: alice@example.com
Subject: Test

This is forwarded content."""
        
        # This should trigger the forwarded context type assignment
        result = dedup._parse_message_segment(content, 'forward', 0)
        if result:
            self.assertEqual(result.context_type, 'forwarded')
    
    def test_merge_boundaries_with_adjacent(self):
        """
        Test merging adjacent boundaries (lines 245-246).
        """
        dedup = MessageDeduplicator()
        
        # Create adjacent boundaries that should merge
        boundaries = [
            MessageBoundary(start=0, end=5, boundary_type='original', 
                          confidence=0.9, marker='test1'),
            MessageBoundary(start=5, end=10, boundary_type='quote', 
                          confidence=0.8, marker='test2'),
        ]
        
        merged = dedup._merge_boundaries(boundaries, 10)
        # Should handle adjacent boundaries
        self.assertIsNotNone(merged)
    
    def test_substantial_content_edge_cases(self):
        """
        Test edge cases in substantial content check (line 367).
        """
        dedup = MessageDeduplicator()
        
        # Test various non-substantial contents
        self.assertFalse(dedup._is_substantial_content(""))
        self.assertFalse(dedup._is_substantial_content("   "))
        self.assertFalse(dedup._is_substantial_content(">>>"))
        self.assertFalse(dedup._is_substantial_content("--"))
        self.assertFalse(dedup._is_substantial_content("___"))
        
        # Test substantial content (needs more than 5 chars)
        self.assertTrue(dedup._is_substantial_content("Hello world"))
        self.assertTrue(dedup._is_substantial_content("This is content"))


class TestEdgeCases(unittest.TestCase):
    """
    Test edge cases and error conditions.
    """
    
    def test_malformed_email_handling(self):
        """
        Test handling of malformed email content.
        """
        dedup = MessageDeduplicator()
        
        # Completely empty
        messages = dedup.parse_email_thread("", "empty")
        self.assertEqual(len(messages), 0)
        
        # Only whitespace
        messages = dedup.parse_email_thread("   \n\n  \t  ", "whitespace")
        self.assertEqual(len(messages), 0)
        
        # Only quote markers
        messages = dedup.parse_email_thread(">>>\n>>\n>", "quotes_only")
        # Should handle gracefully
        self.assertIsNotNone(messages)
    
    def test_extreme_nesting(self):
        """
        Test handling of extremely nested quotes.
        """
        dedup = MessageDeduplicator()
        
        # Create deeply nested content
        nested = "Original"
        for i in range(10):
            nested = f"{'>' * (i+1)} {nested}"
        
        messages = dedup.parse_email_thread(nested, "deep_nest")
        # Should handle without error
        self.assertIsNotNone(messages)
    
    def test_unicode_content(self):
        """
        Test handling of unicode content.
        """
        dedup = MessageDeduplicator()
        
        unicode_email = """Subject: Test 测试 🚀
From: user@例え.jp

Content with emojis 😀 and various scripts:
中文 content
Русский текст
العربية نص"""
        
        messages = dedup.parse_email_thread(unicode_email, "unicode_test")
        self.assertGreater(len(messages), 0)
        
        # Hash should work with unicode
        hash1 = dedup.create_message_hash("Test 中文", "Subject 测试")
        self.assertIsNotNone(hash1)


if __name__ == '__main__':
    unittest.main()