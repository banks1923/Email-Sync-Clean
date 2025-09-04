#!/usr/bin/env python3
"""LibCST codemod to migrate src/ imports to infrastructure/documents/.

This codemod updates all imports from:
- src.chunker.* -> infrastructure.documents.chunker.*
- src.quality.* -> infrastructure.documents.quality.*

Usage:
    python tools/codemods/migrate_src_imports.py --apply .
"""

import argparse
import sys
from pathlib import Path
from typing import Sequence

import libcst as cst


class MigrateSrcImports(cst.CSTTransformer):
    """Migrate imports from src/ to infrastructure/documents/."""

    def __init__(self):
        self.changes_made = 0

    def leave_Import(self, original_node: cst.Import, updated_node: cst.Import) -> cst.Import:
        """Transform regular import statements."""
        return updated_node

    def leave_ImportFrom(self, original_node: cst.ImportFrom, updated_node: cst.ImportFrom) -> cst.ImportFrom:
        """Transform from...import statements."""
        if updated_node.module is None:
            return updated_node
            
        # Build the module path string
        module_parts = self._get_module_parts(updated_node.module)
        module_str = ".".join(module_parts)
        
        # Check if this is a src import we need to update
        new_module_str = None
        
        if module_str.startswith("src.chunker"):
            new_module_str = module_str.replace("src.chunker", "infrastructure.documents.chunker")
        elif module_str.startswith("src.quality"):
            new_module_str = module_str.replace("src.quality", "infrastructure.documents.quality")
        
        if new_module_str:
            # Build new module node
            new_module = self._build_module_node(new_module_str)
            self.changes_made += 1
            return updated_node.with_changes(module=new_module)
        
        return updated_node

    def _get_module_parts(self, module: cst.BaseExpression) -> list[str]:
        """Extract module parts from an Attribute or Name node."""
        parts = []
        current = module
        
        while isinstance(current, cst.Attribute):
            parts.insert(0, current.attr.value)
            current = current.value
            
        if isinstance(current, cst.Name):
            parts.insert(0, current.value)
            
        return parts

    def _build_module_node(self, module_str: str) -> cst.BaseExpression:
        """Build a module node from a dotted string."""
        parts = module_str.split(".")
        
        if len(parts) == 1:
            return cst.Name(parts[0])
        
        # Build from left to right
        node = cst.Name(parts[0])
        for part in parts[1:]:
            node = cst.Attribute(value=node, attr=cst.Name(part))
        
        return node


def transform_file(file_path: Path, dry_run: bool = True) -> tuple[bool, str]:
    """Transform a single Python file.
    
    Returns:
        (changed, diff_text)
    """
    try:
        original_code = file_path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return False, f"Skipping {file_path}: not a text file"
    except Exception as e:
        return False, f"Error reading {file_path}: {e}"

    try:
        # Parse the module
        module = cst.parse_module(original_code)
        
        # Apply transformer
        transformer = MigrateSrcImports()
        new_module = module.visit(transformer)
        new_code = new_module.code
        
        # Check if changes were made
        if new_code != original_code:
            if not dry_run:
                # Write the changes
                file_path.write_text(new_code, encoding="utf-8")
            
            # Generate diff for reporting
            import difflib
            diff_lines = list(
                difflib.unified_diff(
                    original_code.splitlines(keepends=True),
                    new_code.splitlines(keepends=True),
                    fromfile=str(file_path),
                    tofile=str(file_path),
                    lineterm="",
                )
            )
            diff_text = "".join(diff_lines)
            
            return True, diff_text
        
        return False, ""
        
    except Exception as e:
        return False, f"Error processing {file_path}: {e}"


def find_python_files(paths: list[Path]) -> list[Path]:
    """Find all Python files in the given paths."""
    python_files = []
    
    for path in paths:
        if path.is_file() and path.suffix == ".py":
            python_files.append(path)
        elif path.is_dir():
            # Recursively find Python files, excluding common non-source directories
            exclude_dirs = {
                "venv", ".venv", "env", ".env",
                "site-packages", "__pycache__", ".git",
                "node_modules", ".pytest_cache", ".mypy_cache"
            }
            
            for py_file in path.rglob("*.py"):
                # Skip files in excluded directories
                if not any(excluded in py_file.parts for excluded in exclude_dirs):
                    python_files.append(py_file)
    
    return sorted(python_files)


def main():
    """Main entry point for the codemod."""
    parser = argparse.ArgumentParser(
        description="Migrate src/ imports to infrastructure/documents/",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    
    parser.add_argument(
        "paths", nargs="+", type=Path,
        help="Python files or directories to process"
    )
    
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument(
        "--dry-run", action="store_true",
        help="Show what would be changed without modifying files"
    )
    group.add_argument(
        "--apply", action="store_true",
        help="Apply the changes to files"
    )
    
    parser.add_argument(
        "--verbose", "-v", action="store_true",
        help="Show verbose output including unchanged files"
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
    
    for file_path in python_files:
        changed, result = transform_file(file_path, dry_run=args.dry_run)
        
        if changed:
            files_changed += 1
            print(f"{'[DRY RUN] ' if args.dry_run else ''}CHANGED: {file_path}")
            if args.verbose or args.dry_run:
                print(result)
                print("-" * 80)
        elif args.verbose:
            if result and "Error" in result:
                print(f"ERROR: {result}")
            else:
                print(f"UNCHANGED: {file_path}")
    
    # Summary
    print("\nSummary:")
    print(f"  Files processed: {len(python_files)}")
    print(f"  Files changed: {files_changed}")
    
    if args.dry_run and files_changed > 0:
        print("\nTo apply these changes, run with --apply instead of --dry-run")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())