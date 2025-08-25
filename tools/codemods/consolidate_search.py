#!/usr/bin/env python3
"""
Consolidate search/ into search_intelligence/ using LibCST transformations.
"""

import shutil
from pathlib import Path


def update_imports_in_file(file_path: Path, old_import: str, new_import: str):
    """
    Update import statements in a file.
    """

    try:
        with open(file_path) as f:
            content = f.read()

        if old_import not in content:
            return False

        updated_content = content.replace(old_import, new_import)

        with open(file_path, "w") as f:
            f.write(updated_content)

        return True

    except Exception as e:
        print(f"❌ Error updating {file_path}: {e}")
        return False


def consolidate_search():
    """
    Consolidate search directories.
    """

    print("🔀 Consolidating search directories")
    print("=" * 50)

    # Step 1: Move search/main.py to search_intelligence/basic_search.py
    source = Path("search/main.py")
    dest = Path("search_intelligence/basic_search.py")

    if source.exists():
        print(f"📁 Moving {source} → {dest}")
        shutil.move(source, dest)
    else:
        print(f"⚠️ {source} not found, skipping move")

    # Step 2: Update search_intelligence/__init__.py to export both
    init_file = Path("search_intelligence/__init__.py")
    if init_file.exists():
        with open(init_file) as f:
            content = f.read()

        # Add basic_search import
        if (
            "from .basic_search from search_intelligence import basic_search as search"
            not in content
        ):
            content += "\n# Basic search functionality\nfrom .basic_search from search_intelligence import basic_search as search as basic_search\n"

        with open(init_file, "w") as f:
            f.write(content)

        print("✅ Updated search_intelligence/__init__.py")

    # Step 3: Find and update import references
    import_updates = [
        (
            "from search_intelligence.basic_search from search_intelligence import basic_search as search",
            "from search_intelligence.basic_search from search_intelligence import basic_search as search",
        ),
        (
            "from search_intelligence.basic_search from search_intelligence import basic_search as search",
            "from search_intelligence.basic_search from search_intelligence import basic_search as search",
        ),
        (
            "from search_intelligence import basic_search as search",
            "from search_intelligence import basic_search as search",
        ),
    ]

    # Find Python files that might from search_intelligence import basic_search as search
    python_files = list(Path(".").rglob("*.py"))
    updated_files = []

    for py_file in python_files:
        if "search" in str(py_file) or "test" in str(py_file) or "tools" in str(py_file):
            for old_import, new_import in import_updates:
                if update_imports_in_file(py_file, old_import, new_import):
                    updated_files.append(str(py_file))

    if updated_files:
        print(f"🔧 Updated imports in {len(set(updated_files))} files:")
        for file in set(updated_files):
            print(f"   - {file}")

    # Step 4: Remove empty search directory
    search_dir = Path("search")
    if search_dir.exists():
        remaining_files = list(search_dir.rglob("*"))
        if len(remaining_files) <= 2:  # Only __pycache__ and __init__.py
            print("🗑️ Removing empty search directory")
            shutil.rmtree(search_dir)
        else:
            print(f"⚠️ search directory still has files: {[f.name for f in remaining_files]}")

    print("\n✨ Search consolidation complete!")
    print("   - search/main.py → search_intelligence/basic_search.py")
    print("   - Updated imports in affected files")
    print("   - Removed empty search/ directory")


if __name__ == "__main__":
    consolidate_search()
