#!/usr/bin/env python3
"""
Quality scoring module for document chunks.
Computes quality scores and enforces gating thresholds.
"""

import re
import os
from typing import Generator, Optional, Dict, Any, Callable
from functools import wraps
from collections import Counter

import numpy as np
from scipy.stats import entropy
from pydantic_settings import BaseSettings
from pydantic import Field
from loguru import logger

# Import DocumentChunk from chunker
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
from src.chunker.document_chunker import DocumentChunk


class QualitySettings(BaseSettings):
    """Configuration settings for quality scoring."""
    
    min_quality_score: float = Field(
        default=0.35,
        description="Minimum quality score threshold for indexing",
        ge=0.0,
        le=1.0
    )
    
    min_char_length: int = Field(
        default=100,
        description="Minimum character length for chunks"
    )
    
    min_token_count: int = Field(
        default=20,
        description="Minimum token count for chunks"
    )
    
    length_weight: float = Field(
        default=0.4,
        description="Weight for length score in quality formula"
    )
    
    entropy_weight: float = Field(
        default=0.3,
        description="Weight for entropy score in quality formula"
    )
    
    content_weight: float = Field(
        default=0.2,
        description="Weight for content score in quality formula"
    )
    
    quote_weight: float = Field(
        default=0.1,
        description="Weight for quote penalty in quality formula"
    )
    
    quote_penalty_factor: float = Field(
        default=0.2,
        description="Penalty factor per quote depth level"
    )
    
    expected_chunk_tokens: int = Field(
        default=1000,
        description="Expected token count for normalization"
    )
    
    class Config:
        env_prefix = "QUALITY_"
        env_file = ".env"
        extra = "ignore"  # Ignore extra environment variables


