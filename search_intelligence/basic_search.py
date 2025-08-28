"""Simple Search Coordination Module.

Coordinates keyword + semantic search with graceful fallback. Direct
implementation following CLAUDE.md principles: Simple > Complex, Working
> Perfect.
"""

import os
from typing import Any

from loguru import logger

from shared.simple_db import SimpleDB
from utilities.embeddings import get_embedding_service
from utilities.vector_store import get_vector_store

# Feature flag for dynamic weighting
ENABLE_DYNAMIC_WEIGHTS = os.getenv("ENABLE_DYNAMIC_WEIGHTS", "true").lower() == "true"
ENABLE_CHUNK_AGGREGATION = os.getenv("ENABLE_CHUNK_AGGREGATION", "true").lower() == "true"
MIN_CHUNK_QUALITY = float(os.getenv("MIN_CHUNK_QUALITY", "0.35"))
MAX_RESULTS_PER_SOURCE = int(os.getenv("MAX_RESULTS_PER_SOURCE", "3"))


def calculate_weights(query: str) -> tuple[float, float]:
    """Calculate dynamic weights based on query characteristics.
    
    Short queries (1-3 words) benefit from keyword search precision.
    Long queries (4+ words) benefit from semantic understanding.
    Special patterns (emails, dates, quotes) favor keyword matching.
    
    Args:
        query: Search query string
        
    Returns:
        (keyword_weight, semantic_weight) tuple, summing to 1.0
    """
    # Clean and analyze query
    query_clean = query.strip().lower()
    words = query_clean.split()
    word_count = len(words)
    
    # Pattern detection
    has_email = '@' in query
    has_date = any(char.isdigit() for char in query)
    has_quotes = '"' in query
    
    # Base weights on word count
    if word_count <= 2:
        keyword_w, semantic_w = 0.7, 0.3
    elif word_count == 3:
        keyword_w, semantic_w = 0.5, 0.5
    else:  # 4+ words - favor semantic understanding
        keyword_w, semantic_w = 0.3, 0.7
    
    # Adjust for special patterns that need exact matching
    if has_email or has_quotes:  # Exact match likely wanted
        keyword_w += 0.15
        semantic_w -= 0.15
    elif has_date:  # Dates/numbers often need keyword precision
        keyword_w += 0.05
        semantic_w -= 0.05
    
    # Normalize to sum to 1.0 and clamp to valid range
    total = keyword_w + semantic_w
    keyword_w = max(0.1, min(0.9, keyword_w / total))
    semantic_w = 1.0 - keyword_w
    
    return (keyword_w, semantic_w)


def _group_chunks_by_document(chunks: list[dict]) -> dict[str, list[dict]]:
    """Group chunks by document ID extracted from source_id."""
    doc_groups = {}
    
    for chunk in chunks:
        source_id = chunk.get("source_id", "")
        # Extract document ID from chunk source_id format "doc_id:chunk_idx"
        doc_id = source_id.split(":")[0] if ":" in source_id else source_id
        
        if doc_id not in doc_groups:
            doc_groups[doc_id] = []
        doc_groups[doc_id].append(chunk)
    
    return doc_groups


def _aggregate_document_chunks(doc_groups: dict, top_chunks_per_doc: int = 3) -> list[dict]:
    """Aggregate chunks into document-level results."""
    aggregated_docs = []
    
    for doc_id, chunks in doc_groups.items():
        if not chunks:
            continue
            
        # Sort chunks by semantic score (highest first)
        sorted_chunks = sorted(chunks, 
                             key=lambda x: x.get("semantic_score", 0.0), 
                             reverse=True)
        
        # Take top N chunks per document
        top_chunks = sorted_chunks[:top_chunks_per_doc]
        best_chunk = top_chunks[0]
        
        # Create aggregated document result
        doc_result = {
            "content_id": best_chunk.get("content_id"),
            "source_id": doc_id,  # Use document ID, not chunk ID
            "source_type": "document",  # Aggregate as document-level
            "title": best_chunk.get("title", "No title"),
            "content": best_chunk.get("content", "No content"),
            "semantic_rank": best_chunk.get("semantic_rank", 999),
            "semantic_score": best_chunk.get("semantic_score", 0.0),
            "chunk_count": len(chunks),
            "top_chunks": [
                {
                    "chunk_id": chunk.get("source_id"),
                    "score": chunk.get("semantic_score", 0.0),
                    "preview": chunk.get("content", "")[:200] + "..."
                }
                for chunk in top_chunks
            ],
            "highest_quality_chunk": max(chunks, 
                                       key=lambda x: x.get("quality_score", 0.0))
        }
        
        aggregated_docs.append(doc_result)
    
    return aggregated_docs


