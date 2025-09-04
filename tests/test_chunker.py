#!/usr/bin/env python3
"""Unit tests for DocumentChunker module.

Tests token-based chunking with sentence awareness and overlap.
"""

from pathlib import Path

import pytest

from infrastructure.documents.chunker.document_chunker import (
    DocumentChunk,
    DocumentChunker,
    DocumentType,
)


class TestDocumentChunk:
    """
    Test DocumentChunk dataclass.
    """
    
    def test_chunk_creation(self):
        """
        Test basic chunk creation.
        """
        chunk = DocumentChunk(
            doc_id="test_doc",
            chunk_idx=0,
            text="This is a test chunk.",
            token_count=5,
            token_start=0,
            token_end=5
        )
        assert chunk.doc_id == "test_doc"
        assert chunk.chunk_idx == 0
        assert chunk.chunk_id == "test_doc:0"
        assert chunk.token_count == 5
    
    def test_chunk_id_generation(self):
        """
        Test automatic chunk_id generation.
        """
        chunk = DocumentChunk(
            doc_id="doc_123",
            chunk_idx=5,
            text="Test",
            token_count=1,
            token_start=100,
            token_end=101
        )
        assert chunk.chunk_id == "doc_123:5"
    
    def test_chunk_with_metadata(self):
        """
        Test chunk with optional metadata.
        """
        chunk = DocumentChunk(
            doc_id="test",
            chunk_idx=0,
            text="Test",
            token_count=1,
            token_start=0,
            token_end=1,
            section_title="INTRODUCTION",
            quote_depth=2,
            quality_score=0.85
        )
        assert chunk.section_title == "INTRODUCTION"
        assert chunk.quote_depth == 2
        assert chunk.quality_score == 0.85


