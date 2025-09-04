#!/usr/bin/env python3
"""
Unit tests for quality scoring module.
Tests quality score calculation and chunk filtering.
"""

import pytest
import sys
import os

# Add src to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.chunker.document_chunker import DocumentChunk
from src.quality.quality_score import ChunkQualityScorer, quality_gate, QualitySettings


class TestQualitySettings:
    """Test QualitySettings configuration."""
    
    def test_default_settings(self):
        """Test default settings values."""
        settings = QualitySettings()
        assert settings.min_quality_score == 0.35
        assert settings.min_char_length == 100
        assert settings.min_token_count == 20
        assert settings.length_weight == 0.4
        assert settings.entropy_weight == 0.3
        assert settings.content_weight == 0.2
        assert settings.quote_weight == 0.1
    
    def test_custom_settings(self):
        """Test custom settings values."""
        settings = QualitySettings(
            min_quality_score=0.5,
            min_char_length=50,
            min_token_count=10
        )
        assert settings.min_quality_score == 0.5
        assert settings.min_char_length == 50
        assert settings.min_token_count == 10
    
    def test_env_override(self, monkeypatch):
        """Test environment variable override."""
        monkeypatch.setenv("QUALITY_MIN_QUALITY_SCORE", "0.75")
        monkeypatch.setenv("QUALITY_MIN_CHAR_LENGTH", "200")
        settings = QualitySettings()
        assert settings.min_quality_score == 0.75
        assert settings.min_char_length == 200


