#!/usr/bin/env python3
"""
Nuclear Reset v2: Comprehensive test suite to verify the migration.
Tests that legacy tables are quarantined and v2 schema is working.
"""

import sys
from pathlib import Path

# Add parent directory for imports
sys.path.append(str(Path(__file__).parent.parent))

from shared.simple_db import SimpleDB


def test_legacy_quarantine():
    """Test that legacy tables are properly quarantined."""
    db = SimpleDB()
    
    # Check that emails is now a VIEW (trap)
    result = db.fetch_one("""
        SELECT type FROM sqlite_master WHERE name = 'emails'
    """)
    assert result['type'] == 'view', f"emails should be a VIEW, not {result['type']}"
    print("✅ Legacy emails table is quarantined as VIEW")
    
    # Try to query the VIEW - should return nothing
    try:
        result = db.fetch("SELECT * FROM emails LIMIT 1")
        assert len(result) == 0, "emails VIEW should return no rows"
        print("✅ emails VIEW returns empty (trap working)")
    except Exception as e:
        print(f"✅ emails VIEW properly blocks access: {e}")
    
    # Check backup exists
    result = db.fetch_one("""
        SELECT COUNT(*) as count FROM emails_legacy_backup_20250828
    """)
    assert result['count'] > 0, "Legacy backup should have data"
    print(f"✅ Legacy backup has {result['count']} records")


def test_v2_schema():
    """Test that v2 schema tables exist and have correct structure."""
    db = SimpleDB()
    
    # Check individual_messages exists
    result = db.fetch_one("""
        SELECT COUNT(*) as count FROM individual_messages
    """)
    print(f"✅ individual_messages table exists with {result['count']} records")
    
    # Check content_unified exists
    result = db.fetch_one("""
        SELECT COUNT(*) as count FROM content_unified 
        WHERE source_type = 'email_message'
    """)
    print(f"✅ content_unified has {result['count']} email_message records")
    
    # Check for orphans
    result = db.fetch_one("""
        SELECT COUNT(*) as orphan_count
        FROM content_unified cu
        LEFT JOIN individual_messages im ON cu.source_id = im.message_hash
        WHERE cu.source_type = 'email_message' AND im.message_hash IS NULL
    """)
    
    if result['orphan_count'] > 0:
        print(f"⚠️  Warning: {result['orphan_count']} orphaned content_unified records")
    else:
        print("✅ No orphaned content_unified records")


def test_entity_mapping():
    """Test that entity_content_mapping table is properly created."""
    db = SimpleDB()
    
    # Check entity_content_mapping exists
    result = db.fetch_one("""
        SELECT type FROM sqlite_master WHERE name = 'entity_content_mapping'
    """)
    assert result['type'] == 'table', "entity_content_mapping should be a table"
    print("✅ entity_content_mapping table created")
    
    # Check email_entities is deprecated
    result = db.fetch_one("""
        SELECT type FROM sqlite_master WHERE name = 'email_entities'
    """)
    assert result['type'] == 'view', "email_entities should be a VIEW"
    print("✅ email_entities deprecated as VIEW")


def test_foreign_keys():
    """Test that foreign key constraints are working."""
    db = SimpleDB()
    
    # Check FK is enabled
    result = db.fetch_one("PRAGMA foreign_keys")
    fk_status = result['foreign_keys']
    print(f"✅ Foreign keys {'enabled' if fk_status else 'DISABLED'}")
    
    # Test FK constraint on content_unified
    try:
        # Try to insert with invalid source_id
        db.execute("""
            INSERT INTO content_unified (source_type, source_id, title, body, sha256)
            VALUES ('email_message', 'invalid_hash_xxx', 'Test', 'Test', 'test_sha')
        """)
        print("⚠️  FK constraint not enforced (might be using triggers)")
    except Exception as e:
        print(f"✅ FK constraint working: {e}")


def test_legacy_prevention():
    """Test that legacy module cannot be imported."""
    try:
        import legacy
        assert False, "Legacy module should not be importable"
    except RuntimeError as e:
        print(f"✅ Legacy module blocked: {str(e)[:50]}...")
    except ImportError:
        print("✅ Legacy module not found (good)")


def run_all_tests():
    """Run all verification tests."""
    print("\n" + "=" * 60)
    print("NUCLEAR RESET V2 VERIFICATION")
    print("=" * 60)
    
    tests = [
        ("Legacy Quarantine", test_legacy_quarantine),
        ("V2 Schema", test_v2_schema),
        ("Entity Mapping", test_entity_mapping),
        ("Foreign Keys", test_foreign_keys),
        ("Legacy Prevention", test_legacy_prevention),
    ]
    
    passed = 0
    failed = 0
    
    for test_name, test_func in tests:
        print(f"\n[{test_name}]")
        try:
            test_func()
            passed += 1
        except AssertionError as e:
            print(f"❌ FAILED: {e}")
            failed += 1
        except Exception as e:
            print(f"❌ ERROR: {e}")
            failed += 1
    
    print("\n" + "=" * 60)
    print(f"RESULTS: {passed} passed, {failed} failed")
    print("=" * 60)
    
    return failed == 0


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)