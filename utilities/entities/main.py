"""
Entity Extraction Utility Service

Focused utility service for entity extraction and caching.
Extracted from SearchIntelligenceService following CLAUDE.md principles.

Core Functions:
- extract_entities: Extract entities from text content
- cache_entities: Cache entities in database with TTL
- get_cached_entities: Retrieve cached entities
- extract_and_cache_entities: Main extraction function with caching
"""

import json
from datetime import datetime
from typing import Any

from loguru import logger

from entity.extractors.extractor_factory import ExtractorFactory
from shared.simple_db import SimpleDB


def extract_entities(content: str) -> list[dict]:
    """
    Extract entities from text content using SpaCy extractor.
    
    Args:
        content: Text content to extract entities from
        
    Returns:
        List of entity dictionaries
    """
    try:
        # Get the best available extractor (SpaCy)
        extractor = ExtractorFactory.get_best_available_extractor()
        
        # Extract entities using placeholder message_id
        result = extractor.extract_entities(content, message_id="content_search")
        
        # Return entities list or empty list if extraction failed
        if result.get("success"):
            return result.get("entities", [])
        else:
            logger.warning(f"Entity extraction failed: {result.get('error', 'Unknown error')}")
            return []
            
    except Exception as e:
        logger.error(f"Entity extraction failed: {e}")
        return []


def cache_entities(doc_id: str, entities: list[dict]) -> None:
    """
    Cache entities in relationship_cache table.
    
    Args:
        doc_id: Document ID to cache entities for
        entities: List of entity dictionaries to cache
    """
    try:
        db = SimpleDB()
        cache_data = json.dumps(entities)
        
        # Insert or update cache
        query = """
            INSERT OR REPLACE INTO relationship_cache
            (source_id, target_id, relationship_type, cached_data, created_at)
            VALUES (?, ?, 'entities', ?, datetime('now'))
        """
        db.execute(query, (doc_id, doc_id, cache_data))
        
    except Exception as e:
        logger.warning(f"Failed to cache entities for doc {doc_id}: {e}")


def get_cached_entities(doc_id: str) -> list[dict] | None:
    """
    Get cached entities from relationship_cache with TTL check.
    
    Args:
        doc_id: Document ID to retrieve cached entities for
        
    Returns:
        List of cached entities or None if not found/expired
    """
    try:
        db = SimpleDB()
        
        # Query relationship_cache
        query = """
            SELECT cached_data, created_at
            FROM relationship_cache
            WHERE source_id = ? AND relationship_type = 'entities'
            ORDER BY created_at DESC LIMIT 1
        """
        result = db.fetch(query, (doc_id,))
        
        if result:
            # Check TTL (7 days)
            created_at = datetime.fromisoformat(result[0][1])
            if (datetime.now() - created_at).days < 7:
                return json.loads(result[0][0])
        
        return None
        
    except Exception as e:
        logger.debug(f"Failed to get cached entities for doc {doc_id}: {e}")
        return None


def extract_and_cache_entities(
    doc_id: str, force_refresh: bool = False
) -> list[dict[str, Any]]:
    """
    Extract entities and cache in relationship_cache table.
    
    Main function that orchestrates entity extraction with caching.
    Checks cache first unless force_refresh is True.
    
    Args:
        doc_id: Document ID to extract entities from
        force_refresh: If True, skip cache and force fresh extraction
        
    Returns:
        List of entity dictionaries
    """
    try:
        # Check cache first
        if not force_refresh:
            cached = get_cached_entities(doc_id)
            if cached:
                logger.debug(f"Using cached entities for doc {doc_id}")
                return cached
        
        # Get document content
        db = SimpleDB()
        doc = db.get_content(content_id=doc_id)
        if not doc:
            logger.warning(f"Document {doc_id} not found")
            return []
        
        # Extract entities
        content = doc.get("content", "")
        if not content:
            logger.warning(f"No content found for doc {doc_id}")
            return []
            
        entities = extract_entities(content)
        
        # Cache results
        if entities:
            cache_entities(doc_id, entities)
            logger.debug(f"Cached {len(entities)} entities for doc {doc_id}")
        
        return entities
        
    except Exception as e:
        logger.error(f"Entity extraction and caching failed for doc {doc_id}: {e}")
        return []