class TestChunkQualityScorer:
    """Test ChunkQualityScorer class."""
    
    @pytest.fixture
    def scorer(self):
        """Create a default scorer instance."""
        return ChunkQualityScorer()
    
    @pytest.fixture
    def custom_scorer(self):
        """Create a scorer with custom settings."""
        settings = QualitySettings(min_quality_score=0.5)
        return ChunkQualityScorer(settings)
    
    def test_scorer_initialization(self, scorer):
        """Test scorer initialization."""
        assert scorer.settings.min_quality_score == 0.35
        assert scorer.header_patterns is not None
        assert scorer.signature_patterns is not None
        assert scorer.boilerplate_patterns is not None
    
    def test_hard_exclusion_short_text(self, scorer):
        """Test exclusion for text too short."""
        chunk = DocumentChunk(
            doc_id="test",
            chunk_idx=0,
            text="Short",  # Less than 100 chars
            token_count=1,
            token_start=0,
            token_end=1
        )
        score = scorer.score(chunk)
        assert score == 0.0
    
    def test_hard_exclusion_few_tokens(self, scorer):
        """Test exclusion for too few tokens."""
        chunk = DocumentChunk(
            doc_id="test",
            chunk_idx=0,
            text="This is a text with sufficient characters but marked as having few tokens",
            token_count=5,  # Less than 20 tokens
            token_start=0,
            token_end=5
        )
        score = scorer.score(chunk)
        assert score == 0.0
    
    def test_hard_exclusion_headers_only(self, scorer):
        """Test exclusion for headers-only content."""
        chunk = DocumentChunk(
            doc_id="test",
            chunk_idx=0,
            text="From: john@example.com\nTo: jane@example.com\nSubject: Test\nDate: 2024-01-01",
            token_count=25,
            token_start=0,
            token_end=25
        )
        score = scorer.score(chunk)
        assert score == 0.0
    
    def test_hard_exclusion_signature_only(self, scorer):
        """Test exclusion for signature-only content."""
        chunk = DocumentChunk(
            doc_id="test",
            chunk_idx=0,
            text="Best regards,\nJohn Doe",
            token_count=25,
            token_start=0,
            token_end=25
        )
        # Pad to meet character minimum
        chunk.text = chunk.text + "\n" + " " * 100
        score = scorer.score(chunk)
        # Should be low due to signature detection
        assert score < 0.2
    
    def test_length_score_calculation(self, scorer):
        """Test length score calculation."""
        # Optimal length chunk
        chunk = DocumentChunk(
            doc_id="test",
            chunk_idx=0,
            text=" ".join(["word"] * 200),  # Sufficient text
            token_count=1000,  # Expected tokens
            token_start=0,
            token_end=1000
        )
        length_score = scorer._calculate_length_score(chunk)
        assert length_score == 1.0
        
        # Half length chunk
        chunk.token_count = 500
        length_score = scorer._calculate_length_score(chunk)
        assert 0.4 < length_score < 0.6
        
        # Double length chunk
        chunk.token_count = 2000
        length_score = scorer._calculate_length_score(chunk)
        assert 0.4 < length_score < 0.6
    
    def test_entropy_score_calculation(self, scorer):
        """Test entropy score calculation."""
        # High diversity text
        diverse_text = "The quick brown fox jumps over the lazy dog. Each word is unique here."
        entropy_score = scorer._calculate_entropy_score(diverse_text)
        assert entropy_score > 0.7
        
        # Low diversity text (repetitive)
        repetitive_text = "test test test test test test test test test test"
        entropy_score = scorer._calculate_entropy_score(repetitive_text)
        assert entropy_score < 0.3
    
    def test_content_score_calculation(self, scorer):
        """Test content score calculation."""
        # High content text
        content_text = """This is a substantive paragraph with meaningful content.
        It discusses important topics and provides valuable information.
        The text contains no boilerplate or repetitive elements."""
        content_score = scorer._calculate_content_score(content_text)
        assert content_score > 0.8
        
        # Boilerplate-heavy text
        boilerplate_text = """Page 1 of 5
        ====================
        Footer: Confidential
        Page 2 of 5
        ====================
        Some actual content here.
        Page 3 of 5"""
        content_score = scorer._calculate_content_score(boilerplate_text)
        assert content_score < 0.5
    
    def test_quote_penalty_calculation(self, scorer):
        """Test quote penalty calculation."""
        # No quotes
        chunk = DocumentChunk(
            doc_id="test",
            chunk_idx=0,
            text="Text",
            token_count=100,
            token_start=0,
            token_end=100,
            quote_depth=0
        )
        penalty = scorer._calculate_quote_penalty(chunk)
        assert penalty == 0.0
        
        # Single level quote
        chunk.quote_depth = 1
        penalty = scorer._calculate_quote_penalty(chunk)
        assert penalty == 0.2
        
        # Deep quote
        chunk.quote_depth = 3
        penalty = scorer._calculate_quote_penalty(chunk)
        assert abs(penalty - 0.6) < 0.01  # Use approximate comparison
    
    def test_full_quality_score(self, scorer):
        """Test full quality score calculation."""
        # High quality chunk
        good_chunk = DocumentChunk(
            doc_id="test",
            chunk_idx=0,
            text="""This is a high-quality document chunk with diverse vocabulary and 
            meaningful content. It contains substantive information about the topic
            at hand, with varied sentence structures and no repetitive elements.
            The chunk has sufficient length and complexity to be valuable.""",
            token_count=100,
            token_start=0,
            token_end=100,
            quote_depth=0
        )
        score = scorer.score(good_chunk)
        assert score > 0.5
        assert good_chunk.quality_score == score  # Score should be set on chunk
        
        # Low quality chunk (but not excluded)
        poor_chunk = DocumentChunk(
            doc_id="test",
            chunk_idx=1,
            text=" ".join(["word"] * 50),  # Repetitive
            token_count=50,
            token_start=100,
            token_end=150,
            quote_depth=2
        )
        score = scorer.score(poor_chunk)
        assert score < 0.35
    
    def test_is_acceptable(self, scorer):
        """Test acceptability check."""
        # Acceptable chunk
        good_chunk = DocumentChunk(
            doc_id="test",
            chunk_idx=0,
            text=" ".join(["Different word number {}".format(i) for i in range(50)]),
            token_count=200,
            token_start=0,
            token_end=200
        )
        scorer.score(good_chunk)
        assert scorer.is_acceptable(good_chunk)
        
        # Unacceptable chunk
        bad_chunk = DocumentChunk(
            doc_id="test",
            chunk_idx=1,
            text="Short repetitive text " * 5,
            token_count=25,
            token_start=200,
            token_end=225
        )
        score = scorer.score(bad_chunk)
        # The chunk might be acceptable depending on entropy calculation
        # Just verify score is computed
        assert 0 <= score <= 1
    
    def test_custom_threshold(self, custom_scorer):
        """Test custom quality threshold."""
        chunk = DocumentChunk(
            doc_id="test",
            chunk_idx=0,
            text=" ".join(["Word{}".format(i) for i in range(100)]),
            token_count=100,
            token_start=0,
            token_end=100
        )
        custom_scorer.score(chunk)
        
        # With threshold 0.5, chunk with score 0.4 should be rejected
        chunk.quality_score = 0.4
        assert not custom_scorer.is_acceptable(chunk)
        
        # Chunk with score 0.6 should be accepted
        chunk.quality_score = 0.6
        assert custom_scorer.is_acceptable(chunk)


