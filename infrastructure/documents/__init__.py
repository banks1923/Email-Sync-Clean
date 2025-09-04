"""Document Processing System.

Provides document chunking and quality scoring for semantic search.
Follows CLAUDE.md principles with simple, direct implementation.
"""

# Only import modules that actually exist
from .chunker.document_chunker import DocumentChunker, DocumentType
from .quality.quality_score import ChunkQualityScorer

__all__ = [
    "DocumentChunker",
    "DocumentType", 
    "ChunkQualityScorer",
]
