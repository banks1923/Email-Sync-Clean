"""Search Intelligence Module - Semantic-Only.

Minimal semantic search API with literal pattern matching helper.
Pure semantic search using Legal BERT 1024D embeddings and Qdrant.
"""

from typing import List, Optional, Dict, Any

# Import the core functions from basic_search
from .basic_search import search as _semantic_search
from .basic_search import find_literal as _find_literal
from .basic_search import vector_store_available


def search(
    query: str, 
    limit: int = 10,
    filters: Optional[Dict[str, Any]] = None
) -> List[dict]:
    """Semantic vector search using Legal BERT embeddings.
    
    This is the primary search interface - uses 1024D Legal BERT embeddings
    with cosine similarity in Qdrant vector store.
    
    Args:
        query: Search query text
        limit: Maximum number of results (default: 10)
        filters: Optional filters dict with:
            - source_type: Filter by document type
            - date_range: Dict with 'start' and/or 'end' dates
            - party: Filter by party name
            - tags: Filter by tags (string or list)
    
    Returns:
        List of semantically similar documents with scores
    
    Example:
        results = search("lease agreement", limit=5, filters={
            "source_type": "email_message",
            "date_range": {"start": "2024-01-01"}
        })
    """
    return _semantic_search(query, limit, filters)


def find_literal(
    pattern: str,
    limit: int = 50,
    fields: Optional[list] = None
) -> List[dict]:
    """Find documents containing exact patterns.
    
    Use this for finding specific identifiers that need exact matching:
    - BATES IDs (BATES-12345)
    - Section codes (§1234)  
    - Email addresses
    - Phone numbers
    - Invoice/case numbers
    - UUIDs
    
    This is NOT a replacement for semantic search - it's a helper for
    finding exact tokens that semantic search might miss.
    
    Args:
        pattern: The exact pattern to search for (SQL LIKE wildcards supported)
        limit: Maximum results (default: 50)
        fields: Fields to search in (default: body, metadata fields)
    
    Returns:
        List of documents containing the exact pattern
    
    Example:
        # Find documents with a specific BATES number
        docs = find_literal("BATES-00123")
        
        # Find documents mentioning a specific statute
        docs = find_literal("§1983")
    """
    return _find_literal(pattern, limit, fields)


__all__ = [
    "search",
    "find_literal", 
    "vector_store_available",
]