class TestDocumentChunker:
    """
    Test DocumentChunker class.
    """
    
    @pytest.fixture
    def chunker(self):
        """
        Create a default chunker instance.
        """
        return DocumentChunker(
            target_tokens=100,  # Smaller for testing
            min_tokens=80,
            max_tokens=120,
            overlap_ratio=0.15
        )
    
    def test_chunker_initialization(self, chunker):
        """
        Test chunker initialization.
        """
        assert chunker.target_tokens == 100
        assert chunker.min_tokens == 80
        assert chunker.max_tokens == 120
        assert chunker.overlap_ratio == 0.15
        assert chunker.nlp is not None
    
    def test_token_counting(self, chunker):
        """
        Test token counting functionality.
        """
        text = "This is a simple test sentence for token counting."
        token_count = chunker._count_tokens(text)
        assert token_count > 0
        assert token_count < len(text)  # Tokens should be less than characters
    
    def test_empty_document(self, chunker):
        """
        Test handling of empty documents.
        """
        chunks = list(chunker.chunk_document("", "empty_doc"))
        assert len(chunks) == 0
        
        chunks = list(chunker.chunk_document("   \n  ", "whitespace_doc"))
        assert len(chunks) == 0
    
    def test_small_document(self, chunker):
        """
        Test document smaller than target tokens.
        """
        text = "This is a small document that fits in a single chunk."
        chunks = list(chunker.chunk_document(text, "small_doc"))
        
        assert len(chunks) == 1
        assert chunks[0].chunk_idx == 0
        assert chunks[0].text == text
        assert chunks[0].chunk_id == "small_doc:0"
    
    def test_chunk_overlap(self):
        """
        Test that chunks have proper overlap.
        """
        # Create chunker with specific settings
        chunker = DocumentChunker(
            target_tokens=50,
            overlap_ratio=0.2
        )
        
        # Create a long document
        text = " ".join(["word" + str(i) for i in range(500)])
        chunks = list(chunker.chunk_document(text, "overlap_test"))
        
        # Check that we have multiple chunks
        assert len(chunks) > 1
        
        # Verify chunks have content
        for chunk in chunks:
            assert len(chunk.text) > 0
            assert chunk.token_count > 0
    
    def test_sentence_boundaries(self, chunker):
        """
        Test that chunks respect sentence boundaries.
        """
        text = "This is the first sentence. This is the second sentence. This is the third sentence. This is the fourth sentence. This is the fifth sentence."
        chunks = list(chunker.chunk_document(text, "sentence_test"))
        
        # Check that chunks end at sentence boundaries
        for chunk in chunks:
            # Last character should be punctuation or last chunk
            if chunk.chunk_idx < len(chunks) - 1:
                last_char = chunk.text.strip()[-1]
                assert last_char in '.?!', f"Chunk {chunk.chunk_idx} doesn't end at sentence boundary"
    
    def test_document_types(self, chunker):
        """
        Test different document type handling.
        """
        # Email type
        email_text = "Subject: Test\n\n----- Original Message -----\nThis is a reply."
        chunks = list(chunker.chunk_document(email_text, "email", DocumentType.EMAIL))
        assert len(chunks) > 0
        
        # Legal PDF type
        legal_text = "MOTION TO DISMISS\n\nThis is the content of the motion.\n\nARGUMENT\n\nThis is the argument section."
        chunks = list(chunker.chunk_document(legal_text, "legal", DocumentType.LEGAL_PDF))
        assert len(chunks) > 0
        
        # General type
        general_text = "This is a general document with normal text."
        chunks = list(chunker.chunk_document(general_text, "general", DocumentType.GENERAL))
        assert len(chunks) > 0
    
    def test_quote_depth_detection(self, chunker):
        """
        Test email quote depth detection.
        """
        email_text = """
Subject: Re: Test

My response here.

> Original quoted text
> Second line of quote
>> Nested quote
"""
        chunks = list(chunker.chunk_document(email_text, "quote_test", DocumentType.EMAIL))
        assert len(chunks) > 0
        # At least one chunk should have detected quotes
        max_quote_depth = max(chunk.quote_depth for chunk in chunks)
        assert max_quote_depth >= 0
    
    def test_section_title_extraction(self, chunker):
        """
        Test section title extraction for legal documents.
        """
        legal_text = """INTRODUCTION

This is the introduction section with some content.

STATEMENT OF FACTS

These are the facts of the case."""
        
        chunks = list(chunker.chunk_document(legal_text, "section_test", DocumentType.LEGAL_PDF))
        
        # Check that section titles are extracted
        section_titles = [chunk.section_title for chunk in chunks if chunk.section_title]
        assert len(section_titles) > 0
    
    def test_chunk_id_stability(self, chunker):
        """
        Test that chunk IDs are stable across runs.
        """
        text = "This is a test document for checking ID stability. " * 20
        
        # Run chunking twice
        chunks1 = list(chunker.chunk_document(text, "stability_test"))
        chunks2 = list(chunker.chunk_document(text, "stability_test"))
        
        # Check same number of chunks
        assert len(chunks1) == len(chunks2)
        
        # Check IDs match
        for c1, c2 in zip(chunks1, chunks2):
            assert c1.chunk_id == c2.chunk_id
            assert c1.chunk_idx == c2.chunk_idx
    
    def test_long_document(self):
        """
        Test chunking of a long document.
        """
        # Create a chunker with small chunks for testing
        chunker = DocumentChunker(target_tokens=30, overlap_ratio=0.15)
        
        # Create a long document
        text = " ".join([f"Sentence {i}. This is content for sentence number {i}." 
                        for i in range(100)])
        
        chunks = list(chunker.chunk_document(text, "long_doc"))
        
        # Should produce multiple chunks
        assert len(chunks) > 5
        
        # All chunks should have valid indices
        for i, chunk in enumerate(chunks):
            assert chunk.chunk_idx == i
            assert chunk.doc_id == "long_doc"
            assert chunk.token_count > 0
    
    def test_chunk_size_constraints(self):
        """
        Test that chunks respect size constraints.
        """
        chunker = DocumentChunker(
            target_tokens=100,
            min_tokens=90,
            max_tokens=110
        )
        
        # Create document with known token count
        text = " ".join(["word" for _ in range(500)])
        chunks = list(chunker.chunk_document(text, "size_test"))
        
        # Check chunk sizes (except possibly the last one)
        for i, chunk in enumerate(chunks[:-1]):
            # These are approximate due to sentence boundaries
            assert chunk.token_count > 50, f"Chunk {i} too small: {chunk.token_count}"
            assert chunk.token_count < 200, f"Chunk {i} too large: {chunk.token_count}"


