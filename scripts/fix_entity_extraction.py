#!/usr/bin/env python3
"""
Fix Entity Extraction Integration

This script addresses the missing entity extraction in the unified processing pipeline:
1. Extract entities from all content in content_unified table
2. Link entities to their source content via entity_content_mapping
3. Update consolidated entities with proper attribution
4. Verify entity extraction is working across all content types

Status: 
- 1,482 content records without entity extraction
- 695 consolidated entities without source attribution
- 0 entity mappings between entities and content
"""

import sys
import time
from pathlib import Path
from typing import Dict, List, Any

# Add project root to path
sys.path.append(str(Path(__file__).parent.parent))

from loguru import logger
from shared.simple_db import SimpleDB
from entity.main import EntityService


class EntityExtractionFixer:
    """Fix missing entity extraction across unified content"""
    
    def __init__(self):
        self.db = SimpleDB()
        self.entity_service = EntityService()
        self.stats = {
            'content_processed': 0,
            'entities_extracted': 0,
            'entities_mapped': 0,
            'errors': 0,
            'skipped': 0
        }
    
    def analyze_current_state(self) -> Dict[str, Any]:
        """Analyze current entity extraction state"""
        logger.info("🔍 Analyzing current entity extraction state...")
        
        # Get content counts
        content_counts = self.db.fetch("""
            SELECT source_type, COUNT(*) as count 
            FROM content_unified 
            GROUP BY source_type
        """)
        
        # Get entity mapping counts  
        mapping_count = self.db.fetch("SELECT COUNT(*) as count FROM entity_content_mapping")[0]['count']
        
        # Get consolidated entity counts
        consolidated_count = self.db.fetch("SELECT COUNT(*) as count FROM consolidated_entities")[0]['count']
        
        # Get email entities count
        email_entities_count = self.db.fetch("SELECT COUNT(*) as count FROM email_entities")[0]['count']
        
        state = {
            'content_by_type': {row['source_type']: row['count'] for row in content_counts},
            'total_content': sum(row['count'] for row in content_counts),
            'entity_mappings': mapping_count,
            'consolidated_entities': consolidated_count,
            'email_entities': email_entities_count
        }
        
        logger.info(f"Content types: {state['content_by_type']}")
        logger.info(f"Entity mappings: {state['entity_mappings']}")
        logger.info(f"Consolidated entities: {state['consolidated_entities']}")
        logger.info(f"Email entities: {state['email_entities']}")
        
        return state
    
    def extract_entities_from_content(self, batch_size: int = 50) -> Dict[str, int]:
        """Extract entities from all content in content_unified table"""
        logger.info("🔬 Starting entity extraction from unified content...")
        
        # Get all content that needs entity extraction
        content_records = self.db.fetch("""
            SELECT id, source_type, title, body, source_id
            FROM content_unified 
            WHERE body IS NOT NULL 
            AND LENGTH(TRIM(body)) > 10
            ORDER BY created_at DESC
        """)
        
        logger.info(f"Found {len(content_records)} content records to process")
        
        processed = 0
        total_entities = 0
        
        for i, record in enumerate(content_records):
            try:
                content_id = record['id']
                source_type = record['source_type']
                title = record['title'] or ''
                body = record['body']
                source_id = record['source_id']
                
                # Combine title and body for extraction
                full_text = f"{title}\n\n{body}".strip()
                
                # Extract entities using the entity service
                entities = self.entity_service.extract_entities(full_text)
                
                if entities:
                    # Store entity mappings
                    self._store_entity_mappings(content_id, source_id, entities)
                    total_entities += len(entities)
                    
                processed += 1
                
                # Progress update
                if processed % 25 == 0:
                    logger.info(f"Processed {processed}/{len(content_records)} content records, extracted {total_entities} entities")
                
                # Small delay to prevent overwhelming the system
                if processed % 100 == 0:
                    time.sleep(0.1)
                    
            except Exception as e:
                logger.error(f"Error processing content {record.get('id', 'unknown')}: {e}")
                self.stats['errors'] += 1
                continue
        
        self.stats['content_processed'] = processed
        self.stats['entities_extracted'] = total_entities
        
        logger.info(f"✅ Entity extraction complete: {processed} content records, {total_entities} entities")
        return {'processed': processed, 'entities': total_entities}
    
    def _store_entity_mappings(self, content_id: str, source_id: str, entities: List[Dict[str, Any]]):
        """Store entity-to-content mappings"""
        mappings = []
        
        for entity in entities:
            mapping = {
                'entity_id': entity.get('entity_id'),
                'entity_value': entity.get('text', ''),
                'entity_type': entity.get('label', ''),
                'content_id': content_id,
                'message_id': source_id,  # This could be email message_id or document path
                'confidence': entity.get('confidence', 0.8),
                'metadata': f'{{"start_char": {entity.get("start", 0)}, "end_char": {entity.get("end", 0)}}}'
            }
            mappings.append(mapping)
        
        if mappings:
            # Batch insert mappings
            columns = ['entity_id', 'entity_value', 'entity_type', 'content_id', 'message_id', 'confidence', 'metadata']
            values = [[m[col] for col in columns] for m in mappings]
            
            self.db.batch_insert('entity_content_mapping', columns, values)
            self.stats['entities_mapped'] += len(mappings)
    
    def verify_extraction_quality(self) -> Dict[str, Any]:
        """Verify the quality of entity extraction"""
        logger.info("🔍 Verifying entity extraction quality...")
        
        # Check entity distribution by type
        entity_types = self.db.fetch("""
            SELECT entity_type, COUNT(*) as count
            FROM entity_content_mapping
            GROUP BY entity_type
            ORDER BY count DESC
        """)
        
        # Check entities per content type
        entities_per_content = self.db.fetch("""
            SELECT cu.source_type, COUNT(DISTINCT ecm.entity_id) as unique_entities, 
                   COUNT(ecm.id) as total_extractions
            FROM content_unified cu
            JOIN entity_content_mapping ecm ON cu.id = ecm.content_id
            GROUP BY cu.source_type
        """)
        
        # Check for content without entities
        content_without_entities = self.db.fetch("""
            SELECT COUNT(*) as count
            FROM content_unified cu
            LEFT JOIN entity_content_mapping ecm ON cu.id = ecm.content_id
            WHERE ecm.content_id IS NULL
            AND cu.body IS NOT NULL
            AND LENGTH(TRIM(cu.body)) > 10
        """)[0]['count']
        
        quality_report = {
            'entity_types': {row['entity_type']: row['count'] for row in entity_types},
            'entities_per_content_type': {
                row['source_type']: {
                    'unique_entities': row['unique_entities'],
                    'total_extractions': row['total_extractions']
                } for row in entities_per_content
            },
            'content_without_entities': content_without_entities
        }
        
        logger.info("Entity type distribution:")
        for entity_type, count in quality_report['entity_types'].items():
            logger.info(f"  {entity_type}: {count:,}")
        
        logger.info("Entities per content type:")
        for content_type, data in quality_report['entities_per_content_type'].items():
            logger.info(f"  {content_type}: {data['unique_entities']} unique, {data['total_extractions']} total")
        
        if content_without_entities > 0:
            logger.warning(f"⚠️  {content_without_entities} content records still have no entities")
        
        return quality_report
    
    def update_consolidated_entities(self):
        """Update consolidated entities with proper source attribution"""
        logger.info("🔄 Updating consolidated entities with source attribution...")
        
        # This would require more complex logic to merge entity_content_mapping
        # data back into consolidated_entities. For now, just report the gap.
        
        orphaned_entities = self.db.fetch("""
            SELECT COUNT(*) as count
            FROM consolidated_entities ce
            WHERE NOT EXISTS (
                SELECT 1 FROM entity_content_mapping ecm 
                WHERE ecm.entity_value = ce.primary_name
                OR ecm.entity_id = ce.entity_id
            )
        """)[0]['count']
        
        logger.warning(f"⚠️  {orphaned_entities} consolidated entities still lack source attribution")
        
        return orphaned_entities
    
    def run_complete_fix(self) -> Dict[str, Any]:
        """Run complete entity extraction fix"""
        logger.info("🚀 Starting complete entity extraction fix...")
        start_time = time.time()
        
        # 1. Analyze current state
        initial_state = self.analyze_current_state()
        
        # 2. Extract entities from all unified content
        extraction_result = self.extract_entities_from_content()
        
        # 3. Verify extraction quality
        quality_report = self.verify_extraction_quality()
        
        # 4. Update consolidated entities
        orphaned_count = self.update_consolidated_entities()
        
        elapsed_time = time.time() - start_time
        
        final_report = {
            'initial_state': initial_state,
            'extraction_result': extraction_result,
            'quality_report': quality_report,
            'orphaned_entities': orphaned_count,
            'processing_stats': self.stats,
            'elapsed_time_seconds': elapsed_time
        }
        
        logger.info("✅ Entity extraction fix complete!")
        logger.info(f"📊 Final stats:")
        logger.info(f"  Content processed: {self.stats['content_processed']:,}")
        logger.info(f"  Entities extracted: {self.stats['entities_extracted']:,}")
        logger.info(f"  Entity mappings created: {self.stats['entities_mapped']:,}")
        logger.info(f"  Errors: {self.stats['errors']:,}")
        logger.info(f"  Total time: {elapsed_time:.1f} seconds")
        
        return final_report


