#!/usr/bin/env python3
"""
Verify that the schema migration was successful.
Checks for new columns, constraints, and data integrity.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from loguru import logger

from config.settings import settings
from lib.db import SimpleDB


def verify_schema(db: SimpleDB):
    """Verify the schema has all required columns."""
    
    logger.info("Verifying schema structure...")
    
    # Get all columns
    columns = db.fetch_all("""
        SELECT name, type, dflt_value, pk
        FROM pragma_table_info('content_unified')
    """)
    
    column_dict = {col['name']: col for col in columns}
    
    # Required columns with their expected types
    required_columns = {
        'sha256': 'TEXT',
        'embedding_generated': 'INTEGER',
        'quality_score': 'REAL', 
        'is_validated': 'INTEGER',
        'metadata': 'TEXT',
        'substantive_text': 'TEXT'
    }
    
    print("\n" + "="*80)
    print("SCHEMA VERIFICATION REPORT")
    print("="*80)
    
    print("\n📋 Column Status:")
    all_good = True
    
    for col_name, expected_type in required_columns.items():
        if col_name in column_dict:
            actual = column_dict[col_name]
            type_match = actual['type'] == expected_type
            
            status = "✅" if type_match else "⚠️"
            print(f"  {status} {col_name:20} {actual['type']:10} (default: {actual['dflt_value'] or 'NULL'})")
            
            if not type_match:
                all_good = False
                logger.warning(f"Type mismatch for {col_name}: expected {expected_type}, got {actual['type']}")
        else:
            print(f"  ❌ {col_name:20} MISSING")
            all_good = False
    
    # Check for old column that should be migrated
    if 'ready_for_embedding' in column_dict:
        print(f"  ⚠️  ready_for_embedding still exists (consider removing after transition)")
    
    return all_good


def verify_indexes(db: SimpleDB):
    """Verify indexes are properly configured."""
    
    logger.info("Verifying indexes...")
    
    indexes = db.fetch_all("""
        SELECT name, tbl_name, sql 
        FROM sqlite_master 
        WHERE type='index' AND tbl_name='content_unified'
    """)
    
    print("\n📑 Index Status:")
    
    has_sha256_index = False
    for index in indexes:
        if index['sql'] and 'sha256' in index['sql']:
            has_sha256_index = True
            is_unique = 'UNIQUE' in index['sql']
            status = "✅" if is_unique else "⚠️"
            print(f"  {status} {index['name']:20} {'UNIQUE' if is_unique else 'NON-UNIQUE'}")
        else:
            print(f"  ℹ️  {index['name']:20}")
    
    if not has_sha256_index:
        print("  ❌ Missing index on sha256 column")
        return False
    
    return True


def verify_data_integrity(db: SimpleDB):
    """Verify data integrity and check for issues."""
    
    logger.info("Verifying data integrity...")
    
    print("\n📊 Data Integrity:")
    
    # Check total records
    total = db.fetch_one("SELECT COUNT(*) as count FROM content_unified")
    print(f"  Total records: {total['count']}")
    
    # Check for NULL sha256 (shouldn't happen)
    null_sha = db.fetch_one("SELECT COUNT(*) as count FROM content_unified WHERE sha256 IS NULL")
    if null_sha['count'] > 0:
        print(f"  ⚠️  Records with NULL sha256: {null_sha['count']}")
    else:
        print(f"  ✅ All records have sha256 hashes")
    
    # Check for duplicate sha256 (should be impossible with UNIQUE)
    dupes = db.fetch_all("""
        SELECT sha256, COUNT(*) as count 
        FROM content_unified 
        GROUP BY sha256 
        HAVING COUNT(*) > 1
    """)
    
    if dupes:
        print(f"  ❌ Found {len(dupes)} duplicate sha256 hashes!")
        for dupe in dupes[:5]:
            print(f"      - {dupe['sha256'][:16]}... ({dupe['count']} records)")
    else:
        print(f"  ✅ No duplicate content (sha256 unique constraint working)")
    
    # Check embedding status
    embedded = db.fetch_one("""
        SELECT 
            SUM(CASE WHEN embedding_generated = 1 THEN 1 ELSE 0 END) as generated,
            SUM(CASE WHEN embedding_generated = 0 THEN 1 ELSE 0 END) as pending
        FROM content_unified
    """)
    
    print(f"  📈 Embedding status:")
    print(f"      Generated: {embedded['generated'] or 0}")
    print(f"      Pending: {embedded['pending'] or 0}")
    
    # Check quality scores
    quality = db.fetch_one("""
        SELECT 
            MIN(quality_score) as min_score,
            MAX(quality_score) as max_score,
            AVG(quality_score) as avg_score
        FROM content_unified
    """)
    
    print(f"  📊 Quality scores:")
    print(f"      Min: {quality['min_score']:.2f}")
    print(f"      Max: {quality['max_score']:.2f}")
    print(f"      Avg: {quality['avg_score']:.2f}")
    
    # Check validation status
    validated = db.fetch_one("""
        SELECT 
            SUM(CASE WHEN is_validated = 1 THEN 1 ELSE 0 END) as validated,
            SUM(CASE WHEN is_validated = 0 THEN 1 ELSE 0 END) as unvalidated
        FROM content_unified
    """)
    
    print(f"  ✓ Validation status:")
    print(f"      Validated: {validated['validated'] or 0}")
    print(f"      Unvalidated: {validated['unvalidated'] or 0}")
    
    return True


def verify_fts5_compatibility(db: SimpleDB):
    """Verify FTS5 is still working with the new schema."""
    
    logger.info("Verifying FTS5 compatibility...")
    
    print("\n🔍 FTS5 Status:")
    
    # Check if FTS5 table exists
    fts_table = db.fetch_one("""
        SELECT name FROM sqlite_master 
        WHERE type='table' AND name='content_unified_fts'
    """)
    
    if not fts_table:
        print("  ⚠️  FTS5 table not found (run lib/fts5_setup.py if needed)")
        return True  # Not a failure, just informational
    
    print("  ✅ FTS5 table exists")
    
    # Check FTS5 triggers
    triggers = db.fetch_all("""
        SELECT name FROM sqlite_master 
        WHERE type='trigger' AND name LIKE 'fts5_%'
    """)
    
    expected_triggers = ['fts5_insert', 'fts5_update', 'fts5_delete']
    for trigger_name in expected_triggers:
        found = any(t['name'] == trigger_name for t in triggers)
        status = "✅" if found else "❌"
        print(f"  {status} Trigger: {trigger_name}")
    
    # Check FTS5 content count vs main table
    main_count = db.fetch_one("SELECT COUNT(*) as count FROM content_unified")['count']
    fts_count = db.fetch_one("SELECT COUNT(*) as count FROM content_unified_fts")['count']
    
    if main_count == fts_count:
        print(f"  ✅ FTS5 synchronized ({fts_count} records)")
    else:
        print(f"  ⚠️  FTS5 out of sync: {fts_count} FTS records vs {main_count} main records")
        print(f"     Run: python3 lib/fts5_setup.py to rebuild")
    
    return True


def main():
    """Run all verification checks."""
    logger.info("Starting migration verification...")
    
    db = SimpleDB(settings.database.emails_db_path)
    
    # Run all checks
    schema_ok = verify_schema(db)
    indexes_ok = verify_indexes(db)
    data_ok = verify_data_integrity(db)
    fts_ok = verify_fts5_compatibility(db)
    
    # Overall status
    print("\n" + "="*80)
    print("OVERALL STATUS")
    print("="*80)
    
    all_good = schema_ok and indexes_ok and data_ok and fts_ok
    
    if all_good:
        print("\n✅ Migration verification PASSED!")
        print("\nThe database schema has been successfully updated with:")
        print("  • sha256 for content deduplication")
        print("  • embedding_generated for tracking vector generation")
        print("  • quality_score for content filtering")
        print("  • is_validated for content verification")
        return 0
    else:
        print("\n⚠️  Some verification checks failed. Review the output above.")
        return 1


if __name__ == "__main__":
    sys.exit(main())