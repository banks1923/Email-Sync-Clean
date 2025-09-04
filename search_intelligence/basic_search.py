"""Semantic-Only Search Module.

Pure semantic vector search using Legal BERT embeddings and Qdrant.
No keyword search, no hybrid merging, no modes - just clean semantic search.
"""

from typing import Any, Optional

from loguru import logger

from shared.db.simple_db import SimpleDB
from utilities.embeddings import get_embedding_service
from utilities.vector_store import get_vector_store


def search(
    query: str,
    limit: int = 10,
    filters: dict | None = None,
) -> list[dict[str, Any]]:
    """Semantic vector search only.

    Args:
        query: Search query string
        limit: Maximum results to return
        filters: Optional filters (date, source_type, party, tags)

    Returns:
        Semantically similar documents from vector search
    """
    logger.debug(f"Semantic search: '{query}' limit={limit}")
    
    # Pure semantic search - no fallback, no merging
    if not vector_store_available():
        logger.warning("Vector store unavailable - no results possible")
        return []
    
    try:
        results = semantic_search(query, limit, filters)
        logger.debug(f"Semantic search returned {len(results)} results")
        return results
    except Exception as e:
        logger.error(f"Semantic search failed: {e}")
        return []


def semantic_search(
    query: str,
    limit: int = 10,
    filters: dict | None = None,
) -> list[dict[str, Any]]:
    """Perform semantic vector search.

    Args:
        query: Search query string
        limit: Maximum results to return
        filters: Optional filters for vector search

    Returns:
        List of semantically similar documents
    """
    try:
        # Generate query embedding (1024D Legal BERT)
        embedding_service = get_embedding_service()
        query_vector = embedding_service.encode(query).tolist()

        # Search vector store - vectors_v2 collection, cosine similarity
        vector_store = get_vector_store("vectors_v2")

        # Build vector filters from search filters
        vector_filters = _build_vector_filters(filters) if filters else None

        vector_results = vector_store.search(
            vector=query_vector, 
            limit=limit, 
            filter=vector_filters
        )

        # Enrich results with database content
        enriched_results = _enrich_vector_results(vector_results)

        logger.debug(f"Semantic search found {len(enriched_results)} results")
        return enriched_results

    except Exception as e:
        logger.error(f"Semantic search failed: {e}")
        return []


def vector_store_available() -> bool:
    """Check if vector store is available and working.

    Returns:
        True if vector store can be used, False otherwise
    """
    try:
        # Check availability against active collection
        vector_store = get_vector_store("vectors_v2")
        # Simple test - try to get collection info
        vector_store.count()
        return True
    except Exception as e:
        logger.debug(f"Vector store not available: {e}")
        return False


def _build_vector_filters(filters: dict) -> dict | None:
    """Convert search filters to vector store format.
    
    Supported filters:
    - source_type: Filter by document type
    - date_range: Filter by date
    - party: Filter by party name
    - tags: Filter by tags
    """
    if not filters:
        return None

    vector_filters = {}

    # Map source_type filter
    if "source_type" in filters:
        vector_filters["source_type"] = filters["source_type"]

    # Map date range filters
    if "date_range" in filters:
        date_range = filters["date_range"]
        if isinstance(date_range, dict):
            range_filter = {}
            if "start" in date_range:
                range_filter["gte"] = date_range["start"]
            if "end" in date_range:
                range_filter["lte"] = date_range["end"]
            if range_filter:
                vector_filters["created_at"] = range_filter

    # Map party filter
    if "party" in filters:
        vector_filters["party"] = filters["party"]

    # Map tags filter
    if "tags" in filters:
        tags = filters["tags"]
        if isinstance(tags, list):
            vector_filters["tags"] = {"any": tags}
        else:
            vector_filters["tags"] = tags

    return vector_filters if vector_filters else None


