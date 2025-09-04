#!/usr/bin/env python3
"""
Generate embeddings for content in the database.

This script processes content through the v2 embedding pipeline:
1. Fetches chunks ready for embedding from the database
2. Generates Legal BERT embeddings in batches
3. Stores embeddings in Qdrant vector store

Usage:
    python scripts/data/generate_embeddings.py [--limit N] [--batch-size N] [--dry-run]
"""

import argparse
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

# Delayed imports to allow --help to work
logger = None
BatchEmbeddingProcessor = None
SimpleDB = None


def main():
    """Main entry point for embedding generation."""
    parser = argparse.ArgumentParser(
        description="Generate embeddings for content in the database",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Show statistics
  python scripts/data/generate_embeddings.py --stats
  
  # Generate all missing embeddings
  python scripts/data/generate_embeddings.py
  
  # Process only first 100 chunks
  python scripts/data/generate_embeddings.py --limit 100
  
  # Test run without storing
  python scripts/data/generate_embeddings.py --dry-run --limit 10
  
  # Use smaller batches for memory constraints
  python scripts/data/generate_embeddings.py --batch-size 32
"""
    )
    parser.add_argument(
        "--limit",
        type=int,
        help="Maximum number of chunks to process"
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=64,
        help="Number of chunks per batch (default: 64)"
    )
    parser.add_argument(
        "--min-quality",
        type=float,
        default=0.35,
        help="Minimum quality score for chunks (default: 0.35)"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview without storing embeddings"
    )
    parser.add_argument(
        "--stats",
        action="store_true",
        help="Show statistics only"
    )
    
    args = parser.parse_args()
    
    # Do the actual imports after parsing args (so --help works)
    global logger, BatchEmbeddingProcessor, SimpleDB
    from loguru import logger
    from utilities.embeddings.batch_processor import BatchEmbeddingProcessor
    from shared.db.simple_db import SimpleDB
    
    # Check if we're just showing stats
    if args.stats:
        db = SimpleDB()
        
        # Get chunk statistics manually
        total_chunks = db.fetch_one(
            "SELECT COUNT(*) as count FROM content_unified WHERE source_type = 'document_chunk'"
        )
        chunks_with_embeddings = db.fetch_one(
            "SELECT COUNT(*) as count FROM content_unified WHERE source_type = 'document_chunk' AND has_embedding = 1"
        )
        quality_stats = db.fetch_one(
            "SELECT AVG(quality_score) as avg_quality, MIN(quality_score) as min_quality, MAX(quality_score) as max_quality "
            "FROM content_unified WHERE source_type = 'document_chunk' AND quality_score IS NOT NULL"
        )
        
        total = total_chunks["count"] if total_chunks else 0
        with_embeddings = chunks_with_embeddings["count"] if chunks_with_embeddings else 0
        needing_embeddings = total - with_embeddings
        
        print("\n📊 Embedding Statistics:")
        print(f"  Total chunks: {total}")
        print(f"  Chunks with embeddings: {with_embeddings}")
        print(f"  Chunks needing embeddings: {needing_embeddings}")
        
        if quality_stats and quality_stats["avg_quality"]:
            print(f"  Average quality score: {quality_stats['avg_quality']:.3f}")
            print(f"  Quality range: {quality_stats['min_quality']:.3f} - {quality_stats['max_quality']:.3f}")
        
        if needing_embeddings > 0:
            print(f"\n💡 Run this script without --stats to generate {needing_embeddings} missing embeddings")
        else:
            print("\n✅ All chunks have embeddings!")
        
        return 0
    
    # Initialize processor
    logger.info("Initializing batch embedding processor...")
    processor = BatchEmbeddingProcessor(
        batch_size=args.batch_size,
        min_quality=args.min_quality
    )
    
    # Process chunks
    logger.info(f"Starting embedding generation (dry_run={args.dry_run})...")
    
    try:
        result = processor.process_chunks(
            limit=args.limit,
            dry_run=args.dry_run
        )
        
        # Display results
        print("\n📊 Embedding Generation Results:")
        print(f"  Chunks processed: {result['chunks_processed']}")
        print(f"  Embeddings generated: {result['embeddings_generated']}")
        if not args.dry_run:
            print(f"  Vectors stored: {result['vectors_stored']}")
        print(f"  Chunks skipped: {result['chunks_skipped']}")
        
        if result.get('errors'):
            print(f"\n⚠️  Errors encountered: {len(result['errors'])}")
            for error in result['errors'][:5]:  # Show first 5 errors
                print(f"    - {error}")
        
        elapsed = result.get('elapsed_seconds', 0)
        if elapsed > 0:
            rate = result['chunks_processed'] / elapsed if elapsed > 0 else 0
            print(f"\n⏱️  Time: {elapsed:.1f}s ({rate:.1f} chunks/sec)")
        
        if args.dry_run:
            print("\n🔍 DRY RUN - No embeddings were actually stored")
        else:
            print("\n✅ Embeddings generated and stored successfully!")
        
        return 0
        
    except Exception as e:
        logger.error(f"Failed to generate embeddings: {e}")
        print(f"\n❌ Error: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())