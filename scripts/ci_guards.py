#!/usr/bin/env python3
"""
CI Guards for Chain Integrity

Prevents deployment/CI when critical data integrity issues exist.
Returns proper exit codes for CI systems.
"""

import sqlite3
import os
import sys
from pathlib import Path


def check_null_sha256(cursor):
    """Check for NULL SHA256 values"""
    cursor.execute("SELECT COUNT(*) FROM documents WHERE sha256 IS NULL")
    count = cursor.fetchone()[0]
    return count, f"Documents with NULL SHA256: {count}"


def check_duplicate_sha256(cursor):
    """Check for duplicate SHA256 values"""
    cursor.execute("""
        SELECT COUNT(*) FROM (
            SELECT sha256 FROM documents
            WHERE sha256 IS NOT NULL
            GROUP BY sha256
            HAVING COUNT(*) > 1
        )
    """)
    count = cursor.fetchone()[0]
    return count, f"Duplicate SHA256 keys: {count}"


def check_broken_chain(cursor):
    """Check for broken document → content chain"""
    # Only check first chunks (chunk_index=0) for chunked documents
    cursor.execute("""
        SELECT COUNT(*) 
        FROM documents d 
        LEFT JOIN content_unified c ON d.sha256 = c.sha256 
        WHERE d.sha256 IS NOT NULL AND d.chunk_index = 0 AND c.id IS NULL
    """)
    docs_without_content = cursor.fetchone()[0]
    
    cursor.execute("""
        SELECT COUNT(*) 
        FROM content_unified c 
        LEFT JOIN documents d ON c.sha256 = d.sha256 
        WHERE c.sha256 IS NOT NULL AND d.sha256 IS NULL
    """)
    orphaned_content = cursor.fetchone()[0]
    
    total = docs_without_content + orphaned_content
    return total, f"Broken chain total: {total} (docs without content: {docs_without_content}, orphaned content: {orphaned_content})"


def main():
    """Main CI guard entry point"""
    
    db_path = os.getenv("APP_DB_PATH", "data/emails.db")
    
    if not Path(db_path).exists():
        print(f"❌ CI GUARD FAIL: Database not found: {db_path}")
        return 1
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Run all critical checks
        checks = [
            check_null_sha256(cursor),
            check_duplicate_sha256(cursor),
            check_broken_chain(cursor)
        ]
        
        # Evaluate results
        failures = []
        for count, message in checks:
            if count > 0:
                failures.append(message)
        
        conn.close()
        
        if failures:
            print("❌ CI GUARD FAIL: Critical data integrity issues detected")
            for failure in failures:
                print(f"   - {failure}")
            print("\nFix these issues before deployment:")
            print("   1. Run: python3 scripts/sha256_backfill_migration.py")
            print("   2. Run: python3 scripts/fix_duplicate_sha256.py")
            print("   3. Run: python3 scripts/verify_chain.py")
            return 2  # Critical failure
        else:
            print("✅ CI GUARD PASS: All data integrity checks passed")
            return 0  # Success
            
    except Exception as e:
        print(f"❌ CI GUARD ERROR: {e}")
        return 3  # System error


if __name__ == "__main__":
    exit(main())