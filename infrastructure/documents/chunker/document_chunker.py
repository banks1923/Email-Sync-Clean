#!/usr/bin/env python3
"""Document chunking module for semantic search v2.

Splits documents into 900-1100 token chunks with sentence awareness and
overlap.
"""

import re
from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, Generator, List, Optional

import sentencepiece as spm
import spacy
import tiktoken
from boilerpy3 import extractors
from loguru import logger
from spacy.lang.en import English

# Import quality scorer if available
try:
    from ..quality.quality_score import ChunkQualityScorer
    QUALITY_SCORING_AVAILABLE = True
except ImportError:
    QUALITY_SCORING_AVAILABLE = False
    logger.debug("Quality scoring module not available")

# Constants
DEFAULT_TARGET_TOKENS = 1000
DEFAULT_MIN_TOKENS = 900
DEFAULT_MAX_TOKENS = 1100
DEFAULT_OVERLAP_RATIO = 0.15
MIN_CHUNK_TOKENS = 100

class DocumentType(Enum):
    """
    Document type enumeration.
    """
    EMAIL = "email"
    LEGAL_PDF = "legal_pdf"
    OCR_SCAN = "ocr_scan"
    GENERAL = "general"


@dataclass
class DocumentChunk:
    """
    Represents a single document chunk with metadata.
    """
    doc_id: str
    chunk_idx: int
    text: str
    token_count: int
    token_start: int
    token_end: int
    section_title: Optional[str] = None
    quote_depth: int = 0
    chunk_id: Optional[str] = None
    quality_score: Optional[float] = None
    doc_type: Optional[DocumentType] = None
    
    def __post_init__(self):
        """
        Generate chunk_id if not provided.
        """
        if not self.chunk_id:
            self.chunk_id = f"{self.doc_id}:{self.chunk_idx}"


