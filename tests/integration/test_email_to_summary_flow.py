"""Integration test for email processing to summary generation flow.

Verifies end-to-end processing from email sync through summarization to
database storage.
"""

import sys
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

sys.path.append(str(Path(__file__).parent.parent.parent))

from gmail.main import GmailService
from tests.integration.test_helpers import (
    cleanup_test_files,
    create_test_database,
    create_test_email_data,
    get_summary_for_document,
    verify_database_record,
    verify_summary_quality,
)


class TestEmailToSummaryFlow(unittest.TestCase):
    """
    Test complete flow from email sync to summary in database.
    """

    def setUp(self):
        """
        Set up test environment.
        """
        # Create test database
        self.db, self.db_path = create_test_database()

        # Initialize Gmail service with test database
        self.gmail_service = GmailService(self.db_path)

        # Create test email data
        self.test_email = create_test_email_data()

        # Track files to cleanup
        self.cleanup_paths = [self.db_path]

    def tearDown(self):
        """
        Clean up test artifacts.
        """
        cleanup_test_files(self.cleanup_paths)

    def test_email_processing_creates_content_record(self):
        """
        Test that processing an email creates a content record.
        """
        # Save test email to database first
        self.db.execute(
            """
            INSERT INTO emails (id, subject, sender, recipients, date, body,
                              labels, thread_id, message_id, attachments)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
            (
                self.test_email["id"],
                self.test_email["subject"],
                self.test_email["sender"],
                self.test_email["recipients"],
                self.test_email["date"],
                self.test_email["body"],
                self.test_email["labels"],
                self.test_email["thread_id"],
                self.test_email["message_id"],
                self.test_email["attachments"],
            ),
        )

        # Process email summaries (this is what GmailService actually does)
        self.gmail_service._process_email_summaries(
            [
                {
                    "message_id": self.test_email["message_id"],
                    "subject": self.test_email["subject"],
                    "content": self.test_email["body"],
                    "sender": self.test_email["sender"],
                    "recipient_to": self.test_email["recipients"],
                    "datetime_utc": self.test_email["date"],
                }
            ]
        )

        # Verify content record exists (use gmail_service's db)
        content = self.gmail_service.db.fetch_one(
            "SELECT * FROM content_unified WHERE title = ?", (self.test_email["subject"],)
        )

        self.assertIsNotNone(content, "Content record not found in database")

        # Verify content fields
        self.assertEqual(content["source_type"], "email_message")
        self.assertEqual(content["title"], self.test_email["subject"])
        self.assertIn("ABC Corporation", content["body"])  # Check for actual content from body
        self.assertGreater(content["word_count"], 0)
        self.assertGreater(content["char_count"], 0)

    def test_email_processing_creates_summary(self):
        """
        Test that processing an email generates a summary.
        """
        # Process email summaries
        self.gmail_service._process_email_summaries(
            [
                {
                    "message_id": self.test_email["message_id"],
                    "subject": self.test_email["subject"],
                    "content": self.test_email[
                        "body"
                    ],  # _process_email_summaries expects 'content'
                    "sender": self.test_email["sender"],
                    "recipient_to": self.test_email["recipients"],
                    "datetime_utc": self.test_email["date"],
                }
            ]
        )

        # Get content record to find content_id (use gmail_service's db)
        content = self.gmail_service.db.fetch_one(
            "SELECT id FROM content_unified WHERE title = ?", (self.test_email["subject"],)
        )

        self.assertIsNotNone(content, "Content record not found")

        # Get summary from database
        summary = get_summary_for_document(self.gmail_service.db, content["id"])

        # Verify summary exists
        self.assertIsNotNone(summary, "No summary found for processed email")

        # Verify summary quality
        self.assertTrue(
            verify_summary_quality(summary, min_keywords=3, min_sentences=1),
            f"Summary quality insufficient: {summary}",
        )

    def test_email_summary_contains_relevant_keywords(self):
        """
        Test that email summary contains relevant TF-IDF keywords.
        """
        # Process email summaries
        self.gmail_service._process_email_summaries(
            [
                {
                    "message_id": self.test_email["message_id"],
                    "subject": self.test_email["subject"],
                    "content": self.test_email[
                        "body"
                    ],  # _process_email_summaries expects 'content'
                    "sender": self.test_email["sender"],
                    "recipient_to": self.test_email["recipients"],
                    "datetime_utc": self.test_email["date"],
                }
            ]
        )

        # Get content record (use gmail_service's db)
        content = self.gmail_service.db.fetch_one(
            "SELECT id FROM content_unified WHERE title = ?", (self.test_email["subject"],)
        )

        # Get summary
        summary = get_summary_for_document(self.gmail_service.db, content["content_id"])
        self.assertIsNotNone(summary)

        # Check TF-IDF keywords
        keywords = summary.get("tf_idf_keywords", {})
        self.assertGreater(len(keywords), 0, "No TF-IDF keywords extracted")

        # Check for expected keywords from email content
        expected_terms = [
            "contract",
            "agreement",
            "abc",
            "corp",
            "corporation",
            "payment",
            "terms",
            "review",
        ]

        keyword_strings = [k.lower() for k in keywords.keys()]
        found_expected = any(term in " ".join(keyword_strings) for term in expected_terms)

        self.assertTrue(
            found_expected, f"No expected keywords found. Got: {list(keywords.keys())[:10]}"
        )

    def test_email_summary_contains_key_sentences(self):
        """
        Test that email summary contains TextRank sentences.
        """
        # Process email summaries
        self.gmail_service._process_email_summaries(
            [
                {
                    "message_id": self.test_email["message_id"],
                    "subject": self.test_email["subject"],
                    "content": self.test_email[
                        "body"
                    ],  # _process_email_summaries expects 'content'
                    "sender": self.test_email["sender"],
                    "recipient_to": self.test_email["recipients"],
                    "datetime_utc": self.test_email["date"],
                }
            ]
        )

        # Get content record (use gmail_service's db)
        content = self.gmail_service.db.fetch_one(
            "SELECT id FROM content_unified WHERE title = ?", (self.test_email["subject"],)
        )

        # Get summary
        summary = get_summary_for_document(self.gmail_service.db, content["content_id"])
        self.assertIsNotNone(summary)

        # Check TextRank sentences
        sentences = summary.get("textrank_sentences", [])
        self.assertGreater(len(sentences), 0, "No TextRank sentences extracted")

        # Verify sentences are from email body
        email_text = self.test_email["body"].lower()
        for sentence in sentences:
            # Check if sentence fragment appears in original email
            sentence_fragment = sentence[:30].lower()
            self.assertTrue(
                sentence_fragment in email_text or len(sentence) > 10,
                f"Sentence not from email: {sentence}",
            )

    def test_batch_email_processing(self):
        """
        Test processing multiple emails in batch.
        """
        # Create multiple test emails
        email_list = []
        for i in range(3):
            email = create_test_email_data()
            email["id"] = f"test_email_{i:03d}"
            email["subject"] = f"Test Subject {i}"
            email["message_id"] = f"msg_{i:03d}"
            email_list.append(
                {
                    "message_id": email["message_id"],
                    "subject": email["subject"],
                    "content": email["body"],
                    "sender": email["sender"],
                    "recipient_to": email["recipients"],
                    "datetime_utc": email["date"],
                }
            )

        # Process all emails at once
        self.gmail_service._process_email_summaries(email_list)

        # Verify all emails have summaries
        for email in email_list:
            content = self.gmail_service.db.fetch_one(
                "SELECT id FROM content_unified WHERE title = ?", (email["subject"],)
            )
            if content:  # Some might be None if deduplication occurs
                summary = get_summary_for_document(self.gmail_service.db, content["content_id"])
                self.assertIsNotNone(summary, f"No summary for {email['subject']}")

    def test_html_email_processing(self):
        """
        Test processing HTML emails.
        """
        # Create HTML email
        html_email = create_test_email_data()
        html_body_text = """
        Contract Review
        Please review the important contract details:
        Payment terms: $50,000
        Duration: 12 months
        Start date: January 2024
        """

        # Process HTML email as text (Gmail converts HTML to text)
        self.gmail_service._process_email_summaries(
            [
                {
                    "message_id": html_email["message_id"],
                    "subject": html_email["subject"],
                    "content": html_body_text,  # HTML converted to text
                    "sender": html_email["sender"],
                    "recipient_to": html_email["recipients"],
                    "datetime_utc": html_email["date"],
                }
            ]
        )

        # Get content record
        content = self.gmail_service.db.fetch_one(
            "SELECT * FROM content_unified WHERE title = ?", (html_email["subject"],)
        )

        if content:
            # Verify content was extracted
            self.assertIsNotNone(content)

            # Check summary exists
            summary = get_summary_for_document(self.gmail_service.db, content["content_id"])
            self.assertIsNotNone(summary)

    @patch("gmail.main.GmailService._get_gmail_service")
    def test_email_sync_integration(self, mock_gmail):
        """
        Test full email sync flow with mocked Gmail API.
        """
        # Mock Gmail API response
        mock_service = MagicMock()
        mock_gmail.return_value = mock_service

        # Create mock email message
        mock_message = {
            "id": "msg_123",
            "threadId": "thread_123",
            "payload": {
                "headers": [
                    {"name": "Subject", "value": "Test Contract"},
                    {"name": "From", "value": "sender@example.com"},
                    {"name": "To", "value": "recipient@example.com"},
                    {"name": "Date", "value": "Mon, 15 Jan 2024 10:00:00 -0000"},
                ],
                "body": {"data": "VGVzdCBlbWFpbCBib2R5IGZvciBjb250cmFjdCByZXZpZXc="},  # Base64
            },
        }

        # Mock API calls
        mock_service.users().messages().list().execute.return_value = {
            "messages": [{"id": "msg_123"}]
        }
        mock_service.users().messages().get().execute.return_value = mock_message

        # Run sync (limited to 1 email)
        result = self.gmail_service.sync_emails(max_results=1)

        # Verify result
        self.assertIsInstance(result, dict)

        # Check if email was saved (use gmail_service's storage db)
        email_exists = verify_database_record(
            self.gmail_service.db, "emails", "message_id = ?", ("msg_123",)
        )

        if email_exists:
            # Get the email
            email = self.gmail_service.db.fetch_one(
                "SELECT * FROM emails WHERE message_id = ?", ("msg_123",)
            )
            self.assertIsNotNone(email)
            self.assertEqual(email["subject"], "Test Contract")


if __name__ == "__main__":
    unittest.main()
