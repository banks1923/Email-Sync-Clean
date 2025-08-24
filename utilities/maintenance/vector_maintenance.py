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

import argparse
import sys
from typing import Any, List
from collections.abc import Generator

from loguru import logger

from gmail.main import GmailService
from shared.simple_db import SimpleDB
from utilities.embeddings import get_embedding_service
from utilities.vector_store import get_vector_store

# --- Tunables (guidelines, not hard limits) ---
BATCH_SIZE = 500
EMBED_BATCH_SIZE = 16
ID_PAGE_SIZE = 1000

def _chunked(seq: list[Any], size: int) -> Generator[list[Any], None, None]:
    for i in range(0, len(seq), size):
        yield seq[i:i + size]


class VectorMaintenance:
    """Unified vector store maintenance operations."""
    
    def __init__(self) -> None:
        # Direct SimpleDB usage (VectorMaintenanceAdapter removed 2025-08-20)
        self.db = SimpleDB()
        self.embedding_service = get_embedding_service()
        self.vector_store = get_vector_store()
        self.gmail_service = GmailService()
        
    # --- Direct SimpleDB methods (replaced adapter) --------------------------
    def get_all_content_ids(self, content_type: str | None = None) -> list[str]:
        """Get all content IDs, optionally filtered by type."""
        try:
            if content_type:
                # Map collection names to content types
                type_mapping = {
                    'emails': 'email',
                    'pdfs': 'pdf', 
                    'transcriptions': 'transcription',
                    'notes': 'note',
                    'documents': 'document'
                }
                db_type = type_mapping.get(content_type, content_type)
                
                query = "SELECT id FROM content_unified WHERE content_type = ?"
                result = self.db.execute(query, (db_type,))
            else:
                query = "SELECT id FROM content_unified"
                result = self.db.execute(query)
            
            return [row['id'] for row in result.fetchall()]
        except Exception as e:
            logger.error(f"Failed to get content IDs for type {content_type}: {e}")
            return []

    def get_emails_without_vectors(self) -> list[dict]:
        """Get emails that don't have vectors yet."""
        try:
            query = """
                SELECT id, message_id, subject, content 
                FROM content_unified 
                WHERE content_type = 'email' 
                AND id NOT IN (
                    SELECT DISTINCT content_id 
                    FROM embeddings 
                    WHERE content_id IS NOT NULL
                )
            """
            result = self.db.execute(query)
            return [dict(row) for row in result.fetchall()]
        except Exception as e:
            logger.error(f"Failed to get emails without vectors: {e}")
            return []

    # --- Compatibility helpers -------------------------------------------------
    def _db_get_all_content_ids(self, content_type: str) -> list[str]:
        """Get content IDs with fallback compatibility."""
        # Use our new direct method first
        try:
            return self.get_all_content_ids(content_type)
        except Exception as e:
            logger.error(f"Direct content ID lookup failed: {e}")
            return []
    
    def _db_get_emails_without_vectors(self) -> list[dict[str, Any]]:
        """Get emails without vectors with fallback compatibility."""
        # Use our new direct method first
        try:
            return self.get_emails_without_vectors()
        except Exception as e:
            logger.error(f"DB compat: get_emails_without_vectors() not found: {e}")
            return []

    def _db_get_content_by_id(self, content_id: str) -> dict[str, Any] | None:
        candidates = ("get_content_by_id", "get_email_by_id", "get_document_by_id")
        for name in candidates:
            fn = getattr(self.db, name, None)
            if fn:
                try:
                    return fn(content_id)
                except Exception:
                    continue
        logger.warning(f"DB compat: no getter found for content_id={content_id}")
        return None

    def _db_mark_emails_vectorized(self, ids: list[str]) -> None:
        # Prefer bulk if available
        bulk = getattr(self.db, "mark_emails_vectorized", None)
        if bulk:
            try:
                return bulk(ids=ids)
            except TypeError:
                try:
                    return bulk(ids)
                except Exception:
                    pass
        single = getattr(self.db, "mark_email_vectorized", None)
        if single:
            for _id in ids:
                try:
                    single(_id)
                except Exception as e:
                    logger.error(f"DB compat: failed to mark vectorized for {_id}: {e}")

    def _vs_iter_ids(self, collection: str) -> Generator[str, None, None]:
        # Prefer paginated iteration if supported
        it = getattr(self.vector_store, "iter_ids", None)
        if it:
            try:
                for page in it(collection=collection, page_size=ID_PAGE_SIZE):
                    yield from page
                return
            except TypeError:
                # Older signature without keywords
                for page in it(collection, ID_PAGE_SIZE):
                    yield from page
                return
            except Exception:
                pass
        # Fallback: list_all_ids
        lst = getattr(self.vector_store, "list_all_ids", None)
        if lst:
            try:
                yield from lst(collection=collection)
                return
            except TypeError:
                yield from lst(collection)
                return
        logger.warning("VectorStore compat: no iter/list ids available; treating as empty")
        return

    def sync_emails_to_vectors(self, limit: int | None = None) -> dict[str, Any]:
        """Sync email content to vector store (batched with API-compat fallbacks)."""
        logger.info("Starting email to vector sync (batched)")

        get_missing = getattr(self.db, "get_emails_without_vectors", None)
        if not get_missing:
            logger.error("DB compat: get_emails_without_vectors() not found")
            return {"synced": 0, "errors": ["missing API: get_emails_without_vectors"], "status": "error"}

        emails = get_missing(limit=limit)
        total = len(emails) if emails else 0
        if not emails:
            logger.info("No emails need vector sync")
            return {"synced": 0, "status": "no emails to sync"}

        synced_count = 0
        errors = []
        batch_idx = 0

        for batch in _chunked(emails, BATCH_SIZE):
            batch_idx += 1
            logger.info(f"Processing batch {batch_idx} ({synced_count}/{total} done)")
            ids = [e['id'] for e in batch]
            texts = [e.get('body') or '' for e in batch]
            metas = [
                {
                    'subject': e.get('subject'),
                    'from': e.get('sender'),
                    'date': e.get('date')
                } for e in batch
            ]

            # Embeddings (batch preferred)
            try:
                if hasattr(self.embedding_service, 'batch_encode'):
                    embeddings = self.embedding_service.batch_encode(texts, batch_size=EMBED_BATCH_SIZE)
                else:
                    get_emb = getattr(self.embedding_service, 'get_embedding', None) or getattr(self.embedding_service, 'encode')
                    embeddings = [get_emb(t) for t in texts]
            except Exception as e:
                logger.error(f"Batch embedding failed: {e}")
                embeddings = []
                get_emb = getattr(self.embedding_service, 'get_embedding', None) or getattr(self.embedding_service, 'encode')
                for i, t in enumerate(texts):
                    try:
                        embeddings.append(get_emb(t))
                    except Exception as ie:
                        embeddings.append(None)
                        errors.append({"email_id": ids[i], "error": str(ie)})

            # Upsert to vector store (batch preferred)
            valid_points = []
            for i, emb in enumerate(embeddings):
                if emb is None:
                    continue
                valid_points.append({
                    'id': ids[i],
                    'vector': emb,
                    'metadata': metas[i],
                    'collection': 'emails'
                })

            if not valid_points:
                continue

            try:
                if hasattr(self.vector_store, 'batch_upsert'):
                    self.vector_store.batch_upsert(collection='emails', points=valid_points)
                else:
                    add_email = getattr(self.vector_store, 'add_email_vector', None)
                    add_vec = getattr(self.vector_store, 'add_vector', None)
                    for pt in valid_points:
                        if add_email:
                            add_email(email_id=pt['id'], embedding=pt['vector'], metadata=pt['metadata'])
                        elif add_vec:
                            add_vec(id=pt['id'], embedding=pt['vector'], metadata=pt['metadata'], collection='emails')
                        else:
                            raise RuntimeError("VectorStore compat: no add_* method available")

                # Mark vectorized in DB (bulk if possible)
                self._db_mark_emails_vectorized([pt['id'] for pt in valid_points])

                synced_count += len(valid_points)

            except Exception as e:
                logger.error(f"Failed batch upsert: {e}")
                for pt in valid_points:
                    try:
                        add_email = getattr(self.vector_store, 'add_email_vector', None)
                        add_vec = getattr(self.vector_store, 'add_vector', None)
                        if add_email:
                            add_email(email_id=pt['id'], embedding=pt['vector'], metadata=pt['metadata'])
                        elif add_vec:
                            add_vec(id=pt['id'], embedding=pt['vector'], metadata=pt['metadata'], collection='emails')
                        else:
                            raise RuntimeError("VectorStore compat: no add_* method available")
                        self._db_mark_emails_vectorized([pt['id']])
                        synced_count += 1
                    except Exception as ie:
                        errors.append({"email_id": pt['id'], "error": str(ie)})

        logger.info(f"Synced {synced_count} / {total} emails to vector store")
        return {
            "synced": synced_count,
            "errors": errors,
            "batches": batch_idx,
            "status": "completed"
        }
    
    def sync_missing_vectors(self, collection: str = "emails") -> dict[str, Any]:
        """Find and sync content missing from vector store."""
        logger.info(f"Checking for missing vectors in {collection}")

        db_ids = self._db_get_all_content_ids(content_type=collection)

        vector_ids_seen = set()
        for vid in self._vs_iter_ids(collection):
            vector_ids_seen.add(vid)

        missing = db_ids - vector_ids_seen

        if not missing:
            logger.info("No missing vectors found")
            return {"missing": 0, "status": "all synced"}

        logger.info(f"Found {len(missing)} missing vectors; syncing in batches of {BATCH_SIZE}")

        synced = 0
        errors = []
        missing_list = list(missing)

        for batch in _chunked(missing_list, BATCH_SIZE):
            contents, ids, texts, metadatas = [], [], [], []
            for cid in batch:
                c = self._db_get_content_by_id(cid)
                if not c:
                    continue
                contents.append(c)
                ids.append(c.get('id', cid))
                texts.append(c.get('text') or '')
                metadatas.append(c.get('metadata', {}))

            if not ids:
                continue

            try:
                if hasattr(self.embedding_service, 'batch_encode'):
                    embeddings = self.embedding_service.batch_encode(texts, batch_size=EMBED_BATCH_SIZE)
                else:
                    get_emb = getattr(self.embedding_service, 'get_embedding', None) or getattr(self.embedding_service, 'encode')
                    embeddings = [get_emb(t) for t in texts]
            except Exception as e:
                logger.error(f"Batch embedding failed: {e}")
                embeddings = []
                get_emb = getattr(self.embedding_service, 'get_embedding', None) or getattr(self.embedding_service, 'encode')
                for t in texts:
                    try:
                        embeddings.append(get_emb(t))
                    except Exception:
                        embeddings.append(None)

            points = []
            for i, emb in enumerate(embeddings):
                if emb is None:
                    errors.append({"id": ids[i], "error": "embedding failed"})
                    continue
                points.append({'id': ids[i], 'vector': emb, 'metadata': metadatas[i], 'collection': collection})

            try:
                if hasattr(self.vector_store, 'batch_upsert'):
                    self.vector_store.batch_upsert(collection=collection, points=points)
                else:
                    add_vec = getattr(self.vector_store, 'add_vector', None)
                    for pt in points:
                        if add_vec:
                            add_vec(id=pt['id'], embedding=pt['vector'], metadata=pt['metadata'], collection=collection)
                        else:
                            raise RuntimeError("VectorStore compat: add_vector missing")
                synced += len(points)
            except Exception as e:
                logger.error(f"Vector upsert failed: {e}")
                add_vec = getattr(self.vector_store, 'add_vector', None)
                for pt in points:
                    try:
                        if add_vec:
                            add_vec(id=pt['id'], embedding=pt['vector'], metadata=pt['metadata'], collection=collection)
                            synced += 1
                        else:
                            errors.append({"id": pt['id'], "error": "add_vector missing"})
                    except Exception as ie:
                        errors.append({"id": pt['id'], "error": str(ie)})

        return {
            "missing_found": len(missing_list),
            "synced": synced,
            "errors": errors,
            "status": "completed"
        }
    
    def reconcile_vectors(self, fix: bool = False) -> dict[str, Any]:
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
            vector_ids = set(self._vs_iter_ids(collection))
            
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
    
    def verify_sync(self) -> dict[str, Any]:
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
    
    def purge_test_vectors(self, dry_run: bool = True) -> dict[str, Any]:
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
            for vector_id in self._vs_iter_ids(collection):
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
    
    def renormalize_vectors(self, collection: str = None, dry_run: bool = True) -> dict[str, Any]:
        """Re-normalize existing vectors to unit length (L2 norm = 1.0)."""
        import numpy as np
        
        logger.info(f"Re-normalizing vectors (collection={collection}, dry_run={dry_run})")
        
        collections = [collection] if collection else ["emails", "pdfs", "transcriptions", "notes"]
        normalized_count = 0
        already_normalized = 0
        errors = []
        
        for coll in collections:
            try:
                # Get all vectors from collection
                vectors = self.vector_store.client.scroll(
                    collection_name=coll,
                    limit=100,
                    with_vectors=True
                )
                
                for batch in vectors:
                    for point in batch:
                        vector = np.array(point.vector)
                        norm = np.linalg.norm(vector)
                        
                        # Check if already normalized (close to 1.0)
                        if abs(norm - 1.0) < 0.01:
                            already_normalized += 1
                            continue
                        
                        # Normalize the vector
                        if norm > 0:
                            normalized_vector = vector / norm
                            
                            if not dry_run:
                                # Update the vector in Qdrant
                                self.vector_store.client.update_vectors(
                                    collection_name=coll,
                                    points=[{
                                        "id": point.id,
                                        "vector": normalized_vector.tolist()
                                    }]
                                )
                            
                            normalized_count += 1
                            
                            if normalized_count % 100 == 0:
                                logger.info(f"Normalized {normalized_count} vectors...")
                                
            except Exception as e:
                logger.error(f"Error processing collection {coll}: {e}")
                errors.append({"collection": coll, "error": str(e)})
        
        return {
            "normalized_count": normalized_count,
            "already_normalized": already_normalized,
            "errors": errors,
            "dry_run": dry_run,
            "status": "completed" if not errors else "completed_with_errors"
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
    
    # Renormalize command
    renorm = subparsers.add_parser('renormalize', help='Re-normalize vectors to unit length')
    renorm.add_argument('--collection', help='Specific collection to renormalize')
    renorm.add_argument('--execute', action='store_true', help='Actually update (not dry run)')
    
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
    elif args.command == 'renormalize':
        result = maintenance.renormalize_vectors(
            collection=args.collection,
            dry_run=not args.execute
        )
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