class ChunkQualityScorer:
    """
    Computes quality scores for document chunks.
    Implements formula: quality = 0.4*length + 0.3*entropy + 0.2*content + 0.1*(1-quote_penalty)
    """
    
    def __init__(self, settings: Optional[QualitySettings] = None):
        """
        Initialize the quality scorer.
        
        Args:
            settings: Configuration settings (uses defaults if None)
        """
        self.settings = settings or QualitySettings()
        
        # Compile regex patterns for efficiency
        self.header_patterns = [
            re.compile(r'^From:', re.MULTILINE),
            re.compile(r'^Sent:', re.MULTILINE),
            re.compile(r'^To:', re.MULTILINE),
            re.compile(r'^Subject:', re.MULTILINE),
            re.compile(r'^Date:', re.MULTILINE),
            re.compile(r'^-{3,}\s*(Original|Forwarded)\s+Message\s*-{3,}', re.MULTILINE),
        ]
        
        self.signature_patterns = [
            re.compile(r'^(Best regards?|Sincerely|Thanks?|Regards?),?\s*$', re.MULTILINE | re.IGNORECASE),
            re.compile(r'^\s*--\s*$', re.MULTILINE),
            re.compile(r'^Sent from my \w+', re.MULTILINE | re.IGNORECASE),
        ]
        
        self.boilerplate_patterns = [
            re.compile(r'^\s*Page \d+ of \d+\s*$', re.MULTILINE | re.IGNORECASE),
            re.compile(r'^={5,}$', re.MULTILINE),
            re.compile(r'^#{5,}$', re.MULTILINE),
            re.compile(r'^\*{5,}$', re.MULTILINE),
            re.compile(r'^\[PAGE BREAK\]', re.MULTILINE | re.IGNORECASE),
            re.compile(r'^Footer:', re.MULTILINE | re.IGNORECASE),
            re.compile(r'^Header:', re.MULTILINE | re.IGNORECASE),
        ]
        
        logger.info(f"ChunkQualityScorer initialized with threshold={self.settings.min_quality_score}")
    
    def _is_headers_only(self, text: str) -> bool:
        """
        Check if text is primarily email headers.
        
        Args:
            text: Chunk text
            
        Returns:
            True if >80% of lines are headers
        """
        lines = text.strip().split('\n')
        if len(lines) == 0:
            return True
        
        header_lines = 0
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            # Check if line matches header patterns
            for pattern in self.header_patterns:
                if pattern.search(line):
                    header_lines += 1
                    break
        
        header_ratio = header_lines / max(1, len([l for l in lines if l.strip()]))
        return header_ratio > 0.8
    
    def _is_signature_only(self, text: str) -> bool:
        """
        Check if text is primarily signatures.
        
        Args:
            text: Chunk text
            
        Returns:
            True if text appears to be mostly signature content
        """
        # Remove whitespace and check length
        content = text.strip()
        if len(content) < 50:  # Very short, likely signature
            for pattern in self.signature_patterns:
                if pattern.search(content):
                    return True
        
        # Check if majority of text is signature-like
        lines = content.split('\n')
        sig_lines = 0
        for line in lines:
            for pattern in self.signature_patterns:
                if pattern.search(line):
                    sig_lines += 1
                    break
        
        return sig_lines > len(lines) * 0.6
    
    def _calculate_length_score(self, chunk: DocumentChunk) -> float:
        """
        Calculate length score normalized by expected length.
        
        Args:
            chunk: Document chunk
            
        Returns:
            Score between 0 and 1
        """
        # Use token count for scoring
        expected = self.settings.expected_chunk_tokens
        actual = chunk.token_count
        
        if actual < self.settings.min_token_count:
            return 0.0
        
        # Normalized score with sigmoid-like curve
        # Peaks at expected length, drops off on both sides
        ratio = actual / expected
        if ratio <= 1:
            # Linear increase up to expected
            score = ratio
        else:
            # Logarithmic decrease after expected
            # Caps at 2x expected length
            score = 1.0 - min(0.5, (ratio - 1) / 2)
        
        return max(0.0, min(1.0, score))
    
    def _calculate_entropy_score(self, text: str) -> float:
        """
        Calculate Shannon entropy (vocabulary diversity).
        
        Args:
            text: Chunk text
            
        Returns:
            Normalized entropy score between 0 and 1
        """
        # Tokenize text into words
        words = re.findall(r'\b\w+\b', text.lower())
        
        if len(words) == 0:
            return 0.0
        
        # Count word frequencies
        word_counts = Counter(words)
        total_words = len(words)
        
        # Calculate probabilities
        probabilities = np.array([count / total_words for count in word_counts.values()])
        
        # Calculate Shannon entropy
        shannon_entropy = entropy(probabilities, base=2)
        
        # Normalize by maximum possible entropy (all words unique)
        max_entropy = np.log2(len(word_counts)) if len(word_counts) > 1 else 1
        normalized_entropy = shannon_entropy / max_entropy if max_entropy > 0 else 0
        
        # Type-token ratio as additional diversity measure
        type_token_ratio = len(word_counts) / total_words
        
        # Combine entropy and TTR
        diversity_score = (normalized_entropy * 0.7) + (type_token_ratio * 0.3)
        
        return max(0.0, min(1.0, diversity_score))
    
    def _calculate_content_score(self, text: str) -> float:
        """
        Calculate ratio of content vs boilerplate.
        
        Args:
            text: Chunk text
            
        Returns:
            Score between 0 and 1
        """
        lines = text.split('\n')
        total_lines = len([l for l in lines if l.strip()])
        
        if total_lines == 0:
            return 0.0
        
        boilerplate_lines = 0
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            # Check against boilerplate patterns
            for pattern in self.boilerplate_patterns:
                if pattern.search(line):
                    boilerplate_lines += 1
                    break
        
        content_ratio = 1.0 - (boilerplate_lines / total_lines)
        
        # Also check for repetitive content
        unique_lines = len(set(l.strip() for l in lines if l.strip()))
        uniqueness_ratio = unique_lines / total_lines
        
        # Combine content and uniqueness
        score = (content_ratio * 0.7) + (uniqueness_ratio * 0.3)
        
        return max(0.0, min(1.0, score))
    
    def _calculate_quote_penalty(self, chunk: DocumentChunk) -> float:
        """
        Calculate quote penalty based on quote depth.
        
        Args:
            chunk: Document chunk
            
        Returns:
            Penalty value between 0 and 1
        """
        quote_depth = chunk.quote_depth or 0
        penalty = quote_depth * self.settings.quote_penalty_factor
        return min(1.0, penalty)  # Cap at 1.0
    
    def score(self, chunk: DocumentChunk) -> float:
        """
        Compute quality score for a chunk.
        
        Args:
            chunk: Document chunk to score
            
        Returns:
            Quality score between 0 and 1
        """
        # Hard exclusions - return 0 immediately
        if len(chunk.text) < self.settings.min_char_length:
            logger.debug(f"Chunk {chunk.chunk_id} excluded: too short ({len(chunk.text)} chars)")
            return 0.0
        
        if chunk.token_count < self.settings.min_token_count:
            logger.debug(f"Chunk {chunk.chunk_id} excluded: too few tokens ({chunk.token_count})")
            return 0.0
        
        if self._is_headers_only(chunk.text):
            logger.debug(f"Chunk {chunk.chunk_id} excluded: headers only")
            return 0.0
        
        if self._is_signature_only(chunk.text):
            logger.debug(f"Chunk {chunk.chunk_id} excluded: signature only")
            return 0.0
        
        # Calculate component scores
        length_score = self._calculate_length_score(chunk)
        entropy_score = self._calculate_entropy_score(chunk.text)
        content_score = self._calculate_content_score(chunk.text)
        quote_penalty = self._calculate_quote_penalty(chunk)
        
        # Apply formula
        quality_score = (
            self.settings.length_weight * length_score +
            self.settings.entropy_weight * entropy_score +
            self.settings.content_weight * content_score +
            self.settings.quote_weight * (1 - quote_penalty)
        )
        
        # Ensure score is in valid range
        quality_score = max(0.0, min(1.0, quality_score))
        
        logger.debug(
            f"Chunk {chunk.chunk_id} scored {quality_score:.3f} "
            f"(len={length_score:.2f}, ent={entropy_score:.2f}, "
            f"con={content_score:.2f}, quo={1-quote_penalty:.2f})"
        )
        
        # Update chunk's quality score
        chunk.quality_score = quality_score
        
        return quality_score
    
    def is_acceptable(self, chunk: DocumentChunk) -> bool:
        """
        Check if chunk meets minimum quality threshold.
        
        Args:
            chunk: Document chunk
            
        Returns:
            True if quality score >= threshold
        """
        score = chunk.quality_score if chunk.quality_score is not None else self.score(chunk)
        return score >= self.settings.min_quality_score


