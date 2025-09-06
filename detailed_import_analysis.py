#!/usr/bin/env python3
"""
Detailed import analysis for finding all import dependencies.
Creates comprehensive mapping of what imports what.
"""

import ast
import json
import os
import re
from collections import defaultdict, deque
from pathlib import Path
from typing import Dict, List, Set, Tuple


def analyze_file_imports(file_path: Path) -> Dict:
    """Extract all import information from a file."""
    imports = {
        'internal_imports': [],
        'external_imports': [],
        'relative_imports': [],
        'all_imports': []
    }
    
    try:
        content = file_path.read_text(encoding='utf-8')
        tree = ast.parse(content)
        
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    import_info = {
                        'type': 'import',
                        'module': alias.name,
                        'asname': alias.asname,
                        'line': node.lineno
                    }
                    imports['all_imports'].append(import_info)
                    
                    if is_internal_import(alias.name):
                        imports['internal_imports'].append(import_info)
                    else:
                        imports['external_imports'].append(import_info)
                        
            elif isinstance(node, ast.ImportFrom):
                module = node.module or ''
                level = node.level
                
                for alias in node.names:
                    import_info = {
                        'type': 'from_import',
                        'module': module,
                        'name': alias.name,
                        'asname': alias.asname,
                        'level': level,
                        'line': node.lineno
                    }
                    imports['all_imports'].append(import_info)
                    
                    if level > 0:
                        imports['relative_imports'].append(import_info)
                    elif is_internal_import(module):
                        imports['internal_imports'].append(import_info)
                    else:
                        imports['external_imports'].append(import_info)
                        
    except Exception as e:
        print(f"Error analyzing {file_path}: {e}")
    
    return imports

def is_internal_import(module_name: str) -> bool:
    """Check if an import is internal to the project."""
    if not module_name:
        return False
        
    internal_prefixes = [
        'cli', 'config', 'deduplication', 'email_parsing', 'entity',
        'gmail', 'infrastructure', 'lib', 'pdf', 'shared', 'summarization',
        'tools', 'bench', 'scripts', 'web_ui', 'stoneman'
    ]
    
    return any(module_name.startswith(prefix) for prefix in internal_prefixes)

def find_all_imports_needing_update():
    """Find all imports that will need updating in the refactoring."""
    project_root = Path('.')
    python_files = [f for f in project_root.rglob('*.py') if '__pycache__' not in str(f)]
    
    files_with_updates = []
    all_internal_imports = set()
    
    # Load the mapping
    with open('refactoring_analysis.json') as f:
        plan = json.load(f)
    
    import_mapping = plan['import_rewrites']
    
    for file_path in python_files:
        rel_path = file_path.relative_to(project_root)
        imports = analyze_file_imports(file_path)
        
        imports_to_update = []
        
        # Check each import
        for imp in imports['all_imports']:
            if imp['type'] == 'import':
                module = imp['module']
                if module in import_mapping:
                    imports_to_update.append({
                        'current': f"import {module}",
                        'new': f"import {import_mapping[module]}",
                        'line': imp['line']
                    })
                    all_internal_imports.add(module)
            elif imp['type'] == 'from_import':
                module = imp['module']
                if module in import_mapping:
                    imports_to_update.append({
                        'current': f"from {module} import {imp['name']}",
                        'new': f"from {import_mapping[module]} import {imp['name']}",
                        'line': imp['line']
                    })
                    all_internal_imports.add(module)
                else:
                    # Check for partial matches
                    for old_prefix, new_prefix in import_mapping.items():
                        if module.startswith(old_prefix + '.'):
                            new_module = module.replace(old_prefix, new_prefix, 1)
                            imports_to_update.append({
                                'current': f"from {module} import {imp['name']}",
                                'new': f"from {new_module} import {imp['name']}",
                                'line': imp['line']
                            })
                            all_internal_imports.add(module)
                            break
        
        if imports_to_update:
            files_with_updates.append({
                'file': str(rel_path),
                'imports_to_update': imports_to_update,
                'total_imports': len(imports['all_imports']),
                'internal_imports': len(imports['internal_imports'])
            })
    
    return files_with_updates, all_internal_imports

def generate_detailed_report():
    """Generate detailed refactoring report."""
    files_needing_updates, all_internal = find_all_imports_needing_update()
    
    print("=== DETAILED IMPORT ANALYSIS FOR REFACTORING ===\n")
    
    print(f"Files requiring import updates: {len(files_needing_updates)}")
    print(f"Unique internal modules referenced: {len(all_internal)}")
    
    print("\n=== FILES WITH IMPORT UPDATES NEEDED ===")
    
    total_updates = 0
    for file_info in files_needing_updates:
        print(f"\n{file_info['file']}:")
        print(f"  Total imports: {file_info['total_imports']}")
        print(f"  Internal imports: {file_info['internal_imports']}")
        print(f"  Updates needed: {len(file_info['imports_to_update'])}")
        
        for update in file_info['imports_to_update']:
            print(f"    Line {update['line']}: {update['current']} -> {update['new']}")
        
        total_updates += len(file_info['imports_to_update'])
    
    print(f"\n=== SUMMARY ===")
    print(f"Total import statements to update: {total_updates}")
    print(f"Files affected: {len(files_needing_updates)}")
    
    # Save detailed results
    with open('detailed_import_analysis.json', 'w') as f:
        json.dump({
            'files_needing_updates': files_needing_updates,
            'all_internal_modules': sorted(all_internal),
            'total_updates_needed': total_updates
        }, f, indent=2)
    
    print(f"\nDetailed analysis saved to: detailed_import_analysis.json")

if __name__ == '__main__':
    generate_detailed_report()