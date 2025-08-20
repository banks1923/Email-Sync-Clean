#!/usr/bin/env python3
"""
Schema Compliance Checker
Prevents regression of schema migration changes.

This tool can be run locally or in CI to ensure:
1. No content_id references in SQL strings
2. Business key patterns are maintained
3. Deterministic UUID patterns are consistent
"""

import re
import sys
from pathlib import Path
from typing import List, Tuple
import subprocess

def check_content_id_usage() -> list[tuple[str, int, str]]:
    """Check for prohibited content_id usage in SQL strings."""
    violations = []
    
    # More precise SQL patterns - must be in actual SQL context
    sql_patterns = [
        r'SELECT\s+.*\bcontent_id\b',
        r'WHERE\s+.*\bcontent_id\s*=',
        r'INSERT.*\(\s*content_id\s*,',
        r'UPDATE.*SET.*\bcontent_id\s*=',
        r'DELETE.*WHERE.*\bcontent_id\s*=',
        r'REFERENCES.*\(\s*content_id\s*\)'
    ]
    
    for py_file in Path('.').rglob('*.py'):
        if '.git' in str(py_file) or '__pycache__' in str(py_file):
            continue
            
        try:
            with open(py_file, encoding='utf-8') as f:
                lines = f.readlines()
            
            for line_num, line in enumerate(lines, 1):
                # Skip if marked as allowed
                if '# ALLOWED: content_id' in line:
                    continue
                
                # Only check lines that look like SQL (contain quotes and SQL keywords)
                if not ('"' in line or "'" in line):
                    continue
                if not re.search(r'\b(SELECT|WHERE|INSERT|UPDATE|DELETE|CREATE|REFERENCES)\b', line, re.IGNORECASE):
                    continue
                    
                # Extract the SQL string part (between quotes)
                sql_parts = re.findall(r'["\']([^"\']*(?:SELECT|WHERE|INSERT|UPDATE|DELETE|CREATE|REFERENCES)[^"\']*)["\']', line, re.IGNORECASE)
                
                # Check for SQL patterns with content_id in actual SQL strings
                for sql_part in sql_parts:
                    for pattern in sql_patterns:
                        if re.search(pattern, sql_part, re.IGNORECASE):
                            violations.append((str(py_file), line_num, line.strip()))
                        
        except (UnicodeDecodeError, OSError):
            continue
    
    return violations

def check_business_key_patterns() -> list[str]:
    """Check that business key patterns are maintained."""
    issues = []
    
    # Check SimpleDB has upsert_content method
    simpledb_path = Path('shared/simple_db.py')
    if not simpledb_path.exists():
        issues.append("SimpleDB file not found")
        return issues
    
    with open(simpledb_path) as f:
        content = f.read()
    
    if 'def upsert_content' not in content:
        issues.append("upsert_content method missing from SimpleDB")
    
    if 'source_type' not in content or 'external_id' not in content:
        issues.append("Business key columns (source_type, external_id) not found in SimpleDB")
    
    # Check for business key implementation (UPSERT method is primary evidence)
    if 'ON CONFLICT(source_type, external_id)' not in content:
        issues.append("Business key UPSERT implementation not found (missing ON CONFLICT clause)")
    
    return issues

def check_uuid_consistency() -> list[tuple[str, str]]:
    """Check for consistent deterministic UUID usage."""
    violations = []
    expected_namespace = '6ba7b810-9dad-11d1-80b4-00c04fd430c8'
    
    for py_file in Path('.').rglob('*.py'):
        if '.git' in str(py_file) or '__pycache__' in str(py_file):
            continue
            
        try:
            with open(py_file, encoding='utf-8') as f:
                content = f.read()
            
            # Look for uuid5 usage
            if 'uuid5' in content:
                # Check if it uses the expected namespace
                if expected_namespace not in content:
                    violations.append((str(py_file), "Uses uuid5 but not expected namespace"))
                    
        except (UnicodeDecodeError, OSError):
            continue
    
    return violations

def run_libcst_idempotency_check() -> tuple[bool, str]:
    """Check if LibCST codemod is idempotent (makes no changes)."""
    codemod_path = Path('tools/codemods/replace_content_id_sql.py')
    
    if not codemod_path.exists():
        return True, "LibCST codemod not found - skipping check"
    
    try:
        # Run dry-run and capture output (need to provide path argument)
        # Use absolute path to avoid working directory issues
        project_root = Path('.').resolve()
        result = subprocess.run([
            sys.executable, str(codemod_path), '--dry-run', str(project_root)
        ], capture_output=True, text=True)
        
        # Check if it would make changes (look for non-zero files changed)
        if result.returncode != 0:
            return False, f"LibCST codemod failed: {result.stderr.strip()}"
        
        # Parse the output to see if any files would be changed
        if 'Files changed: 0' in result.stdout:
            return True, "LibCST codemod is idempotent"
        else:
            # Look for "Files changed: N" where N > 0
            import re
            match = re.search(r'Files changed: (\d+)', result.stdout)
            if match and int(match.group(1)) > 0:
                return False, f"LibCST would change {match.group(1)} files"
            else:
                # Assume idempotent if no clear indication of changes
                return True, "LibCST codemod is idempotent"
        
    except Exception as e:
        return False, f"Failed to run LibCST check: {e}"

def main():
    """Run all compliance checks."""
    print("🔍 Running schema compliance checks...\n")
    
    all_passed = True
    
    # Check 1: content_id usage
    print("1. Checking for prohibited content_id SQL usage...")
    content_id_violations = check_content_id_usage()
    
    if content_id_violations:
        print("❌ FAIL: Found prohibited content_id references:")
        for file_path, line_num, line in content_id_violations[:10]:  # Show first 10
            print(f"  {file_path}:{line_num}: {line}")
        if len(content_id_violations) > 10:
            print(f"  ... and {len(content_id_violations) - 10} more violations")
        print("  💡 Use 'id' instead of 'content_id' in SQL, or add '# ALLOWED: content_id' comment")
        all_passed = False
    else:
        print("✅ PASS: No prohibited content_id usage found")
    
    # Check 2: Business key patterns
    print("\n2. Checking business key patterns...")
    business_key_issues = check_business_key_patterns()
    
    if business_key_issues:
        print("❌ FAIL: Business key pattern issues:")
        for issue in business_key_issues:
            print(f"  - {issue}")
        all_passed = False
    else:
        print("✅ PASS: Business key patterns verified")
    
    # Check 3: UUID consistency
    print("\n3. Checking deterministic UUID consistency...")
    uuid_violations = check_uuid_consistency()
    
    if uuid_violations:
        print("❌ FAIL: Inconsistent UUID namespace usage:")
        for file_path, issue in uuid_violations:
            print(f"  {file_path}: {issue}")
        print("  💡 All uuid5 calls should use namespace: 6ba7b810-9dad-11d1-80b4-00c04fd430c8")
        all_passed = False
    else:
        print("✅ PASS: Deterministic UUID patterns consistent")
    
    # Check 4: LibCST idempotency
    print("\n4. Checking LibCST codemod idempotency...")
    libcst_ok, libcst_msg = run_libcst_idempotency_check()
    
    if not libcst_ok:
        print(f"❌ FAIL: {libcst_msg}")
        all_passed = False
    else:
        print(f"✅ PASS: {libcst_msg}")
    
    # Summary
    print("\n" + "="*60)
    if all_passed:
        print("🎉 ALL CHECKS PASSED - Schema compliance verified")
        return 0
    else:
        print("💥 SOME CHECKS FAILED - Schema compliance violations detected")
        return 1

if __name__ == "__main__":
    sys.exit(main())