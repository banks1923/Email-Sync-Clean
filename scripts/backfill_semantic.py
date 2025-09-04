#!/usr/bin/env python3
"""Backfill semantic enrichment for existing emails.

Processes old emails through the semantic pipeline (entities,
embeddings, timeline).
"""

import argparse
import sys
from datetime import datetime, timedelta
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from loguru import logger

from shared.simple_db import SimpleDB
from utilities.semantic_pipeline import get_semantic_pipeline
from summarization import get_document_summarizer


def backfill_semantic(
    steps: list = None,
    batch_size: int = 50,
    limit: int = None,
    force: bool = False,
    since_days: int = None,
):
    """Backfill semantic enrichment for existing emails.

    Args:
        steps: Specific steps to run (default: all except summary)
        batch_size: Number of emails per batch
        limit: Maximum emails to process (None = all)
        force: Force reprocessing even if already done
        since_days: Only process emails from last N days
    """
    print("=" * 60)
    print("Semantic Enrichment Backfill")
    print("=" * 60)

    db = SimpleDB()

    # Default steps (summary is optional and can be backfilled)
    if steps is None:
        steps = ["entities", "embeddings", "timeline"]

    print("\n📋 Configuration:")
    print(f"  Steps: {', '.join(steps)}")
    print(f"  Batch size: {batch_size}")
    print(f"  Limit: {limit or 'No limit'}")
    print(f"  Force reprocess: {force}")

    # Build query to get emails needing enrichment - UPDATED FOR v2.0 SCHEMA
    # Use individual_messages (deduplicated) and content_unified for processing
    query = "SELECT message_hash FROM individual_messages WHERE message_hash IS NOT NULL"
    params = []

    if since_days:
        cutoff = (datetime.now() - timedelta(days=since_days)).isoformat()
        query += " AND date_sent > ?"
        params.append(cutoff)

    if not force:
        # Skip content already processed for embeddings
        query += " AND message_hash IN (SELECT source_id FROM content_unified WHERE source_type='email_message' AND (embedding_generated IS NULL OR embedding_generated = 0))"

    query += " ORDER BY date_sent DESC"

    if limit:
        query += f" LIMIT {limit}"

    cursor = db.execute(query, params)
    all_message_ids = [row["message_hash"] for row in cursor.fetchall()]

    total_count = len(all_message_ids)

    if total_count == 0:
        print("\n✅ No emails need processing!")
        return

    print(f"\n📧 Found {total_count} emails to process")

    # Initialize pipeline
    pipeline = get_semantic_pipeline()

    # Process in batches
    processed = 0
    total_results = {
        "entities": {"processed": 0, "skipped": 0, "errors": 0},
        "embeddings": {"processed": 0, "skipped": 0, "errors": 0},
        "timeline": {"processed": 0, "skipped": 0, "errors": 0},
        "summaries": {"processed": 0, "skipped": 0, "errors": 0},
    }

    for i in range(0, total_count, batch_size):
        batch = all_message_ids[i : i + batch_size]
        batch_num = (i // batch_size) + 1
        total_batches = (total_count + batch_size - 1) // batch_size

        print(f"\n🔄 Processing batch {batch_num}/{total_batches} ({len(batch)} emails)")

        try:
            result = pipeline.run_for_messages(message_ids=batch, steps=[s for s in steps if s != "summaries"])  # summaries handled below

            # Aggregate results
            for step in steps:
                if step in result.get("step_results", {}):
                    step_result = result["step_results"][step]
                    for key in ["processed", "skipped", "errors"]:
                        total_results[step][key] += step_result.get(key, 0)

            processed += len(batch)

            # Optional: run summaries backfill for this batch
            if "summaries" in steps:
                s_result = _backfill_summaries_for_messages(db, batch, force=force)
                for key in ["processed", "skipped", "errors"]:
                    total_results["summaries"][key] += s_result.get(key, 0)

            # Progress update
            print(f"  Progress: {processed}/{total_count} ({100*processed/total_count:.1f}%)")

            for step in steps:
                if step in total_results:
                    r = total_results[step]
                    print(
                        f"  {step}: processed={r['processed']}, skipped={r['skipped']}, errors={r['errors']}"
                    )

        except Exception as e:
            logger.error(f"Batch {batch_num} failed: {e}")
            continue

    # Final summary
    print("\n" + "=" * 60)
    print("BACKFILL COMPLETE")
    print("=" * 60)

    for step in steps:
        if step in total_results:
            r = total_results[step]
            total = r["processed"] + r["skipped"] + r["errors"]
            if total > 0:
                success_rate = 100 * r["processed"] / total
                print(f"\n{step.upper()}:")
                print(f"  Processed: {r['processed']} ({success_rate:.1f}%)")
                print(f"  Skipped: {r['skipped']}")
                print(f"  Errors: {r['errors']}")

    print(f"\n✅ Backfill completed for {processed} emails")


def main():
    """
    CLI entry point.
    """
    parser = argparse.ArgumentParser(description="Backfill semantic enrichment for emails")

    parser.add_argument(
        "--steps",
        nargs="+",
        choices=["entities", "embeddings", "timeline", "summaries"],
        help="Specific steps to run (default: all except summaries)",
    )
    parser.add_argument(
        "--batch-size", type=int, default=50, help="Number of emails per batch (default: 50)"
    )
    parser.add_argument("--limit", type=int, help="Maximum emails to process (default: all)")
    parser.add_argument(
        "--force", action="store_true", help="Force reprocessing even if already done"
    )
    parser.add_argument("--since-days", type=int, help="Only process emails from last N days")

    args = parser.parse_args()

    backfill_semantic(
        steps=args.steps,
        batch_size=args.batch_size,
        limit=args.limit,
        force=args.force,
        since_days=args.since_days,
    )


def _backfill_summaries_for_messages(db: SimpleDB, message_ids: list[str], force: bool = False) -> dict:
    """Backfill summaries for a list of individual_messages (by message_hash).

    Writes summaries into content_unified with source_type='email_summary' and
    source_id set to the original content_unified.id (string) for uniqueness.
    """
    result = {"processed": 0, "skipped": 0, "errors": 0}
    if not message_ids:
        return result

    # Map message_hash -> content_unified row for email_message
    placeholders = ",".join(["?"] * len(message_ids))
    rows = db.fetch(
        f"""
        SELECT c.id as content_id, c.title, c.body, im.message_hash
        FROM individual_messages im
        JOIN content_unified c
          ON c.source_type = 'email_message'
         AND c.source_id = im.message_hash
        WHERE im.message_hash IN ({placeholders})
        """,
        tuple(message_ids),
    )

    if not rows:
        return result

    summarizer = get_document_summarizer()

    for row in rows:
        content_id = str(row["content_id"])
        title = row.get("title") or "Email"
        body = row.get("body") or ""

        # Skip if summary exists unless forced
        if not force:
            exists = db.fetch_one(
                "SELECT 1 FROM content_unified WHERE source_type='email_summary' AND source_id = ? LIMIT 1",
                (content_id,),
            )
            if exists:
                result["skipped"] += 1
                continue

        try:
            summary = summarizer.extract_summary(body, max_sentences=3, max_keywords=10, summary_type="combined")
            summary_text = summary.get("summary_text") or "(No summary content)"

            # Insert summary content; ready_for_embedding defaults to 1 but embedding not required
            db.execute(
                """
                INSERT OR REPLACE INTO content_unified (source_type, source_id, title, body, ready_for_embedding, embedding_generated)
                VALUES ('email_summary', ?, ?, ?, 0, 0)
                """,
                (content_id, f"Summary: {title}", summary_text),
            )
            result["processed"] += 1
        except Exception:
            result["errors"] += 1

    return result


if __name__ == "__main__":
    main()
