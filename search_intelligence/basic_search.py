"""Simple Search Coordination Module.

Coordinates keyword + semantic search with graceful fallback. Direct
implementation following CLAUDE.md principles: Simple > Complex, Working
> Perfect.
"""

from typing import Any

from loguru import logger

from shared.simple_db import SimpleDB
from utilities.embeddings import get_embedding_service
from utilities.vector_store import get_vector_store


def search(
    query: str,
    limit: int = 10,
    filters: dict | None = None,
    keyword_weight: float = 0.4,
    semantic_weight: float = 0.6,
) -> list[dict[str, Any]]:
    """Coordinate keyword + semantic search with RRF merging.

    Args:
        query: Search query string
        limit: Maximum results to return
        filters: Optional filters (date, content_type, etc.)
        keyword_weight: Weight for keyword results in RRF (0-1)
        semantic_weight: Weight for semantic results in RRF (0-1)

    Returns:
        Merged and ranked search results
    """
    logger.debug(f"Search request: '{query}' limit={limit}")

    # Get keyword results
    keyword_results = _keyword_search(query, limit * 2, filters)
    logger.debug(f"Keyword search returned {len(keyword_results)} results")

    # Get semantic results (with graceful fallback)
    semantic_results = []
    if vector_store_available():
        try:
            semantic_results = semantic_search(query, limit * 2, filters)
            logger.debug(f"Semantic search returned {len(semantic_results)} results")
        except Exception as e:
            logger.warning(f"Semantic search failed, using keyword only: {e}")
    else:
        logger.debug("Vector store unavailable, using keyword search only")

    # Merge results using RRF
    if semantic_results:
        merged_results = _merge_results_rrf(
            keyword_results, semantic_results, keyword_weight, semantic_weight
        )
        logger.debug(f"Merged {len(merged_results)} results using RRF")
    else:
        merged_results = keyword_results
        logger.debug("Using keyword results only")

    return merged_results[:limit]


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
        # Generate query embedding
        embedding_service = get_embedding_service()
        query_vector = embedding_service.encode(query).tolist()

        # Search vector store
        vector_store = get_vector_store()

        # Build vector filters from search filters
        vector_filters = _build_vector_filters(filters) if filters else None

        vector_results = vector_store.search(
            vector=query_vector, limit=limit, filter=vector_filters
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
        vector_store = get_vector_store()
        # Simple test - try to get collection info
        vector_store.count()
        return True
    except Exception as e:
        logger.debug(f"Vector store not available: {e}")
        return False


def _keyword_search(query: str, limit: int, filters: dict | None = None) -> list[dict[str, Any]]:
    """
    Perform keyword search using SimpleDB.
    """
    try:
        db = SimpleDB()
        raw_results = db.search_content(query, limit=limit, filters=filters)

        # Normalize results format to match semantic search expectations
        results = []
        for i, result in enumerate(raw_results):
            normalized = {
                "content_id": str(result["id"]),
                "source_id": result["source_id"],
                "source_type": result["source_type"],
                "title": result["title"] or "No title",
                "content": result["body"] or "No content",
                "keyword_rank": i + 1,
                "keyword_score": 1.0 / (i + 1),  # Simple relevance scoring
            }

            # Add additional metadata if available
            for field in ["sender", "datetime_utc", "created_at"]:
                if field in result:
                    normalized[field] = result[field]

            results.append(normalized)

        return results
    except Exception as e:
        logger.error(f"Keyword search failed: {e}")
        return []


def _build_vector_filters(filters: dict) -> dict | None:
    """
    Convert search filters to vector store format.
    """
    if not filters:
        return None

    vector_filters = {}

    # Map content_types to vector filter
    if "content_types" in filters:
        vector_filters["content_type"] = filters["content_types"][0]  # Take first for now

    # Map single content_type
    if "content_type" in filters:
        vector_filters["content_type"] = filters["content_type"]

    return vector_filters if vector_filters else None


def _enrich_vector_results(vector_results: list[dict]) -> list[dict[str, Any]]:
    """
    Enrich vector search results with database content.
    """
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
                    # Look up content in content_unified table using content_id (primary approach)
                    content_rows = db.fetch(
                        "SELECT id, source_id, source_type, title, body FROM content_unified WHERE id = ? LIMIT 1",
                        (int(content_id),),
                    )

                    if content_rows:
                        row = content_rows[0]
                        content = {
                            "content_id": str(row["id"]),
                            "source_id": row["source_id"],
                            "source_type": row["source_type"],
                            "title": row["title"] or "No title",
                            "content": row["body"] or "No content",
                        }

                        # Add sender and datetime from payload if available
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
                content["semantic_rank"] = i + 1
                content["semantic_score"] = result.get("score", 0.0)
                content["vector_id"] = result.get("id")
                enriched.append(content)

        return enriched
    except Exception as e:
        logger.error(f"Failed to enrich vector results: {type(e).__name__}: {e}")
        import traceback

        logger.debug(f"Traceback: {traceback.format_exc()}")
        return []


def _merge_results_rrf(
    keyword_results: list[dict],
    semantic_results: list[dict],
    keyword_weight: float = 0.4,
    semantic_weight: float = 0.6,
    k: int = 60,
) -> list[dict[str, Any]]:
    """Merge results using Reciprocal Rank Fusion (RRF).

    Args:
        keyword_results: Results from keyword search
        semantic_results: Results from semantic search
        keyword_weight: Weight for keyword results
        semantic_weight: Weight for semantic results
        k: RRF parameter (typically 60)

    Returns:
        Merged and ranked results
    """
    # Create lookup maps - use 'id' or 'content_id' as the key
    keyword_map = {
        r.get("content_id", r.get("id")): (i + 1, r) for i, r in enumerate(keyword_results)
    }
    semantic_map = {
        r.get("content_id", r.get("id")): (i + 1, r) for i, r in enumerate(semantic_results)
    }

    # Get all unique content IDs
    all_ids = set(keyword_map.keys()) | set(semantic_map.keys())

    # Calculate RRF scores
    rrf_scores = []
    for content_id in all_ids:
        keyword_rank, keyword_doc = keyword_map.get(content_id, (float("inf"), None))
        semantic_rank, semantic_doc = semantic_map.get(content_id, (float("inf"), None))

        # RRF formula with weights
        keyword_rrf = keyword_weight / (k + keyword_rank) if keyword_rank != float("inf") else 0
        semantic_rrf = semantic_weight / (k + semantic_rank) if semantic_rank != float("inf") else 0

        total_rrf = keyword_rrf + semantic_rrf

        # Use the document with more complete information
        doc = semantic_doc if semantic_doc else keyword_doc
        if doc:
            doc = doc.copy()  # Don't modify original
            doc["rrf_score"] = total_rrf
            doc["keyword_rank"] = keyword_rank if keyword_rank != float("inf") else None
            doc["semantic_rank"] = semantic_rank if semantic_rank != float("inf") else None
            rrf_scores.append(doc)

    # Sort by RRF score
    rrf_scores.sort(key=lambda x: x["rrf_score"], reverse=True)

    logger.debug(f"RRF merged {len(rrf_scores)} unique documents")
    return rrf_scores