def main():
    """Main function"""
    if len(sys.argv) > 1 and sys.argv[1] == '--dry-run':
        logger.info("🔍 DRY RUN MODE - Analysis only, no changes made")
        fixer = EntityExtractionFixer()
        state = fixer.analyze_current_state()
        
        print("\n📊 Current Entity Extraction State:")
        print(f"  Total content records: {state['total_content']:,}")
        print(f"  Entity mappings: {state['entity_mappings']:,}")
        print(f"  Consolidated entities: {state['consolidated_entities']:,}")
        print(f"  Email entities: {state['email_entities']:,}")
        print("\nContent by type:")
        for content_type, count in state['content_by_type'].items():
            print(f"  - {content_type}: {count:,}")
        
        print(f"\n⚠️  ISSUES IDENTIFIED:")
        if state['entity_mappings'] == 0:
            print(f"  - NO entity-to-content mappings (should be >1000)")
        if state['email_entities'] == 0:
            print(f"  - NO email entities extracted (should be >1000)")
        print(f"  - {state['consolidated_entities']} entities without source attribution")
        
    else:
        logger.info("🔧 RUNNING FULL FIX - This will modify the database")
        fixer = EntityExtractionFixer()
        report = fixer.run_complete_fix()
        
        # Save report for analysis
        import json
        report_path = Path("data/system_data/entity_extraction_fix_report.json")
        with open(report_path, 'w') as f:
            json.dump(report, f, indent=2, default=str)
        logger.info(f"📄 Full report saved to: {report_path}")


if __name__ == "__main__":
    main()