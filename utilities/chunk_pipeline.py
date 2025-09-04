#!/usr/bin/env python3
"""
Chunk Pipeline - Orchestrates document chunking, quality scoring, and storage.

Coordinates the v2 semantic pipeline:
1. Fetch documents ready for embedding
2. Chunk using DocumentChunker
3. Score chunks with ChunkQualityScorer  
4. Filter by quality threshold
5. Store chunks in database
6. Return metrics

Simple, direct implementation following CLAUDE.md principles.
"""

import time
from typing import Any, Dict, List, Optional
from datetime import datetime

from loguru import logger

from shared.simple_db import SimpleDB
from src.chunker.document_chunker import DocumentChunker, DocumentType
from src.quality.quality_score import ChunkQualityScorer


class ChunkPipeline:
    """Orchestrates document chunking and quality filtering pipeline."""
    
    def __init__(
        self,
        db: Optional[SimpleDB] = None,
        chunker: Optional[DocumentChunker] = None,
        scorer: Optional[ChunkQualityScorer] = None,
        quality_threshold: float = 0.35
    ):
        """Initialize pipeline with services.
        
        Args:
            db: Database connection (creates new if None)
            chunker: Document chunker (creates new if None)
            scorer: Quality scorer (creates new if None)
            quality_threshold: Minimum quality score to accept chunks
        """
        self.db = db or SimpleDB()
        self.chunker = chunker or DocumentChunker()
        self.scorer = scorer or ChunkQualityScorer()
        self.quality_threshold = quality_threshold
        
    def process_documents(
        self,
        limit: Optional[int] = None,
        source_types: Optional[List[str]] = None,
        dry_run: bool = False
    ) -> Dict[str, Any]:
        """Process documents ready for chunking.
        
        Args:
            limit: Maximum documents to process
            source_types: List of source types to process (default: email_message)
            dry_run: If True, preview without storing
            
        Returns:
            Processing metrics and results
        """
        start_time = time.time()
        
        # Default to email_message if not specified
        if source_types is None:
            source_types = ["email_message"]
        
        # Initialize metrics
        metrics = {
            "started_at": datetime.now().isoformat(),
            "documents_processed": 0,
            "chunks_created": 0,
            "chunks_dropped_quality": 0,
            "chunks_already_exist": 0,
            "errors": [],
            "dry_run": dry_run
        }
        
        logger.info(f"Starting chunk pipeline (dry_run={dry_run})")
        logger.info(f"Quality threshold: {self.quality_threshold}")
        logger.info(f"Processing source types: {source_types}")
        
        # Fetch documents ready for chunking
        documents = self._fetch_documents_for_chunking(source_types, limit)
        
        if not documents:
            logger.info("No documents found ready for chunking")
            metrics["message"] = "No documents to process"
            metrics["elapsed_seconds"] = time.time() - start_time
            return metrics
        
        logger.info(f"Found {len(documents)} documents to process")
        
        # Process each document
        for doc in documents:
            try:
                doc_metrics = self._process_single_document(doc, dry_run)
                
                # Update metrics
                metrics["documents_processed"] += 1
                metrics["chunks_created"] += doc_metrics["chunks_created"]
                metrics["chunks_dropped_quality"] += doc_metrics["chunks_dropped"]
                metrics["chunks_already_exist"] += doc_metrics["chunks_skipped"]
                
                # Log progress every 10 documents
                if metrics["documents_processed"] % 10 == 0:
                    logger.info(
                        f"Progress: {metrics['documents_processed']}/{len(documents)} docs, "
                        f"{metrics['chunks_created']} chunks created"
                    )
                    
            except Exception as e:
                error_msg = f"Error processing doc {doc['id']}: {e}"
                logger.error(error_msg)
                metrics["errors"].append(error_msg)
        
        # Calculate summary stats
        elapsed = time.time() - start_time
        metrics["elapsed_seconds"] = elapsed
        metrics["completed_at"] = datetime.now().isoformat()
        
        # Log summary
        logger.info(f"Chunk pipeline completed in {elapsed:.1f}s")
        logger.info(
            f"Processed {metrics['documents_processed']} documents → "
            f"{metrics['chunks_created']} chunks created, "
            f"{metrics['chunks_dropped_quality']} dropped (quality < {self.quality_threshold})"
        )
        
        return metrics
    
    def _fetch_documents_for_chunking(
        self,
        source_types: List[str],
        limit: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """Fetch documents ready for chunking that haven't been chunked yet.
        
        Args:
            source_types: List of source types to fetch
            limit: Maximum number of documents
            
        Returns:
            List of document records
        """
        # Build query with placeholders
        type_placeholders = ",".join(["?" for _ in source_types])
        
        query = f"""
        SELECT id, source_id, source_type, title, body
        FROM content_unified
        WHERE ready_for_embedding = 1
        AND source_type IN ({type_placeholders})
        AND NOT EXISTS (
            SELECT 1 FROM content_unified c2
            WHERE c2.source_type = 'document_chunk'
            AND c2.source_id LIKE content_unified.source_id || ':%'
        )
        """
        
        params = source_types
        
        if limit:
            query += " LIMIT ?"
            params.append(limit)
        
        return self.db.fetch(query, params)
    
    def _process_single_document(
        self,
        doc: Dict[str, Any],
        dry_run: bool = False
    ) -> Dict[str, Any]:
        """Process a single document into chunks.
        
        Args:
            doc: Document record from database
            dry_run: If True, don't store chunks
            
        Returns:
            Processing metrics for this document
        """
        doc_metrics = {
            "chunks_created": 0,
            "chunks_dropped": 0,
            "chunks_skipped": 0
        }
        
        # Determine document type
        doc_type = self._determine_document_type(doc)
        
        # Check for existing chunks (idempotency)
        existing_chunks = self._get_existing_chunks(doc["source_id"])
        if existing_chunks:
            logger.debug(f"Document {doc['source_id']} already has {len(existing_chunks)} chunks")
            doc_metrics["chunks_skipped"] = len(existing_chunks)
            return doc_metrics
        
        # Chunk the document
        chunks = self.chunker.chunk_document(
            text=doc["body"],
            doc_id=doc["source_id"],
            doc_type=doc_type
        )
        
        # Process each chunk
        for chunk in chunks:
            # Score the chunk
            quality_score = self.scorer.score(chunk)
            
            # Apply quality threshold
            if quality_score < self.quality_threshold:
                doc_metrics["chunks_dropped"] += 1
                logger.debug(
                    f"Dropped chunk {chunk.chunk_id} - "
                    f"quality {quality_score:.3f} < {self.quality_threshold}"
                )
                continue
            
            # Store chunk (unless dry run)
            if not dry_run:
                try:
                    # Extract chunk index from chunk_id (format: "doc_id:chunk_idx")
                    chunk_idx = int(chunk.chunk_id.split(":")[-1])
                    
                    # Store chunk with quality score
                    self.db.add_document_chunk(
                        doc_id=doc["source_id"],
                        chunk_idx=chunk_idx,
                        text=chunk.text,
                        token_count=chunk.token_count,
                        metadata={
                            "token_start": chunk.token_start,
                            "token_end": chunk.token_end,
                            "section_title": chunk.section_title,
                            "quote_depth": chunk.quote_depth,
                            "doc_type": doc_type.value
                        },
                        quality_score=quality_score
                    )
                    doc_metrics["chunks_created"] += 1
                    
                except Exception as e:
                    logger.error(f"Failed to store chunk {chunk.chunk_id}: {e}")
            else:
                # Dry run - just count
                doc_metrics["chunks_created"] += 1
        
        return doc_metrics
    
    def _determine_document_type(self, doc: Dict[str, Any]) -> DocumentType:
        """Determine document type from source metadata.
        
        Args:
            doc: Document record
            
        Returns:
            DocumentType enum value
        """
        source_type = doc.get("source_type", "").lower()
        title = doc.get("title", "").lower()
        
        # Map source types to document types
        if source_type == "email_message" or "email" in title:
            return DocumentType.EMAIL
        elif "legal" in title or "court" in title or "case" in title:
            return DocumentType.LEGAL_PDF
        elif "ocr" in title or "scan" in title:
            return DocumentType.OCR_SCAN
        else:
            return DocumentType.GENERAL
    
    def _get_existing_chunks(self, doc_id: str) -> List[Dict[str, Any]]:
        """Check for existing chunks for a document.
        
        Args:
            doc_id: Document source_id
            
        Returns:
            List of existing chunk records
        """
        return self.db.get_chunks_for_document(doc_id)
    
    def get_pipeline_stats(self) -> Dict[str, Any]:
        """Get current pipeline statistics.
        
        Returns:
            Statistics about documents and chunks
        """
        stats = {}
        
        # Count documents ready for chunking
        ready_docs = self.db.fetch(
            """
            SELECT COUNT(*) as count
            FROM content_unified
            WHERE ready_for_embedding = 1
            AND source_type IN ('email_message', 'document')
            """,
            []
        )
        stats["documents_ready"] = ready_docs[0]["count"] if ready_docs else 0
        
        # Count documents already chunked
        chunked_docs = self.db.fetch(
            """
            SELECT COUNT(DISTINCT SUBSTR(source_id, 1, INSTR(source_id || ':', ':') - 1)) as count
            FROM content_unified
            WHERE source_type = 'document_chunk'
            """,
            []
        )
        stats["documents_chunked"] = chunked_docs[0]["count"] if chunked_docs else 0
        
        # Count total chunks
        total_chunks = self.db.fetch(
            """
            SELECT 
                COUNT(*) as total,
                COUNT(CASE WHEN quality_score >= ? THEN 1 END) as high_quality,
                COUNT(CASE WHEN quality_score < ? THEN 1 END) as low_quality
            FROM content_unified
            WHERE source_type = 'document_chunk'
            """,
            [self.quality_threshold, self.quality_threshold]
        )
        
        if total_chunks:
            stats["total_chunks"] = total_chunks[0]["total"]
            stats["high_quality_chunks"] = total_chunks[0]["high_quality"]
            stats["low_quality_chunks"] = total_chunks[0]["low_quality"]
        else:
            stats["total_chunks"] = 0
            stats["high_quality_chunks"] = 0
            stats["low_quality_chunks"] = 0
        
        # Count chunks ready for embedding
        ready_chunks = self.db.fetch(
            """
            SELECT COUNT(*) as count
            FROM content_unified
            WHERE source_type = 'document_chunk'
            AND ready_for_embedding = 1
            AND embedding_generated = 0
            AND quality_score >= ?
            """,
            [self.quality_threshold]
        )
        stats["chunks_ready_for_embedding"] = ready_chunks[0]["count"] if ready_chunks else 0
        
        return stats


def main():
    """CLI entry point for testing."""
    import argparse
    import json
    
    parser = argparse.ArgumentParser(description="Chunk Pipeline")
    parser.add_argument("--limit", type=int, help="Maximum documents to process")
    parser.add_argument("--dry-run", action="store_true", help="Preview without storing")
    parser.add_argument("--stats", action="store_true", help="Show pipeline statistics")
    parser.add_argument("--quality-threshold", type=float, default=0.35,
                       help="Minimum quality score (default: 0.35)")
    parser.add_argument("--json", action="store_true", help="Output as JSON")
    
    args = parser.parse_args()
    
    pipeline = ChunkPipeline(quality_threshold=args.quality_threshold)
    
    if args.stats:
        stats = pipeline.get_pipeline_stats()
        
        if args.json:
            print(json.dumps(stats, indent=2))
        else:
            print("\n📊 Chunk Pipeline Statistics")
            print("=" * 40)
            for key, value in stats.items():
                print(f"{key}: {value}")
    else:
        result = pipeline.process_documents(
            limit=args.limit,
            dry_run=args.dry_run
        )
        
        if args.json:
            print(json.dumps(result, indent=2, default=str))
        else:
            print("\n✅ Chunk Pipeline Results")
            print("=" * 40)
            print(f"Documents processed: {result['documents_processed']}")
            print(f"Chunks created: {result['chunks_created']}")
            print(f"Chunks dropped (low quality): {result['chunks_dropped_quality']}")
            print(f"Chunks skipped (already exist): {result['chunks_already_exist']}")
            print(f"Elapsed time: {result['elapsed_seconds']:.1f}s")
            
            if result["errors"]:
                print(f"\n❌ Errors ({len(result['errors'])})")
                for error in result["errors"][:5]:
                    print(f"  - {error}")


if __name__ == "__main__":
    main()