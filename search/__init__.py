"""
Simple Search Coordination Module

Provides unified search interface combining keyword and semantic search.
"""

from .main import search, semantic_search, vector_store_available

__all__ = ["search", "semantic_search", "vector_store_available"]