def _enrich_vector_results(vector_results: list[dict]) -> list[dict[str, Any]]:
    """Enrich vector search results with database content."""
    if not vector_results:
        return []

    try:
        db = SimpleDB()
        enriched = []

        for i, result in enumerate(vector_results):
            payload = result.get("payload", {})
            content_id = payload.get("content_id")
            content = None

            if content_id is not None:
                try:
                    # Look up content in content_unified table, preferring substantive_text
                    content_rows = db.fetch(
                        "SELECT id, source_id, source_type, title, body, substantive_text FROM content_unified WHERE id = ? LIMIT 1",
                        (int(content_id),),
                    )

                    if content_rows:
                        row = content_rows[0]
                        # Prefer substantive_text if available, otherwise use body
                        content_text = row["substantive_text"] if row.get("substantive_text") else row["body"]
                        content = {
                            "content_id": str(row["id"]),
                            "source_id": row["source_id"],
                            "source_type": row["source_type"],
                            "title": row["title"] or "No title",
                            "content": content_text or "No content",
                        }

                        # Add metadata from payload if available
                        content["sender"] = payload.get("sender", "unknown")
                        content["datetime_utc"] = payload.get("datetime_utc")

                except (ValueError, TypeError) as e:
                    logger.debug(f"Failed to lookup content_id {content_id}: {e}")

            # Fallback: construct from payload if no content found
            if not content and payload:
                content = {
                    "content_id": result.get("id", "unknown"),
                    "source_id": payload.get("message_id", "unknown"),
                    "source_type": payload.get("source_type", "unknown"),
                    "title": payload.get("title", "No title"),
                    "sender": payload.get("sender", "unknown"),
                    "content": "Content not found in database",
                }

            if content:
                # Add vector search metadata
                content["semantic_score"] = result.get("score", 0.0)
                content["vector_id"] = result.get("id")
                enriched.append(content)

        return enriched
    except Exception as e:
        logger.error(f"Failed to enrich vector results: {type(e).__name__}: {e}")
        return []


def find_literal(
    pattern: str,
    limit: int = 50,
    fields: Optional[list] = None
) -> list[dict[str, Any]]:
    """Direct pattern matching for exact tokens.
    
    Use this for finding specific identifiers that need exact matching:
    - BATES IDs (BATES-12345)
    - Section codes (§1234)
    - Email addresses
    - Phone numbers
    - Invoice numbers
    - UUIDs
    
    Args:
        pattern: The pattern to search for (supports SQL LIKE wildcards)
        limit: Maximum results to return
        fields: Fields to search in (default: body, bates_id, case_no, citations)
    
    Returns:
        List of documents containing the exact pattern
    """
    if not pattern:
        return []
    
    fields = fields or ["body", "metadata"]
    
    try:
        db = SimpleDB()
        results = []
        
        # Build WHERE clause for each field
        where_clauses = []
        params = []
        
        for field in fields:
            if field == "body":
                where_clauses.append("body LIKE ?")
                params.append(f"%{pattern}%")
            elif field == "metadata":
                # Search in JSON metadata field
                where_clauses.append("json_extract(metadata, '$.bates_id') LIKE ?")
                params.append(f"%{pattern}%")
                where_clauses.append("json_extract(metadata, '$.case_no') LIKE ?")
                params.append(f"%{pattern}%")
                where_clauses.append("json_extract(metadata, '$.citations') LIKE ?")
                params.append(f"%{pattern}%")
            elif field in ["title", "source_id"]:
                where_clauses.append(f"{field} LIKE ?")
                params.append(f"%{pattern}%")
        
        if not where_clauses:
            return []
        
        # Execute query
        where_clause = " OR ".join(where_clauses)
        query = f"""
            SELECT id, source_id, source_type, title, body, substantive_text, metadata
            FROM content_unified
            WHERE {where_clause}
            ORDER BY created_at DESC
            LIMIT ?
        """
        params.append(limit)
        
        rows = db.fetch(query, tuple(params))
        
        # Format results
        for row in rows or []:
            # Prefer substantive_text if available, otherwise use body
            content_text = row["substantive_text"] if row.get("substantive_text") else row["body"]
            results.append({
                "content_id": str(row["id"]),
                "source_id": row["source_id"],
                "source_type": row["source_type"],
                "title": row["title"] or "No title",
                "content": content_text or "No content",
                "metadata": row.get("metadata"),
                "match_type": "literal",
            })
        
        logger.debug(f"Literal search for '{pattern}' found {len(results)} results")
        return results
        
    except Exception as e:
        logger.error(f"Literal search failed: {e}")
        return []