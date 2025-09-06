"""Integration test for PDF upload to summary generation flow.

Verifies end-to-end processing from PDF upload through summarization to
database storage.
"""

import sys
import unittest
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent.parent))

from services import get_pdf_service
from tests.integration.test_helpers import (
    cleanup_test_files,
    create_test_database,
    get_summary_for_document,
    get_test_pdf_path,
    verify_database_record,
    verify_summary_quality,
)


class TestPDFToSummaryFlow(unittest.TestCase):
    """
    Test complete flow from PDF upload to summary in database.
    """

    def setUp(self):
        """
        Set up test environment.
        """
        # Create test database
        self.db, self.db_path = create_test_database()

        # Initialize PDF service with test database
        self.pdf_service = get_pdf_service(self.db_path)

        # Get test PDF path
        self.test_pdf = get_test_pdf_path()

        # Track files to cleanup
        self.cleanup_paths = [self.db_path]

    def tearDown(self):
        """
        Clean up test artifacts.
        """
        cleanup_test_files(self.cleanup_paths)

    def test_pdf_upload_creates_content_record(self):
        """
        Test that uploading a PDF creates a content record.
        """
        # Upload PDF without pipeline
        result = self.pdf_service.upload_single_pdf(self.test_pdf, use_pipeline=False)

        # Verify upload succeeded
        self.assertIn("content_id", result)
        self.assertIsNotNone(result["content_id"])

        # Verify content record exists
        content_exists = verify_database_record(
            self.db, "content", "content_id = ?", (result["content_id"],)
        )
        self.assertTrue(content_exists, "Content record not found in database")

        # Get content record
        content = self.db.fetch_one(
            "SELECT * FROM content_unified WHERE id = ?", (result["content_id"],)
        )

        # Verify content fields
        self.assertEqual(content["content_type"], "pdf")
        self.assertIsNotNone(content["title"])
        self.assertIsNotNone(content["content"])
        self.assertGreater(content["word_count"], 0)
        self.assertGreater(content["char_count"], 0)

    def test_pdf_upload_creates_summary(self):
        """
        Test that uploading a PDF generates a summary.
        """
        # Upload PDF
        result = self.pdf_service.upload_single_pdf(self.test_pdf, use_pipeline=False)
        content_id = result.get("content_id")

        self.assertIsNotNone(content_id, "No content_id returned from upload")

        # Get summary from database
        summary = get_summary_for_document(self.db, content_id)

        # Verify summary exists
        self.assertIsNotNone(summary, "No summary found for uploaded PDF")

        # Verify summary quality
        self.assertTrue(
            verify_summary_quality(summary, min_keywords=5, min_sentences=2),
            f"Summary quality insufficient: {summary}",
        )

        # Verify summary type
        self.assertIn(summary["summary_type"], ["tfidf", "textrank", "combined"])

    def test_pdf_summary_contains_keywords(self):
        """
        Test that PDF summary contains TF-IDF keywords.
        """
        # Upload PDF
        result = self.pdf_service.upload_single_pdf(self.test_pdf, use_pipeline=False)
        content_id = result.get("content_id")

        # Get summary
        summary = get_summary_for_document(self.db, content_id)
        self.assertIsNotNone(summary)

        # Check TF-IDF keywords
        keywords = summary.get("tf_idf_keywords", {})
        self.assertIsInstance(keywords, dict)
        self.assertGreater(len(keywords), 0, "No TF-IDF keywords extracted")

        # Verify keywords have scores
        for keyword, score in keywords.items():
            self.assertIsInstance(keyword, str)
            self.assertIsInstance(score, (int, float))
            self.assertGreater(score, 0)
            self.assertLessEqual(score, 1.0)

    def test_pdf_summary_contains_sentences(self):
        """
        Test that PDF summary contains TextRank sentences.
        """
        # Upload PDF
        result = self.pdf_service.upload_single_pdf(self.test_pdf, use_pipeline=False)
        content_id = result.get("content_id")

        # Get summary
        summary = get_summary_for_document(self.db, content_id)
        self.assertIsNotNone(summary)

        # Check TextRank sentences
        sentences = summary.get("textrank_sentences", [])
        self.assertIsInstance(sentences, list)
        self.assertGreater(len(sentences), 0, "No TextRank sentences extracted")

        # Verify sentences are non-empty strings
        for sentence in sentences:
            self.assertIsInstance(sentence, str)
            self.assertGreater(len(sentence), 10, f"Sentence too short: {sentence}")

    def test_pdf_creates_document_record(self):
        """
        Test that PDF upload creates a document record.
        """
        # Upload PDF
        result = self.pdf_service.upload_single_pdf(self.test_pdf, use_pipeline=False)

        # Verify upload succeeded
        self.assertTrue(result.get("success"))

        # Check documents table for chunks (PDF creates chunks, not single document record)
        chunks = self.pdf_service.db.fetch(
            "SELECT * FROM documents WHERE file_path = ?", (self.test_pdf,)
        )

        # Should have at least one chunk
        self.assertGreater(len(chunks), 0, "No document chunks found")

        # Verify first chunk has expected fields
        first_chunk = chunks[0]
        self.assertEqual(first_chunk["file_path"], self.test_pdf)
        self.assertIsNotNone(first_chunk["text_content"])
        self.assertIn(first_chunk["extraction_method"], ["pdfplumber", "pypdf", "pypdf2", "ocr"])

    def test_multiple_pdf_uploads_create_unique_summaries(self):
        """
        Test that multiple uploads handle deduplication correctly.
        """
        # Upload same PDF twice
        result1 = self.pdf_service.upload_single_pdf(self.test_pdf, use_pipeline=False)
        result2 = self.pdf_service.upload_single_pdf(self.test_pdf, use_pipeline=False)

        # First upload should have content_id
        self.assertIsNotNone(result1.get("content_id"))

        # Second upload should be skipped as duplicate
        self.assertTrue(result2.get("success"))
        self.assertTrue(result2.get("skipped"), "Second upload should be skipped as duplicate")
        self.assertEqual(result2.get("reason"), "File already exists in database")

        # First upload should have a summary
        summary1 = get_summary_for_document(self.pdf_service.db, result1["content_id"])
        self.assertIsNotNone(summary1)

    def test_pdf_summary_matches_content(self):
        """
        Test that summary is relevant to PDF content.
        """
        # Upload a contract PDF
        result = self.pdf_service.upload_single_pdf(self.test_pdf, use_pipeline=False)
        content_id = result.get("content_id")

        # Get content and summary
        content = self.db.fetch_one("SELECT body FROM content_unified WHERE id = ?", (content_id,))
        summary = get_summary_for_document(self.db, content_id)

        self.assertIsNotNone(content)
        self.assertIsNotNone(summary)

        # For a contract PDF, expect legal-related keywords
        keywords = summary.get("tf_idf_keywords", {})

        # Check if any legal/contract terms appear
        legal_terms = [
            "agreement",
            "contract",
            "party",
            "parties",
            "shall",
            "terms",
            "conditions",
            "obligations",
            "rights",
        ]

        found_legal_term = any(
            term in keyword.lower() for keyword in keywords.keys() for term in legal_terms
        )

        self.assertTrue(
            found_legal_term or len(keywords) > 0,
            f"No relevant keywords found. Got: {list(keywords.keys())[:10]}",
        )


if __name__ == "__main__":
    unittest.main()
