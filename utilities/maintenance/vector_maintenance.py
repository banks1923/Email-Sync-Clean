#!/usr/bin/env python3
"""
Consolidated Vector Store Maintenance Utilities

Combines functionality from:
- sync_emails_to_qdrant.py
- sync_missing_vectors.py
- reconcile_qdrant_vectors.py
- verify_vector_sync.py
- purge_test_vectors.py
"""

import sys
import hashlib
import argparse
from pathlib import Path
from typing import Optional, Set, Dict, Any
from loguru import logger
from qdrant_client import QdrantClient
from qdrant_client.models import PointStruct

from shared.simple_db import SimpleDB
from utilities.embeddings import get_embedding_service
from utilities.vector_store import get_vector_store
from gmail.main import GmailService


class VectorMaintenance:
    """Unified vector store maintenance operations."""
    
    def __init__(self):
        self.db = SimpleDB()
        self.embedding_service = get_embedding_service()
        self.vector_store = get_vector_store()
        self.gmail_service = GmailService()
        
    def sync_emails_to_vectors(self, limit: Optional[int] = None) -> Dict[str, Any]:
        """Sync email content to vector store."""
        logger.info("Starting email to vector sync")
        
        # Get emails without vectors
        emails = self.db.get_emails_without_vectors(limit=limit)
        if not emails:
            logger.info("No emails need vector sync")
            return {"synced": 0, "status": "no emails to sync"}
            
        synced_count = 0
        errors = []
        
        for email in emails:
            try:
                # Generate embedding
                embedding = self.embedding_service.get_embedding(email['body'])
                
                # Store in vector store
                self.vector_store.add_email_vector(
                    email_id=email['id'],
                    embedding=embedding,
                    metadata={
                        'subject': email['subject'],
                        'from': email['sender'],
                        'date': email['date']
                    }
                )
                
                # Update database
                self.db.mark_email_vectorized(email['id'])
                synced_count += 1
                
            except Exception as e:
                logger.error(f"Failed to sync email {email['id']}: {e}")
                errors.append({"email_id": email['id'], "error": str(e)})
                
        logger.info(f"Synced {synced_count} emails to vector store")
        return {
            "synced": synced_count,
            "errors": errors,
            "status": "completed"
        }
    
    def sync_missing_vectors(self, collection: str = "emails") -> Dict[str, Any]:
        """Find and sync content missing from vector store."""
        logger.info(f"Checking for missing vectors in {collection}")
        
        # Get IDs from database
        db_ids = set(self.db.get_all_content_ids(content_type=collection))
        
        # Get IDs from vector store
        vector_ids = self.vector_store.list_all_ids(collection=collection)
        
        # Find missing
        missing = db_ids - vector_ids
        
        if not missing:
            logger.info("No missing vectors found")
            return {"missing": 0, "status": "all synced"}
            
        logger.info(f"Found {len(missing)} missing vectors, syncing...")
        
        synced = 0
        errors = []
        
        for content_id in missing:
            try:
                # Get content from database
                content = self.db.get_content_by_id(content_id)
                if not content:
                    continue
                    
                # Generate embedding
                embedding = self.embedding_service.get_embedding(content['text'])
                
                # Add to vector store
                self.vector_store.add_vector(
                    id=content_id,
                    embedding=embedding,
                    metadata=content.get('metadata', {}),
                    collection=collection
                )
                
                synced += 1
                
            except Exception as e:
                logger.error(f"Failed to sync {content_id}: {e}")
                errors.append({"id": content_id, "error": str(e)})
                
        return {
            "missing_found": len(missing),
            "synced": synced,
            "errors": errors,
            "status": "completed"
        }
    
    def reconcile_vectors(self, fix: bool = False) -> Dict[str, Any]:
        """Reconcile vector store with database."""
        logger.info("Starting vector reconciliation")
        
        results = {
            "orphaned_vectors": [],
            "missing_vectors": [],
            "mismatched_metadata": [],
            "fixes_applied": 0
        }
        
        # Check all collections
        collections = ["emails", "pdfs", "transcriptions", "notes"]
        
        for collection in collections:
            logger.info(f"Checking {collection}")
            
            # Get IDs from both sources
            db_ids = set(self.db.get_all_content_ids(content_type=collection))
            vector_ids = self.vector_store.list_all_ids(collection=collection)
            
            # Find discrepancies
            orphaned = vector_ids - db_ids  # In vectors but not DB
            missing = db_ids - vector_ids   # In DB but not vectors
            
            results["orphaned_vectors"].extend([
                {"collection": collection, "id": id} for id in orphaned
            ])
            results["missing_vectors"].extend([
                {"collection": collection, "id": id} for id in missing
            ])
            
            if fix:
                # Remove orphaned vectors
                for vector_id in orphaned:
                    try:
                        self.vector_store.delete_vector(vector_id, collection)
                        results["fixes_applied"] += 1
                    except Exception as e:
                        logger.error(f"Failed to delete orphaned vector {vector_id}: {e}")
                        
                # Add missing vectors
                for content_id in missing:
                    try:
                        content = self.db.get_content_by_id(content_id)
                        if content:
                            embedding = self.embedding_service.get_embedding(content['text'])
                            self.vector_store.add_vector(
                                id=content_id,
                                embedding=embedding,
                                metadata=content.get('metadata', {}),
                                collection=collection
                            )
                            results["fixes_applied"] += 1
                    except Exception as e:
                        logger.error(f"Failed to add missing vector {content_id}: {e}")
                        
        return results
    
    def verify_sync(self) -> Dict[str, Any]:
        """Verify vector sync status across all collections."""
        logger.info("Verifying vector sync status")
        
        status = {}
        
        collections = ["emails", "pdfs", "transcriptions", "notes"]
        
        for collection in collections:
            db_count = self.db.get_content_count(content_type=collection)
            vector_count = self.vector_store.get_collection_stats(collection).get('vectors_count', 0)
            
            status[collection] = {
                "database_count": db_count,
                "vector_count": vector_count,
                "synced": db_count == vector_count,
                "difference": abs(db_count - vector_count)
            }
            
        # Overall health
        all_synced = all(s["synced"] for s in status.values())
        
        return {
            "collections": status,
            "all_synced": all_synced,
            "status": "healthy" if all_synced else "needs_sync"
        }
    
    def purge_test_vectors(self, dry_run: bool = True) -> Dict[str, Any]:
        """Remove test vectors from production collections."""
        logger.info(f"Purging test vectors (dry_run={dry_run})")
        
        test_patterns = [
            "test_",
            "tmp_",
            "temp_",
            "_test",
            "_tmp"
        ]
        
        purged = []
        
        collections = ["emails", "pdfs", "transcriptions", "notes"]
        
        for collection in collections:
            vector_ids = self.vector_store.list_all_ids(collection=collection)
            
            for vector_id in vector_ids:
                # Check if it's a test vector
                if any(pattern in vector_id.lower() for pattern in test_patterns):
                    if not dry_run:
                        try:
                            self.vector_store.delete_vector(vector_id, collection)
                            purged.append({"collection": collection, "id": vector_id})
                        except Exception as e:
                            logger.error(f"Failed to purge {vector_id}: {e}")
                    else:
                        purged.append({"collection": collection, "id": vector_id})
                        
        return {
            "purged_count": len(purged),
            "purged_vectors": purged,
            "dry_run": dry_run,
            "status": "completed"
        }


