#!/usr/bin/env python3
"""
Analyze imports and table references after migration.
Shows which modules depend on content_unified table.
"""

import ast
import re
from pathlib import Path


def analyze_file(filepath):
    """Analyze a Python file for imports and table references."""
    with open(filepath) as f:
        content = f.read()
    
    # Check for table references
    tables = {
        'content_unified': len(re.findall(r'content_unified', content)),
        'content_table': len(re.findall(r'FROM content[^_]', content)),
        'body_column': len(re.findall(r'\["body"\]', content)),
        'content_column': len(re.findall(r'\["content"\]', content)),
    }
    
    # Parse imports
    imports = []
    try:
        tree = ast.parse(content)
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom):
                if node.module:
                    imports.append(node.module)
    except:
        pass
    
    return {
        'imports': imports,
        'tables': tables,
        'has_simpledb': 'simple_db' in content or 'SimpleDB' in content
    }

def main():
    # Key directories to analyze
    dirs_to_check = [
        'shared',
        'knowledge_graph', 
        'search_intelligence',
        'gmail',
        'pdf',
        'utilities',
        'tools/scripts'
    ]
    
    results = {}
    
    for dir_path in dirs_to_check:
        if not Path(dir_path).exists():
            continue
            
        for py_file in Path(dir_path).glob('**/*.py'):
            if '__pycache__' in str(py_file) or 'test_' in py_file.name:
                continue
                
            analysis = analyze_file(py_file)
            
            # Only include files with relevant references
            if (analysis['tables']['content_unified'] > 0 or 
                analysis['tables']['content_table'] > 0 or
                analysis['has_simpledb']):
                
                rel_path = str(py_file).replace('/Users/jim/Projects/Email-Sync-Clean-Backup/', '')
                results[rel_path] = analysis
    
    # Print report
    print("=" * 60)
    print("IMPORT & TABLE REFERENCE ANALYSIS")
    print("=" * 60)
    
    # Files still referencing old 'content' table
    print("\n❌ Files with OLD 'content' table references:")
    old_refs = []
    for filepath, data in results.items():
        if data['tables']['content_table'] > 0:
            old_refs.append(f"  - {filepath}: {data['tables']['content_table']} references")
    
    if old_refs:
        for ref in old_refs:
            print(ref)
    else:
        print("  ✅ None found - migration complete!")
    
    # Files correctly using content_unified
    print("\n✅ Files using content_unified table:")
    unified_count = 0
    for filepath, data in results.items():
        if data['tables']['content_unified'] > 0:
            unified_count += 1
            print(f"  - {filepath}: {data['tables']['content_unified']} references")
    print(f"\nTotal: {unified_count} files")
    
    # Column usage
    print("\n📊 Column Reference Status:")
    body_count = sum(d['tables']['body_column'] for d in results.values())
    content_count = sum(d['tables']['content_column'] for d in results.values())
    print(f"  - 'body' column (correct): {body_count} references")
    print(f"  - 'content' column (old): {content_count} references")
    
    # Import dependencies
    print("\n🔗 Modules importing SimpleDB:")
    simpledb_users = []
    for filepath, data in results.items():
        if data['has_simpledb']:
            simpledb_users.append(filepath)
    
    for user in sorted(simpledb_users)[:10]:  # First 10
        print(f"  - {user}")
    
    if len(simpledb_users) > 10:
        print(f"  ... and {len(simpledb_users) - 10} more")
    
    print(f"\nTotal SimpleDB users: {len(simpledb_users)} files")

if __name__ == "__main__":
    main()