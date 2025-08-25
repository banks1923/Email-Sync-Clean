#!/usr/bin/env python3
"""
Fix duplicate PDF entries with empty content.
These were created by SimpleUploadProcessor but the same files exist with proper text in the PDF pipeline.
"""

import sys
from pathlib import Path

# Add project root to path
sys.path.append(str(Path(__file__).parent.parent))

from loguru import logger
from shared.simple_db import SimpleDB


def main():
    """Main execution function."""
    
    logger.info("🔧 Fix Duplicate Empty PDF Records")
    logger.info("=" * 60)
    
    db = SimpleDB()
    
    # Find empty document/upload records that have matching PDF records with text
    query = """
    WITH empty_records AS (
        SELECT 
            cu.id,
            cu.source_type,
            cu.title,
            cu.sha256
        FROM content_unified cu
        WHERE cu.source_type IN ('document', 'upload')
        AND (cu.body IS NULL OR LENGTH(TRIM(cu.body)) <= 20)
    ),
    matching_pdfs AS (
        SELECT 
            cu2.title,
            cu2.body,
            LENGTH(cu2.body) as body_len
        FROM content_unified cu2
        WHERE cu2.source_type = 'pdf'
        AND cu2.body IS NOT NULL
        AND LENGTH(TRIM(cu2.body)) > 20
    )
    SELECT 
        er.id,
        er.source_type,
        er.title,
        mp.body,
        mp.body_len
    FROM empty_records er
    JOIN matching_pdfs mp ON er.title = mp.title
    """
    
    records = db.fetch(query)
    logger.info(f"Found {len(records)} empty records with matching PDF text")
    
    if not records:
        # Try another approach - match by similar file names
        query2 = """
        SELECT 
            cu1.id,
            cu1.source_type,
            cu1.title as empty_title,
            cu2.title as pdf_title,
            cu2.body,
            LENGTH(cu2.body) as body_len
        FROM content_unified cu1
        JOIN content_unified cu2 ON (
            REPLACE(REPLACE(cu1.title, ' ', ''), '_', '') = REPLACE(REPLACE(cu2.title, ' ', ''), '_', '')
            OR cu1.title = cu2.title
        )
        WHERE cu1.source_type IN ('document', 'upload')
        AND (cu1.body IS NULL OR LENGTH(TRIM(cu1.body)) <= 20)
        AND cu2.source_type = 'pdf'
        AND cu2.body IS NOT NULL
        AND LENGTH(TRIM(cu2.body)) > 20
        """
        
        records = db.fetch(query2)
        logger.info(f"Found {len(records)} empty records with similar PDF names")
    
    if not records:
        logger.info("No matching records found to fix")
        
        # Show what we do have
        empty_count = db.fetch_one("""
            SELECT COUNT(*) as count 
            FROM content_unified 
            WHERE source_type IN ('document', 'upload')
            AND (body IS NULL OR LENGTH(TRIM(body)) <= 20)
        """)['count']
        
        logger.info(f"Still have {empty_count} empty document/upload records")
        return
    
    # Fix each record
    fixed_count = 0
    for record in records[:10]:  # Limit to first 10 for safety
        content_id = record['id']
        title = record.get('empty_title', record.get('title', 'Unknown'))
        body = record['body']
        body_len = record['body_len']
        
        logger.info(f"Fixing: {title} (content_id: {content_id}, {body_len} chars)")
        
        # Update with the PDF text
        update_query = """
        UPDATE content_unified
        SET body = ?
        WHERE id = ?
        """
        
        db.execute(update_query, (body, content_id))
        fixed_count += 1
        logger.success(f"✅ Updated content_id {content_id}")
    
    logger.info("=" * 60)
    logger.info(f"📊 Fixed {fixed_count} records")
    
    # Run entity extraction on fixed content
    if fixed_count > 0:
        logger.info("\n🔬 Running entity extraction on fixed content...")
        
        from shared.unified_entity_processor import UnifiedEntityProcessor
        entity_processor = UnifiedEntityProcessor()
        
        # Process the records we just fixed
        content_ids = [r['id'] for r in records[:fixed_count]]
        
        result = entity_processor.process_content_entities(
            content_ids=content_ids,
            batch_size=25
        )
        
        logger.info(f"Entity extraction complete:")
        logger.info(f"  Processed: {result.get('processed', 0)}")
        logger.info(f"  Entities extracted: {result.get('entities_extracted', 0)}")


if __name__ == "__main__":
    main()