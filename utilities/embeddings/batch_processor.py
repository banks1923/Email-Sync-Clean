#!/usr/bin/env python3
"""
Batch Embedding Processor - Generates and stores embeddings for chunks.

Fetches chunks ready for embedding, generates Legal BERT embeddings in batches,
and stores them in Qdrant vectors_v2 collection.

Simple, direct implementation following CLAUDE.md principles.
"""

import hashlib
import time
from typing import Any, Dict, List, Optional
from datetime import datetime

from loguru import logger
import numpy as np

from shared.simple_db import SimpleDB
from utilities.embeddings import get_embedding_service
from utilities.vector_store import get_vector_store


class BatchEmbeddingProcessor:
    """Processes chunks through embedding generation and vector storage."""
    
    def __init__(
        self,
        db: Optional[SimpleDB] = None,
        embedding_service=None,
        vector_store=None,
        batch_size: int = 64,
        min_quality: float = 0.35
    ):
        """Initialize processor with services.
        
        Args:
            db: Database connection
            embedding_service: Embedding service (Legal BERT)
            vector_store: Vector store (Qdrant)
            batch_size: Number of chunks per batch (default: 64)
            min_quality: Minimum quality score for chunks (default: 0.35)
        """
        self.db = db or SimpleDB()
        self.embedding_service = embedding_service or get_embedding_service()
        self.batch_size = batch_size
        self.min_quality = min_quality
        
        # Use vectors_v2 collection for v2 chunks
        self.vector_store = vector_store or get_vector_store("vectors_v2")
        
    def process_chunks(
        self,
        limit: Optional[int] = None,
        dry_run: bool = False
    ) -> Dict[str, Any]:
        """Process chunks ready for embedding.
        
        Args:
            limit: Maximum chunks to process
            dry_run: If True, preview without storing
            
        Returns:
            Processing metrics
        """
        start_time = time.time()
        
        metrics = {
            "started_at": datetime.now().isoformat(),
            "chunks_processed": 0,
            "embeddings_generated": 0,
            "vectors_stored": 0,
            "chunks_skipped": 0,
            "errors": [],
            "dry_run": dry_run,
            "batch_size": self.batch_size
        }
        
        logger.info(f"Starting batch embedding processor (dry_run={dry_run})")
        logger.info(f"Batch size: {self.batch_size}, Min quality: {self.min_quality}")
        
        # Process in batches
        total_processed = 0
        while True:
            # Fetch next batch of chunks
            batch_limit = min(self.batch_size, limit - total_processed) if limit else self.batch_size
            chunks = self.db.get_chunks_for_embedding(
                min_quality=self.min_quality,
                limit=batch_limit
            )
            
            if not chunks:
                logger.info("No more chunks to process")
                break
            
            logger.info(f"Processing batch of {len(chunks)} chunks")
            
            # Process batch
            batch_result = self._process_batch(chunks, dry_run)
            
            # Update metrics
            metrics["chunks_processed"] += batch_result["processed"]
            metrics["embeddings_generated"] += batch_result["embeddings_generated"]
            metrics["vectors_stored"] += batch_result["vectors_stored"]
            metrics["chunks_skipped"] += batch_result["skipped"]
            metrics["errors"].extend(batch_result.get("errors", []))
            
            total_processed += len(chunks)
            
            # Log progress
            logger.info(
                f"Batch complete: {batch_result['embeddings_generated']} embeddings, "
                f"Total: {metrics['embeddings_generated']}/{metrics['chunks_processed']}"
            )
            
            # Check limit
            if limit and total_processed >= limit:
                logger.info(f"Reached limit of {limit} chunks")
                break
            
            # Small delay between batches to avoid overwhelming the system
            if not dry_run and len(chunks) == self.batch_size:
                time.sleep(0.1)
        
        # Calculate summary
        elapsed = time.time() - start_time
        metrics["elapsed_seconds"] = elapsed
        metrics["completed_at"] = datetime.now().isoformat()
        
        if metrics["chunks_processed"] > 0:
            metrics["embeddings_per_second"] = metrics["embeddings_generated"] / elapsed
        
        # Log summary
        logger.info(f"Batch embedding completed in {elapsed:.1f}s")
        logger.info(
            f"Processed {metrics['chunks_processed']} chunks → "
            f"{metrics['embeddings_generated']} embeddings → "
            f"{metrics['vectors_stored']} vectors stored"
        )
        
        return metrics
    
    def _process_batch(
        self,
        chunks: List[Dict[str, Any]],
        dry_run: bool = False
    ) -> Dict[str, Any]:
        """Process a single batch of chunks.
        
        Args:
            chunks: List of chunk records
            dry_run: If True, don't store results
            
        Returns:
            Batch processing metrics
        """
        batch_result = {
            "processed": len(chunks),
            "embeddings_generated": 0,
            "vectors_stored": 0,
            "skipped": 0,
            "errors": []
        }
        
        # Extract texts for embedding
        texts = []
        valid_chunks = []
        
        for chunk in chunks:
            # Check if already embedded (shouldn't happen with get_chunks_for_embedding)
            if chunk.get("embedding_generated"):
                batch_result["skipped"] += 1
                continue
            
            texts.append(chunk["body"])
            valid_chunks.append(chunk)
        
        if not texts:
            logger.debug("No valid texts in batch")
            return batch_result
        
        # Generate embeddings in batch
        try:
            logger.debug(f"Generating embeddings for {len(texts)} chunks")
            embeddings = self.embedding_service.batch_encode(texts, batch_size=16)
            batch_result["embeddings_generated"] = len(embeddings)
            
        except Exception as e:
            error_msg = f"Failed to generate embeddings: {e}"
            logger.error(error_msg)
            batch_result["errors"].append(error_msg)
            return batch_result
        
        # Store embeddings (unless dry run)
        if not dry_run:
            vectors_to_store = []
            chunk_ids_to_mark = []
            
            for chunk, embedding in zip(valid_chunks, embeddings):
                # Generate a numeric ID from the chunk's source_id hash
                # Use the database row ID if available, otherwise hash the source_id
                if "id" in chunk and chunk["id"]:
                    vector_id = int(chunk["id"])  # Use database row ID as integer
                else:
                    # Generate stable numeric ID from source_id hash
                    hash_bytes = hashlib.sha256(chunk["source_id"].encode()).digest()
                    vector_id = int.from_bytes(hash_bytes[:8], 'big') % (2**53)  # Safe JavaScript integer
                
                # Prepare vector metadata
                metadata = {
                    "chunk_id": chunk["source_id"],  # Format: "doc_id:chunk_idx"
                    "doc_id": chunk["source_id"].split(":")[0],
                    "chunk_idx": int(chunk["source_id"].split(":")[-1]),
                    "quality_score": chunk.get("quality_score", 1.0),
                    "source_type": "document_chunk",
                    "timestamp": datetime.now().isoformat()
                }
                
                # Add to batch
                vectors_to_store.append({
                    "id": vector_id,  # Use numeric ID for Qdrant
                    "vector": embedding.tolist(),
                    "metadata": metadata
                })
                
                chunk_ids_to_mark.append(chunk["source_id"])
            
            # Batch store vectors
            if vectors_to_store:
                try:
                    stored_ids = self.vector_store.batch_upsert(
                        collection="vectors_v2",
                        points=vectors_to_store
                    )
                    batch_result["vectors_stored"] = len(stored_ids)
                    
                    # Mark chunks as embedded
                    for chunk_id in chunk_ids_to_mark:
                        try:
                            self.db.mark_chunk_embedded(chunk_id)
                        except Exception as e:
                            logger.warning(f"Failed to mark chunk {chunk_id} as embedded: {e}")
                    
                    logger.debug(f"Stored {len(stored_ids)} vectors in Qdrant")
                    
                except Exception as e:
                    error_msg = f"Failed to store vectors: {e}"
                    logger.error(error_msg)
                    batch_result["errors"].append(error_msg)
        
        return batch_result
    
    def get_processor_stats(self) -> Dict[str, Any]:
        """Get current processor statistics.
        
        Returns:
            Statistics about chunks and embeddings
        """
        stats = {}
        
        # Get chunks ready for embedding
        ready_chunks = self.db.fetch(
            """
            SELECT COUNT(*) as count
            FROM content_unified
            WHERE source_type = 'document_chunk'
            AND ready_for_embedding = 1
            AND embedding_generated = 0
            AND quality_score >= ?
            """,
            [self.min_quality]
        )
        stats["chunks_ready"] = ready_chunks[0]["count"] if ready_chunks else 0
        
        # Get already embedded chunks
        embedded_chunks = self.db.fetch(
            """
            SELECT COUNT(*) as count
            FROM content_unified
            WHERE source_type = 'document_chunk'
            AND embedding_generated = 1
            """,
            []
        )
        stats["chunks_embedded"] = embedded_chunks[0]["count"] if embedded_chunks else 0
        
        # Get vector count from Qdrant
        try:
            vector_stats = self.vector_store.get_collection_stats("vectors_v2")
            stats["vectors_in_qdrant"] = vector_stats.get("points_count", 0)
        except Exception as e:
            logger.warning(f"Could not get Qdrant stats: {e}")
            stats["vectors_in_qdrant"] = "unknown"
        
        # Calculate remaining work
        stats["chunks_remaining"] = stats["chunks_ready"]
        
        if stats["chunks_ready"] > 0:
            # Estimate time remaining (assuming ~50 chunks/second)
            stats["estimated_minutes"] = round(stats["chunks_ready"] / (50 * 60), 1)
        
        return stats