def main():
    """CLI interface for vector maintenance."""
    parser = argparse.ArgumentParser(description="Vector Store Maintenance")
    
    subparsers = parser.add_subparsers(dest='command', help='Commands')
    
    # Sync emails command
    sync_emails = subparsers.add_parser('sync-emails', help='Sync emails to vectors')
    sync_emails.add_argument('--limit', type=int, help='Limit number of emails to sync')
    
    # Sync missing command
    sync_missing = subparsers.add_parser('sync-missing', help='Sync missing vectors')
    sync_missing.add_argument('--collection', default='emails', help='Collection to check')
    
    # Reconcile command
    reconcile = subparsers.add_parser('reconcile', help='Reconcile vectors with database')
    reconcile.add_argument('--fix', action='store_true', help='Apply fixes')
    
    # Verify command
    subparsers.add_parser('verify', help='Verify sync status')
    
    # Purge command
    purge = subparsers.add_parser('purge-test', help='Purge test vectors')
    purge.add_argument('--execute', action='store_true', help='Actually delete (not dry run)')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        sys.exit(1)
        
    maintenance = VectorMaintenance()
    
    if args.command == 'sync-emails':
        result = maintenance.sync_emails_to_vectors(limit=args.limit)
    elif args.command == 'sync-missing':
        result = maintenance.sync_missing_vectors(collection=args.collection)
    elif args.command == 'reconcile':
        result = maintenance.reconcile_vectors(fix=args.fix)
    elif args.command == 'verify':
        result = maintenance.verify_sync()
    elif args.command == 'purge-test':
        result = maintenance.purge_test_vectors(dry_run=not args.execute)
    else:
        parser.print_help()
        sys.exit(1)
        
    # Print results
    import json
    print(json.dumps(result, indent=2))
    
    # Exit with error if not healthy
    if result.get('status') not in ['completed', 'healthy', 'all synced', 'no emails to sync']:
        sys.exit(1)


if __name__ == "__main__":
    main()