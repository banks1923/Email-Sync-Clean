#!/usr/bin/env python3
"""
Qdrant Vector Reconciliation Script

After schema migration, reconcile Qdrant vectors with content table using deterministic UUIDs.
This ensures vector IDs match content.id values.

Usage:
    python utilities/maintenance/reconcile_qdrant_vectors.py [--dry-run] [--batch-size=100]
"""

import sys
import time
import csv
from pathlib import Path
from typing import Dict
from uuid import UUID, uuid5

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from loguru import logger
from shared.simple_db import SimpleDB
from utilities.embeddings import get_embedding_service
from utilities.vector_store import get_vector_store

# UUID namespace for deterministic ID generation (same as migration)
UUID_NAMESPACE = UUID('6ba7b810-9dad-11d1-80b4-00c04fd430c8')


class QdrantReconciliation:
    """Handles reconciliation of Qdrant vectors with post-migration content table."""
    
    def __init__(self):
        self.db = SimpleDB()
        self.vector_store = get_vector_store()
        self.embedding_service = get_embedding_service()
        self.metrics = {
            'vectors_analyzed': 0,
            'vectors_migrated': 0,
            'vectors_orphaned': 0,
            'vectors_created': 0,
            'content_without_vectors': 0,
            'errors': []
        }
        self.audit_log = []  # Track all actions for CSV export
    
    def run_reconciliation(self, dry_run: bool = False, batch_size: int = 100) -> Dict:
        """Execute complete Qdrant reconciliation."""
        logger.info(f"Starting Qdrant reconciliation (dry_run={dry_run})")
        
        # Check if Qdrant is available
        try:
            self.vector_store.client.get_collections()
        except Exception as e:
            logger.error(f"Qdrant not connected - cannot perform reconciliation: {e}")
            return {'error': 'Qdrant not available'}
        
        try:
            # Phase 1: Analyze current state
            self._analyze_current_state()
            
            # Phase 2: Handle orphaned vectors
            if not dry_run:
                self._remove_orphaned_vectors(batch_size)
            
            # Phase 3: Migrate vectors to new IDs
            if not dry_run:
                self._migrate_vector_ids(batch_size)
            
            # Phase 4: Create missing vectors
            if not dry_run:
                self._create_missing_vectors(batch_size)
            
            # Phase 5: Verify reconciliation
            self._verify_reconciliation()
            
        except Exception as e:
            logger.error(f"Reconciliation failed: {e}")
            self.metrics['errors'].append(str(e))
            raise
        
        # Export audit log
        self._export_audit_log(dry_run)
        
        return self.metrics
    
    def _export_audit_log(self, dry_run: bool):
        """Export audit log to CSV."""
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        filename = f"qdrant_reconciliation_{'dryrun_' if dry_run else ''}{timestamp}.csv"
        filepath = Path("logs") / filename
        
        # Ensure logs directory exists
        filepath.parent.mkdir(exist_ok=True)
        
        with open(filepath, 'w', newline='') as csvfile:
            fieldnames = ['timestamp', 'action', 'vector_id', 'content_id', 'status', 'details']
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            
            writer.writeheader()
            for entry in self.audit_log:
                writer.writerow(entry)
        
        logger.info(f"Audit log exported to: {filepath}")
    
    def _log_action(self, action: str, vector_id: str = None, content_id: str = None, 
                   status: str = "success", details: str = ""):
        """Log an action for the audit trail."""
        self.audit_log.append({
            'timestamp': time.strftime("%Y-%m-%d %H:%M:%S"),
            'action': action,
            'vector_id': vector_id or '',
            'content_id': content_id or '',
            'status': status,
            'details': details
        })
    
    def _analyze_current_state(self):
        """Analyze current state of vectors and content."""
        logger.info("Phase 1: Analyzing current state")
        self._log_action("analyze_start", details="Beginning analysis of vectors and content")
        
        # Get content with deterministic IDs
        content_records = self.db.fetch("""
            SELECT id, source_type, external_id, type, title, content
            FROM content 
            WHERE source_type IS NOT NULL AND external_id IS NOT NULL
        """)
        
        # Calculate what the deterministic IDs should be
        expected_mappings = {}
        for record in content_records:
            deterministic_id = str(uuid5(
                UUID_NAMESPACE, 
                f"{record['source_type']}:{record['external_id']}"
            ))
            expected_mappings[record['id']] = {
                'deterministic_id': deterministic_id,
                'record': record
            }
        
        logger.info(f"Content with business keys: {len(expected_mappings)}")
        
        # Get current vectors from Qdrant
        try:
            all_points = self.vector_store.client.scroll(
                collection_name=self.vector_store.collection,
                limit=10000,
                with_payload=True,
                with_vectors=False
            )[0]
            
            current_vectors = {}
            for point in all_points:
                current_vectors[str(point.id)] = point.payload
                
            logger.info(f"Current vectors in Qdrant: {len(current_vectors)}")
            self.metrics['vectors_analyzed'] = len(current_vectors)
            
        except Exception as e:
            logger.error(f"Failed to retrieve vectors: {e}")
            raise
        
        # Analyze mismatches
        orphaned_vectors = set(current_vectors.keys()) - set(expected_mappings.keys())
        content_without_vectors = set(expected_mappings.keys()) - set(current_vectors.keys())
        
        logger.info(f"Orphaned vectors: {len(orphaned_vectors)}")
        logger.info(f"Content without vectors: {len(content_without_vectors)}")
        
        self.metrics['vectors_orphaned'] = len(orphaned_vectors)
        self.metrics['content_without_vectors'] = len(content_without_vectors)
        
        # Store for use in later phases
        self._expected_mappings = expected_mappings
        self._current_vectors = current_vectors
        self._orphaned_vectors = orphaned_vectors
        self._content_without_vectors = content_without_vectors
    
    def _remove_orphaned_vectors(self, batch_size: int):
        """Remove vectors that don't correspond to current content."""
        logger.info("Phase 2: Removing orphaned vectors")
        
        if not self._orphaned_vectors:
            logger.info("No orphaned vectors to remove")
            return
        
        orphaned_list = list(self._orphaned_vectors)
        logger.info(f"Removing {len(orphaned_list)} orphaned vectors")
        
        # Process in batches
        for i in range(0, len(orphaned_list), batch_size):
            batch = orphaned_list[i:i+batch_size]
            try:
                self.vector_store.delete_many(batch)
                logger.debug(f"Deleted batch of {len(batch)} orphaned vectors")
            except Exception as e:
                logger.error(f"Failed to delete orphaned batch: {e}")
                self.metrics['errors'].append(f"Delete orphaned: {e}")
    
    def _migrate_vector_ids(self, batch_size: int):
        """Migrate existing vectors to use deterministic content IDs."""
        logger.info("Phase 3: Migrating vector IDs")
        
        # Find vectors that need ID migration (exist but with wrong ID)
        vectors_to_migrate = []
        
        for content_id, mapping in self._expected_mappings.items():
            deterministic_id = mapping['deterministic_id']
            record = mapping['record']
            
            # Check if we have a vector with old ID pattern that should map to this content
            old_id_candidates = [
                record['external_id'],  # message_id directly
                f"email_{record['external_id']}",  # prefixed pattern
                # Add other potential old ID patterns here
            ]
            
            for old_id in old_id_candidates:
                if old_id in self._current_vectors and old_id != content_id:
                    vectors_to_migrate.append({
                        'old_id': old_id,
                        'new_id': content_id,
                        'deterministic_id': deterministic_id,
                        'record': record,
                        'vector_data': self._current_vectors[old_id]
                    })
                    break
        
        logger.info(f"Found {len(vectors_to_migrate)} vectors needing ID migration")
        
        if not vectors_to_migrate:
            logger.info("No vector ID migration needed")
            return
        
        # Process migrations in batches
        for i in range(0, len(vectors_to_migrate), batch_size):
            batch = vectors_to_migrate[i:i+batch_size]
            
            for migration in batch:
                try:
                    # Get the full vector data
                    old_point = self.vector_store.client.retrieve(
                        collection_name=self.vector_store.collection,
                        ids=[migration['old_id']],
                        with_vectors=True
                    )[0]
                    
                    if not old_point:
                        continue
                    
                    # Create new point with correct ID and updated payload
                    new_payload = {
                        'content_id': migration['new_id'],
                        'content_type': migration['record']['type'],
                        'title': migration['record']['title'] or 'Untitled',
                        'char_count': len(migration['record']['content'] or '')
                    }
                    
                    # Upsert with new ID
                    self.vector_store.upsert(
                        id=migration['new_id'],
                        vector=old_point.vector,
                        payload=new_payload
                    )
                    
                    # Delete old vector
                    self.vector_store.delete_many([migration['old_id']])
                    
                    self.metrics['vectors_migrated'] += 1
                    logger.debug(f"Migrated vector: {migration['old_id']} -> {migration['new_id']}")
                    
                except Exception as e:
                    logger.error(f"Failed to migrate vector {migration['old_id']}: {e}")
                    self.metrics['errors'].append(f"Vector migration: {e}")
            
            # Brief pause between batches
            time.sleep(0.1)
    
    def _create_missing_vectors(self, batch_size: int):
        """Create embeddings for content that doesn't have vectors."""
        logger.info("Phase 4: Creating missing vectors")
        
        if not self._content_without_vectors:
            logger.info("No missing vectors to create")
            return
        
        missing_content = []
        for content_id in self._content_without_vectors:
            if content_id in self._expected_mappings:
                record = self._expected_mappings[content_id]['record']
                missing_content.append(record)
        
        logger.info(f"Creating vectors for {len(missing_content)} content items")
        
        # Process in batches
        for i in range(0, len(missing_content), batch_size):
            batch = missing_content[i:i+batch_size]
            
            for record in batch:
                try:
                    # Generate embedding
                    content_text = record['content'] or ''
                    if len(content_text) > 8000:
                        content_text = content_text[:8000]  # Truncate for embedding
                    
                    embedding = self.embedding_service.encode(content_text)
                    
                    # Create payload
                    payload = {
                        'content_id': record['id'],
                        'content_type': record['type'],
                        'title': record['title'] or 'Untitled',
                        'char_count': len(record['content'] or '')
                    }
                    
                    # Store vector
                    self.vector_store.upsert(
                        id=record['id'],
                        vector=embedding.tolist(),
                        payload=payload
                    )
                    
                    self.metrics['vectors_created'] += 1
                    logger.debug(f"Created vector for content: {record['id']}")
                    
                except Exception as e:
                    logger.error(f"Failed to create vector for {record['id']}: {e}")
                    self.metrics['errors'].append(f"Vector creation: {e}")
            
            # Brief pause between batches
            time.sleep(0.2)
    
    def _verify_reconciliation(self):
        """Verify reconciliation was successful."""
        logger.info("Phase 5: Verifying reconciliation")
        
        try:
            # Count final vectors
            vector_count = self.vector_store.count()
            
            # Count content with business keys
            content_count = self.db.fetch_one("""
                SELECT COUNT(*) as count 
                FROM content 
                WHERE source_type IS NOT NULL AND external_id IS NOT NULL
            """)['count']
            
            # Check for remaining mismatches
            content_ids = {r['id'] for r in self.db.fetch("SELECT id FROM content WHERE source_type IS NOT NULL")}
            
            current_vectors = self.vector_store.client.scroll(
                collection_name=self.vector_store.collection,
                limit=10000,
                with_payload=False,
                with_vectors=False
            )[0]
            
            vector_ids = {str(point.id) for point in current_vectors}
            
            still_orphaned = vector_ids - content_ids
            still_missing = content_ids - vector_ids
            
            logger.info("Final verification:")
            logger.info(f"  Content items: {content_count}")
            logger.info(f"  Vectors: {vector_count}")
            logger.info(f"  Still orphaned: {len(still_orphaned)}")
            logger.info(f"  Still missing: {len(still_missing)}")
            
            if len(still_orphaned) == 0 and len(still_missing) == 0:
                logger.info("✓ Reconciliation successful - perfect sync")
            else:
                logger.warning(f"⚠ Reconciliation incomplete: {len(still_orphaned)} orphaned, {len(still_missing)} missing")
            
        except Exception as e:
            logger.error(f"Verification failed: {e}")
            self.metrics['errors'].append(f"Verification: {e}")


