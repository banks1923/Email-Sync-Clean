#!/usr/bin/env python3
"""
Purge test vectors from Qdrant vector store.
Removes all test data that pollutes search results.
"""

from qdrant_client import QdrantClient
from qdrant_client.models import Filter, FieldCondition, MatchText
from loguru import logger


def purge_test_vectors(client: QdrantClient, collection: str = "emails") -> dict:
    """Remove all test vectors from Qdrant.
    
    Args:
        client: Qdrant client instance
        collection: Collection name
        
    Returns:
        Dict with purge statistics
    """
    # Get initial count
    info_before = client.get_collection(collection)
    count_before = info_before.points_count
    
    purged_patterns = []
    
    # Pattern 1: Test Subject documents
    try:
        # Try with MatchText first
        filter_test = Filter(
            must=[FieldCondition(key="title", match=MatchText(text="Test Subject"))]
        )
        client.delete(collection_name=collection, points_selector=filter_test)
        purged_patterns.append("Test Subject")
    except Exception as e:
        logger.warning(f"Could not delete 'Test Subject' pattern: {e}")
    
    # Pattern 2: tmp test documents
    for prefix in ["tmpesc8d0r8", "tmpikvnso9i"]:
        try:
            filter_tmp = Filter(
                must=[FieldCondition(key="title", match=MatchText(text=prefix))]
            )
            client.delete(collection_name=collection, points_selector=filter_tmp)
            purged_patterns.append(prefix)
        except Exception as e:
            logger.warning(f"Could not delete '{prefix}' pattern: {e}")
    
    # Alternative approach: scroll through and delete by ID
    # This is more reliable if MatchText doesn't work
    try:
        # Get all points with payload
        scroll_result = client.scroll(
            collection_name=collection,
            limit=1000,
            with_payload=True,
            with_vectors=False
        )
        
        ids_to_delete = []
        for point in scroll_result[0]:
            if point.payload and "title" in point.payload:
                title = point.payload["title"]
                if (title and (
                    "Test Subject" in title or
                    "tmpesc8d0r8" in title or
                    "tmpikvnso9i" in title
                )):
                    ids_to_delete.append(point.id)
        
        if ids_to_delete:
            client.delete(
                collection_name=collection,
                points_selector=ids_to_delete
            )
            logger.info(f"Deleted {len(ids_to_delete)} test vectors by ID")
    except Exception as e:
        logger.error(f"Failed to delete by ID: {e}")
    
    # Get final count
    info_after = client.get_collection(collection)
    count_after = info_after.points_count
    
    return {
        "count_before": count_before,
        "count_after": count_after,
        "deleted": count_before - count_after,
        "patterns_processed": purged_patterns
    }


def main():
    """Main entry point."""
    logger.info("Starting test vector purge...")
    
    # Connect to Qdrant
    client = QdrantClient("localhost", port=6333)
    
    # Purge test vectors
    result = purge_test_vectors(client)
    
    logger.info(f"Purge complete: {result}")
    print(f"✅ Purged {result['deleted']} test vectors")
    print(f"   Before: {result['count_before']} vectors")
    print(f"   After: {result['count_after']} vectors")
    
    return result


if __name__ == "__main__":
    main()