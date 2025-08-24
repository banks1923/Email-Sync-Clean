#!/usr/bin/env python3
"""
Backfill summaries for all existing emails in content_unified table.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from shared.simple_db import SimpleDB
from summarization.engine import DocumentSummarizer
from loguru import logger
import time

def backfill_email_summaries():
    """Generate summaries for all emails without summaries."""
    db = SimpleDB()
    summarizer = DocumentSummarizer()
    
    # Get all emails without summaries
    query = """
        SELECT cu.id, cu.title, cu.body, cu.source_id
        FROM content_unified cu
        LEFT JOIN document_summaries ds ON cu.id = ds.document_id
        WHERE cu.source_type = 'email' 
        AND ds.summary_id IS NULL
        AND cu.body IS NOT NULL
        AND LENGTH(cu.body) > 100
    """
    
    import sqlite3
    with sqlite3.connect(db.db_path) as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute(query)
        emails = cursor.fetchall()
    
    logger.info(f"Found {len(emails)} emails without summaries")
    
    success_count = 0
    error_count = 0
    
    for i, email in enumerate(emails, 1):
        content_id = email['id']
        subject = email['title'] or "No Subject"
        body = email['body']
        source_id = email['source_id']
        
        logger.info(f"[{i}/{len(emails)}] Processing: {subject[:50]}...")
        
        try:
            # Generate summary
            summary = summarizer.extract_summary(
                body,
                max_sentences=3,
                max_keywords=10,
                summary_type="combined"
            )
            
            if summary:
                # Store summary
                summary_id = db.add_document_summary(
                    document_id=content_id,
                    summary_type="combined",
                    summary_text=summary.get("summary_text"),
                    tf_idf_keywords=summary.get("tf_idf_keywords"),
                    textrank_sentences=summary.get("textrank_sentences")
                )
                
                if summary_id:
                    logger.success(f"✓ Created summary {summary_id}")
                    success_count += 1
                else:
                    logger.warning(f"Failed to store summary")
                    error_count += 1
            else:
                logger.warning(f"No summary generated")
                error_count += 1
                
            # Rate limit to avoid overwhelming
            if i % 10 == 0:
                time.sleep(0.1)
                
        except Exception as e:
            logger.error(f"Error processing email {content_id}: {e}")
            error_count += 1
    
    logger.info(f"\nBackfill complete:")
    logger.info(f"  ✓ Success: {success_count}")
    logger.info(f"  ✗ Errors: {error_count}")
    logger.info(f"  Total processed: {len(emails)}")
    
    # Verify results
    verify_query = """
        SELECT COUNT(DISTINCT ds.id) as summary_count,
               COUNT(DISTINCT cu.id) as email_count
        FROM content_unified cu
        LEFT JOIN document_summaries ds ON cu.id = ds.document_id
        WHERE cu.source_type = 'email'
    """
    
    with sqlite3.connect(db.db_path) as conn:
        cursor = conn.cursor()
        cursor.execute(verify_query)
        result = cursor.fetchone()
        if result:
            summary_count, email_count = result
            logger.info(f"\nDatabase status:")
            logger.info(f"  Total emails: {email_count}")
            logger.info(f"  Emails with summaries: {summary_count}")
            if email_count > 0:
                logger.info(f"  Coverage: {summary_count/email_count*100:.1f}%")

if __name__ == "__main__":
    backfill_email_summaries()