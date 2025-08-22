#!/usr/bin/env python3
"""
Fix remaining column reference issues after incomplete table migration.
Handles dictionary access patterns, SQL column names, and table references.
"""

import re
import shutil
from pathlib import Path
from typing import List, Tuple


def backup_file(filepath: Path) -> Path:
    """Create backup of file before modification."""
    backup_path = filepath.with_suffix(filepath.suffix + '.bak')
    shutil.copy2(filepath, backup_path)
    print(f"  ✅ Backed up: {filepath.name} -> {backup_path.name}")
    return backup_path

def fix_file_content(content: str, fixes: List[Tuple[str, str]]) -> str:
    """Apply fixes to file content."""
    modified = content
    for pattern, replacement in fixes:
        modified = re.sub(pattern, replacement, modified)
    return modified

def fix_process_embeddings():
    """Fix process_embeddings.py table and column references."""
    filepath = Path("tools/scripts/process_embeddings.py")
    
    if not filepath.exists():
        print(f"  ⚠️  {filepath} not found, skipping")
        return
    
    backup_file(filepath)
    
    with open(filepath, 'r') as f:
        content = f.read()
    
    fixes = [
        # Fix PRAGMA table_info to check correct table
        (r'PRAGMA table_info\(content\)', r'PRAGMA table_info(content_unified)'),
        # Fix ALTER TABLE to target correct table
        (r'ALTER TABLE content ADD', r'ALTER TABLE content_unified ADD'),
        # Fix SELECT statement column aliases
        (r'SELECT id, type as source_type, title, content\s+FROM content_unified', 
         r'SELECT id, source_type, title, body\n        FROM content_unified'),
    ]
    
    modified = fix_file_content(content, fixes)
    
    with open(filepath, 'w') as f:
        f.write(modified)
    
    print(f"  ✅ Fixed: {filepath}")

def fix_knowledge_graph_files():
    """Fix knowledge_graph module dictionary access patterns."""
    files_to_fix = [
        ("knowledge_graph/similarity_analyzer.py", [
            (r'\["content_unified"\]', r'["body"]'),
        ]),
        ("knowledge_graph/topic_clustering.py", [
            (r'\["content_unified"\]', r'["body"]'),
            (r'SELECT.*?,\s*content\s+FROM', r'SELECT *, body FROM'),
            (r'SELECT.*?content\s+FROM', r'SELECT * FROM'),
        ]),
    ]
    
    for filepath_str, fixes in files_to_fix:
        filepath = Path(filepath_str)
        
        if not filepath.exists():
            print(f"  ⚠️  {filepath} not found, skipping")
            continue
        
        backup_file(filepath)
        
        with open(filepath, 'r') as f:
            content = f.read()
        
        modified = fix_file_content(content, fixes)
        
        with open(filepath, 'w') as f:
            f.write(modified)
        
        print(f"  ✅ Fixed: {filepath}")

def fix_search_intelligence_files():
    """Fix search_intelligence module dictionary access patterns."""
    files_to_fix = [
        ("search_intelligence/duplicate_detector.py", [
            (r'\["content_unified"\]', r'["body"]'),
        ]),
        ("search_intelligence/similarity.py", [
            (r'\["content_unified"\]', r'["body"]'),
        ]),
    ]
    
    for filepath_str, fixes in files_to_fix:
        filepath = Path(filepath_str)
        
        if not filepath.exists():
            print(f"  ⚠️  {filepath} not found, skipping")
            continue
        
        backup_file(filepath)
        
        with open(filepath, 'r') as f:
            content = f.read()
        
        modified = fix_file_content(content, fixes)
        
        with open(filepath, 'w') as f:
            f.write(modified)
        
        print(f"  ✅ Fixed: {filepath}")

def fix_simple_db():
    """Fix SimpleDB to use content_unified table and correct columns."""
    filepath = Path("shared/simple_db.py")
    
    if not filepath.exists():
        print(f"  ⚠️  {filepath} not found, skipping")
        return
    
    backup_file(filepath)
    
    with open(filepath, 'r') as f:
        content = f.read()
    
    fixes = [
        # Fix get_content method to use content_unified
        (r'SELECT \* FROM content WHERE id = \?', 
         r'SELECT * FROM content_unified WHERE id = ?'),
        
        # Fix search_content method column references
        (r'\(title LIKE \? OR content LIKE \?\)', 
         r'(title LIKE ? OR body LIKE ?)'),
        
        # Fix content_type filter
        (r'content_type = \?', 
         r'source_type = ?'),
         
        # Fix ORDER BY clause
        (r'ORDER BY created_at DESC', 
         r'ORDER BY created_time DESC'),
    ]
    
    modified = fix_file_content(content, fixes)
    
    with open(filepath, 'w') as f:
        f.write(modified)
    
    print(f"  ✅ Fixed: {filepath}")

def validate_fixes():
    """Run quick validation to ensure fixes worked."""
    print("\n🔍 Validating fixes...")
    
    validation_passed = True
    
    # Check process_embeddings.py
    filepath = Path("tools/scripts/process_embeddings.py")
    if filepath.exists():
        with open(filepath, 'r') as f:
            content = f.read()
            if 'PRAGMA table_info(content)' in content:
                print("  ❌ process_embeddings.py still has wrong PRAGMA")
                validation_passed = False
            else:
                print("  ✅ process_embeddings.py PRAGMA fixed")
    
    # Check SimpleDB
    filepath = Path("shared/simple_db.py")
    if filepath.exists():
        with open(filepath, 'r') as f:
            content = f.read()
            if 'FROM content WHERE' in content:
                print("  ❌ SimpleDB still queries old table")
                validation_passed = False
            else:
                print("  ✅ SimpleDB table reference fixed")
    
    # Check for remaining content_unified dictionary access
    kg_files = list(Path("knowledge_graph").glob("*.py"))
    remaining_issues = []
    
    for filepath in kg_files:
        with open(filepath, 'r') as f:
            if '["content_unified"]' in f.read():
                remaining_issues.append(filepath.name)
    
    if remaining_issues:
        print(f"  ❌ Files still have ['content_unified']: {', '.join(remaining_issues)}")
        validation_passed = False
    else:
        print("  ✅ Knowledge graph dictionary access fixed")
    
    return validation_passed

def main():
    """Main execution function."""
    print("🔧 Column Reference Migration Fix")
    print("=" * 50)
    
    print("\n📝 Fixing table and column references...")
    
    # Phase 1: Fix process_embeddings.py
    print("\n1️⃣ Fixing process_embeddings.py...")
    fix_process_embeddings()
    
    # Phase 2: Fix knowledge_graph modules
    print("\n2️⃣ Fixing knowledge_graph modules...")
    fix_knowledge_graph_files()
    
    # Phase 3: Fix search_intelligence modules
    print("\n3️⃣ Fixing search_intelligence modules...")
    fix_search_intelligence_files()
    
    # Phase 4: Fix SimpleDB
    print("\n4️⃣ Fixing SimpleDB...")
    fix_simple_db()
    
    # Phase 5: Validate
    if validate_fixes():
        print("\n✅ All fixes completed successfully!")
        print("\n💡 Next steps:")
        print("  1. Test embedding generation: python3 tools/scripts/process_embeddings.py")
        print("  2. Test search: tools/scripts/vsearch search 'test query'")
        print("  3. Test knowledge graph: python3 -c 'from knowledge_graph import get_similarity_analyzer'")
        print("  4. Update CHANGELOG.md with these fixes")
    else:
        print("\n⚠️  Some issues remain. Review the validation output above.")
        print("Backup files created with .bak extension if you need to rollback.")

if __name__ == "__main__":
    main()