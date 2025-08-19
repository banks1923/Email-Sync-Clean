#!/usr/bin/env python3
"""
Sync missing vectors between database and Qdrant.
Ensures DB and vector store have the same documents.
"""

import sys
import hashlib
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent.parent))

from qdrant_client import QdrantClient
from qdrant_client.models import PointStruct
from loguru import logger
from shared.simple_db import SimpleDB
from utilities.embeddings import get_embedding_service


def string_to_uuid(s: str) -> str:
    """Deterministic UUID v4-like string from arbitrary text."""
    h = hashlib.sha256(s.encode("utf-8")).hexdigest()
    return f"{h[:8]}-{h[8:12]}-{h[12:16]}-{h[16:20]}-{h[20:32]}"


def encode_point_id(original_id: str) -> str:
    """Wrapper for clarity at call sites."""
    return string_to_uuid(original_id)


def list_qdrant_ids(client: QdrantClient, collection: str) -> set[str]:
    """
    Return the set of original doc ids present in Qdrant.
    We rely on payload["doc_id"] (preferred) or payload["id"] as fallback.
    Points with no payload are skipped (cannot recover original id from UUID).
    """
    present: set[str] = set()
    next_offset = None
    
    while True:
        points, next_offset = client.scroll(
            collection_name=collection,
            limit=10_000,
            with_payload=True,
            with_vectors=False,
            offset=next_offset,
        )
        for p in points:
            payload = getattr(p, "payload", None) or {}
            raw = payload.get("doc_id") or payload.get("id") or payload.get("content_id")
            if raw is not None:
                present.add(str(raw))
        if not next_offset:
            break
    
    return present


def sync_missing_vectors(
    db: SimpleDB,
    client: QdrantClient,
    collection: str,
    embed_service
) -> dict:
    """Sync missing vectors from database to Qdrant.
    
    Args:
        db: SimpleDB instance
        client: Qdrant client
        collection: Collection name
        embed_service: Embedding service
        
    Returns:
        Dict with sync statistics
    """
    # Get all content from database
    db_content = db.search_content("", limit=10000)  # Get all
    
    # Build ID mapping (content_id is the key in db results)
    db_ids = {str(item['content_id']) for item in db_content}
    
    # Get all IDs from Qdrant (based on payload)
    qdrant_ids = list_qdrant_ids(client, collection)
    
    # Find missing IDs
    missing_ids = db_ids - qdrant_ids
    extra_ids = qdrant_ids - db_ids
    
    logger.info(f"Database has {len(db_ids)} documents")
    logger.info(f"Qdrant has {len(qdrant_ids)} vectors")
    logger.info(f"Missing in Qdrant: {len(missing_ids)}")
    logger.info(f"Extra in Qdrant: {len(extra_ids)}")
    
    if not missing_ids:
        return {
            "synced": 0,
            "db_count": len(db_ids),
            "qdrant_count": len(qdrant_ids),
            "missing": 0,
            "extra": len(extra_ids)
        }
    
    # Get content for missing IDs
    missing_content = [
        item for item in db_content 
        if str(item['content_id']) in missing_ids
    ]
    
    # Generate embeddings
    texts = [item.get('content', '') or '' for item in missing_content]
    logger.info(f"Generating embeddings for {len(texts)} documents...")
    
    embeddings = embed_service.get_embeddings(texts)
    
    # Create points for Qdrant with UUID point IDs
    points = []
    for item, embedding in zip(missing_content, embeddings):
        original_id = str(item['content_id'])
        points.append(
            PointStruct(
                id=encode_point_id(original_id),  # Qdrant point id = UUID
                vector=embedding.tolist(),
                payload={                          # preserve original id for parity
                    "doc_id": original_id,
                    "content_id": original_id,     # Also store as content_id for compatibility
                    "title": item.get('title', ''),
                    "content_type": item.get('content_type', 'unknown'),
                    "type": item.get('type', 'content')
                }
            )
        )
    
    # Upsert to Qdrant
    logger.info(f"Upserting {len(points)} vectors to Qdrant...")
    client.upsert(collection_name=collection, points=points)
    
    # Verify final counts
    final_qdrant_ids = list_qdrant_ids(client, collection)
    
    return {
        "synced": len(points),
        "db_count": len(db_ids),
        "qdrant_count": len(final_qdrant_ids),
        "missing": 0,
        "extra": len(final_qdrant_ids - db_ids),
        "parity": len(db_ids) == len(final_qdrant_ids)
    }


def main() -> dict:
    """Main entry point."""
    logger.info("Starting vector sync...")
    
    # Initialize services
    db = SimpleDB()
    client = QdrantClient("localhost", port=6333)
    embed_service = get_embedding_service()
    
    # Sync missing vectors
    result = sync_missing_vectors(db, client, "emails", embed_service)
    
    logger.info(f"Sync complete: {result}")
    print(f"✅ Synced {result['synced']} missing vectors")
    print(f"   Database: {result['db_count']} documents")
    print(f"   Qdrant: {result['qdrant_count']} vectors")
    print(f"   Parity achieved: {result['parity']}")
    
    return result


if __name__ == "__main__":
    main()