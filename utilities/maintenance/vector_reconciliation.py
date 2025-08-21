#!/usr/bin/env python3
"""
Vector Reconciliation System - Ensures Qdrant vectors match database state.
Handles email vector cleanup, orphan detection, and sync operations.
"""

import json
from typing import Dict, List, Tuple, Any, Optional, Set
from dataclasses import dataclass
from datetime import datetime

from loguru import logger
from shared.simple_db import SimpleDB
from utilities.vector_store import get_vector_store


@dataclass
class VectorSyncResult:
    """Result of vector synchronization operation."""
    vectors_deleted: int
    vectors_upserted: int
    orphaned_vectors: int
    missing_vectors: int
    content_entries_created: int
    errors: List[str]


class VectorReconciliationService:
    """Manages vector store reconciliation with database state."""
    
    def __init__(self, db_path: str = "data/emails.db", collection: str = "emails"):
        self.db = SimpleDB(db_path)
        self.collection = collection
        self.vector_store = None
        
    def _get_vector_store(self):
        """Get vector store connection with error handling."""
        if self.vector_store is None:
            try:
                self.vector_store = get_vector_store(self.collection)
                if not self.vector_store.health():
                    raise RuntimeError("Vector store health check failed")
                logger.info(f"Connected to Qdrant collection: {self.collection}")
            except Exception as e:
                logger.error(f"Failed to connect to vector store: {e}")
                return None
        return self.vector_store
    
    def reconcile_email_vectors(self) -> VectorSyncResult:
        """
        Complete email vector reconciliation process.
        
        Returns:
            VectorSyncResult with operation summary
        """
        logger.info("Starting complete email vector reconciliation")
        
        result = VectorSyncResult(
            vectors_deleted=0,
            vectors_upserted=0,
            orphaned_vectors=0,
            missing_vectors=0,
            content_entries_created=0,
            errors=[]
        )
        
        vector_store = self._get_vector_store()
        if not vector_store:
            result.errors.append("Vector store unavailable")
            return result
        
        try:
            # Step 1: Clean up quarantined email vectors
            deleted_quarantined = self._delete_quarantined_vectors()
            result.vectors_deleted += deleted_quarantined
            
            # Step 2: Find and remove orphaned vectors
            orphaned_count = self._cleanup_orphaned_vectors()
            result.orphaned_vectors = orphaned_count
            result.vectors_deleted += orphaned_count
            
            # Step 3: Create missing content_unified entries
            content_created = self._create_missing_content_entries()
            result.content_entries_created = content_created
            
            # Step 4: Identify emails missing embeddings/vectors
            missing_vectors = self._find_missing_vectors()
            result.missing_vectors = len(missing_vectors)
            
            logger.info(f"Vector reconciliation complete: "
                       f"deleted={result.vectors_deleted}, "
                       f"content_created={result.content_entries_created}, "
                       f"missing_vectors={result.missing_vectors}")
            
        except Exception as e:
            error_msg = f"Vector reconciliation failed: {e}"
            logger.error(error_msg)
            result.errors.append(error_msg)
        
        return result
    
    def _delete_quarantined_vectors(self) -> int:
        """Delete vectors for quarantined emails."""
        vector_store = self._get_vector_store()
        if not vector_store:
            return 0
        
        # Get quarantined email message IDs
        quarantined_ids = self.db.execute("""
            SELECT DISTINCT message_id 
            FROM emails_quarantine 
            WHERE status = 'quarantined'
        """).fetchall()
        
        if not quarantined_ids:
            logger.debug("No quarantined emails found")
            return 0
        
        message_ids = [row[0] for row in quarantined_ids]
        
        try:
            # Delete vectors by message_id (assumes vectors use message_id as ID)
            vector_store.delete_many(message_ids)
            logger.info(f"Deleted {len(message_ids)} vectors for quarantined emails")
            return len(message_ids)
        except Exception as e:
            logger.error(f"Failed to delete quarantined vectors: {e}")
            return 0
    
    def _cleanup_orphaned_vectors(self) -> int:
        """Find and remove vectors that don't correspond to valid emails."""
        vector_store = self._get_vector_store()
        if not vector_store:
            return 0
        
        try:
            # Get all vector IDs from Qdrant
            all_vector_ids = vector_store.list_all_ids(self.collection)
            
            if not all_vector_ids:
                logger.debug("No vectors found in collection")
                return 0
            
            # Get all valid email message IDs from database
            valid_email_ids = self.db.execute("""
                SELECT DISTINCT message_id FROM emails
                UNION
                SELECT DISTINCT message_id FROM emails_quarantine WHERE status = 'restored'
            """).fetchall()
            valid_ids = {row[0] for row in valid_email_ids}
            
            # Find orphaned vectors (exist in Qdrant but not in valid emails)
            orphaned_ids = [vid for vid in all_vector_ids if vid not in valid_ids]
            
            if orphaned_ids:
                logger.info(f"Found {len(orphaned_ids)} orphaned vectors")
                vector_store.delete_many(orphaned_ids)
                logger.info(f"Deleted {len(orphaned_ids)} orphaned vectors")
                return len(orphaned_ids)
            else:
                logger.debug("No orphaned vectors found")
                return 0
                
        except Exception as e:
            logger.error(f"Failed to cleanup orphaned vectors: {e}")
            return 0
    
    def _create_missing_content_entries(self) -> int:
        """Create content_unified entries for emails that don't have them."""
        # Find emails missing content_unified entries
        emails_missing_content = self.db.execute("""
            SELECT e.id, e.message_id, e.subject, e.content, e.datetime_utc, e.content_hash
            FROM emails e
            LEFT JOIN content_unified c ON c.source_type = 'email' AND c.source_id = e.id
            WHERE c.id IS NULL
        """).fetchall()
        
        if not emails_missing_content:
            logger.debug("All emails have content_unified entries")
            return 0
        
        created_count = 0
        
        for email_id, message_id, subject, content, datetime_utc, content_hash in emails_missing_content:
            try:
                # Generate SHA256 if missing
                if not content_hash:
                    content_hash = self._generate_sha256(content or '')
                
                # Create content_unified entry
                self.db.execute("""
                    INSERT INTO content_unified 
                    (source_type, source_id, title, body, ready_for_embedding, sha256, chunk_index)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (
                    'email',
                    email_id,
                    subject or f'Email {message_id}',
                    content or '',
                    1,  # Ready for embedding
                    content_hash,
                    0   # Single chunk for emails
                ))
                
                created_count += 1
                logger.debug(f"Created content_unified entry for email {email_id}")
                
            except Exception as e:
                logger.error(f"Failed to create content_unified for email {email_id}: {e}")
        
        if created_count > 0:
            logger.info(f"Created {created_count} content_unified entries")
        
        return created_count
    
    def _find_missing_vectors(self) -> List[Dict[str, Any]]:
        """Find emails that should have vectors but don't."""
        # Find content_unified entries for emails that don't have embeddings
        missing_embeddings = self.db.execute("""
            SELECT c.id, c.source_id, c.title, c.body, e.message_id
            FROM content_unified c
            JOIN emails e ON e.id = c.source_id
            LEFT JOIN embeddings emb ON emb.content_id = c.id
            WHERE c.source_type = 'email' 
              AND c.ready_for_embedding = 1 
              AND emb.id IS NULL
        """).fetchall()
        
        missing_vectors = []
        for content_id, email_id, title, body, message_id in missing_embeddings:
            missing_vectors.append({
                'content_id': content_id,
                'email_id': email_id,
                'message_id': message_id,
                'title': title,
                'body_length': len(body or ''),
                'needs_embedding': True
            })
        
        if missing_vectors:
            logger.info(f"Found {len(missing_vectors)} emails missing embeddings")
        
        return missing_vectors
    
    def _generate_sha256(self, content: str) -> str:
        """Generate SHA256 hash for content."""
        import hashlib
        return hashlib.sha256(content.encode('utf-8')).hexdigest()
    
    def get_vector_sync_status(self) -> Dict[str, Any]:
        """Get current sync status between database and vector store."""
        vector_store = self._get_vector_store()
        
        status = {
            "timestamp": datetime.now().isoformat(),
            "vector_store_available": vector_store is not None,
            "collection": self.collection
        }
        
        if not vector_store:
            status.update({
                "error": "Vector store unavailable",
                "qdrant_vectors": 0,
                "database_emails": 0,
                "content_unified_entries": 0,
                "embeddings": 0
            })
            return status
        
        try:
            # Get counts from various sources
            qdrant_stats = vector_store.get_collection_stats(self.collection)
            qdrant_count = qdrant_stats.get('points_count', 0)
            
            db_email_count = self.db.execute("SELECT COUNT(*) FROM emails").fetchall()[0][0]
            
            content_unified_count = self.db.execute("""
                SELECT COUNT(*) FROM content_unified WHERE source_type = 'email'
            """).fetchall()[0][0]
            
            embeddings_count = self.db.execute("""
                SELECT COUNT(*) FROM embeddings e
                JOIN content_unified c ON e.content_id = c.id
                WHERE c.source_type = 'email'
            """).fetchall()[0][0]
            
            quarantined_count = self.db.execute("""
                SELECT COUNT(*) FROM emails_quarantine WHERE status = 'quarantined'
            """).fetchall()[0][0]
            
            status.update({
                "qdrant_vectors": qdrant_count,
                "database_emails": db_email_count,
                "content_unified_entries": content_unified_count,
                "embeddings": embeddings_count,
                "quarantined_emails": quarantined_count,
                "sync_ratio": embeddings_count / max(db_email_count, 1),
                "needs_reconciliation": embeddings_count < db_email_count
            })
            
        except Exception as e:
            status["error"] = f"Failed to get sync status: {e}"
        
        return status
    
    def force_rebuild_vectors(self, limit: int = 100) -> VectorSyncResult:
        """
        Force rebuild vectors for emails (emergency recovery).
        
        Args:
            limit: Maximum number of vectors to rebuild at once
            
        Returns:
            VectorSyncResult with operation summary
        """
        logger.warning(f"Force rebuilding vectors (limit={limit})")
        
        result = VectorSyncResult(
            vectors_deleted=0,
            vectors_upserted=0,
            orphaned_vectors=0,
            missing_vectors=0,
            content_entries_created=0,
            errors=[]
        )
        
        try:
            # First ensure content_unified entries exist
            content_created = self._create_missing_content_entries()
            result.content_entries_created = content_created
            
            # Find content ready for embedding
            ready_content = self.db.execute("""
                SELECT c.id, c.body, e.message_id
                FROM content_unified c
                JOIN emails e ON e.id = c.source_id
                LEFT JOIN embeddings emb ON emb.content_id = c.id
                WHERE c.source_type = 'email' 
                  AND c.ready_for_embedding = 1 
                  AND emb.id IS NULL
                LIMIT ?
            """, (limit,)).fetchall()
            
            result.missing_vectors = len(ready_content)
            
            if ready_content:
                logger.info(f"Found {len(ready_content)} emails ready for vector rebuild")
                # Note: Actual embedding generation would be handled by embedding service
                # This just identifies what needs to be processed
            
        except Exception as e:
            error_msg = f"Force rebuild failed: {e}"
            logger.error(error_msg)
            result.errors.append(error_msg)
        
        return result