def main():
    """CLI entry point for testing."""
    import argparse
    import json
    
    parser = argparse.ArgumentParser(description="Batch Embedding Processor")
    parser.add_argument("--limit", type=int, help="Maximum chunks to process")
    parser.add_argument("--batch-size", type=int, default=64,
                       help="Chunks per batch (default: 64)")
    parser.add_argument("--min-quality", type=float, default=0.35,
                       help="Minimum quality score (default: 0.35)")
    parser.add_argument("--dry-run", action="store_true", help="Preview without storing")
    parser.add_argument("--stats", action="store_true", help="Show processor statistics")
    parser.add_argument("--json", action="store_true", help="Output as JSON")
    
    args = parser.parse_args()
    
    processor = BatchEmbeddingProcessor(
        batch_size=args.batch_size,
        min_quality=args.min_quality
    )
    
    if args.stats:
        stats = processor.get_processor_stats()
        
        if args.json:
            print(json.dumps(stats, indent=2))
        else:
            print("\n📊 Embedding Processor Statistics")
            print("=" * 40)
            for key, value in stats.items():
                print(f"{key}: {value}")
    else:
        result = processor.process_chunks(
            limit=args.limit,
            dry_run=args.dry_run
        )
        
        if args.json:
            print(json.dumps(result, indent=2, default=str))
        else:
            print("\n✅ Embedding Processing Results")
            print("=" * 40)
            print(f"Chunks processed: {result['chunks_processed']}")
            print(f"Embeddings generated: {result['embeddings_generated']}")
            print(f"Vectors stored: {result['vectors_stored']}")
            print(f"Chunks skipped: {result['chunks_skipped']}")
            print(f"Elapsed time: {result['elapsed_seconds']:.1f}s")
            
            if result.get("embeddings_per_second"):
                print(f"Rate: {result['embeddings_per_second']:.1f} embeddings/sec")
            
            if result["errors"]:
                print(f"\n❌ Errors ({len(result['errors'])})")
                for error in result["errors"][:5]:
                    print(f"  - {error}")


if __name__ == "__main__":
    main()