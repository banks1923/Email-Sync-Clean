#!/usr/bin/env python3
"""
Entity Extraction Recovery Script - Extract entities from all synced content
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from shared.simple_db import SimpleDB
from entity.main import EntityService
from loguru import logger

def main():
    """Run entity extraction on all content"""
    logger.info("Starting entity extraction recovery...")
    
    db = SimpleDB()
    entity_service = EntityService()
    
    # Get all content that needs entity extraction
    content = db.execute("""
        SELECT id, source_type, source_id, title, body
        FROM content_unified
        WHERE source_type IN ('email_message', 'document')
        AND body IS NOT NULL
        AND LENGTH(body) > 50
    """).fetchall()
    
    logger.info(f"Found {len(content)} items for entity extraction")
    
    success = 0
    failed = 0
    
    for i, row in enumerate(content, 1):
        content_id, source_type, source_id, title, body = row
        
        if i % 10 == 0:
            logger.info(f"Processing {i}/{len(content)}: {success} success, {failed} failed")
        
        try:
            # Extract entities
            entities = entity_service.extract_entities(body, source_type)
            
            if entities:
                # Store entities in database
                for entity in entities:
                    db.execute("""
                        INSERT OR IGNORE INTO entities
                        (entity_type, entity_value, source_type, source_id, confidence_score)
                        VALUES (?, ?, ?, ?, ?)
                    """, (
                        entity['entity_type'],
                        entity['entity_value'],
                        source_type,
                        source_id,
                        entity.get('confidence_score', 0.8)
                    ))
                success += 1
            else:
                failed += 1
                
        except Exception as e:
            logger.error(f"Failed to process {content_id}: {e}")
            failed += 1
    
    # Final stats
    logger.info(f"Entity extraction complete: {success} success, {failed} failed")
    
    # Check entity counts
    entity_count = db.execute("SELECT COUNT(DISTINCT entity_value) FROM entities").fetchone()[0]
    logger.info(f"Total unique entities extracted: {entity_count}")
    
    # Show entity type breakdown
    types = db.execute("""
        SELECT entity_type, COUNT(DISTINCT entity_value) as count
        FROM entities
        GROUP BY entity_type
        ORDER BY count DESC
    """).fetchall()
    
    logger.info("Entity type breakdown:")
    for entity_type, count in types:
        logger.info(f"  {entity_type}: {count}")

if __name__ == "__main__":
    main()