def quality_gate(
    min_score: Optional[float] = None,
    settings: Optional[QualitySettings] = None
) -> Callable:
    """
    Decorator to filter chunks by quality score.
    
    Args:
        min_score: Minimum quality score (overrides settings)
        settings: Quality settings to use
        
    Returns:
        Decorated generator function
    """
    def decorator(func: Callable[..., Generator[DocumentChunk, None, None]]) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs) -> Generator[DocumentChunk, None, None]:
            # Initialize scorer
            scorer_settings = settings or QualitySettings()
            if min_score is not None:
                scorer_settings.min_quality_score = min_score
            
            scorer = ChunkQualityScorer(scorer_settings)
            
            # Track statistics
            total_chunks = 0
            passed_chunks = 0
            
            # Process chunks from generator
            for chunk in func(*args, **kwargs):
                total_chunks += 1
                
                # Score chunk if not already scored
                if chunk.quality_score is None:
                    scorer.score(chunk)
                
                # Check threshold
                if scorer.is_acceptable(chunk):
                    passed_chunks += 1
                    yield chunk
                else:
                    logger.debug(
                        f"Chunk {chunk.chunk_id} filtered: "
                        f"score {chunk.quality_score:.3f} < {scorer_settings.min_quality_score}"
                    )
            
            # Log statistics
            if total_chunks > 0:
                pass_rate = passed_chunks / total_chunks * 100
                logger.info(
                    f"Quality gate: {passed_chunks}/{total_chunks} chunks passed "
                    f"({pass_rate:.1f}%) with threshold {scorer_settings.min_quality_score}"
                )
        
        return wrapper
    return decorator


