#!/usr/bin/env python3
"""
⚠️ DEPRECATED - DO NOT USE ⚠️

This script is deprecated. Please use one of the following instead:
- scripts/backfill_embeddings.py - For batch embedding generation
- utilities/semantic_pipeline.py - For integrated pipeline processing

Process embeddings for all content in database.
Updates ready_for_embedding flag and stores in Qdrant.
"""

print("⚠️ WARNING: This script is deprecated!")
print("Please use: python3 scripts/backfill_embeddings.py")
print("Or for pipeline: python3 utilities/semantic_pipeline.py")
import sys

sys.exit(1)

import time
from pathlib import Path

# Add project root to path
sys.path.append(str(Path(__file__).parent.parent))

from shared.simple_db import SimpleDB
from utilities.embeddings import get_embedding_service
from utilities.vector_store import get_vector_store


def process_all_embeddings(batch_size: int = 10):
    """
    Process embeddings for all unprocessed content.
    """

    db = SimpleDB()
    emb = get_embedding_service()
    store = get_vector_store()

    if not store:
        print("❌ Qdrant not available. Cannot process embeddings.")
        return

    # Get unprocessed content
    import sqlite3

    conn = sqlite3.connect(db.db_path)
    cursor = conn.cursor()

    # Check if ready_for_embedding column exists
    cursor.execute("PRAGMA table_info(content_unified)")
    columns = {col[1] for col in cursor.fetchall()}

    if "ready_for_embedding" in columns:
        where_clause = "WHERE ready_for_embedding = 0 OR ready_for_embedding IS NULL"
    else:
        # Add the column if it doesn't exist
        cursor.execute(
            "ALTER TABLE content_unified ADD COLUMN ready_for_embedding INTEGER DEFAULT 0"
        )
        where_clause = "WHERE ready_for_embedding = 0 OR ready_for_embedding IS NULL"

    cursor.execute(
        f"""
        SELECT id, source_type, title, body
        FROM content_unified
        {where_clause}
        ORDER BY created_at DESC
    """
    )

    unprocessed = cursor.fetchall()
    total = len(unprocessed)

    if total == 0:
        print("✅ All content already has embeddings")
        return

    print(f"📊 Found {total} items without embeddings")
    print("🔄 Processing embeddings...")

    processed = 0
    errors = 0

    for i in range(0, total, batch_size):
        batch = unprocessed[i : i + batch_size]
        batch_end = min(i + batch_size, total)
        print(f"\n  Processing batch {i+1}-{batch_end} of {total}")

        for content_id, content_type, title, content_text in batch:
            try:
                # Truncate very long content for embedding
                text_for_embedding = (
                    content_text[:8000] if len(content_text) > 8000 else content_text
                )

                # Generate embedding
                embedding = emb.encode(text_for_embedding)

                # Store in Qdrant
                payload = {
                    "content_id": content_id,
                    "content_type": content_type,
                    "title": title or "Untitled",
                    "char_count": len(content_text),
                }

                store.upsert(
                    vector=embedding.tolist(),  # Convert numpy array to list
                    payload=payload,
                    id=content_id,
                )

                # Update ready_for_embedding flag
                cursor.execute(
                    """
                    UPDATE content_unified
                    SET ready_for_embedding = 1
                    WHERE id = ?
                """,
                    (content_id,),
                )

                processed += 1
                print(f"    ✅ {content_type}: {title[:50] if title else 'Untitled'}")

            except Exception as e:
                errors += 1
                print(f"    ❌ Error processing {content_id}: {str(e)}")

        # Commit batch
        conn.commit()

        # Brief pause between batches
        if i + batch_size < total:
            time.sleep(0.5)

    conn.close()

    print("\n📊 Embedding Processing Complete:")
    print(f"  ✅ Processed: {processed}")
    print(f"  ❌ Errors: {errors}")
    print(f"  📦 Total in Qdrant: {processed}")

    # Verify in Qdrant
    try:
        import requests

        response = requests.get("http://localhost:6333/collections/emails")
        if response.ok:
            data = response.json()
            if "result" in data:
                count = data["result"]["points_count"]
                print(f"  🔍 Qdrant verified: {count} vectors")
    except (ImportError, requests.RequestException, KeyError, ValueError):
        pass


def main():
    """
    Main function.
    """
    import argparse

    parser = argparse.ArgumentParser(description="Process embeddings for all content")
    parser.add_argument("--batch-size", type=int, default=10, help="Batch size for processing")
    parser.add_argument("--content-type", type=str, help="Process only specific content type")

    args = parser.parse_args()

    if args.content_type:
        print(f"Processing embeddings for {args.content_type} content only...")
        # TODO: Add filtering by content type

    process_all_embeddings(batch_size=args.batch_size)


if __name__ == "__main__":
    main()