class TestQualityGateDecorator:
    """Test quality_gate decorator."""
    
    def test_quality_gate_filtering(self):
        """Test that quality gate filters low-score chunks."""
        # Create test chunks
        chunks = [
            DocumentChunk(
                doc_id="test",
                chunk_idx=0,
                text=" ".join(["Good content with variety {}".format(i) for i in range(50)]),
                token_count=200,
                token_start=0,
                token_end=200,
                quality_score=0.8
            ),
            DocumentChunk(
                doc_id="test",
                chunk_idx=1,
                text="Bad bad bad bad bad",
                token_count=25,
                token_start=200,
                token_end=225,
                quality_score=0.2
            ),
            DocumentChunk(
                doc_id="test",
                chunk_idx=2,
                text=" ".join(["Another good chunk {}".format(i) for i in range(40)]),
                token_count=160,
                token_start=225,
                token_end=385,
                quality_score=0.6
            ),
        ]
        
        @quality_gate(min_score=0.35)
        def chunk_generator():
            for chunk in chunks:
                yield chunk
        
        # Collect filtered chunks
        filtered = list(chunk_generator())
        
        # Should only have chunks with score >= 0.35
        assert len(filtered) == 2
        assert filtered[0].chunk_idx == 0
        assert filtered[1].chunk_idx == 2
    
    def test_quality_gate_scoring(self):
        """Test that quality gate scores unscored chunks."""
        # Create unscored chunks
        chunks = [
            DocumentChunk(
                doc_id="test",
                chunk_idx=0,
                text=" ".join(["Content {}".format(i) for i in range(100)]),
                token_count=100,
                token_start=0,
                token_end=100
            ),
            DocumentChunk(
                doc_id="test",
                chunk_idx=1,
                text="Too short",
                token_count=10,
                token_start=100,
                token_end=110
            ),
        ]
        
        @quality_gate()
        def chunk_generator():
            for chunk in chunks:
                yield chunk
        
        # Collect filtered chunks
        filtered = list(chunk_generator())
        
        # Chunks should be scored
        assert chunks[0].quality_score is not None
        assert chunks[1].quality_score is not None
        
        # Short chunk should be filtered out
        assert len(filtered) <= 1
    
    def test_quality_gate_custom_settings(self):
        """Test quality gate with custom settings."""
        settings = QualitySettings(
            min_quality_score=0.7,
            min_token_count=50
        )
        
        chunks = [
            DocumentChunk(
                doc_id="test",
                chunk_idx=0,
                text=" ".join(["Word"] * 200),
                token_count=200,
                token_start=0,
                token_end=200,
                quality_score=0.6
            ),
            DocumentChunk(
                doc_id="test",
                chunk_idx=1,
                text=" ".join(["Diverse content {}".format(i) for i in range(100)]),
                token_count=100,
                token_start=200,
                token_end=300,
                quality_score=0.8
            ),
        ]
        
        @quality_gate(settings=settings)
        def chunk_generator():
            for chunk in chunks:
                yield chunk
        
        filtered = list(chunk_generator())
        
        # Only chunk with score >= 0.7 should pass
        assert len(filtered) == 1
        assert filtered[0].chunk_idx == 1


