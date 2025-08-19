#!/usr/bin/env python3
"""
Sync missing vectors between database and Qdrant.
Ensures DB and vector store have the same documents.
"""

import sys
import uuid
import hashlib
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent.parent))

from qdrant_client import QdrantClient
from qdrant_client.models import PointStruct
from loguru import logger
from shared.simple_db import SimpleDB
from utilities.embeddings import get_embedding_service


def string_to_uuid(s: str) -> str:
    """Convert any string to a valid UUID using deterministic hashing.
    
    Args:
        s: Input string
        
    Returns:
        UUID string
    """
    # Use SHA-256 hash to create deterministic UUID from string
    hash_obj = hashlib.sha256(s.encode('utf-8'))
    hash_hex = hash_obj.hexdigest()
    # Format as UUID (8-4-4-4-12)
    return f"{hash_hex[:8]}-{hash_hex[8:12]}-{hash_hex[12:16]}-{hash_hex[16:20]}-{hash_hex[20:32]}"


def list_qdrant_ids(client: QdrantClient, collection: str) -> set[str]:
    """Get all IDs from Qdrant collection.
    
    Args:
        client: Qdrant client
        collection: Collection name
        
    Returns:
        Set of string IDs (original content IDs, not UUIDs)
    """
    id_map = {}  # Maps UUID back to original ID
    ids = set()
    
    # Scroll through all points
    scroll_result = client.scroll(
        collection_name=collection,
        limit=10000,
        with_payload=False,
        with_vectors=False
    )
    
    ids.update(str(p.id) for p in scroll_result[0])
    
    # Continue scrolling if there are more
    while scroll_result[1] is not None:
        scroll_result = client.scroll(
            collection_name=collection,
            offset=scroll_result[1],
            limit=10000,
            with_payload=False,
            with_vectors=False
        )
        ids.update(str(p.id) for p in scroll_result[0])
    
    return ids


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
    db_ids = {str(item['content_id']) for item in db_content}
    
    # Get all IDs from Qdrant
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
    
    # Create points for Qdrant
    points = []
    for item, embedding in zip(missing_content, embeddings):
        points.append(
            PointStruct(
                id=str(item['content_id']),
                vector=embedding.tolist(),
                payload={
                    "title": item.get('title', ''),
                    "content_type": item.get('content_type', 'unknown'),
                    "doc_id": str(item['content_id'])
                }
            )
        )
    
    # Upsert to Qdrant
    logger.info(f"Upserting {len(points)} vectors to Qdrant...")
    client.upsert(collection_name=collection, points=points)
    
    return {
        "synced": len(points),
        "db_count": len(db_ids),
        "qdrant_count": len(qdrant_ids) + len(points),
        "missing": 0,
        "extra": len(extra_ids)
    }


def main():
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
    print(f"   Parity achieved: {result['db_count'] == result['qdrant_count']}")
    
    return result


if __name__ == "__main__":
    main()