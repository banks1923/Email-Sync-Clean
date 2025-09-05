#!/usr/bin/env python3
"""
Generate embeddings for content marked ready_for_embedding.
Fail-fast with loud errors. Supports cloud and local embeddings.
"""

import os
import sys
import time
from pathlib import Path
from typing import List, Dict, Any

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from loguru import logger
from lib.db import SimpleDB
from lib.vector_store import get_vector_store
from lib.exceptions import ValidationError, VectorStoreError, EnrichmentError


def get_embedding_service_with_failfast():
    """Get embedding service with fail-fast validation."""
    
    use_cloud = os.getenv("USE_CLOUD_EMBEDDINGS", "").lower() in ("1", "true", "yes")
    
    if use_cloud:
        logger.info("Using CLOUD embeddings")
        from lib.cloud_embeddings import CloudEmbeddingService
        
        # FAIL FAST: Check token
        if not os.getenv("HF_TOKEN") and not os.getenv("HUGGINGFACE_API_TOKEN"):
            raise ValidationError(
                "CLOUD EMBEDDINGS ENABLED BUT NO TOKEN! "
                "Set HF_TOKEN or HUGGINGFACE_API_TOKEN environment variable"
            )
        
        service = CloudEmbeddingService()
        
        # FAIL FAST: Test embedding
        try:
            test_vec = service.encode("test")
            if len(test_vec) != 1024:
                raise ValidationError(
                    f"Cloud embedding dimension mismatch! "
                    f"Expected 1024, got {len(test_vec)}"
                )
        except Exception as e:
            raise ValidationError(f"Cloud embedding test failed: {e}")
            
    else:
        logger.info("Using LOCAL embeddings")
        from lib.embeddings import get_embedding_service
        
        service = get_embedding_service(use_mock=False)
        
        # FAIL FAST: Ensure not mock
        if not hasattr(service, 'model') or service.model is None:
            raise ValidationError(
                "LOCAL EMBEDDING SERVICE NOT LOADED! "
                "Check sentence-transformers installation"
            )
        
        # FAIL FAST: Test dimension
        test_vec = service.encode("test")
        if len(test_vec) != 1024:
            raise ValidationError(
                f"Local embedding dimension mismatch! "
                f"Expected 1024, got {len(test_vec)}"
            )
    
    logger.success(f"Embedding service validated: {type(service).__name__}")
    return service


def preprocess_text(text: str, source_type: str) -> str:
    """Minimal preprocessing for better embeddings."""
    import ftfy
    
    # ALWAYS: Fix encoding issues
    text = ftfy.fix_text(text)
    
    # ALWAYS: Normalize whitespace
    text = ' '.join(text.split())
    
    # Type-specific light cleaning
    if source_type == "email_message" and text.startswith("From:"):
        # Remove email headers
        lines = text.split('\n')
        for i, line in enumerate(lines):
            if not line.startswith(('From:', 'To:', 'Date:', 'Subject:', 'Cc:', 'Bcc:')):
                text = '\n'.join(lines[i:])
                break
    
    # FAIL FAST: Ensure we have content
    if len(text.strip()) < 10:
        raise ValidationError(f"Text too short after preprocessing: '{text[:50]}'")
    
    return text


