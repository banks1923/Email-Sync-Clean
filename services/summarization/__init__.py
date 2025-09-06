"""Document Summarization Engine for Email Sync System.

Provides TF-IDF and TextRank-based document summarization.
"""

from .engine import DocumentSummarizer, TextRankSummarizer, TFIDFSummarizer, get_document_summarizer

__all__ = ["TFIDFSummarizer", "TextRankSummarizer", "DocumentSummarizer", "get_document_summarizer"]