class DocumentChunker:
    """Token-based document chunker with sentence awareness.

    Creates chunks of 900-1100 tokens with ~15% overlap.
    """
    
    def __init__(
        self,
        target_tokens: int = DEFAULT_TARGET_TOKENS,
        min_tokens: int = DEFAULT_MIN_TOKENS,
        max_tokens: int = DEFAULT_MAX_TOKENS,
        overlap_ratio: float = DEFAULT_OVERLAP_RATIO,
        model_name: str = "cl100k_base",
        enable_quality_scoring: bool = True,
        quality_threshold: Optional[float] = None
    ):
        """Initialize the document chunker.

        Args:
            target_tokens: Target token count per chunk
            min_tokens: Minimum tokens per chunk
            max_tokens: Maximum tokens per chunk
            overlap_ratio: Ratio of overlap between chunks
            model_name: Tokenizer model name
            enable_quality_scoring: Whether to compute quality scores
            quality_threshold: Optional quality threshold (uses default if None)
        """
        self.target_tokens = target_tokens
        self.min_tokens = min_tokens
        self.max_tokens = max_tokens
        self.overlap_ratio = overlap_ratio
        self.enable_quality_scoring = enable_quality_scoring and QUALITY_SCORING_AVAILABLE
        
        # Initialize quality scorer if requested
        self.quality_scorer = None
        if self.enable_quality_scoring:
            try:
                if quality_threshold is not None:
                    from ..quality.quality_score import QualitySettings
                    settings = QualitySettings(min_quality_score=quality_threshold)
                    self.quality_scorer = ChunkQualityScorer(settings)
                else:
                    self.quality_scorer = ChunkQualityScorer()
                logger.debug("Quality scoring enabled")
            except Exception as e:
                logger.warning(f"Failed to initialize quality scorer: {e}")
                self.enable_quality_scoring = False
        
        # Initialize tokenizer
        try:
            self.tokenizer = tiktoken.get_encoding(model_name)
            self.use_tiktoken = True
            logger.debug(f"Using tiktoken with {model_name} encoding")
        except Exception as e:
            logger.warning(f"Failed to load tiktoken: {e}, falling back to sentencepiece")
            # Fallback to sentencepiece for unknown models
            self.spm_model = spm.SentencePieceProcessor()
            # Use a simple unigram model as fallback
            self.use_tiktoken = False
            
        # Initialize spaCy for sentence detection
        try:
            # Try to load existing model
            self.nlp = spacy.load("en_core_web_sm", disable=["ner", "lemmatizer", "tagger"])
        except OSError:
            # Fallback to blank English model
            self.nlp = English()
        
        # Add sentencizer for fast sentence detection
        if "sentencizer" not in self.nlp.pipe_names:
            self.nlp.add_pipe("sentencizer")
        
        logger.info(f"DocumentChunker initialized: target={target_tokens}, overlap={overlap_ratio}")
    
    def _count_tokens(self, text: str) -> int:
        """
        Count tokens in text.
        """
        if self.use_tiktoken:
            return len(self.tokenizer.encode(text))
        else:
            # Simple word-based approximation as fallback
            # Roughly 1.3 tokens per word is typical
            return int(len(text.split()) * 1.3)
    
    def _pre_split_document(self, text: str, doc_type: DocumentType) -> List[str]:
        """Pre-split document based on type-specific patterns.

        Args:
            text: Document text
            doc_type: Type of document

        Returns:
            List of text segments
        """
        segments = []
        
        if doc_type == DocumentType.EMAIL:
            # Split on forward/reply separators
            patterns = [
                r'^\s*[-]{3,}\s*Original Message\s*[-]{3,}',
                r'^\s*On .+ wrote:',
                r'^From:.*?Subject:.*?$',
                r'^[-]{3,}\s*Forwarded message\s*[-]{3,}',
            ]
            combined_pattern = '|'.join(f'({p})' for p in patterns)
            
            # Split but keep separators
            parts = re.split(f'({combined_pattern})', text, flags=re.MULTILINE)
            current_segment = ""
            
            for part in parts:
                if part and re.match(combined_pattern, part, re.MULTILINE):
                    if current_segment.strip():
                        segments.append(current_segment.strip())
                    current_segment = part
                elif part:
                    current_segment += part
            
            if current_segment.strip():
                segments.append(current_segment.strip())
                
        elif doc_type == DocumentType.LEGAL_PDF:
            # Split on section headers (ALL CAPS lines)
            lines = text.split('\n')
            current_segment = []
            
            for line in lines:
                # Check if line is a section header
                if line.strip() and line.isupper() and len(line.strip()) > 3:
                    # Save current segment
                    if current_segment:
                        segments.append('\n'.join(current_segment))
                    # Start new segment with header
                    current_segment = [line]
                else:
                    current_segment.append(line)
            
            if current_segment:
                segments.append('\n'.join(current_segment))
                
        elif doc_type == DocumentType.OCR_SCAN:
            # Use boilerpy3 to remove boilerplate
            try:
                extractor = extractors.ArticleExtractor()
                cleaned_text = extractor.get_content(text)
                if cleaned_text:
                    segments = [cleaned_text]
                else:
                    segments = [text]
            except Exception as e:
                logger.warning(f"Boilerplate extraction failed: {e}")
                segments = [text]
        else:
            # For general documents, use the whole text
            segments = [text]
        
        # Filter out empty segments
        segments = [s for s in segments if s.strip()]
        
        logger.debug(f"Pre-split {doc_type.value} into {len(segments)} segments")
        return segments if segments else [text]
    
    def _find_sentence_boundary(self, text: str, target_pos: int, backward: bool = True) -> int:
        """Find nearest sentence boundary to target position.

        Args:
            text: Text to search
            target_pos: Target character position
            backward: Search backward (True) or forward (False)

        Returns:
            Position of sentence boundary
        """
        # Process text with spaCy
        doc = self.nlp(text[:target_pos + 200] if backward else text[max(0, target_pos - 200):])
        
        # Get sentence boundaries
        sentences = list(doc.sents)
        if not sentences:
            return target_pos
        
        # Find closest sentence boundary
        if backward:
            # Find last complete sentence before target
            char_count = 0
            for sent in sentences:
                sent_end = char_count + len(sent.text)
                if sent_end > target_pos:
                    return char_count if char_count > 0 else target_pos
                char_count = sent_end
            return char_count
        else:
            # Find next sentence start after target
            if not backward:
                offset = max(0, target_pos - 200)
                char_count = 0
                for sent in sentences:
                    sent_start = offset + char_count
                    if sent_start >= target_pos:
                        return sent_start
                    char_count += len(sent.text)
            return target_pos
    
    def _create_chunk_with_overlap(
        self,
        segment: str,
        start_pos: int,
        chunk_tokens: int,
        overlap_tokens: int,
        _
    ) -> tuple[str, int, int]:
        """Create a chunk with overlap handling.

        Returns:
            Tuple of (chunk_text, actual_start_pos, actual_end_pos)
        """
        # Simple character-based approximation
        # Roughly 4 characters per token is typical
        chars_per_token = 4
        
        # Calculate positions
        end_pos = min(start_pos + chunk_tokens * chars_per_token, len(segment))
        
        # Find sentence boundary
        if end_pos < len(segment):
            end_pos = self._find_sentence_boundary(segment, end_pos, backward=True)
        
        chunk_text = segment[start_pos:end_pos].strip()
        
        # Calculate next start position with overlap
        next_start = max(start_pos, end_pos - overlap_tokens * chars_per_token)
        
        return chunk_text, start_pos, next_start
    
    def chunk_document(
        self,
        text: str,
        doc_id: str,
        doc_type: DocumentType = DocumentType.GENERAL,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Generator[DocumentChunk, None, None]:
        """Chunk a document into token-based segments.

        Args:
            text: Document text to chunk
            doc_id: Document identifier
            doc_type: Type of document
            metadata: Optional metadata dictionary

        Yields:
            DocumentChunk objects
        """
        if not text or not text.strip():
            logger.warning(f"Empty document {doc_id}, skipping")
            return
        
        # Pre-split based on document type
        segments = self._pre_split_document(text, doc_type)
        
        chunk_idx = 0
        global_token_offset = 0
        overlap_tokens = int(self.target_tokens * self.overlap_ratio)
        
        for segment_idx, segment in enumerate(segments):
            if not segment.strip():
                continue
            
            # Extract section title if present (first line of segment)
            lines = segment.split('\n', 1)
            section_title = lines[0].strip() if lines[0].strip() and len(lines[0]) < 100 else None
            
            # Detect quote depth for email segments
            quote_depth = 0
            if doc_type == DocumentType.EMAIL:
                # Count leading '>' characters
                for line in segment.split('\n')[:5]:  # Check first 5 lines
                    quote_markers = len(line) - len(line.lstrip('>'))
                    quote_depth = max(quote_depth, quote_markers)
            
            # Process segment into chunks
            segment_tokens = self._count_tokens(segment)
            
            if segment_tokens <= self.max_tokens:
                # Segment fits in single chunk
                chunk = DocumentChunk(
                    doc_id=doc_id,
                    chunk_idx=chunk_idx,
                    text=segment,
                    token_count=segment_tokens,
                    token_start=global_token_offset,
                    token_end=global_token_offset + segment_tokens,
                    section_title=section_title,
                    quote_depth=quote_depth
                )
                
                # Apply quality scoring if enabled
                if self.enable_quality_scoring and self.quality_scorer:
                    self.quality_scorer.score(chunk)
                
                yield chunk
                chunk_idx += 1
                global_token_offset += segment_tokens
            else:
                # Split segment into multiple chunks with overlap
                pos = 0
                segment_chunk_start = global_token_offset
                
                while pos < len(segment):
                    # Calculate chunk size
                    remaining = segment[pos:]
                    remaining_tokens = self._count_tokens(remaining)
                    
                    if remaining_tokens <= MIN_CHUNK_TOKENS:
                        # Don't create tiny chunks
                        break
                    
                    # Create chunk with overlap
                    chunk_text, actual_start, next_pos = self._create_chunk_with_overlap(
                        segment, pos, self.target_tokens, overlap_tokens, segment_chunk_start
                    )
                    
                    if not chunk_text.strip():
                        break
                    
                    chunk_tokens = self._count_tokens(chunk_text)
                    
                    # Skip chunks that are too small unless it's the last one
                    if chunk_tokens < MIN_CHUNK_TOKENS and next_pos < len(segment):
                        pos = next_pos
                        continue
                    
                    chunk = DocumentChunk(
                        doc_id=doc_id,
                        chunk_idx=chunk_idx,
                        text=chunk_text,
                        token_count=chunk_tokens,
                        token_start=segment_chunk_start,
                        token_end=segment_chunk_start + chunk_tokens,
                        section_title=section_title if pos == 0 else None,
                        quote_depth=quote_depth,
                        doc_type=doc_type
                    )
                    
                    # Apply quality scoring if enabled
                    if self.enable_quality_scoring and self.quality_scorer:
                        self.quality_scorer.score(chunk)
                    
                    yield chunk
                    
                    chunk_idx += 1
                    segment_chunk_start += chunk_tokens - overlap_tokens
                    pos = next_pos
                    
                    # Break if we've processed the whole segment
                    if pos >= len(segment) - 10:  # Allow small remainder
                        break
                
                global_token_offset = segment_chunk_start
        
        logger.info(f"Chunked document {doc_id} into {chunk_idx} chunks")


def main():
    """
    CLI interface for testing the chunker.
    """
    import argparse
    import json
    from pathlib import Path
    
    parser = argparse.ArgumentParser(description="Document chunker CLI")
    parser.add_argument("--file", required=True, help="File to chunk")
    parser.add_argument("--doc-type", default="general",
                       choices=["email", "legal_pdf", "ocr_scan", "general"],
                       help="Document type")
    parser.add_argument("--doc-id", help="Document ID (defaults to filename)")
    parser.add_argument("--target-tokens", type=int, default=1000,
                       help="Target tokens per chunk")
    parser.add_argument("--overlap", type=float, default=0.15,
                       help="Overlap ratio between chunks")
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
    
    # Determine doc_id
    doc_id = args.doc_id or file_path.stem
    
    # Map string to enum
    doc_type_map = {
        "email": DocumentType.EMAIL,
        "legal_pdf": DocumentType.LEGAL_PDF,
        "ocr_scan": DocumentType.OCR_SCAN,
        "general": DocumentType.GENERAL
    }
    doc_type = doc_type_map[args.doc_type]
    
    # Create chunker
    chunker = DocumentChunker(
        target_tokens=args.target_tokens,
        overlap_ratio=args.overlap
    )
    
    # Chunk document
    chunks = list(chunker.chunk_document(text, doc_id, doc_type))
    
    # Display results
    print(f"\nChunked into {len(chunks)} chunks:")
    print("-" * 50)
    
    for chunk in chunks:
        print(f"Chunk {chunk.chunk_idx}: {chunk.token_count} tokens")
        print(f"  Range: [{chunk.token_start}:{chunk.token_end}]")
        if chunk.section_title:
            print(f"  Section: {chunk.section_title}")
        if chunk.quote_depth > 0:
            print(f"  Quote depth: {chunk.quote_depth}")
        print(f"  Preview: {chunk.text[:100]}...")
        print()
    
    # Save to JSON if requested
    if args.output:
        output_data = [
            {
                "chunk_id": chunk.chunk_id,
                "chunk_idx": chunk.chunk_idx,
                "token_count": chunk.token_count,
                "token_start": chunk.token_start,
                "token_end": chunk.token_end,
                "section_title": chunk.section_title,
                "quote_depth": chunk.quote_depth,
                "text": chunk.text
            }
            for chunk in chunks
        ]
        
        with open(args.output, 'w', encoding='utf-8') as f:
            json.dump(output_data, f, indent=2)
        print(f"Saved chunks to {args.output}")
    
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main())