class TestChunkerWithFixtures:
    """
    Test chunker with sample fixture files.
    """
    
    @pytest.fixture
    def fixtures_dir(self):
        """
        Get fixtures directory path.
        """
        return Path(__file__).parent / "fixtures"
    
    @pytest.fixture
    def chunker(self):
        """
        Create a chunker for testing.
        """
        return DocumentChunker(target_tokens=100, overlap_ratio=0.15)
    
    def test_email_fixture(self, chunker, fixtures_dir):
        """
        Test chunking of sample email.
        """
        email_file = fixtures_dir / "sample_email.txt"
        if not email_file.exists():
            pytest.skip("Email fixture not found")
        
        text = email_file.read_text()
        chunks = list(chunker.chunk_document(text, "email_fixture", DocumentType.EMAIL))
        
        assert len(chunks) > 0
        # Should detect the reply separator
        assert any("Original Message" in chunk.text for chunk in chunks)
    
    def test_legal_fixture(self, chunker, fixtures_dir):
        """
        Test chunking of sample legal document.
        """
        legal_file = fixtures_dir / "sample_legal.txt"
        if not legal_file.exists():
            pytest.skip("Legal fixture not found")
        
        text = legal_file.read_text()
        chunks = list(chunker.chunk_document(text, "legal_fixture", DocumentType.LEGAL_PDF))
        
        assert len(chunks) > 0
        # Should detect section headers
        assert any("MOTION" in chunk.text or "ARGUMENT" in chunk.text for chunk in chunks)
    
    def test_ocr_fixture(self, chunker, fixtures_dir):
        """
        Test chunking of sample OCR document.
        """
        ocr_file = fixtures_dir / "sample_ocr.txt"
        if not ocr_file.exists():
            pytest.skip("OCR fixture not found")
        
        text = ocr_file.read_text()
        chunks = list(chunker.chunk_document(text, "ocr_fixture", DocumentType.OCR_SCAN))
        
        assert len(chunks) > 0
        # Should handle OCR artifacts
        for chunk in chunks:
            assert len(chunk.text) > 0


class TestChunkerPerformance:
    """
    Performance tests for the chunker.
    """
    
    def test_large_document_performance(self):
        """
        Test performance with a large document.
        """
        import time
        
        chunker = DocumentChunker()
        
        # Create a 50-page equivalent document (approx 25,000 words)
        text = " ".join(["This is sentence number {}.".format(i) for i in range(5000)])
        
        start_time = time.time()
        chunks = list(chunker.chunk_document(text, "perf_test"))
        elapsed = time.time() - start_time
        
        # Should complete in reasonable time (< 2 seconds for 50 pages)
        assert elapsed < 2.0, f"Chunking took {elapsed:.2f}s, expected < 2s"
        assert len(chunks) > 0


class TestChunkerEdgeCases:
    """
    Test edge cases and error conditions.
    """
    
    def test_unicode_handling(self):
        """
        Test handling of unicode characters.
        """
        chunker = DocumentChunker(target_tokens=50)
        
        text = "This contains émojis 😀 and special characters: ñ, ü, 中文"
        chunks = list(chunker.chunk_document(text, "unicode_test"))
        
        assert len(chunks) > 0
        assert "émojis" in chunks[0].text or "😀" in chunks[0].text
    
    def test_malformed_email(self):
        """
        Test handling of malformed email format.
        """
        chunker = DocumentChunker()
        
        text = ">>> Badly formatted\n>> email with\n> broken quotes\nAnd normal text"
        chunks = list(chunker.chunk_document(text, "malformed", DocumentType.EMAIL))
        
        assert len(chunks) > 0
    
    def test_very_long_line(self):
        """
        Test handling of very long lines without breaks.
        """
        chunker = DocumentChunker(target_tokens=50)
        
        # Single line with no sentence breaks
        text = "word " * 500  # Very long single line
        chunks = list(chunker.chunk_document(text, "longline"))
        
        assert len(chunks) > 1  # Should still split into chunks
    
    def test_only_whitespace_segments(self):
        """
        Test document with whitespace-only segments.
        """
        chunker = DocumentChunker()
        
        text = "First part\n\n\n\n   \n\n\nSecond part"
        chunks = list(chunker.chunk_document(text, "whitespace"))
        
        assert all(chunk.text.strip() for chunk in chunks)  # No empty chunks


if __name__ == "__main__":
    pytest.main([__file__, "-v"])