def generate_embeddings(
    limit: int = None,
    batch_size: int = 10,
    force: bool = False
) -> Dict[str, Any]:
    """
    Generate embeddings for pending content.
    
    Args:
        limit: Max items to process (None = all)
        batch_size: Items per batch
        force: Re-generate even if already done
        
    Returns:
        Statistics dict
    """
    
    logger.info("=" * 60)
    logger.info("EMBEDDING GENERATION PIPELINE")
    logger.info("=" * 60)
    
    # Initialize services with fail-fast
    try:
        embedding_service = get_embedding_service_with_failfast()
        vector_store = get_vector_store('vectors_v2')
        db = SimpleDB()
    except Exception as e:
        logger.error(f"INITIALIZATION FAILED: {e}")
        raise
    
    # Get pending content
    where_clause = "ready_for_embedding=1"
    if not force:
        where_clause += " AND embedding_generated=0"
    
    query = f"""
        SELECT id, source_id, source_type, title, body, substantive_text, metadata
        FROM content_unified 
        WHERE {where_clause}
        ORDER BY id
    """
    
    if limit:
        query += f" LIMIT {limit}"
    
    logger.info(f"Loading content to embed...")
    content = db.fetch_all(query)
    
    if not content:
        logger.warning("No content needs embedding")
        return {"processed": 0, "failed": 0, "skipped": 0}
    
    logger.info(f"Found {len(content)} items to process")
    
    # Process in batches
    processed = 0
    failed = 0
    skipped = 0
    start_time = time.time()
    
    for i in range(0, len(content), batch_size):
        batch = content[i:i + batch_size]
        batch_texts = []
        batch_items = []
        
        # Prepare batch
        for item in batch:
            # CRITICAL: Prefer substantive_text over body
            text = item['substantive_text'] or item['body']
            
            if not text:
                logger.warning(f"Item {item['id']} has no text - skipping")
                skipped += 1
                continue
            
            try:
                # Preprocess with validation
                text = preprocess_text(text, item['source_type'])
                batch_texts.append(text)
                batch_items.append(item)
            except ValidationError as e:
                logger.error(f"Item {item['id']} preprocessing failed: {e}")
                failed += 1
                continue
        
        if not batch_texts:
            continue
        
        # Generate embeddings
        try:
            logger.info(f"Generating {len(batch_texts)} embeddings...")
            
            if len(batch_texts) == 1:
                # Single item
                vectors = [embedding_service.encode(batch_texts[0])]
            else:
                # Batch
                vectors = embedding_service.encode(batch_texts)
                if not isinstance(vectors[0], list):
                    vectors = [vectors]  # Ensure list of lists
            
            # Store vectors
            for item, vector in zip(batch_items, vectors):
                # CRITICAL: Use database ID as vector ID for consistency
                point_id = item['id']
                
                # Build metadata
                metadata = {
                    'content_id': item['id'],
                    'source_id': item['source_id'],
                    'source_type': item['source_type'],
                    'title': item.get('title', 'No title'),
                }
                
                # Add optional fields from metadata JSON if present
                if item.get('metadata'):
                    try:
                        import json
                        meta_dict = json.loads(item['metadata']) if isinstance(item['metadata'], str) else item['metadata']
                        if meta_dict.get('sender'):
                            metadata['sender'] = meta_dict['sender']
                        if meta_dict.get('datetime_utc'):
                            metadata['datetime_utc'] = meta_dict['datetime_utc']
                    except:
                        pass  # Ignore metadata parse errors
                
                # Store in Qdrant
                try:
                    vector_store.add_vector(
                        vector=vector,
                        metadata=metadata,
                        point_id=point_id
                    )
                    
                    # Update database
                    db.execute("""
                        UPDATE content_unified 
                        SET embedding_generated=1,
                            embedding_generated_at=CURRENT_TIMESTAMP
                        WHERE id=?
                    """, (item['id'],))
                    
                    processed += 1
                    
                except Exception as e:
                    logger.error(f"Failed to store vector for {item['id']}: {e}")
                    failed += 1
                    
        except Exception as e:
            logger.error(f"Batch embedding generation failed: {e}")
            failed += len(batch_items)
            continue
        
        # Progress report
        if processed % 50 == 0:
            elapsed = time.time() - start_time
            rate = processed / elapsed if elapsed > 0 else 0
            logger.info(f"Progress: {processed}/{len(content)} ({rate:.1f}/sec)")
    
    # Final report
    elapsed = time.time() - start_time
    
    logger.info("=" * 60)
    logger.success("EMBEDDING GENERATION COMPLETE")
    logger.info(f"  Processed: {processed}")
    logger.info(f"  Failed: {failed}")
    logger.info(f"  Skipped: {skipped}")
    logger.info(f"  Time: {elapsed:.1f}s")
    logger.info(f"  Rate: {processed/elapsed:.1f} items/sec" if elapsed > 0 else "")
    logger.info("=" * 60)
    
    return {
        "processed": processed,
        "failed": failed,
        "skipped": skipped,
        "elapsed": elapsed
    }


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Generate embeddings for content")
    parser.add_argument("--limit", type=int, help="Max items to process")
    parser.add_argument("--batch-size", type=int, default=10, help="Batch size")
    parser.add_argument("--force", action="store_true", help="Re-generate existing")
    parser.add_argument("--cloud", action="store_true", help="Use cloud embeddings")
    
    args = parser.parse_args()
    
    if args.cloud:
        os.environ["USE_CLOUD_EMBEDDINGS"] = "1"
    
    try:
        stats = generate_embeddings(
            limit=args.limit,
            batch_size=args.batch_size,
            force=args.force
        )
        
        # Exit code based on failures
        if stats["failed"] > 0:
            logger.warning(f"Exiting with code 1 due to {stats['failed']} failures")
            sys.exit(1)
        else:
            sys.exit(0)
            
    except Exception as e:
        logger.critical(f"FATAL ERROR: {e}")
        sys.exit(2)