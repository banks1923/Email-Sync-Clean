#!/usr/bin/env python3
"""
CI Guard: Ensure no legacy tables exist in the database.
This test MUST always pass to prevent regression to old schema.
"""

import sys
from pathlib import Path

# Add parent directory for imports
sys.path.append(str(Path(__file__).parent.parent))

from shared.db.simple_db import SimpleDB


def test_no_emails_table():
    """Ensure the legacy 'emails' table does not exist."""
    db = SimpleDB()
    
    result = db.fetch_one("""
        SELECT COUNT(*) as count 
        FROM sqlite_master 
        WHERE type='table' AND name='emails'
    """)
    
    assert result['count'] == 0, "FATAL: Legacy 'emails' table exists! Use content_unified instead."
    print("✅ No legacy 'emails' table found")


def test_no_email_entities_table():
    """Ensure the legacy 'email_entities' table does not exist."""
    db = SimpleDB()
    
    result = db.fetch_one("""
        SELECT COUNT(*) as count 
        FROM sqlite_master 
        WHERE type='table' AND name='email_entities'
    """)
    
    assert result['count'] == 0, "FATAL: Legacy 'email_entities' table exists! Use entity_content_mapping instead."
    print("✅ No legacy 'email_entities' table found")


def test_no_legacy_artifacts():
    """Ensure no backup or legacy tables remain."""
    db = SimpleDB()
    
    result = db.fetch("""
        SELECT name, type
        FROM sqlite_master 
        WHERE (name LIKE '%legacy%' OR name LIKE '%backup%')
        AND type IN ('table', 'view')
    """)
    
    if result:
        artifacts = [f"{r['type']}:{r['name']}" for r in result]
        assert False, f"FATAL: Legacy artifacts found: {artifacts}"
    
    print("✅ No legacy artifacts found")


def test_correct_source_types():
    """Ensure only correct source_type values are used."""
    db = SimpleDB()
    
    result = db.fetch("""
        SELECT DISTINCT source_type 
        FROM content_unified
        ORDER BY source_type
    """)
    
    valid_types = {'email_message', 'email_summary', 'document', 'document_chunk'}
    found_types = {r['source_type'] for r in result}
    
    invalid_types = found_types - valid_types
    assert not invalid_types, f"FATAL: Invalid source_types found: {invalid_types}"
    
    # Check for plural form (common mistake)
    assert 'email_messages' not in found_types, "FATAL: Found 'email_messages' (plural) - should be 'email_message'"
    
    print(f"✅ Valid source_types only: {found_types}")


def test_foreign_keys_enabled():
    """Ensure foreign keys are enabled."""
    db = SimpleDB()
    
    result = db.fetch_one("PRAGMA foreign_keys")
    assert result['foreign_keys'] == 1, "FATAL: Foreign keys are disabled!"
    
    print("✅ Foreign keys enabled")


def run_all_guards():
    """Run all guard tests."""
    print("\n" + "=" * 60)
    print("CI GUARD TESTS - PREVENTING LEGACY REGRESSION")
    print("=" * 60)
    
    tests = [
        test_no_emails_table,
        test_no_email_entities_table,
        test_no_legacy_artifacts,
        test_correct_source_types,
        test_foreign_keys_enabled,
    ]
    
    for test_func in tests:
        try:
            test_func()
        except AssertionError as e:
            print(f"\n❌ GUARD FAILED: {e}")
            return False
    
    print("\n" + "=" * 60)
    print("✅ ALL GUARDS PASSED - System is clean")
    print("=" * 60)
    return True


if __name__ == "__main__":
    success = run_all_guards()
    sys.exit(0 if success else 1)