def _enforce_result_diversity(results: list[dict]) -> list[dict]:
    """Enforce diversity by limiting results per source_type."""
    source_counts = {}
    filtered_results = []
    
    for result in results:
        source_type = result.get("source_type", "unknown")
        current_count = source_counts.get(source_type, 0)
        
        if current_count < MAX_RESULTS_PER_SOURCE:
            filtered_results.append(result)
            source_counts[source_type] = current_count + 1
    
    return filtered_results


def search(
    query: str,
    limit: int = 10,
    filters: dict | None = None,
    keyword_weight: float | None = None,
    semantic_weight: float | None = None,
    use_chunk_aggregation: bool = None,
) -> list[dict[str, Any]]:
    """Coordinate keyword + semantic search with RRF merging.

    Args:
        query: Search query string
        limit: Maximum results to return
        filters: Optional filters (date, content_type, etc.)
        keyword_weight: Weight for keyword results in RRF (0-1), auto-calculated if None
        semantic_weight: Weight for semantic results in RRF (0-1), auto-calculated if None
        use_chunk_aggregation: Enable chunk-to-document aggregation, uses env var if None

    Returns:
        Merged and ranked search results with optional chunk aggregation
    """
    logger.debug(f"Search request: '{query}' limit={limit}")
    
    # Calculate dynamic weights if not provided and feature enabled
    if ENABLE_DYNAMIC_WEIGHTS and (keyword_weight is None or semantic_weight is None):
        keyword_weight, semantic_weight = calculate_weights(query)
        logger.debug(f"Dynamic weights: keyword={keyword_weight:.2f}, semantic={semantic_weight:.2f}")
    elif keyword_weight is None or semantic_weight is None:
        # Fallback to default weights if dynamic weighting disabled
        keyword_weight, semantic_weight = 0.4, 0.6
        logger.debug("Using default weights: keyword=0.4, semantic=0.6")

    # Get keyword results
    keyword_results = _keyword_search(query, limit * 2, filters)
    logger.debug(f"Keyword search returned {len(keyword_results)} results")

    # Get semantic results (with graceful fallback)
    semantic_results = []
    if vector_store_available():
        try:
            semantic_results = semantic_search(query, limit * 2, filters, use_chunk_aggregation)
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
    use_chunk_aggregation: bool = None,
) -> list[dict[str, Any]]:
    """Perform semantic vector search with optional chunk aggregation.

    Args:
        query: Search query string
        limit: Maximum results to return
        filters: Optional filters for vector search
        use_chunk_aggregation: Override chunk aggregation setting

    Returns:
        List of semantically similar documents or aggregated chunks
    """
    try:
        # Determine if chunk aggregation should be used
        if use_chunk_aggregation is None:
            use_chunk_aggregation = ENABLE_CHUNK_AGGREGATION
            
        # Generate query embedding
        embedding_service = get_embedding_service()
        query_vector = embedding_service.encode(query).tolist()

        # Search vector store - request more results if aggregating chunks
        search_limit = limit * 4 if use_chunk_aggregation else limit
        vector_store = get_vector_store()

        # Build vector filters from search filters
        vector_filters = _build_vector_filters(filters) if filters else None
        
        # Add quality filter for chunks if aggregation enabled
        if use_chunk_aggregation and MIN_CHUNK_QUALITY > 0:
            quality_filter = {"quality_score": {"gte": MIN_CHUNK_QUALITY}}
            if vector_filters:
                vector_filters = {"must": [vector_filters, quality_filter]}
            else:
                vector_filters = quality_filter

        vector_results = vector_store.search(
            vector=query_vector, limit=search_limit, filter=vector_filters
        )

        # Enrich results with database content
        enriched_results = _enrich_vector_results(vector_results)
        
        # Apply chunk aggregation if enabled
        if use_chunk_aggregation and enriched_results:
            # Check if we have chunks (source_type='document_chunk')
            chunks = [r for r in enriched_results if r.get("source_type") == "document_chunk"]
            non_chunks = [r for r in enriched_results if r.get("source_type") != "document_chunk"]
            
            if chunks:
                # Group chunks by document and aggregate
                doc_groups = _group_chunks_by_document(chunks)
                aggregated_docs = _aggregate_document_chunks(doc_groups)
                
                # Combine aggregated documents with non-chunk results
                final_results = aggregated_docs + non_chunks
                
                # Sort by semantic score and apply diversity
                final_results.sort(key=lambda x: x.get("semantic_score", 0.0), reverse=True)
                final_results = _enforce_result_diversity(final_results)
                
                logger.debug(f"Chunk aggregation: {len(chunks)} chunks -> {len(aggregated_docs)} documents")
                return final_results[:limit]
        
        # Apply diversity enforcement even without chunk aggregation
        enriched_results = _enforce_result_diversity(enriched_results)

        logger.debug(f"Semantic search found {len(enriched_results)} results")
        return enriched_results[:limit]

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
