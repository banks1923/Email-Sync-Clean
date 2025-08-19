"""
Entity Extraction Utility Service

Focused utility service for entity extraction and caching.
Provides clean, direct functions for entity operations.

Public API:
- extract_entities: Extract entities from text content
- cache_entities: Cache entities in database with TTL
- get_cached_entities: Retrieve cached entities  
- extract_and_cache_entities: Main extraction function with caching
"""

from .main import (
    extract_entities,
    cache_entities,
    get_cached_entities,
    extract_and_cache_entities,
)

__version__ = "0.1.0"
__all__ = [
    "extract_entities",
    "cache_entities", 
    "get_cached_entities",
    "extract_and_cache_entities",
]