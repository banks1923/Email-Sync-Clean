#!/usr/bin/env python3
"""
Vector Store Synchronization Script
Removes orphaned vectors from Qdrant that no longer have corresponding content in the database.
This ensures the vector store stays synchronized with the cleaned database.

Usage: python scripts/sync_vector_store.py [--dry-run]
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from loguru import logger

from shared.simple_db import SimpleDB
from utilities.vector_store import get_vector_store

# Logger is now imported globally from loguru


def get_orphaned_vectors(db) -> dict:
    """Find vectors that don't have corresponding content in database"""
    try:
        # Get all content IDs from database
        content_records = db.fetch("SELECT content_id FROM content")
        valid_content_ids = {record["content_id"] for record in content_records}

        logger.info(f"Database has {len(valid_content_ids)} content records")

        # Get vector count from Qdrant
        vector_store = get_vector_store()
        vector_count = vector_store.count()
        logger.info(f"Vector store has {vector_count} vectors")

        # Get all vector IDs from Qdrant (using scroll to get all)
        try:
            # Note: This is a simplified approach. In a real production system,
            # you'd want to use scroll/pagination for very large collections
            all_points = vector_store.client.scroll(
                collection_name=vector_store.collection,
                limit=10000,  # Adjust based on your collection size
                with_payload=True,
                with_vectors=False,
            )[
                0
            ]  # Get points, ignore next_page_offset

            vector_ids = {str(point.id) for point in all_points}
            logger.info(f"Retrieved {len(vector_ids)} vector IDs from Qdrant")

        except Exception as e:
            logger.error(f"Failed to retrieve vector IDs from Qdrant: {e}")
            return {"error": str(e)}

        # Find orphaned vectors (vectors without corresponding content)
        orphaned_vectors = vector_ids - valid_content_ids

        logger.info(f"Found {len(orphaned_vectors)} orphaned vectors")

        return {
            "total_vectors": vector_count,
            "total_content": len(valid_content_ids),
            "orphaned_vectors": list(orphaned_vectors),
            "orphaned_count": len(orphaned_vectors),
        }

    except Exception as e:
        logger.error(f"Error analyzing vector store: {e}")
        return {"error": str(e)}


def remove_orphaned_vectors(vector_store, orphaned_vector_ids: list, dry_run: bool = False) -> dict:
    """Remove orphaned vectors from vector store"""
    if not orphaned_vector_ids:
        return {"removed": 0, "errors": 0}

    stats = {"removed": 0, "errors": 0}

    logger.info(
        f"{'[DRY RUN] ' if dry_run else ''}Removing {len(orphaned_vector_ids)} orphaned vectors"
    )

    # Process in batches for better performance
    batch_size = 100
    for i in range(0, len(orphaned_vector_ids), batch_size):
        batch = orphaned_vector_ids[i : i + batch_size]

        if dry_run:
            logger.info(f"[DRY RUN] Would delete batch of {len(batch)} vectors: {batch[:5]}...")
            stats["removed"] += len(batch)
        else:
            try:
                vector_store.delete_many(batch)
                stats["removed"] += len(batch)
                logger.debug(f"Deleted batch of {len(batch)} vectors")

            except Exception as e:
                logger.error(f"Failed to delete vector batch: {e}")
                stats["errors"] += len(batch)

    return stats


def verify_synchronization(vector_store, db) -> dict:
    """Verify that vector store is now synchronized with database"""
    try:
        vector_store = get_vector_store()
        vector_count = vector_store.count()
        content_count = db.fetch_one("SELECT COUNT(*) as count FROM content")["count"]

        # Check for remaining orphaned vectors
        analysis = get_orphaned_vectors(vector_store, db)

        if "error" in analysis:
            return {"error": analysis["error"]}

        return {
            "vector_count": vector_count,
            "content_count": content_count,
            "difference": vector_count - content_count,
            "remaining_orphaned": analysis["orphaned_count"],
            "synchronized": analysis["orphaned_count"] == 0,
        }

    except Exception as e:
        logger.error(f"Verification failed: {e}")
        return {"error": str(e)}


def main():
    """Run the vector store synchronization"""
    import argparse

    parser = argparse.ArgumentParser(description="Synchronize vector store with cleaned database")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be deleted without actually deleting",
    )
    args = parser.parse_args()

    logger.info(
        f"Starting vector store synchronization {'(DRY RUN)' if args.dry_run else '(LIVE RUN)'}"
    )

    try:
        # Initialize services
        vector_store = get_vector_store()
        db = SimpleDB()

        # Step 1: Analyze current state
        logger.info("Step 1: Analyzing vector store and database...")
        analysis = get_orphaned_vectors(vector_store, db)

        if "error" in analysis:
            logger.error(f"Analysis failed: {analysis['error']}")
            return False

        # Step 2: Remove orphaned vectors
        logger.info("Step 2: Removing orphaned vectors...")
        removal_stats = remove_orphaned_vectors(
            vector_store, analysis["orphaned_vectors"], args.dry_run
        )

        # Step 3: Verify synchronization
        if not args.dry_run:
            logger.info("Step 3: Verifying synchronization...")
            verification = verify_synchronization(vector_store, db)
        else:
            verification = {"dry_run": True}

        # Summary
        print("\n" + "=" * 60)
        print(f"VECTOR STORE SYNCHRONIZATION SUMMARY {'(DRY RUN)' if args.dry_run else ''}")
        print("=" * 60)
        print(f"Initial vector count: {analysis.get('total_vectors', 'unknown')}")
        print(f"Database content count: {analysis.get('total_content', 'unknown')}")
        print(f"Orphaned vectors found: {analysis.get('orphaned_count', 'unknown')}")
        print(f"Vectors removed: {removal_stats['removed']}")
        print(f"Removal errors: {removal_stats['errors']}")

        if not args.dry_run:
            print(f"Final vector count: {verification.get('vector_count', 'unknown')}")
            print(f"Remaining difference: {verification.get('difference', 'unknown')}")
            print(f"Synchronization successful: {'✓' if verification.get('synchronized') else '✗'}")

        print("=" * 60)

        if args.dry_run:
            print("\n💡 This was a dry run. Use without --dry-run to actually remove vectors.")
            return True
        elif verification.get("synchronized"):
            print("\n✅ Vector store synchronized successfully!")
            return True
        else:
            print("\n⚠️  Synchronization completed but issues remain. Check logs for details.")
            return False

    except Exception as e:
        logger.error(f"Synchronization failed: {e}")
        print(f"\n❌ Vector store synchronization failed: {e}")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
