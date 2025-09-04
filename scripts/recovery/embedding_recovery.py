#!/usr/bin/env python3
"""
Embedding Recovery Script - Generate Legal BERT embeddings for all content
"""

import sys
import os

from shared.db.simple_db import SimpleDB
from utilities.embeddings.legal_bert import LegalBertEmbeddings
from utilities.vector_store.qdrant_store import QdrantStore
from infrastructure.documents.chunker.document_chunker import DocumentChunker
from infrastructure.documents.quality.quality_score import ChunkQualityScorer
from loguru import logger
import hashlib
import json

def main():
    """Generate embeddings for all search-ready content"""
    logger.info("Starting embedding generation recovery...")
    
    db = SimpleDB()
    embedder = LegalBertEmbeddings()
    vector_store = QdrantStore()
    chunker = DocumentChunker()
    quality_scorer = ChunkQualityScorer()
    
    # Get all content ready for embedding
    content = db.execute("""
        SELECT id, source_type, source_id, title, body, metadata
        FROM content_unified
        WHERE ready_for_embedding = 1
        AND body IS NOT NULL
        AND LENGTH(body) > 50
    """).fetchall()
    
    logger.info(f"Found {len(content)} items ready for embedding")
    
    success = 0
    failed = 0
    chunks_created = 0
    
    for i, row in enumerate(content, 1):
        content_id, source_type, source_id, title, body, metadata_str = row
        
        if i % 10 == 0:
            logger.info(f"Processing {i}/{len(content)}: {success} success, {failed} failed, {chunks_created} chunks")
        
        try:
            # Parse metadata
            json.loads(metadata_str) if metadata_str else {}
            
            # Create chunks for documents
            if source_type == 'document' and len(body) > 1500:
                chunks = chunker.chunk_document(body, {
                    'source_type': source_type,
                    'source_id': source_id,
                    'title': title
                })
            else:
                # For emails or short content, use as single chunk
                chunks = [{
                    'text': body,
                    'metadata': {
                        'source_type': source_type,
                        'source_id': source_id,
                        'title': title,
                        'chunk_index': 0,
                        'total_chunks': 1
                    }
                }]
            
            # Process each chunk
            for chunk in chunks:
                # Calculate quality score
                quality_score = quality_scorer.calculate_quality_score(chunk['text'])
                
                # Skip low-quality chunks
                if quality_score < 0.35:
                    logger.debug(f"Skipping low-quality chunk (score: {quality_score:.2f})")
                    continue
                
                # Generate embedding
                embedding = embedder.encode(chunk['text'])
                
                if embedding is not None:
                    # Generate chunk ID
                    chunk_hash = hashlib.sha256(chunk['text'].encode()).hexdigest()[:16]
                    chunk_id = f"{source_id[:8]}_{chunk['metadata']['chunk_index']}_{chunk_hash}"
                    
                    # Store in vector database
                    vector_store.add_documents(
                        documents=[chunk['text']],
                        embeddings=[embedding],
                        metadatas=[{
                            **chunk['metadata'],
                            'content_id': content_id,
                            'quality_score': quality_score
                        }],
                        ids=[chunk_id]
                    )
                    
                    # Store embedding reference in database
                    db.execute("""
                        INSERT OR IGNORE INTO content_embeddings
                        (content_id, chunk_index, chunk_text, embedding_id, quality_score)
                        VALUES (?, ?, ?, ?, ?)
                    """, (
                        content_id,
                        chunk['metadata']['chunk_index'],
                        chunk['text'][:500],  # Store preview
                        chunk_id,
                        quality_score
                    ))
                    
                    chunks_created += 1
            
            success += 1
            
        except Exception as e:
            logger.error(f"Failed to process content {content_id}: {e}")
            failed += 1
    
    # Final stats
    logger.info(f"Embedding generation complete: {success} documents, {chunks_created} chunks created")
    
    # Check vector store status
    collection_info = vector_store.get_collection_info()
    if collection_info:
        logger.info(f"Vector store: {collection_info.get('vectors_count', 0)} vectors")
    
    # Check database status
    embedding_count = db.execute("SELECT COUNT(*) FROM content_embeddings").fetchone()[0]
    logger.info(f"Database: {embedding_count} embedding references")

if __name__ == "__main__":
    main()