#!/usr/bin/env python3
"""
LibCST-based codemod to safely replace content_id with id in SQL string literals.

This transformer:
1. Only targets SQL string literals (not Python identifiers)
2. Preserves formatting and comments
3. Handles multiline SQL, f-strings, and aliases
4. Is idempotent and testable

Usage:
    python tools/codemods/replace_content_id_sql.py --dry-run .
    python tools/codemods/replace_content_id_sql.py --apply .
"""

import argparse
import re
import sys
from pathlib import Path

import libcst as cst
from libcst import RemovalSentinel

# SQL patterns to replace content_id with id
SQL_PATTERNS = [
    # SELECT statements
    (re.compile(r"\bSELECT\s+content_id\b", re.IGNORECASE), "SELECT id"),
    (re.compile(r"\bSELECT\s+(.*?),\s*content_id\b", re.IGNORECASE), r"SELECT \1, id"),
    (re.compile(r"\bSELECT\s+content_id\s*,", re.IGNORECASE), "SELECT id,"),
    
    # WHERE clauses
    (re.compile(r"\bWHERE\s+content_id\s*=\s*\?", re.IGNORECASE), "WHERE id = ?"),
    (re.compile(r"\bAND\s+content_id\s*=\s*\?", re.IGNORECASE), "AND id = ?"),
    (re.compile(r"\bOR\s+content_id\s*=\s*\?", re.IGNORECASE), "OR id = ?"),
    
    # DELETE statements
    (re.compile(r"\bDELETE\s+FROM\s+content\s+WHERE\s+content_id\s*=\s*\?", re.IGNORECASE), 
     "DELETE FROM content WHERE id = ?"),
    
    # Aliased column references
    (re.compile(r"\bcontent\.content_id\b", re.IGNORECASE), "content.id"),
    (re.compile(r"\bc\.content_id\b", re.IGNORECASE), "c.id"),
    (re.compile(r"\b([A-Za-z_]\w*)\.content_id\b", re.IGNORECASE), r"\1.id"),
    
    # INSERT statements
    (re.compile(r"INSERT\s+OR\s+IGNORE\s+INTO\s+content\s*\(\s*content_id\s*,", re.IGNORECASE),
     "INSERT OR IGNORE INTO content (id,"),
    (re.compile(r"INSERT\s+INTO\s+content\s*\(\s*content_id\s*,", re.IGNORECASE),
     "INSERT INTO content (id,"),
    (re.compile(r"\(\s*content_id\s*,", re.IGNORECASE), "(id,"),
    
    # UPDATE statements  
    (re.compile(r"UPDATE\s+content\s+SET\s+(.*?)\s+WHERE\s+content_id\s*=\s*\?", re.IGNORECASE | re.DOTALL),
     r"UPDATE content SET \1 WHERE id = ?"),
    
    # Foreign key references
    (re.compile(r"REFERENCES\s+content\s*\(\s*content_id\s*\)", re.IGNORECASE), 
     "REFERENCES content(id)"),
    (re.compile(r"FOREIGN\s+KEY\s*\(\s*content_id\s*\)", re.IGNORECASE),
     "FOREIGN KEY (id)"),
    
    # Column definitions in CREATE TABLE
    (re.compile(r"content_id\s+TEXT\s+PRIMARY\s+KEY", re.IGNORECASE), "id TEXT PRIMARY KEY"),
    (re.compile(r"content_id\s+TEXT\s+NOT\s+NULL", re.IGNORECASE), "id TEXT NOT NULL"),
    
    # Common column lists
    (re.compile(r'"content_id"\s*,\s*"content_type"', re.IGNORECASE), '"id", "content_type"'),
    (re.compile(r"'content_id'\s*,\s*'content_type'", re.IGNORECASE), "'id', 'content_type'"),
]

# Pattern to identify SQL strings (heuristic)
SQL_MARKERS = re.compile(r"\b(SELECT|INSERT|UPDATE|DELETE|CREATE\s+TABLE|ALTER\s+TABLE|DROP\s+TABLE|REFERENCES|FOREIGN\s+KEY|PRIMARY\s+KEY)\b", re.IGNORECASE)


class SqlStringRewriter(cst.CSTTransformer):
    """Transforms SQL string literals to replace content_id with id."""
    
    def __init__(self):
        self.changes_made = 0
        self.files_changed = 0
    
    def _is_sql_string(self, content: str) -> bool:
        """Heuristic to identify SQL strings."""
        return bool(SQL_MARKERS.search(content))
    
    def _rewrite_sql(self, content: str) -> str:
        """Apply all SQL transformations to the string content."""
        if not self._is_sql_string(content):
            return content
            
        original = content
        result = content
        
        for pattern, replacement in SQL_PATTERNS:
            new_result = pattern.sub(replacement, result)
            if new_result != result:
                result = new_result
                
        if result != original:
            self.changes_made += 1
            
        return result
    
    def leave_SimpleString(
        self, original_node: cst.SimpleString, updated_node: cst.SimpleString
    ) -> cst.SimpleString | RemovalSentinel:
        """Transform simple string literals containing SQL."""
        raw_value = updated_node.value
        
        # Handle different quote styles
        if raw_value.startswith('"""') or raw_value.startswith("'''"):
            # Triple-quoted string
            quote_chars = raw_value[:3]
            content = raw_value[3:-3]
            new_content = self._rewrite_sql(content)
            if new_content != content:
                return updated_node.with_changes(value=quote_chars + new_content + quote_chars)
        elif raw_value.startswith('"') or raw_value.startswith("'"):
            # Single or double quoted string
            quote_char = raw_value[0]
            content = raw_value[1:-1]
            new_content = self._rewrite_sql(content)
            if new_content != content:
                return updated_node.with_changes(value=quote_char + new_content + quote_char)
        
        return updated_node
    
    def leave_FormattedString(
        self, original_node: cst.FormattedString, updated_node: cst.FormattedString
    ) -> cst.FormattedString | RemovalSentinel:
        """Transform f-string literals containing SQL (only the literal parts)."""
        new_parts = []
        changed = False
        
        for part in updated_node.parts:
            if isinstance(part, cst.FormattedStringText):
                # Only transform literal text parts, not expressions
                original_value = part.value
                new_value = self._rewrite_sql(original_value)
                if new_value != original_value:
                    new_parts.append(part.with_changes(value=new_value))
                    changed = True
                else:
                    new_parts.append(part)
            else:
                # Keep expressions unchanged
                new_parts.append(part)
        
        if changed:
            return updated_node.with_changes(parts=new_parts)
        
        return updated_node


