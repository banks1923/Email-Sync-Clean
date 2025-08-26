#!/usr/bin/env python3
"""Backfill content_id in Qdrant vector payloads.

This fixes the issue where semantic search returns 0 results because the
payload doesn't have content_id for database lookups.
"""

import sqlite3

from loguru import logger
from qdrant_client import QdrantClient

from config.settings import settings


def map_original_hash_to_content_id(orig_hash: str) -> str | None:
    """
    Map original_hash to content_id from emails table.
    """
    try:
        conn = sqlite3.connect(settings.database.emails_db_path)
        cursor = conn.execute("SELECT id FROM emails WHERE content_hash = ? LIMIT 1", (orig_hash,))
        row = cursor.fetchone()
        conn.close()

        if row:
            # Return the email ID as string
            return str(row[0])
    except Exception as e:
        logger.error(f"Failed to map hash {orig_hash}: {e}")

    return None


def main():
    """
    Backfill content_id in all Qdrant points.
    """
    q = QdrantClient(host="localhost", port=6333)
    coll = "emails"
    offset = None
    updated = 0
    scanned = 0
    already_has_content_id = 0

    logger.info(f"Starting backfill of content_id in collection '{coll}'")

    while True:
        # Scroll through all points
        points, offset = q.scroll(
            collection_name=coll,
            limit=100,  # Process in smaller batches
            with_payload=True,
            with_vectors=False,
            offset=offset,
        )

        if not points:
            break

        for p in points:
            scanned += 1
            payload = p.payload or {}

            # Skip if already has content_id
            if "content_id" in payload:
                already_has_content_id += 1
                continue

            # Try to map from original_hash
            cid = None
            if "original_hash" in payload:
                cid = map_original_hash_to_content_id(payload["original_hash"])
                if cid:
                    logger.debug(
                        f"Mapped hash {payload['original_hash'][:20]}... to content_id {cid}"
                    )

            # Fallback: use point id (works if DB id == Qdrant id)
            if not cid:
                cid = str(p.id)
                logger.debug(f"Using point ID as content_id: {cid}")

            # Update payload
            payload["content_id"] = cid
            payload.setdefault("content_type", "email")

            try:
                q.set_payload(collection_name=coll, payload=payload, points=[p.id])
                updated += 1

                if updated % 50 == 0:
                    logger.info(f"Progress: scanned={scanned}, updated={updated}")

            except Exception as e:
                logger.error(f"Failed set_payload for {p.id}: {e}")

        if offset is None:
            break

    logger.success("Backfill complete!")
    logger.info(f"  Total scanned: {scanned}")
    logger.info(f"  Already had content_id: {already_has_content_id}")
    logger.info(f"  Updated with content_id: {updated}")

    # Verify by checking first point
    if scanned > 0:
        pts, _ = q.scroll(collection_name=coll, limit=1, with_payload=True, with_vectors=False)
        if pts:
            logger.info(f"Sample payload after backfill: {pts[0].payload}")


if __name__ == "__main__":
    main()
