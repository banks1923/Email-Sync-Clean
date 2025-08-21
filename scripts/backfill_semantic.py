#!/usr/bin/env python3
"""Backfill semantic enrichment for existing emails.

Processes old emails through the semantic pipeline (entities, embeddings, timeline).
"""

import sys
from pathlib import Path
from datetime import datetime, timedelta
import argparse

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from loguru import logger
from shared.simple_db import SimpleDB
from utilities.semantic_pipeline import get_semantic_pipeline


def backfill_semantic(
    steps: list = None,
    batch_size: int = 50,
    limit: int = None,
    force: bool = False,
    since_days: int = None
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
    
    # Default steps (skip summary as it's already done during ingestion)
    if steps is None:
        steps = ['entities', 'embeddings', 'timeline']
    
    print(f"\n📋 Configuration:")
    print(f"  Steps: {', '.join(steps)}")
    print(f"  Batch size: {batch_size}")
    print(f"  Limit: {limit or 'No limit'}")
    print(f"  Force reprocess: {force}")
    
    # Build query to get emails needing enrichment
    query = "SELECT message_id FROM emails WHERE message_id IS NOT NULL"
    params = []
    
    if since_days:
        cutoff = (datetime.now() - timedelta(days=since_days)).isoformat()
        query += " AND datetime_utc > ?"
        params.append(cutoff)
        
    if not force:
        # Skip emails that might already be processed
        # This is a simple heuristic - could be improved
        query += " AND message_id NOT IN (SELECT DISTINCT message_id FROM entity_content_mapping WHERE message_id IS NOT NULL)"
        
    query += " ORDER BY datetime_utc DESC"
    
    if limit:
        query += f" LIMIT {limit}"
        
    cursor = db.execute(query, params)
    all_message_ids = [row['message_id'] for row in cursor.fetchall()]
    
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
        'entities': {'processed': 0, 'skipped': 0, 'errors': 0},
        'embeddings': {'processed': 0, 'skipped': 0, 'errors': 0},
        'timeline': {'processed': 0, 'skipped': 0, 'errors': 0}
    }
    
    for i in range(0, total_count, batch_size):
        batch = all_message_ids[i:i + batch_size]
        batch_num = (i // batch_size) + 1
        total_batches = (total_count + batch_size - 1) // batch_size
        
        print(f"\n🔄 Processing batch {batch_num}/{total_batches} ({len(batch)} emails)")
        
        try:
            result = pipeline.run_for_messages(
                message_ids=batch,
                steps=steps
            )
            
            # Aggregate results
            for step in steps:
                if step in result.get('step_results', {}):
                    step_result = result['step_results'][step]
                    for key in ['processed', 'skipped', 'errors']:
                        total_results[step][key] += step_result.get(key, 0)
                        
            processed += len(batch)
            
            # Progress update
            print(f"  Progress: {processed}/{total_count} ({100*processed/total_count:.1f}%)")
            
            for step in steps:
                if step in total_results:
                    r = total_results[step]
                    print(f"  {step}: processed={r['processed']}, skipped={r['skipped']}, errors={r['errors']}")
                    
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
            total = r['processed'] + r['skipped'] + r['errors']
            if total > 0:
                success_rate = 100 * r['processed'] / total
                print(f"\n{step.upper()}:")
                print(f"  Processed: {r['processed']} ({success_rate:.1f}%)")
                print(f"  Skipped: {r['skipped']}")
                print(f"  Errors: {r['errors']}")
                
    print(f"\n✅ Backfill completed for {processed} emails")


def main():
    """CLI entry point."""
    parser = argparse.ArgumentParser(description="Backfill semantic enrichment for emails")
    
    parser.add_argument(
        '--steps',
        nargs='+',
        choices=['entities', 'embeddings', 'timeline'],
        help='Specific steps to run (default: all)'
    )
    parser.add_argument(
        '--batch-size',
        type=int,
        default=50,
        help='Number of emails per batch (default: 50)'
    )
    parser.add_argument(
        '--limit',
        type=int,
        help='Maximum emails to process (default: all)'
    )
    parser.add_argument(
        '--force',
        action='store_true',
        help='Force reprocessing even if already done'
    )
    parser.add_argument(
        '--since-days',
        type=int,
        help='Only process emails from last N days'
    )
    
    args = parser.parse_args()
    
    backfill_semantic(
        steps=args.steps,
        batch_size=args.batch_size,
        limit=args.limit,
        force=args.force,
        since_days=args.since_days
    )


if __name__ == "__main__":
    main()