#!/usr/bin/env python3
"""
Dead code analyzer for Litigator_solo project.
Finds unused imports, functions, classes, and modules.
"""

import ast
import os
import re
from collections import Counter, defaultdict
from pathlib import Path
from typing import Dict, List, Set, Tuple


class DeadCodeAnalyzer:
    def __init__(self, project_root: str):
        self.project_root = Path(project_root)
        self.target_dirs = ['lib', 'services', 'infrastructure', 'shared']
        
        # Track definitions and usages
        self.definitions = defaultdict(set)  # module -> {functions, classes}
        self.imports = defaultdict(list)     # module -> [(imported_module, imported_names)]
        self.usage_patterns = defaultdict(set)  # module -> {usage_patterns}
        
        # Files analysis
        self.python_files = []
        self.import_errors = []
        
    def find_python_files(self) -> List[Path]:
        """Find all Python files in target directories."""
        files = []
        for target_dir in self.target_dirs:
            dir_path = self.project_root / target_dir
            if dir_path.exists():
                files.extend(dir_path.rglob("*.py"))
        
        # Also include tests for usage analysis
        test_dir = self.project_root / "tests"
        if test_dir.exists():
            files.extend(test_dir.rglob("*.py"))
            
        return files
    
    def parse_file(self, file_path: Path) -> Dict:
        """Parse a Python file and extract definitions and imports."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                
            tree = ast.parse(content)
            
            # Get relative module path
            rel_path = file_path.relative_to(self.project_root)
            module_name = str(rel_path).replace('/', '.').replace('.py', '')
            
            result = {
                'module': module_name,
                'path': file_path,
                'functions': [],
                'classes': [],
                'imports': [],
                'from_imports': [],
                'string_usages': []
            }
            
            # Extract function and class definitions
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef):
                    result['functions'].append(node.name)
                elif isinstance(node, ast.ClassDef):
                    result['classes'].append(node.name)
                elif isinstance(node, ast.Import):
                    for alias in node.names:
                        result['imports'].append(alias.name)
                elif isinstance(node, ast.ImportFrom):
                    if node.module:
                        module = node.module
                        names = [alias.name for alias in node.names]
                        result['from_imports'].append((module, names))
            
            # Look for string-based usage patterns (like getattr, __import__, etc.)
            string_patterns = re.findall(r'[\'\"]([\w\.]+)[\'\"]\s*[,\)]', content)
            result['string_usages'] = string_patterns
            
            return result
            
        except Exception as e:
            self.import_errors.append((file_path, str(e)))
            return None
    
    def analyze_all_files(self):
        """Analyze all Python files in the project."""
        self.python_files = self.find_python_files()
        
        file_data = {}
        for file_path in self.python_files:
            data = self.parse_file(file_path)
            if data:
                file_data[data['module']] = data
                
        return file_data
    
    def find_unused_definitions(self, file_data: Dict) -> Dict:
        """Find functions and classes that are defined but never used."""
        all_usages = set()
        
        # Collect all possible usages
        for module, data in file_data.items():
            # Direct imports
            for imp in data['imports']:
                all_usages.add(imp)
            
            # From imports
            for module_name, names in data['from_imports']:
                for name in names:
                    all_usages.add(name)
                    all_usages.add(f"{module_name}.{name}")
            
            # String usages
            for usage in data['string_usages']:
                all_usages.add(usage)
                if '.' in usage:
                    parts = usage.split('.')
                    for i in range(len(parts)):
                        all_usages.add('.'.join(parts[i:]))
        
        # Also scan all file contents for name patterns
        usage_patterns = set()
        for file_path in self.python_files:
            try:
                with open(file_path, 'r') as f:
                    content = f.read()
                    # Look for function/class name patterns
                    names = re.findall(r'\b([A-Za-z_][A-Za-z0-9_]*)\b', content)
                    usage_patterns.update(names)
            except:
                continue
        
        all_usages.update(usage_patterns)
        
        unused = defaultdict(list)
        for module, data in file_data.items():
            # Check functions
            for func in data['functions']:
                if func not in all_usages and not func.startswith('_') and func not in ['main', 'setup', 'teardown']:
                    unused[module].append(('function', func))
            
            # Check classes
            for cls in data['classes']:
                if cls not in all_usages and not cls.startswith('_'):
                    unused[module].append(('class', cls))
        
        return unused
    
    def find_unused_imports(self, file_data: Dict) -> Dict:
        """Find import statements that are unused in the file."""
        unused_imports = defaultdict(list)
        
        for module, data in file_data.items():
            try:
                with open(data['path'], 'r') as f:
                    content = f.read()
                
                # Check direct imports
                for imp in data['imports']:
                    # Skip if used in content
                    if not re.search(rf'\b{re.escape(imp)}\b', content.replace(f'import {imp}', '')):
                        unused_imports[module].append(('import', imp))
                
                # Check from imports
                for module_name, names in data['from_imports']:
                    for name in names:
                        if name != '*' and not re.search(rf'\b{re.escape(name)}\b', 
                                                       content.replace(f'from {module_name} import', '')):
                            unused_imports[module].append(('from_import', f"{module_name}.{name}"))
                            
            except Exception:
                continue
        
        return unused_imports
    
    def find_unused_modules(self, file_data: Dict) -> List[str]:
        """Find modules that are never imported anywhere."""
        all_imported_modules = set()
        
        # Collect all imported modules
        for module, data in file_data.items():
            for imp in data['imports']:
                all_imported_modules.add(imp)
                # Handle dotted imports
                if '.' in imp:
                    parts = imp.split('.')
                    for i in range(len(parts)):
                        all_imported_modules.add('.'.join(parts[:i+1]))
            
            for module_name, names in data['from_imports']:
                all_imported_modules.add(module_name)
                if '.' in module_name:
                    parts = module_name.split('.')
                    for i in range(len(parts)):
                        all_imported_modules.add('.'.join(parts[:i+1]))
        
        # Find modules that are never imported
        unused_modules = []
        for module in file_data.keys():
            # Skip test modules and __init__ files
            if 'test_' in module or '__init__' in module or '__main__' in module:
                continue
                
            # Check if module or any parent module is imported
            module_imported = False
            module_parts = module.split('.')
            
            for imported in all_imported_modules:
                if imported == module or module.startswith(imported + '.'):
                    module_imported = True
                    break
                
            if not module_imported:
                unused_modules.append(module)
        
        return unused_modules
    
    def check_broken_imports(self, file_data: Dict) -> List[Tuple[str, str]]:
        """Check for imports that reference non-existent modules."""
        broken_imports = []
        existing_modules = set(file_data.keys())
        
        for module, data in file_data.items():
            for imp in data['imports']:
                # Convert to module path format
                if imp not in existing_modules and '.' in imp:
                    # Check if it's an internal import
                    if any(imp.startswith(target) for target in self.target_dirs):
                        broken_imports.append((module, imp))
            
            for module_name, names in data['from_imports']:
                if module_name and '.' in module_name:
                    if any(module_name.startswith(target) for target in self.target_dirs):
                        if module_name not in existing_modules:
                            broken_imports.append((module, module_name))
        
        return broken_imports

def main():
    analyzer = DeadCodeAnalyzer('/Users/jim/Projects/Litigator_solo')
    
    print("Analyzing Python files...")
    file_data = analyzer.analyze_all_files()
    
    print(f"Found {len(file_data)} Python files to analyze\n")
    
    # Find unused definitions
    print("=" * 50)
    print("UNUSED FUNCTIONS AND CLASSES")
    print("=" * 50)
    unused_defs = analyzer.find_unused_definitions(file_data)
    if unused_defs:
        for module, items in unused_defs.items():
            if items:
                print(f"\n{module}:")
                for def_type, name in items:
                    print(f"  - {def_type}: {name}")
    else:
        print("No unused definitions found.")
    
    # Find unused imports
    print("\n" + "=" * 50)
    print("UNUSED IMPORTS")
    print("=" * 50)
    unused_imports = analyzer.find_unused_imports(file_data)
    if unused_imports:
        for module, items in unused_imports.items():
            if items:
                print(f"\n{module}:")
                for imp_type, name in items:
                    print(f"  - {imp_type}: {name}")
    else:
        print("No unused imports found.")
    
    # Find unused modules
    print("\n" + "=" * 50)
    print("POTENTIALLY UNUSED MODULES")
    print("=" * 50)
    unused_modules = analyzer.find_unused_modules(file_data)
    if unused_modules:
        for module in unused_modules:
            print(f"  - {module}")
    else:
        print("No unused modules found.")
    
    # Find broken imports
    print("\n" + "=" * 50)
    print("BROKEN IMPORTS")
    print("=" * 50)
    broken_imports = analyzer.check_broken_imports(file_data)
    if broken_imports:
        for module, broken_import in broken_imports:
            print(f"  - {module} -> {broken_import}")
    else:
        print("No broken imports found.")
    
    # Show import errors
    if analyzer.import_errors:
        print("\n" + "=" * 50)
        print("PARSE ERRORS")
        print("=" * 50)
        for file_path, error in analyzer.import_errors:
            print(f"  - {file_path}: {error}")

if __name__ == "__main__":
    main()