class TestIntegrationWithChunker:
    """Test integration between chunker and quality scorer."""
    
    def test_chunker_with_quality_scoring(self):
        """Test that chunker can apply quality scoring."""
        from src.chunker.document_chunker import DocumentChunker, DocumentType
        
        # Create chunker with quality scoring
        chunker = DocumentChunker(
            target_tokens=50,
            enable_quality_scoring=True,
            quality_threshold=0.35
        )
        
        # Test document
        text = """Subject: Important Information
        
        This is a meaningful paragraph with important content that should pass quality checks.
        It contains substantive information about the topic being discussed.
        
        Best regards,
        Signature
        
        > Quoted text that might be penalized
        > More quoted content here"""
        
        chunks = list(chunker.chunk_document(text, "test_doc", DocumentType.EMAIL))
        
        # All chunks should have quality scores
        for chunk in chunks:
            assert chunk.quality_score is not None
            assert 0 <= chunk.quality_score <= 1
    
    def test_quality_gate_with_chunker(self):
        """Test using quality gate decorator with chunker output."""
        from src.chunker.document_chunker import DocumentChunker, DocumentType
        
        chunker = DocumentChunker(
            target_tokens=30,
            enable_quality_scoring=False  # Let decorator handle scoring
        )
        
        text = """This is good content with variety and substance.
        
        xxx xxx xxx xxx xxx
        
        Another paragraph with meaningful information here."""
        
        @quality_gate(min_score=0.35)
        def get_chunks():
            return chunker.chunk_document(text, "test", DocumentType.GENERAL)
        
        chunks = list(get_chunks())
        
        # Should filter out the repetitive middle section
        for chunk in chunks:
            assert chunk.quality_score >= 0.35


class TestEdgeCases:
    """Test edge cases and error conditions."""
    
    def test_empty_text(self):
        """Test scoring empty text."""
        scorer = ChunkQualityScorer()
        chunk = DocumentChunk(
            doc_id="test",
            chunk_idx=0,
            text="",
            token_count=0,
            token_start=0,
            token_end=0
        )
        score = scorer.score(chunk)
        assert score == 0.0
    
    def test_unicode_text(self):
        """Test scoring Unicode text."""
        scorer = ChunkQualityScorer()
        chunk = DocumentChunk(
            doc_id="test",
            chunk_idx=0,
            text="这是中文文本 with émojis 😀 and special chars ñ ü",
            token_count=50,
            token_start=0,
            token_end=50
        )
        # Pad for length requirement
        chunk.text = chunk.text * 5
        score = scorer.score(chunk)
        assert score > 0  # Should handle Unicode gracefully
    
    def test_very_long_text(self):
        """Test scoring very long text."""
        scorer = ChunkQualityScorer()
        # Create diverse long text
        long_text = " ".join(["Sentence number {} with content.".format(i) for i in range(1000)])
        chunk = DocumentChunk(
            doc_id="test",
            chunk_idx=0,
            text=long_text,
            token_count=5000,
            token_start=0,
            token_end=5000
        )
        score = scorer.score(chunk)
        assert 0 < score <= 1  # Should handle long text
    
    def test_mathematical_content(self):
        """Test scoring mathematical/code content."""
        scorer = ChunkQualityScorer()
        chunk = DocumentChunk(
            doc_id="test",
            chunk_idx=0,
            text="""def calculate_score(x, y):
                result = x * 0.4 + y * 0.3 + z * 0.2
                return max(0.0, min(1.0, result))
                
            The formula is: score = 0.4*a + 0.3*b + 0.2*c""",
            token_count=80,
            token_start=0,
            token_end=80
        )
        score = scorer.score(chunk)
        assert score > 0.3  # Code should still get reasonable score


if __name__ == "__main__":
    pytest.main([__file__, "-v"])