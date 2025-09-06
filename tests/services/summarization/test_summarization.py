"""
Unit tests for document summarization engine.
"""

import sys
import unittest
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent))

from services.summarization.engine import (
    DocumentSummarizer,
    TextRankSummarizer,
    TFIDFSummarizer,
    get_document_summarizer,
)


class TestTFIDFSummarizer(unittest.TestCase):
    """
    Test TF-IDF summarizer functionality.
    """

    def setUp(self):
        """
        Set up test fixtures.
        """
        self.summarizer = TFIDFSummarizer()
        self.sample_text = """
        This is a legal contract between ABC Corporation and XYZ Company.
        The contract establishes terms for software development services.
        ABC Corporation agrees to provide development resources.
        XYZ Company agrees to pay monthly fees for the services.
        The contract duration is twelve months with option to renew.
        Both parties must provide 30 days notice for termination.
        """

    def test_preprocess_text(self):
        """
        Test text preprocessing.
        """
        text = "This is a TEST! With special #chars & numbers 123."
        processed = self.summarizer.preprocess_text(text)

        self.assertNotIn("!", processed)
        self.assertNotIn("#", processed)
        self.assertNotIn("&", processed)
        self.assertIn("123", processed)
        self.assertEqual(processed, processed.lower())

    def test_extract_keywords(self):
        """
        Test keyword extraction.
        """
        keywords = self.summarizer.extract_keywords(self.sample_text, max_keywords=5)

        self.assertIsInstance(keywords, dict)
        self.assertLessEqual(len(keywords), 5)

        # Check that scores are floats between 0 and 1
        for keyword, score in keywords.items():
            self.assertIsInstance(keyword, str)
            self.assertIsInstance(score, float)
            self.assertGreaterEqual(score, 0)
            self.assertLessEqual(score, 1)

        # Contract-related terms should be present
        keywords_text = " ".join(keywords.keys()).lower()
        self.assertTrue(
            "contract" in keywords_text
            or "corporation" in keywords_text
            or "company" in keywords_text
        )

    def test_extract_keywords_empty(self):
        """
        Test keyword extraction with empty text.
        """
        keywords = self.summarizer.extract_keywords("")
        self.assertEqual(keywords, {})

        keywords = self.summarizer.extract_keywords("   ")
        self.assertEqual(keywords, {})

    def test_extract_keywords_batch(self):
        """
        Test batch keyword extraction.
        """
        texts = [
            self.sample_text,
            "This is another document about legal matters and court proceedings.",
            "Software development requires careful planning and execution.",
        ]

        results = self.summarizer.extract_keywords_batch(texts, max_keywords=3)

        self.assertEqual(len(results), 3)
        for result in results:
            self.assertIsInstance(result, dict)
            self.assertLessEqual(len(result), 3)


class TestTextRankSummarizer(unittest.TestCase):
    """
    Test TextRank summarizer functionality.
    """

    def setUp(self):
        """
        Set up test fixtures.
        """
        self.summarizer = TextRankSummarizer()
        self.sample_text = """
        This is a legal contract between ABC Corporation and XYZ Company.
        The contract establishes terms for software development services.
        ABC Corporation agrees to provide development resources.
        XYZ Company agrees to pay monthly fees for the services.
        The contract duration is twelve months with option to renew.
        Both parties must provide 30 days notice for termination.
        Confidentiality clauses protect proprietary information.
        Dispute resolution will be handled through arbitration.
        """

    def test_split_sentences(self):
        """
        Test sentence splitting.
        """
        text = "First sentence here. Second sentence here! Third sentence here? Fourth sentence."
        sentences = self.summarizer.split_sentences(text)

        self.assertEqual(len(sentences), 4)
        self.assertIn("First sentence here", sentences)
        self.assertIn("Second sentence here", sentences)

    def test_extract_sentences(self):
        """
        Test sentence extraction.
        """
        sentences = self.summarizer.extract_sentences(self.sample_text, max_sentences=3)

        self.assertIsInstance(sentences, list)
        self.assertLessEqual(len(sentences), 3)

        for sentence in sentences:
            self.assertIsInstance(sentence, str)
            self.assertGreater(len(sentence), 0)

    def test_extract_sentences_empty(self):
        """
        Test sentence extraction with empty text.
        """
        sentences = self.summarizer.extract_sentences("", max_sentences=3)
        self.assertEqual(sentences, [])

        sentences = self.summarizer.extract_sentences("   ", max_sentences=3)
        self.assertEqual(sentences, [])

    def test_extract_sentences_short_text(self):
        """
        Test sentence extraction with short text.
        """
        text = "Only one sentence here."
        sentences = self.summarizer.extract_sentences(text, max_sentences=3)

        self.assertEqual(len(sentences), 1)
        self.assertEqual(sentences[0], "Only one sentence here")


