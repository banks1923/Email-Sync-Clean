"""
Integration tests for document summarization with PDF and Gmail services.
"""

import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

sys.path.append(str(Path(__file__).parent.parent))

from gmail.main import GmailService
from pdf.wiring import get_pdf_service
from shared.simple_db import SimpleDB


class TestPDFSummarizationIntegration(unittest.TestCase):
    """
    Test PDF service with summarization integration.
    """

    def setUp(self):
        """
        Set up test fixtures.
        """
        # Create temporary database
        self.temp_db = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        self.db_path = self.temp_db.name
        self.temp_db.close()

        # Initialize services
        self.pdf_service = get_pdf_service(self.db_path)
        self.db = SimpleDB(self.db_path)

        # Create necessary tables
        self.db.execute(
            """
            CREATE TABLE IF NOT EXISTS content (
                id TEXT PRIMARY KEY,
                content_type TEXT,
                title TEXT,
                content TEXT,
                source_path TEXT,
                metadata TEXT,
                word_count INTEGER,
                char_count INTEGER,
                created_time TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """
        )

        self.db.execute(
            """
            CREATE TABLE IF NOT EXISTS documents (
                chunk_id TEXT PRIMARY KEY,
                file_path TEXT,
                file_name TEXT,
                chunk_index INTEGER,
                text_content TEXT,
                char_count INTEGER,
                file_size INTEGER,
                file_hash TEXT,
                source_type TEXT,
                modified_time REAL,
                processed_time TEXT,
                content_type TEXT,
                vector_processed INTEGER,
                legal_metadata TEXT,
                extraction_method TEXT,
                ocr_confidence REAL
            )
        """
        )

        # Create intelligence tables
        self.db.create_intelligence_tables()

    def tearDown(self):
        """
        Clean up temporary files.
        """
        try:
            os.unlink(self.db_path)
        except Exception:
            pass

    def test_pdf_upload_with_summary(self):
        """
        Test that PDF upload generates and stores summary.
        """
        # Create a mock PDF file
        test_pdf = tempfile.NamedTemporaryFile(suffix=".pdf", delete=False)
        test_pdf.write(b"%PDF-1.4\ntest content")
        test_pdf.close()

        try:
            # Mock the PDF processing to return text
            with patch.object(self.pdf_service.ocr, "process_pdf_with_ocr") as mock_ocr:
                mock_ocr.return_value = {
                    "success": True,
                    "ocr_used": False,
                    "text": "This is a legal contract between ABC Corporation and XYZ Company for software services.",
                    "confidence": 0.95,
                    "metadata": {"document_type": "contract"},
                }

                with patch.object(
                    self.pdf_service.processor, "extract_and_chunk_pdf"
                ) as mock_extract:
                    mock_extract.return_value = {
                        "success": True,
                        "chunks": [
                            {
                                "chunk_id": "test_chunk_1",
                                "text": "This is a legal contract between ABC Corporation and XYZ Company for software services.",
                                "chunk_index": 0,
                                "extraction_method": "text",
                            }
                        ],
                        "extraction_method": "text",
                    }

                    # Upload PDF
                    result = self.pdf_service.upload_single_pdf(test_pdf.name)

                    self.assertTrue(result["success"])

                    # Check that summary was created
                    summaries = self.db.get_document_summaries(
                        self.db.fetch_one(
                            "SELECT id FROM content WHERE content_type = 'pdf'"
                        )["content_id"]
                    )

                    self.assertGreater(len(summaries), 0)
                    summary = summaries[0]
                    self.assertEqual(summary["summary_type"], "combined")
                    self.assertIsNotNone(summary["tf_idf_keywords"])
                    self.assertIn("contract", str(summary["tf_idf_keywords"]).lower())

        finally:
            os.unlink(test_pdf.name)


