#!/usr/bin/env python3
"""Reindex existing Qdrant points with valid UUID point IDs.

Fixes invalid point ID formats that cause upsert failures.
This script:
1. Scrolls through existing points
2. Re-upserts with normalized UUIDs 
3. Deletes old points with invalid IDs
4. Preserves all payload data for traceability
"""

import sys
import uuid
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from loguru import logger
from qdrant_client import QdrantClient
from qdrant_client.models import PointStruct


def normalize_point_id(content_id: str = None, message_id: str = None) -> str:
    """Generate a deterministic UUID for Qdrant point ID."""
    # Same namespace as used in semantic_pipeline.py
    NAMESPACE = uuid.UUID("00000000-0000-0000-0000-00000000E1D0")
    
    key = (message_id or content_id or '').strip()
    if not key:
        return str(uuid.uuid4())
        
    return str(uuid.uuid5(NAMESPACE, key))


def reindex_collection(collection_name: str = 'emails', batch_size: int = 100, dry_run: bool = False):
    """Reindex all points in a collection with valid UUIDs."""
    print(f"🔄 {'[DRY RUN] ' if dry_run else ''}Reindexing Qdrant collection: {collection_name}")
    
    try:
        client = QdrantClient(host="localhost", port=6333)
        
        # Get collection info
        collection_info = client.get_collection(collection_name)
        total_points = collection_info.points_count
        print(f"Collection has {total_points} points")
        
        if total_points == 0:
            print("✅ No points to reindex")
            return
            
    except Exception as e:
        print(f"❌ Failed to connect to Qdrant: {e}")
        return
        
    reindexed = 0
    skipped = 0
    errors = 0
    offset = None
    
    while True:
        try:
            # Scroll through points with vectors and payload
            points, next_offset = client.scroll(
                collection_name=collection_name,
                with_vectors=True,
                with_payload=True,
                limit=batch_size,
                offset=offset
            )
            
            if not points:
                break
                
            new_points = []
            old_point_ids = []
            
            for point in points:
                # Extract identifiers from payload
                payload = point.payload or {}
                content_id = payload.get('content_id')
                message_id = payload.get('message_id')
                
                # Generate normalized ID
                new_id = normalize_point_id(content_id=content_id, message_id=message_id)
                
                # Check if ID needs changing
                if str(point.id) == new_id:
                    skipped += 1
                    continue
                    
                print(f"  Reindexing: {point.id} → {new_id}")
                
                # Prepare new point with same vector and payload
                new_point = PointStruct(
                    id=new_id,
                    vector=point.vector,
                    payload=payload
                )
                
                new_points.append(new_point)
                old_point_ids.append(point.id)
                
            # Process batch
            if new_points and not dry_run:
                try:
                    # Upsert new points
                    client.upsert(collection_name=collection_name, points=new_points)
                    
                    # Delete old points
                    if old_point_ids:
                        client.delete(
                            collection_name=collection_name,
                            points_selector={"points": old_point_ids}
                        )
                        
                    reindexed += len(new_points)
                    print(f"  ✅ Reindexed batch of {len(new_points)} points")
                    
                except Exception as e:
                    print(f"  ❌ Batch reindex failed: {e}")
                    errors += len(new_points)
                    
            elif new_points and dry_run:
                print(f"  [DRY RUN] Would reindex {len(new_points)} points")
                reindexed += len(new_points)
                
            # Continue scrolling
            offset = next_offset
            if offset is None:
                break
                
        except Exception as e:
            logger.error(f"Scroll batch failed: {e}")
            errors += batch_size
            break
            
    # Final report
    print("\n" + "=" * 60)
    print(f"Qdrant Reindexing {'Simulation ' if dry_run else ''}Complete")
    print("=" * 60)
    print(f"Total points processed: {reindexed + skipped + errors}")
    print(f"Points reindexed: {reindexed}")
    print(f"Points skipped (already valid): {skipped}")
    print(f"Errors: {errors}")
    
    if not dry_run and reindexed > 0:
        # Verify final count
        try:
            final_info = client.get_collection(collection_name)
            print(f"Final collection size: {final_info.points_count} points")
            
            if final_info.points_count == total_points:
                print("✅ Point count preserved - reindexing successful")
            else:
                print("⚠️  Point count changed - verify manually")
                
        except Exception as e:
            print(f"⚠️  Could not verify final count: {e}")
            
    return reindexed, skipped, errors


def verify_point_ids(collection_name: str = 'emails', sample_size: int = 10):
    """Verify that point IDs are now valid UUIDs."""
    print(f"\n🔍 Verifying point IDs in collection: {collection_name}")
    
    try:
        client = QdrantClient(host="localhost", port=6333)
        
        # Get sample points
        points, _ = client.scroll(
            collection_name=collection_name,
            with_payload=True,
            with_vectors=False,
            limit=sample_size
        )
        
        valid_uuids = 0
        invalid_ids = []
        
        for point in points:
            try:
                # Try to parse as UUID
                uuid.UUID(str(point.id))
                valid_uuids += 1
            except ValueError:
                invalid_ids.append(str(point.id))
                
        print(f"Sample of {len(points)} points:")
        print(f"  Valid UUIDs: {valid_uuids}")
        print(f"  Invalid IDs: {len(invalid_ids)}")
        
        if invalid_ids:
            print(f"  Examples of invalid IDs: {invalid_ids[:3]}")
            return False
        else:
            print("  ✅ All sampled point IDs are valid UUIDs")
            return True
            
    except Exception as e:
        print(f"❌ Verification failed: {e}")
        return False


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Reindex Qdrant points with valid UUIDs")
    parser.add_argument("--collection", default="emails", help="Collection name (default: emails)")
    parser.add_argument("--batch-size", type=int, default=100, help="Batch size for processing")
    parser.add_argument("--dry-run", action="store_true", help="Simulate reindexing without making changes")
    parser.add_argument("--verify-only", action="store_true", help="Only verify existing point IDs")
    
    args = parser.parse_args()
    
    if args.verify_only:
        verify_point_ids(args.collection)
    else:
        # Run reindexing
        reindexed, skipped, errors = reindex_collection(
            collection_name=args.collection,
            batch_size=args.batch_size,
            dry_run=args.dry_run
        )
        
        # Verify results
        if not args.dry_run and reindexed > 0:
            verify_point_ids(args.collection)
            
        sys.exit(0 if errors == 0 else 1)