def main():
    """CLI interface for testing quality scoring."""
    import argparse
    import json
    from pathlib import Path
    
    # Import chunker
    from src.chunker.document_chunker import DocumentChunker, DocumentType
    
    parser = argparse.ArgumentParser(description="Quality scorer CLI")
    parser.add_argument("--file", required=True, help="File to process")
    parser.add_argument("--doc-type", default="general",
                       choices=["email", "legal_pdf", "ocr_scan", "general"],
                       help="Document type")
    parser.add_argument("--threshold", type=float, default=0.35,
                       help="Quality score threshold")
    parser.add_argument("--output", help="Output JSON file")
    parser.add_argument("--verbose", action="store_true",
                       help="Enable verbose output")
    
    args = parser.parse_args()
    
    # Set up logging
    if args.verbose:
        logger.remove()
        logger.add(lambda msg: print(msg, end=""), level="DEBUG")
    else:
        logger.remove()
        logger.add(lambda msg: print(msg, end=""), level="INFO")
    
    # Read input file
    file_path = Path(args.file)
    if not file_path.exists():
        print(f"Error: File {file_path} not found")
        return 1
    
    with open(file_path, 'r', encoding='utf-8') as f:
        text = f.read()
    
    # Map string to enum
    doc_type_map = {
        "email": DocumentType.EMAIL,
        "legal_pdf": DocumentType.LEGAL_PDF,
        "ocr_scan": DocumentType.OCR_SCAN,
        "general": DocumentType.GENERAL
    }
    doc_type = doc_type_map[args.doc_type]
    
    # Create chunker and scorer
    chunker = DocumentChunker()
    settings = QualitySettings(min_quality_score=args.threshold)
    scorer = ChunkQualityScorer(settings)
    
    # Process document
    chunks = list(chunker.chunk_document(text, file_path.stem, doc_type))
    
    # Score chunks
    passed_chunks = []
    for chunk in chunks:
        score = scorer.score(chunk)
        
        print(f"\nChunk {chunk.chunk_idx}: Score = {score:.3f}")
        print(f"  Tokens: {chunk.token_count}")
        print(f"  Quote depth: {chunk.quote_depth}")
        print(f"  Preview: {chunk.text[:100]}...")
        
        if score >= args.threshold:
            print(f"  ✅ PASSED (>= {args.threshold})")
            passed_chunks.append(chunk)
        else:
            print(f"  ❌ FILTERED (< {args.threshold})")
    
    print("\n" + "=" * 50)
    print(f"Summary: {len(passed_chunks)}/{len(chunks)} chunks passed quality threshold")
    
    # Save to JSON if requested
    if args.output:
        output_data = [
            {
                "chunk_id": chunk.chunk_id,
                "chunk_idx": chunk.chunk_idx,
                "quality_score": chunk.quality_score,
                "token_count": chunk.token_count,
                "text": chunk.text[:200] + "..." if len(chunk.text) > 200 else chunk.text
            }
            for chunk in passed_chunks
        ]
        
        with open(args.output, 'w', encoding='utf-8') as f:
            json.dump(output_data, f, indent=2)
        print(f"\nSaved passed chunks to {args.output}")
    
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main())