#!/usr/bin/env python3
"""
Content Quality Assessment - Batch Evaluation
Scores all existing content and updates quality metrics in database.
"""

import uuid
from datetime import datetime
from shared.simple_db import SimpleDB
from shared.content_quality_scorer import ContentQualityScorer, ValidationStatus
from loguru import logger

def assess_all_content(limit: int = None, source_types: list = None):
    """
    Batch assess content quality for all documents.
    Updates database with quality metrics and validation status.
    """
    
    db = SimpleDB()
    scorer = ContentQualityScorer()
    pipeline_run_id = str(uuid.uuid4())[:8]  # Short run ID
    
    # Build query filters
    where_clauses = []
    params = []
    
    if source_types:
        placeholders = ','.join(['?' for _ in source_types])
        where_clauses.append(f"source_type IN ({placeholders})")
        params.extend(source_types)
    
    where_sql = f"WHERE {' AND '.join(where_clauses)}" if where_clauses else ""
    limit_sql = f"LIMIT {limit}" if limit else ""
    
    # Get content to assess
    query = f"""
        SELECT id, source_type, title, body, 
               LENGTH(COALESCE(body, '')) as text_length,
               validation_status
        FROM content_unified 
        {where_sql}
        ORDER BY text_length DESC 
        {limit_sql}
    """
    
    content_records = db.fetch(query, params)
    total_records = len(content_records)
    
    print(f"📊 Content Quality Assessment")
    print(f"Pipeline Run ID: {pipeline_run_id}")
    print(f"Records to process: {total_records:,}")
    print("-" * 50)
    
    if total_records == 0:
        print("No content found to assess.")
        return
    
    # Track statistics
    stats = {
        'processed': 0,
        'pass': 0,
        'borderline': 0, 
        'fail': 0,
        'empty': 0,
        'by_source_type': {}
    }
    
    batch_updates = []
    
    for i, record in enumerate(content_records, 1):
        content_id = record['id']
        source_type = record['source_type']
        body = record['body'] or ''
        
        # Initialize source type stats
        if source_type not in stats['by_source_type']:
            stats['by_source_type'][source_type] = {'total': 0, 'pass': 0, 'fail': 0, 'empty': 0}
        
        stats['by_source_type'][source_type]['total'] += 1
        stats['processed'] += 1
        
        # Skip empty content
        if not body.strip():
            stats['empty'] += 1
            stats['by_source_type'][source_type]['empty'] += 1
            
            batch_updates.append({
                'id': content_id,
                'text_quality_score': 0.0,
                'alpha_ratio': 0.0,
                'symbol_ratio': 0.0,
                'unique_bigrams': 0,
                'english_dict_hits': 0,
                'chars_per_page': 0.0,
                'validation_status': ValidationStatus.INGESTED.value,
                'pipeline_run_id': pipeline_run_id,
                'quality_failure_reasons': 'empty_content',
                'last_attempt_at': datetime.now().isoformat()
            })
            continue
        
        # Score content quality
        try:
            metrics = scorer.score_content(body, page_count=1)  # Assume 1 page for now
            status, description = scorer.classify_quality(metrics.quality_score)
            
            # Update statistics
            if status == 'PASS':
                stats['pass'] += 1
                stats['by_source_type'][source_type]['pass'] += 1
            elif status == 'BORDERLINE':
                stats['borderline'] += 1
            else:
                stats['fail'] += 1
                stats['by_source_type'][source_type]['fail'] += 1
            
            # Prepare batch update
            batch_updates.append({
                'id': content_id,
                'text_quality_score': metrics.quality_score,
                'alpha_ratio': metrics.alpha_ratio,
                'symbol_ratio': metrics.symbol_ratio,
                'unique_bigrams': metrics.unique_bigrams,
                'english_dict_hits': metrics.english_dict_hits,
                'chars_per_page': metrics.chars_per_page,
                'validation_status': metrics.validation_status.value,
                'pipeline_run_id': pipeline_run_id,
                'quality_failure_reasons': '|'.join(metrics.failure_reasons) if metrics.failure_reasons else None,
                'last_attempt_at': datetime.now().isoformat()
            })
            
        except Exception as e:
            logger.error(f"Error scoring content {content_id}: {e}")
            stats['fail'] += 1
            stats['by_source_type'][source_type]['fail'] += 1
        
        # Progress indicator
        if i % 100 == 0 or i == total_records:
            print(f"  Progress: {i:,}/{total_records:,} ({i/total_records*100:.1f}%)")
    
    # Batch update database
    print(f"\\n💾 Updating database with quality metrics...")
    
    for update in batch_updates:
        content_id = update.pop('id')
        
        # Build SET clause dynamically
        set_clauses = []
        values = []
        for key, value in update.items():
            set_clauses.append(f"{key} = ?")
            values.append(value)
        
        values.append(content_id)  # For WHERE clause
        
        update_sql = f"""
            UPDATE content_unified 
            SET {', '.join(set_clauses)}
            WHERE id = ?
        """
        
        try:
            db.execute(update_sql, values)
        except Exception as e:
            logger.error(f"Failed to update content {content_id}: {e}")
    
    # Print final statistics
    print(f"\\n📊 Quality Assessment Results:")
    print(f"  Total processed: {stats['processed']:,}")
    print(f"  ✅ PASS (≥0.7):        {stats['pass']:,} ({stats['pass']/stats['processed']*100:.1f}%)")
    print(f"  ⚠️  BORDERLINE (0.5-0.7): {stats['borderline']:,} ({stats['borderline']/stats['processed']*100:.1f}%)")
    print(f"  ❌ FAIL (<0.5):        {stats['fail']:,} ({stats['fail']/stats['processed']*100:.1f}%)")
    print(f"  📄 Empty content:      {stats['empty']:,} ({stats['empty']/stats['processed']*100:.1f}%)")
    
    print(f"\\n📊 Results by Source Type:")
    for source_type, source_stats in stats['by_source_type'].items():
        total = source_stats['total']
        pass_rate = source_stats['pass'] / total * 100 if total > 0 else 0
        fail_rate = source_stats['fail'] / total * 100 if total > 0 else 0
        empty_rate = source_stats['empty'] / total * 100 if total > 0 else 0
        
        print(f"  {source_type:12s}: {total:4d} total | {pass_rate:5.1f}% pass | {fail_rate:5.1f}% fail | {empty_rate:5.1f}% empty")
    
    print(f"\\n✅ Quality assessment complete. Pipeline run: {pipeline_run_id}")

def main():
    """Main function with CLI options"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Assess content quality")
    parser.add_argument('--limit', type=int, help="Limit number of documents to process")
    parser.add_argument('--source-types', nargs='+', help="Filter by source types", 
                       choices=['pdf', 'email', 'email_message', 'document', 'upload'])
    parser.add_argument('--pdfs-only', action='store_true', help="Process only PDF documents")
    
    args = parser.parse_args()
    
    source_types = None
    if args.pdfs_only:
        source_types = ['pdf']
    elif args.source_types:
        source_types = args.source_types
    
    assess_all_content(limit=args.limit, source_types=source_types)

if __name__ == "__main__":
    main()