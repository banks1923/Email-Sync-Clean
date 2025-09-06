#!/usr/bin/env python3
"""
Pre-migration analysis to detect duplicate content before adding SHA256 UNIQUE constraint.
Identifies records that would conflict and provides cleanup recommendations.
"""

import hashlib
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from loguru import logger

from config.settings import settings
from lib.db import SimpleDB


def compute_content_hash(substantive_text: str = None, body: str = None) -> str:
    """Compute SHA256 hash of normalized content.
    
    Uses substantive_text if available, otherwise body.
    Normalizes by stripping whitespace and converting to lowercase.
    """
    content = substantive_text or body or ''
    normalized = content.strip().lower()
    return hashlib.sha256(normalized.encode('utf-8')).hexdigest()


def analyze_duplicates(db: SimpleDB):
    """Find and analyze duplicate content in content_unified table."""
    
    logger.info("Fetching all content records...")
    records = db.fetch_all("""
        SELECT id, source_type, source_id, title, 
               substantive_text, body, created_at
        FROM content_unified
        ORDER BY id
    """)
    
    logger.info(f"Found {len(records)} total records")
    
    # Group by content hash
    hash_groups = defaultdict(list)
    for record in records:
        content_hash = compute_content_hash(
            record.get('substantive_text'),
            record.get('body')
        )
        hash_groups[content_hash].append(record)
    
    # Find duplicates
    duplicates = {
        hash_val: records 
        for hash_val, records in hash_groups.items() 
        if len(records) > 1
    }
    
    if not duplicates:
        logger.success("✅ No duplicate content found! Safe to add UNIQUE constraint.")
        return
    
    # Analyze duplicates
    logger.warning(f"⚠️  Found {len(duplicates)} groups of duplicate content")
    logger.warning(f"Total duplicate records: {sum(len(recs) - 1 for recs in duplicates.values())}")
    
    print("\n" + "="*80)
    print("DUPLICATE CONTENT ANALYSIS")
    print("="*80)
    
    for i, (content_hash, dupe_records) in enumerate(duplicates.items(), 1):
        print(f"\nDuplicate Group {i}:")
        print(f"  Hash: {content_hash[:16]}...")
        print(f"  Count: {len(dupe_records)} records")
        
        # Show record details
        for record in dupe_records:
            title = (record.get('title') or 'No title')[:50]
            print(f"    - ID: {record['id']:5} | Type: {record['source_type']:15} | Title: {title}")
        
        # Show content preview
        first_record = dupe_records[0]
        content = first_record.get('substantive_text') or first_record.get('body') or ''
        preview = content[:100].replace('\n', ' ')
        print(f"  Content preview: {preview}...")
        
        # Recommendation
        print(f"  → Recommendation: Keep ID {dupe_records[0]['id']}, delete {[r['id'] for r in dupe_records[1:]]}")
    
    # Summary and recommendations
    print("\n" + "="*80)
    print("MIGRATION IMPACT SUMMARY")
    print("="*80)
    
    total_to_delete = sum(len(recs) - 1 for recs in duplicates.values())
    print(f"\n📊 Statistics:")
    print(f"  - Total records: {len(records)}")
    print(f"  - Unique content: {len(hash_groups)}")
    print(f"  - Duplicate groups: {len(duplicates)}")
    print(f"  - Records to delete: {total_to_delete}")
    print(f"  - Records after cleanup: {len(records) - total_to_delete}")
    
    # Check for vector orphans
    print(f"\n⚠️  Vector Store Impact:")
    duplicate_ids = []
    for dupe_records in duplicates.values():
        duplicate_ids.extend([r['id'] for r in dupe_records[1:]])
    
    print(f"  - Content IDs that will be deleted: {duplicate_ids[:10]}{'...' if len(duplicate_ids) > 10 else ''}")
    print(f"  - These may have orphaned vectors in Qdrant that need cleanup")
    
    # Generate cleanup SQL
    print(f"\n💾 Cleanup SQL (save as cleanup_duplicates.sql):")
    print("-- Delete duplicate records, keeping the lowest ID in each group")
    print("BEGIN TRANSACTION;")
    for dupe_records in duplicates.values():
        ids_to_delete = [str(r['id']) for r in dupe_records[1:]]
        if ids_to_delete:
            print(f"DELETE FROM content_unified WHERE id IN ({','.join(ids_to_delete)});")
    print("COMMIT;")
    
    return duplicates


def check_existing_constraints(db: SimpleDB):
    """Check if SHA256 column or constraints already exist."""
    
    # Check for sha256 column
    columns = db.fetch_all("""
        SELECT name, type, dflt_value, pk
        FROM pragma_table_info('content_unified')
        WHERE name = 'sha256'
    """)
    
    if columns:
        logger.warning("⚠️  sha256 column already exists!")
        return True
    
    return False


def main():
    """Run pre-migration analysis."""
    logger.info("Starting pre-migration duplicate analysis...")
    
    db = SimpleDB(settings.database.emails_db_path)
    
    # Check existing schema
    if check_existing_constraints(db):
        logger.warning("Migration may have already been partially applied")
    
    # Analyze duplicates
    duplicates = analyze_duplicates(db)
    
    if duplicates:
        print("\n" + "="*80)
        print("NEXT STEPS:")
        print("="*80)
        print("\n1. Review the duplicate analysis above")
        print("2. Optionally run the cleanup SQL to remove duplicates")
        print("3. Run the migration script: python tools/migrations/migrate_schema.py")
        print("4. Verify with: python tools/migrations/verify_migration.py")
    else:
        print("\n✅ No duplicates found. Safe to proceed with migration!")
        print("Run: python tools/migrations/migrate_schema.py")


if __name__ == "__main__":
    main()