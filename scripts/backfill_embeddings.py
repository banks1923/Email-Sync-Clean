#!/usr/bin/env python3
"""
Simple Embedding Backfill Script
Processes content from content_unified table using existing semantic pipeline.

Following CLAUDE.md principles: Simple > Complex, Direct > Indirect
"""

import argparse
import sys
import os
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from utilities.semantic_pipeline import SemanticPipeline
from shared.simple_db import SimpleDB
from loguru import logger


def main():
    parser = argparse.ArgumentParser(
        description="Backfill embeddings for documents in content_unified table",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Process all content types
  python3 scripts/backfill_embeddings.py
  
  # Process only PDFs
  python3 scripts/backfill_embeddings.py --type pdf
  
  # Process specific number of documents
  python3 scripts/backfill_embeddings.py --limit 50
  
  # Check what needs processing (dry run)
  python3 scripts/backfill_embeddings.py --dry-run
        """
    )
    
    parser.add_argument(
        "--type", 
        choices=["all", "pdf", "email"], 
        default="all",
        help="Content type to process (default: all)"
    )
    parser.add_argument(
        "--limit", 
        type=int, 
        default=100,
        help="Maximum documents to process (default: 100)"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be processed without doing it"
    )
    
    args = parser.parse_args()
    
    # Check environment
    db_path = os.getenv("APP_DB_PATH", "data/emails.db")
    if not Path(db_path).exists():
        print(f"❌ Database not found: {db_path}")
        print("Set APP_DB_PATH environment variable or ensure database exists")
        sys.exit(1)
    
    print("Embedding Backfill")
    print("=" * 50)
    print(f"Content type: {args.type}")
    print(f"Limit: {args.limit}")
    print(f"Database: {db_path}")
    
    # Initialize services
    try:
        db = SimpleDB()
        pipeline = SemanticPipeline(db=db)
        
        # Check what needs processing
        where_clause = "WHERE ready_for_embedding = 1"
        params = []
        
        if args.type != 'all':
            where_clause += " AND source_type = ?"
            params.append(args.type)
        
        query = f"""
            SELECT COUNT(*) as total, source_type
            FROM content_unified 
            {where_clause}
            GROUP BY source_type
            ORDER BY total DESC
        """
        
        cursor = db.execute(query, tuple(params))
        pending = cursor.fetchall()
        
        if not pending:
            print(f"✅ No content ready for embedding (type={args.type})")
            return
        
        print("\n📊 Content ready for embedding:")
        total_pending = 0
        for row in pending:
            count = row['total']
            content_type = row['source_type'] or 'unknown'
            total_pending += count
            print(f"  {content_type}: {count} documents")
        
        print(f"  Total: {total_pending} documents")
        
        if args.dry_run:
            print(f"\n🔍 Dry run complete - would process {min(total_pending, args.limit)} documents")
            return
        
        if total_pending == 0:
            print(f"✅ All {args.type} content already has embeddings")
            return
        
        # Proceed with processing
        print(f"\n🚀 Processing {min(total_pending, args.limit)} documents...")
        
        result = pipeline.process_content_unified(
            content_type=args.type,
            limit=args.limit
        )
        
        # Display results
        print("\n📈 Processing Results:")
        print(f"  ✅ Processed: {result['processed']}")
        print(f"  ⏭️  Skipped: {result['skipped']}")  
        print(f"  ❌ Errors: {result['errors']}")
        print(f"  🎯 Vectors stored: {result['vectors_stored']}")
        
        if result['errors'] > 0:
            print(f"\n⚠️  {result['errors']} documents failed processing")
            print("Check logs for details")
            
        if result['processed'] > 0:
            print(f"\n✅ Successfully processed {result['processed']} documents")
            print("Documents are now searchable via semantic search")
            
    except ImportError as e:
        print(f"❌ Missing dependencies: {e}")
        print("Ensure Qdrant is running and embedding service is available")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Processing failed: {e}")
        logger.exception("Backfill failed")
        sys.exit(1)


if __name__ == "__main__":
    main()