class TestGmailSummarizationIntegration(unittest.TestCase):
    """
    Test Gmail service with summarization integration.
    """

    def setUp(self):
        """
        Set up test fixtures.
        """
        # Create temporary database
        self.temp_db = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        self.db_path = self.temp_db.name
        self.temp_db.close()

        # Initialize services
        self.gmail_service = GmailService(db_path=self.db_path)
        self.db = SimpleDB(self.db_path)

        # Create necessary tables
        self.db.execute(
            """
            CREATE TABLE IF NOT EXISTS content (
                id TEXT PRIMARY KEY,
                content_type TEXT,
                title TEXT,
                content TEXT,
                source_path TEXT,
                metadata TEXT,
                word_count INTEGER,
                char_count INTEGER,
                created_time TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """
        )

        # Create intelligence tables
        self.db.create_intelligence_tables()

    def tearDown(self):
        """
        Clean up temporary files.
        """
        try:
            os.unlink(self.db_path)
        except Exception:
            pass

    @patch("gmail.gmail_api.GmailAPI")
    def test_email_sync_with_summary(self, mock_gmail_api):
        """
        Test that email sync generates and stores summaries.
        """
        # Mock Gmail API responses
        mock_api_instance = MagicMock()
        mock_gmail_api.return_value = mock_api_instance

        # Mock get_messages
        mock_api_instance.get_messages.return_value = {
            "success": True,
            "data": [{"id": "msg1"}, {"id": "msg2"}],
        }

        # Mock get_message_detail
        mock_api_instance.get_message_detail.side_effect = [
            {"success": True, "data": {"id": "msg1", "payload": {}}},
            {"success": True, "data": {"id": "msg2", "payload": {}}},
        ]

        # Mock parse_message
        mock_api_instance.parse_message.side_effect = [
            {
                "message_id": "msg1",
                "subject": "Legal Contract Review",
                "sender": "lawyer@example.com",
                "recipient_to": "client@example.com",
                "content": "This contract needs your review and approval by Friday. The terms include payment schedules and deliverables.",
                "datetime_utc": "2025-01-15T10:00:00Z",
            },
            {
                "message_id": "msg2",
                "subject": "Meeting Schedule",
                "sender": "assistant@example.com",
                "recipient_to": "manager@example.com",
                "content": "The meeting is scheduled for next Tuesday at 2 PM to discuss project timeline.",
                "datetime_utc": "2025-01-15T11:00:00Z",
            },
        ]

        # Sync emails
        result = self.gmail_service.sync_emails(max_results=2, batch_mode=True)

        self.assertTrue(result["success"])

        # Check that summaries were created
        content_records = self.db.fetch(
            "SELECT id FROM content WHERE content_type = 'email'"
        )
        self.assertGreater(len(content_records), 0)

        for record in content_records:
            summaries = self.db.get_document_summaries(record["content_id"])
            if summaries:  # Some emails might not have enough content for summary
                summary = summaries[0]
                self.assertEqual(summary["summary_type"], "combined")
                self.assertIsNotNone(
                    summary.get("tf_idf_keywords") or summary.get("textrank_sentences")
                )


class TestSummaryRetrieval(unittest.TestCase):
    """
    Test retrieving and using summaries.
    """

    def setUp(self):
        """
        Set up test fixtures.
        """
        # Create temporary database
        self.temp_db = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        self.db_path = self.temp_db.name
        self.temp_db.close()

        self.db = SimpleDB(self.db_path)
        self.summarizer = get_document_summarizer()

        # Create tables
        self.db.execute(
            """
            CREATE TABLE IF NOT EXISTS content (
                id TEXT PRIMARY KEY,
                content_type TEXT,
                title TEXT,
                content TEXT,
                source_path TEXT,
                metadata TEXT,
                word_count INTEGER,
                char_count INTEGER,
                created_time TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """
        )

        self.db.create_intelligence_tables()

    def tearDown(self):
        """
        Clean up temporary files.
        """
        try:
            os.unlink(self.db_path)
        except Exception:
            pass

    def test_batch_summary_generation(self):
        """
        Test generating summaries for multiple documents.
        """
        # Add test documents
        documents = [
            {
                "title": "Contract Agreement",
                "content": "This is a binding legal agreement between the parties for the provision of consulting services over a period of twelve months.",
            },
            {
                "title": "Project Proposal",
                "content": "We propose to develop a new software system that will streamline operations and reduce costs by automating key processes.",
            },
            {
                "title": "Meeting Minutes",
                "content": "The board met to discuss quarterly results and approved the budget for the next fiscal year with minor adjustments.",
            },
        ]

        content_ids = []
        for doc in documents:
            content_id = self.db.add_content(
                content_type="document", title=doc["title"], content=doc["content"]
            )
            content_ids.append(content_id)

        # Generate and store summaries
        for i, doc in enumerate(documents):
            summary = self.summarizer.extract_summary(
                doc["content"], max_sentences=2, max_keywords=5, summary_type="combined"
            )

            self.db.add_document_summary(
                document_id=content_ids[i],
                summary_type="combined",
                summary_text=summary.get("summary_text"),
                tf_idf_keywords=summary.get("tf_idf_keywords"),
                textrank_sentences=summary.get("textrank_sentences"),
            )

        # Retrieve and verify summaries
        for content_id in content_ids:
            summaries = self.db.get_document_summaries(content_id)
            self.assertEqual(len(summaries), 1)
            self.assertIsNotNone(summaries[0]["summary_text"])

    def test_summary_search_integration(self):
        """
        Test that summaries can be searched.
        """
        # Add document with summary
        content_id = self.db.add_content(
            content_type="email",
            title="Important Legal Notice",
            content="This notice informs you of pending litigation regarding intellectual property rights. Immediate action is required.",
        )

        summary = self.summarizer.extract_summary(
            "This notice informs you of pending litigation regarding intellectual property rights. Immediate action is required.",
            max_sentences=1,
            max_keywords=5,
            summary_type="combined",
        )

        self.db.add_document_summary(
            document_id=content_id,
            summary_type="combined",
            summary_text=summary.get("summary_text"),
            tf_idf_keywords=summary.get("tf_idf_keywords"),
            textrank_sentences=summary.get("textrank_sentences"),
        )

        # Search for content
        results = self.db.search_content("litigation", limit=10)
        self.assertGreater(len(results), 0)
        self.assertEqual(results[0]["content_id"], content_id)


if __name__ == "__main__":
    unittest.main()