class TestDocumentSummarizer(unittest.TestCase):
    """
    Test document summarizer orchestration.
    """

    def setUp(self):
        """
        Set up test fixtures.
        """
        self.summarizer = DocumentSummarizer()
        self.sample_text = """
        This legal agreement is entered into between ABC Corporation,
        a Delaware corporation, and XYZ Company, a California LLC.
        The purpose of this agreement is to establish terms and conditions
        for the provision of software development services.
        ABC Corporation will provide skilled developers and project management.
        XYZ Company will compensate ABC Corporation with monthly payments.
        The initial term is twelve months, commencing on January 1, 2025.
        Either party may terminate with 30 days written notice.
        All proprietary information shall remain confidential.
        Disputes will be resolved through binding arbitration in Delaware.
        This agreement is governed by Delaware state law.
        """

    def test_extract_summary_combined(self):
        """
        Test combined summary extraction.
        """
        summary = self.summarizer.extract_summary(
            self.sample_text, max_sentences=2, max_keywords=5, summary_type="combined"
        )

        self.assertEqual(summary["summary_type"], "combined")
        self.assertIsNotNone(summary["tf_idf_keywords"])
        self.assertIsNotNone(summary["textrank_sentences"])
        self.assertIsNotNone(summary["summary_text"])

        # Check keywords
        self.assertIsInstance(summary["tf_idf_keywords"], dict)
        self.assertLessEqual(len(summary["tf_idf_keywords"]), 5)

        # Check sentences
        self.assertIsInstance(summary["textrank_sentences"], list)
        self.assertLessEqual(len(summary["textrank_sentences"]), 2)

    def test_extract_summary_tfidf_only(self):
        """
        Test TF-IDF only summary.
        """
        summary = self.summarizer.extract_summary(
            self.sample_text, max_keywords=5, summary_type="tfidf"
        )

        self.assertEqual(summary["summary_type"], "tfidf")
        self.assertIsNotNone(summary["tf_idf_keywords"])
        self.assertIsNone(summary["textrank_sentences"])
        self.assertIsNotNone(summary["summary_text"])
        self.assertIn("Key topics:", summary["summary_text"])

    def test_extract_summary_textrank_only(self):
        """
        Test TextRank only summary.
        """
        summary = self.summarizer.extract_summary(
            self.sample_text, max_sentences=2, summary_type="textrank"
        )

        self.assertEqual(summary["summary_type"], "textrank")
        self.assertIsNone(summary["tf_idf_keywords"])
        self.assertIsNotNone(summary["textrank_sentences"])
        self.assertIsNotNone(summary["summary_text"])

    def test_summarize_batch(self):
        """
        Test batch summarization.
        """
        texts = [
            self.sample_text,
            "Another legal document about intellectual property rights.",
            "Technical specifications for the software system.",
        ]

        summaries = self.summarizer.summarize_batch(
            texts, max_sentences=1, max_keywords=3, summary_type="combined"
        )

        self.assertEqual(len(summaries), 3)
        for summary in summaries:
            self.assertEqual(summary["summary_type"], "combined")
            if summary["tf_idf_keywords"]:  # May be None for short texts
                self.assertLessEqual(len(summary["tf_idf_keywords"]), 3)

    def test_singleton_pattern(self):
        """
        Test that get_document_summarizer returns singleton.
        """
        summarizer1 = get_document_summarizer()
        summarizer2 = get_document_summarizer()

        self.assertIs(summarizer1, summarizer2)


if __name__ == "__main__":
    unittest.main()