def transform_file(file_path: Path, dry_run: bool = True) -> tuple[bool, str]:
    """
    Transform a single Python file.
    
    Returns:
        (changed, diff_text)
    """
    try:
        original_code = file_path.read_text(encoding='utf-8')
    except UnicodeDecodeError:
        return False, f"Skipping {file_path}: not a text file"
    except Exception as e:
        return False, f"Error reading {file_path}: {e}"
    
    try:
        # Parse the module
        module = cst.parse_module(original_code)
        
        # Apply the transformer
        transformer = SqlStringRewriter()
        new_module = module.visit(transformer)
        new_code = new_module.code
        
        # Check if changes were made
        if new_code != original_code and transformer.changes_made > 0:
            if not dry_run:
                # Write the changes
                file_path.write_text(new_code, encoding='utf-8')
            
            # Generate diff for reporting
            import difflib
            diff_lines = list(difflib.unified_diff(
                original_code.splitlines(keepends=True),
                new_code.splitlines(keepends=True),
                fromfile=str(file_path),
                tofile=str(file_path),
                lineterm=''
            ))
            diff_text = ''.join(diff_lines)
            
            return True, diff_text
        
        return False, ""
        
    except Exception as e:
        return False, f"Error processing {file_path}: {e}"


def find_python_files(paths: list[Path]) -> list[Path]:
    """Find all Python files in the given paths."""
    python_files = []
    
    for path in paths:
        if path.is_file() and path.suffix == '.py':
            python_files.append(path)
        elif path.is_dir():
            # Recursively find Python files, excluding common non-source directories
            exclude_dirs = {'venv', '.venv', 'env', '.env', 'site-packages', '__pycache__', 
                          '.git', 'node_modules', '.pytest_cache', '.mypy_cache'}
            
            for py_file in path.rglob("*.py"):
                # Skip files in excluded directories
                if not any(excluded in py_file.parts for excluded in exclude_dirs):
                    python_files.append(py_file)
    
    return sorted(python_files)


def main():
    """Main entry point for the codemod."""
    parser = argparse.ArgumentParser(
        description="Replace content_id with id in SQL string literals using LibCST",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    # Dry run on current directory
    python tools/codemods/replace_content_id_sql.py --dry-run .
    
    # Apply changes to specific files
    python tools/codemods/replace_content_id_sql.py --apply shared/simple_db.py
    
    # Apply changes to entire project
    python tools/codemods/replace_content_id_sql.py --apply .
        """
    )
    
    parser.add_argument(
        'paths', nargs='+', type=Path,
        help='Python files or directories to process'
    )
    
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument(
        '--dry-run', action='store_true',
        help='Show what would be changed without modifying files'
    )
    group.add_argument(
        '--apply', action='store_true', 
        help='Apply the changes to files'
    )
    
    parser.add_argument(
        '--verbose', '-v', action='store_true',
        help='Show verbose output including unchanged files'
    )
    
    args = parser.parse_args()
    
    # Find all Python files to process
    python_files = find_python_files(args.paths)
    
    if not python_files:
        print("No Python files found to process")
        return 0
    
    print(f"Processing {len(python_files)} Python files...")
    if args.dry_run:
        print("DRY RUN MODE - no files will be modified\n")
    
    files_changed = 0
    total_changes = 0
    
    for file_path in python_files:
        changed, result = transform_file(file_path, dry_run=args.dry_run)
        
        if changed:
            files_changed += 1
            changes_count = result.count('\n-') if result else 0
            total_changes += changes_count
            
            print(f"{'[DRY RUN] ' if args.dry_run else ''}CHANGED: {file_path}")
            if args.verbose or args.dry_run:
                print(result)
                print("-" * 80)
        elif args.verbose:
            print(f"UNCHANGED: {file_path}")
        elif result and "Error" in result:
            print(f"ERROR: {result}")
    
    # Summary
    print("\nSummary:")
    print(f"  Files processed: {len(python_files)}")
    print(f"  Files changed: {files_changed}")
    print(f"  Total changes: {total_changes}")
    
    if args.dry_run and files_changed > 0:
        print("\nTo apply these changes, run with --apply instead of --dry-run")
    
    # Return non-zero exit code if changes were found (useful for CI)
    return 1 if files_changed > 0 and args.dry_run else 0


if __name__ == "__main__":
    sys.exit(main())