def main():
    """Run Qdrant reconciliation."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Reconcile Qdrant vectors with post-migration content table")
    parser.add_argument('--dry-run', action='store_true',
                       help='Show what would be done without making changes')
    parser.add_argument('--batch-size', type=int, default=100,
                       help='Batch size for processing (default: 100)')
    
    args = parser.parse_args()
    
    reconciliation = QdrantReconciliation()
    metrics = reconciliation.run_reconciliation(dry_run=args.dry_run, batch_size=args.batch_size)
    
    # Report results
    logger.info("=== QDRANT RECONCILIATION SUMMARY ===")
    for key, value in metrics.items():
        if key != 'errors':
            logger.info(f"{key}: {value}")
    
    if metrics.get('errors'):
        logger.error(f"Errors encountered: {len(metrics['errors'])}")
        for error in metrics['errors'][:5]:  # Show first 5 errors
            logger.error(f"  - {error}")
        if len(metrics['errors']) > 5:
            logger.error(f"  ... and {len(metrics['errors']) - 5} more errors")
        return 1
    
    if args.dry_run:
        logger.info("DRY RUN complete - no changes made")
        logger.info("Run without --dry-run to apply changes")
    else:
        logger.info("Reconciliation completed successfully")
    
    return 0


if __name__ == "__main__":
    exit(main())