#!/usr/bin/env python3
"""Backfill summaries for existing content that lacks them.

This script generates summaries for all content_unified records that
don't have corresponding entries in document_summaries table.
"""


import time

from loguru import logger

from lib.db import SimpleDB
from services.summarization import get_document_summarizer


def backfill_summaries(batch_size: int = 50, source_type: str = None, limit: int = None):
    """Generate summaries for existing content without them.

    Args:
        batch_size: Number of records to process at a time
        source_type: Filter by source type (email_message, document, etc.)
        limit: Maximum number of records to process
    """
    db = SimpleDB()
    summarizer = get_document_summarizer()
    
    # Build query to find content without summaries
    query = """
        SELECT cu.id, cu.source_type, cu.title, cu.body
        FROM content_unified cu
        LEFT JOIN document_summaries ds ON cu.id = ds.document_id
        WHERE ds.document_id IS NULL
        AND cu.body IS NOT NULL
        AND LENGTH(cu.body) > 100
    """
    
    params = []
    if source_type:
        query += " AND cu.source_type = ?"
        params.append(source_type)
    
    if limit:
        query += f" LIMIT {limit}"
    
    logger.info(f"Starting summary backfill (source_type={source_type}, limit={limit})")
    
    cursor = db.execute(query, params)
    records = cursor.fetchall()
    
    if not records:
        logger.info("No content found without summaries")
        return
    
    logger.info(f"Found {len(records)} content items without summaries")
    
    processed = 0
    errors = 0
    skipped = 0
    
    for i in range(0, len(records), batch_size):
        batch = records[i:i + batch_size]
        logger.info(f"Processing batch {i//batch_size + 1} ({len(batch)} items)")
        
        for record in batch:
            content_id, source_type, title, body = record
            
            try:
                # Skip very short content
                if not body or len(body) < 100:
                    skipped += 1
                    continue
                
                # Generate summary
                summary = summarizer.extract_summary(
                    body,
                    max_sentences=3 if source_type == "email_message" else 5,
                    max_keywords=10,
                    summary_type="combined"
                )
                
                if summary and summary.get("summary_text"):
                    # Store summary
                    db.add_document_summary(
                        document_id=str(content_id),
                        summary_type="combined",
                        summary_text=summary.get("summary_text"),
                        tf_idf_keywords=summary.get("tf_idf_keywords"),
                        textrank_sentences=summary.get("textrank_sentences")
                    )
                    processed += 1
                    
                    if processed % 10 == 0:
                        logger.info(f"Progress: {processed} summaries generated")
                else:
                    logger.warning(f"Empty summary for content_id {content_id}")
                    skipped += 1
                    
            except Exception as e:
                logger.error(f"Error processing content_id {content_id}: {e}")
                errors += 1
                
            # Rate limiting to avoid overwhelming the system
            if processed % 25 == 0:
                time.sleep(1)
    
    logger.info(f"""
    Backfill complete:
    - Processed: {processed}
    - Skipped: {skipped}
    - Errors: {errors}
    - Total: {len(records)}
    """)
    
    # Verify results
    cursor = db.execute("""
        SELECT source_type, COUNT(*) as count
        FROM content_unified cu
        INNER JOIN document_summaries ds ON cu.id = ds.document_id
        GROUP BY source_type
    """)
    
    logger.info("Summary counts by type:")
    for row in cursor.fetchall():
        logger.info(f"  {row[0]}: {row[1]}")


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Backfill summaries for existing content")
    parser.add_argument("--batch-size", type=int, default=50, help="Batch size for processing")
    parser.add_argument("--source-type", help="Filter by source type (email_message, document, etc.)")
    parser.add_argument("--limit", type=int, help="Maximum records to process")
    
    args = parser.parse_args()
    
    backfill_summaries(
        batch_size=args.batch_size,
        source_type=args.source_type,
        limit=args.limit
    )


if __name__ == "__main__":
    main()
