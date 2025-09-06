#!/usr/bin/env python3
"""
Validate import depth enforcement for the codebase.

This script scans Python files for imports that violate the two-level import rule.
Exit code 0 = success, 1 = violations found.
"""

import ast
import sys
from pathlib import Path
from typing import List, Tuple

# Packages that must use two-level imports
ENFORCED_PACKAGES = ["lib", "services", "infrastructure", "gmail"]

# Files/paths to exclude from validation
EXCLUDED_PATHS = [
    "__pycache__",
    ".venv",
    "venv",
    ".git",
    "build",
    "dist",
    ".cache",
    "logs",
    "qdrant_data",
]


def is_deep_import(import_path: str, file_path: Path) -> Tuple[bool, bool]:
    """Check if an import violates the two-level rule.
    
    Returns:
        (is_violation, is_internal): Whether it's a violation and if it's internal
    """
    parts = import_path.split(".")
    
    # Check if it's from one of our enforced packages
    if not parts or parts[0] not in ENFORCED_PACKAGES:
        return False, False
    
    # Check if it's more than 2 levels deep
    if len(parts) <= 2:
        return False, False
    
    # Check if it's an internal import (within the same package)
    file_parts = str(file_path).split("/")
    
    # For files in services/pdf/*, allow imports from services.pdf.*
    # For files in services/cli/*, allow imports from services.cli.*
    # For files in gmail/*, allow imports from gmail.*
    # etc.
    is_internal = False
    if len(file_parts) >= 2:
        # Get the package path from the file location
        for i, part in enumerate(file_parts):
            if part in ENFORCED_PACKAGES:
                # The file is in this package
                file_package = part
                
                # Check if the import is from the same top-level package
                import_package = parts[0]
                if import_package == file_package:
                    is_internal = True
                    break
    
    return True, is_internal


def extract_imports(file_path: Path) -> List[Tuple[int, str]]:
    """Extract all import statements from a Python file."""
    imports = []
    
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            tree = ast.parse(f.read(), filename=str(file_path))
    except (SyntaxError, UnicodeDecodeError):
        # Skip files with syntax errors or encoding issues
        return imports
    
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imports.append((node.lineno, alias.name))
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                imports.append((node.lineno, node.module))
    
    return imports


def should_exclude(path: Path) -> bool:
    """Check if a path should be excluded from validation."""
    path_str = str(path)
    for excluded in EXCLUDED_PATHS:
        if excluded in path_str:
            return True
    return False


def validate_file(file_path: Path) -> Tuple[List[str], int]:
    """Validate imports in a single file.
    
    Returns:
        (violations, internal_count): List of violations and count of allowed internal imports
    """
    violations = []
    internal_count = 0
    imports = extract_imports(file_path)
    
    for line_num, import_path in imports:
        is_violation, is_internal = is_deep_import(import_path, file_path)
        if is_violation:
            if is_internal:
                # Internal imports are allowed
                internal_count += 1
            else:
                violations.append(
                    f"{file_path}:{line_num} - Deep import violation: '{import_path}'"
                )
    
    return violations, internal_count


def main():
    """Main validation function."""
    project_root = Path.cwd()
    all_violations = []
    total_internal = 0
    
    # Find all Python files
    python_files = []
    for py_file in project_root.rglob("*.py"):
        if not should_exclude(py_file):
            python_files.append(py_file)
    
    print(f"Checking {len(python_files)} Python files for import violations...")
    
    # Validate each file
    for py_file in python_files:
        violations, internal_count = validate_file(py_file)
        all_violations.extend(violations)
        total_internal += internal_count
    
    # Report results
    if all_violations:
        print(f"\n❌ Found {len(all_violations)} import violation(s):\n")
        for violation in all_violations:
            print(f"  {violation}")
        print("\nFix these violations by using the public API exports from package __init__.py files.")
        print("Example: Instead of 'from lib.db import SimpleDB', use 'from lib import SimpleDB'")
        return 1
    else:
        print(f"✅ All imports are valid! No deep imports found.")
        if total_internal > 0:
            print(f"   ({total_internal} internal imports allowed within packages)")
        return 0


if __name__ == "__main__":
    sys.exit(main())