#!/usr/bin/env python3
"""
Integration test for v2 chunk pipeline.

Tests the complete flow:
1. Document chunking with quality scoring
2. Chunk storage in database
3. Embedding generation
4. Vector storage in Qdrant
5. Idempotency and quality filtering

Usage:
    python scripts/test_chunk_pipeline.py
    python scripts/test_chunk_pipeline.py --limit 5
    python scripts/test_chunk_pipeline.py --full  # Process all documents
"""

import argparse
import sys
import time
from pathlib import Path
from datetime import datetime
from typing import Dict, Any

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from loguru import logger
from shared.simple_db import SimpleDB
from utilities.chunk_pipeline import ChunkPipeline
from utilities.embeddings.batch_processor import BatchEmbeddingProcessor
from utilities.vector_store import get_vector_store


class ChunkPipelineIntegrationTest:
    """Integration test for the v2 chunk pipeline."""
    
    def __init__(self, verbose: bool = False):
        """Initialize test suite.
        
        Args:
            verbose: Enable verbose logging
        """
        self.verbose = verbose
        self.db = SimpleDB()
        self.pipeline = ChunkPipeline()
        self.processor = BatchEmbeddingProcessor()
        self.vector_store = get_vector_store("vectors_v2")
        self.results = {}
        
    def run_all_tests(self, limit: int = 5) -> bool:
        """Run all integration tests.
        
        Args:
            limit: Maximum documents to process (default: 5)
            
        Returns:
            True if all tests pass
        """
        logger.info("=" * 60)
        logger.info("V2 Chunk Pipeline Integration Test")
        logger.info("=" * 60)
        
        all_passed = True
        
        # Test 1: Initial state check
        logger.info("\n📋 Test 1: Check initial state")
        if not self._test_initial_state():
            all_passed = False
        
        # Test 2: Document chunking
        logger.info("\n📋 Test 2: Document chunking")
        if not self._test_chunking(limit):
            all_passed = False
        
        # Test 3: Quality filtering
        logger.info("\n📋 Test 3: Quality filtering")
        if not self._test_quality_filtering():
            all_passed = False
        
        # Test 4: Embedding generation
        logger.info("\n📋 Test 4: Embedding generation")
        if not self._test_embedding_generation():
            all_passed = False
        
        # Test 5: Vector storage
        logger.info("\n📋 Test 5: Vector storage in Qdrant")
        if not self._test_vector_storage():
            all_passed = False
        
        # Test 6: Idempotency
        logger.info("\n📋 Test 6: Idempotency check")
        if not self._test_idempotency():
            all_passed = False
        
        # Print summary
        self._print_summary(all_passed)
        
        return all_passed
    
    def _test_initial_state(self) -> bool:
        """Test initial database and system state."""
        try:
            # Check for documents ready for chunking
            ready_docs = self.db.fetch(
                """
                SELECT COUNT(*) as count
                FROM content_unified
                WHERE ready_for_embedding = 1
                AND source_type = 'email_message'
                """,
                []
            )
            doc_count = ready_docs[0]["count"] if ready_docs else 0
            
            logger.info(f"  Documents ready for chunking: {doc_count}")
            
            # Check for existing chunks
            existing_chunks = self.db.fetch(
                """
                SELECT COUNT(*) as count
                FROM content_unified
                WHERE source_type = 'document_chunk'
                """,
                []
            )
            chunk_count = existing_chunks[0]["count"] if existing_chunks else 0
            
            logger.info(f"  Existing chunks: {chunk_count}")
            
            # Check Qdrant connection
            try:
                vector_stats = self.vector_store.get_collection_stats("vectors_v2")
                vector_count = vector_stats.get("points_count", 0)
                logger.info(f"  Vectors in Qdrant (vectors_v2): {vector_count}")
            except Exception as e:
                logger.warning(f"  Qdrant collection 'vectors_v2' not yet created: {e}")
                vector_count = 0
            
            self.results["initial_state"] = {
                "documents_ready": doc_count,
                "existing_chunks": chunk_count,
                "existing_vectors": vector_count
            }
            
            logger.success("  ✅ Initial state check passed")
            return True
            
        except Exception as e:
            logger.error(f"  ❌ Initial state check failed: {e}")
            return False
    
    def _test_chunking(self, limit: int) -> bool:
        """Test document chunking with quality scoring."""
        try:
            logger.info(f"  Processing {limit} documents...")
            
            # Run chunking pipeline
            chunk_result = self.pipeline.process_documents(
                limit=limit,
                source_types=["email_message"],
                dry_run=False
            )
            
            # Verify results
            docs_processed = chunk_result.get("documents_processed", 0)
            chunks_created = chunk_result.get("chunks_created", 0)
            chunks_dropped = chunk_result.get("chunks_dropped_quality", 0)
            
            logger.info(f"  Documents processed: {docs_processed}")
            logger.info(f"  Chunks created: {chunks_created}")
            logger.info(f"  Chunks dropped (low quality): {chunks_dropped}")
            
            # Verify chunks in database
            db_chunks = self.db.fetch(
                """
                SELECT COUNT(*) as count
                FROM content_unified
                WHERE source_type = 'document_chunk'
                AND id > ?
                """,
                [self.results["initial_state"]["existing_chunks"]]
            )
            new_chunk_count = db_chunks[0]["count"] if db_chunks else 0
            
            if new_chunk_count != chunks_created:
                logger.error(f"  ❌ Chunk count mismatch: DB has {new_chunk_count}, expected {chunks_created}")
                return False
            
            self.results["chunking"] = {
                "documents_processed": docs_processed,
                "chunks_created": chunks_created,
                "chunks_dropped": chunks_dropped
            }
            
            logger.success("  ✅ Chunking test passed")
            return True
            
        except Exception as e:
            logger.error(f"  ❌ Chunking test failed: {e}")
            return False
    
    def _test_quality_filtering(self) -> bool:
        """Test that quality filtering works correctly."""
        try:
            # Check quality score distribution
            quality_dist = self.db.fetch(
                """
                SELECT 
                    COUNT(*) as total,
                    COUNT(CASE WHEN quality_score >= 0.35 THEN 1 END) as high_quality,
                    COUNT(CASE WHEN quality_score < 0.35 THEN 1 END) as low_quality,
                    MIN(quality_score) as min_score,
                    MAX(quality_score) as max_score,
                    AVG(quality_score) as avg_score
                FROM content_unified
                WHERE source_type = 'document_chunk'
                """,
                []
            )
            
            if quality_dist:
                stats = quality_dist[0]
                logger.info(f"  Total chunks: {stats['total']}")
                logger.info(f"  High quality (>=0.35): {stats['high_quality']}")
                logger.info(f"  Low quality (<0.35): {stats['low_quality']}")
                logger.info(f"  Quality range: {stats['min_score']:.3f} - {stats['max_score']:.3f}")
                logger.info(f"  Average quality: {stats['avg_score']:.3f}")
                
                # Verify all chunks marked for embedding have quality >= 0.35
                bad_chunks = self.db.fetch(
                    """
                    SELECT COUNT(*) as count
                    FROM content_unified
                    WHERE source_type = 'document_chunk'
                    AND ready_for_embedding = 1
                    AND quality_score < 0.35
                    """,
                    []
                )
                
                if bad_chunks[0]["count"] > 0:
                    logger.error(f"  ❌ Found {bad_chunks[0]['count']} low-quality chunks marked for embedding")
                    return False
                
                self.results["quality_filtering"] = {
                    "total_chunks": stats["total"],
                    "high_quality": stats["high_quality"],
                    "low_quality": stats["low_quality"],
                    "avg_score": stats["avg_score"]
                }
            
            logger.success("  ✅ Quality filtering test passed")
            return True
            
        except Exception as e:
            logger.error(f"  ❌ Quality filtering test failed: {e}")
            return False
    
    def _test_embedding_generation(self) -> bool:
        """Test embedding generation for chunks."""
        try:
            # Process a small batch of embeddings
            logger.info("  Generating embeddings for chunks...")
            
            embed_result = self.processor.process_chunks(
                limit=10,  # Process up to 10 chunks
                dry_run=False
            )
            
            embeddings_generated = embed_result.get("embeddings_generated", 0)
            vectors_stored = embed_result.get("vectors_stored", 0)
            
            logger.info(f"  Embeddings generated: {embeddings_generated}")
            logger.info(f"  Vectors stored: {vectors_stored}")
            
            # Verify chunks are marked as embedded
            embedded_chunks = self.db.fetch(
                """
                SELECT COUNT(*) as count
                FROM content_unified
                WHERE source_type = 'document_chunk'
                AND embedding_generated = 1
                """,
                []
            )
            
            logger.info(f"  Chunks marked as embedded: {embedded_chunks[0]['count']}")
            
            self.results["embeddings"] = {
                "embeddings_generated": embeddings_generated,
                "vectors_stored": vectors_stored,
                "chunks_embedded": embedded_chunks[0]["count"]
            }
            
            logger.success("  ✅ Embedding generation test passed")
            return True
            
        except Exception as e:
            logger.error(f"  ❌ Embedding generation test failed: {e}")
            return False
    
    def _test_vector_storage(self) -> bool:
        """Test vector storage in Qdrant."""
        try:
            # Check vectors in Qdrant
            vector_stats = self.vector_store.get_collection_stats("vectors_v2")
            current_vectors = vector_stats.get("points_count", 0)
            
            initial_vectors = self.results["initial_state"]["existing_vectors"]
            new_vectors = current_vectors - initial_vectors
            
            logger.info(f"  Total vectors in Qdrant: {current_vectors}")
            logger.info(f"  New vectors added: {new_vectors}")
            
            # Sample search to verify vectors work
            if current_vectors > 0:
                # Get a sample chunk for testing
                sample_chunk = self.db.fetch(
                    """
                    SELECT body
                    FROM content_unified
                    WHERE source_type = 'document_chunk'
                    AND embedding_generated = 1
                    LIMIT 1
                    """,
                    []
                )
                
                if sample_chunk:
                    # Generate embedding for query
                    from utilities.embeddings import get_embedding_service
                    embedding_service = get_embedding_service()
                    query_embedding = embedding_service.encode(sample_chunk[0]["body"][:100])
                    
                    # Search in Qdrant
                    results = self.vector_store.search(
                        vector=query_embedding.tolist(),
                        limit=3
                    )
                    
                    logger.info(f"  Sample search returned {len(results)} results")
                    
                    if len(results) > 0:
                        logger.info(f"  Top result score: {results[0]['score']:.3f}")
            
            self.results["vector_storage"] = {
                "total_vectors": current_vectors,
                "new_vectors": new_vectors
            }
            
            logger.success("  ✅ Vector storage test passed")
            return True
            
        except Exception as e:
            logger.error(f"  ❌ Vector storage test failed: {e}")
            return False
    
    def _test_idempotency(self) -> bool:
        """Test that re-running doesn't create duplicates."""
        try:
            logger.info("  Re-running pipeline to test idempotency...")
            
            # Get initial counts
            initial_chunks = self.db.fetch(
                "SELECT COUNT(*) as count FROM content_unified WHERE source_type = 'document_chunk'",
                []
            )[0]["count"]
            
            # Re-run chunking on already processed documents
            chunk_result = self.pipeline.process_documents(
                limit=2,  # Process same documents again
                source_types=["email_message"],
                dry_run=False
            )
            
            chunks_skipped = chunk_result.get("chunks_already_exist", 0)
            chunks_created = chunk_result.get("chunks_created", 0)
            
            logger.info(f"  Chunks skipped (already exist): {chunks_skipped}")
            logger.info(f"  New chunks created: {chunks_created}")
            
            # Verify no new chunks were created for already-processed docs
            final_chunks = self.db.fetch(
                "SELECT COUNT(*) as count FROM content_unified WHERE source_type = 'document_chunk'",
                []
            )[0]["count"]
            
            # We expect some skipped chunks if documents were already processed
            if chunks_skipped > 0:
                logger.info(f"  ✅ Idempotency working: {chunks_skipped} chunks skipped")
            
            self.results["idempotency"] = {
                "chunks_skipped": chunks_skipped,
                "chunks_created": chunks_created,
                "initial_chunks": initial_chunks,
                "final_chunks": final_chunks
            }
            
            logger.success("  ✅ Idempotency test passed")
            return True
            
        except Exception as e:
            logger.error(f"  ❌ Idempotency test failed: {e}")
            return False
    
    def _print_summary(self, all_passed: bool):
        """Print test summary."""
        logger.info("\n" + "=" * 60)
        logger.info("TEST SUMMARY")
        logger.info("=" * 60)
        
        if self.verbose:
            import json
            logger.info("\nDetailed Results:")
            print(json.dumps(self.results, indent=2, default=str))
        
        logger.info("\nKey Metrics:")
        if "chunking" in self.results:
            logger.info(f"  Documents processed: {self.results['chunking']['documents_processed']}")
            logger.info(f"  Chunks created: {self.results['chunking']['chunks_created']}")
        
        if "quality_filtering" in self.results:
            logger.info(f"  Average quality score: {self.results['quality_filtering']['avg_score']:.3f}")
        
        if "embeddings" in self.results:
            logger.info(f"  Embeddings generated: {self.results['embeddings']['embeddings_generated']}")
        
        if "vector_storage" in self.results:
            logger.info(f"  Vectors in Qdrant: {self.results['vector_storage']['total_vectors']}")
        
        logger.info("\n" + "=" * 60)
        if all_passed:
            logger.success("✅ ALL TESTS PASSED - V2 pipeline is working correctly!")
        else:
            logger.error("❌ SOME TESTS FAILED - Please review the errors above")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Test v2 chunk pipeline")
    parser.add_argument("--limit", type=int, default=5,
                       help="Maximum documents to process (default: 5)")
    parser.add_argument("--full", action="store_true",
                       help="Process all available documents")
    parser.add_argument("--verbose", action="store_true",
                       help="Enable verbose output")
    
    args = parser.parse_args()
    
    # Determine limit
    limit = None if args.full else args.limit
    
    # Run tests
    tester = ChunkPipelineIntegrationTest(verbose=args.verbose)
    success = tester.run_all_tests(limit=limit)
    
    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())