#!/usr/bin/env python3
"""
Comprehensive import analysis for Litigator_solo refactoring.
Extracts all imports, maps dependencies, and identifies refactoring needs.
"""

import os
import re
import ast
import sys
from pathlib import Path
from collections import defaultdict, deque
from typing import Dict, List, Set, Tuple, Optional
import json

class ImportAnalyzer:
    def __init__(self, project_root: str):
        self.project_root = Path(project_root)
        self.file_imports = {}  # file_path -> list of imports
        self.import_graph = defaultdict(set)  # module -> set of modules it imports
        self.reverse_graph = defaultdict(set)  # module -> set of modules that import it
        self.all_modules = set()
        self.python_files = []
        
    def collect_python_files(self):
        """Collect all Python files in the project."""
        for root, dirs, files in os.walk(self.project_root):
            # Skip cache directories
            dirs[:] = [d for d in dirs if d not in ['__pycache__', '.cache', '.git', 'node_modules']]
            for file in files:
                if file.endswith('.py'):
                    full_path = Path(root) / file
                    rel_path = full_path.relative_to(self.project_root)
                    self.python_files.append(str(rel_path))
        
    def parse_file_imports(self, file_path: str) -> List[Dict]:
        """Parse imports from a single file."""
        full_path = self.project_root / file_path
        imports = []
        
        try:
            with open(full_path, 'r', encoding='utf-8') as f:
                content = f.read()
                
            tree = ast.parse(content)
            
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        imports.append({
                            'type': 'import',
                            'module': alias.name,
                            'asname': alias.asname,
                            'line': node.lineno
                        })
                elif isinstance(node, ast.ImportFrom):
                    module = node.module or ''
                    for alias in node.names:
                        imports.append({
                            'type': 'from_import',
                            'module': module,
                            'name': alias.name,
                            'asname': alias.asname,
                            'level': node.level,
                            'line': node.lineno
                        })
                        
        except Exception as e:
            print(f"Error parsing {file_path}: {e}")
            
        return imports
    
    def is_internal_module(self, module_name: str) -> bool:
        """Check if a module is internal to the project."""
        if not module_name:
            return False
            
        # These are clearly internal modules
        internal_prefixes = [
            'cli', 'config', 'deduplication', 'email_parsing', 'entity',
            'gmail', 'infrastructure', 'lib', 'pdf', 'shared', 'summarization',
            'tests', 'tools', 'bench', 'scripts'
        ]
        
        return any(module_name.startswith(prefix) for prefix in internal_prefixes)
    
    def normalize_module_path(self, file_path: str, import_info: Dict) -> Optional[str]:
        """Convert import to normalized module path."""
        if import_info['type'] == 'import':
            if self.is_internal_module(import_info['module']):
                return import_info['module']
        elif import_info['type'] == 'from_import':
            module = import_info['module']
            level = import_info.get('level', 0)
            
            if level > 0:  # Relative import
                current_dir = Path(file_path).parent
                for _ in range(level - 1):
                    current_dir = current_dir.parent
                if module:
                    full_module = str(current_dir / module).replace('/', '.')
                else:
                    full_module = str(current_dir).replace('/', '.')
                return full_module
            elif self.is_internal_module(module):
                return module
                
        return None
    
    def analyze_all_files(self):
        """Analyze imports in all Python files."""
        self.collect_python_files()
        
        print(f"Analyzing {len(self.python_files)} Python files...")
        
        for file_path in self.python_files:
            imports = self.parse_file_imports(file_path)
            self.file_imports[file_path] = imports
            
            # Convert file path to module path
            file_module = str(Path(file_path).with_suffix('')).replace('/', '.')
            if file_module.endswith('.__init__'):
                file_module = file_module[:-9]
            
            self.all_modules.add(file_module)
            
            # Build dependency graph
            for imp in imports:
                target_module = self.normalize_module_path(file_path, imp)
                if target_module:
                    self.import_graph[file_module].add(target_module)
                    self.reverse_graph[target_module].add(file_module)
    
    def find_circular_dependencies(self) -> List[List[str]]:
        """Find circular dependencies using DFS."""
        visited = set()
        rec_stack = set()
        cycles = []
        
        def dfs(node, path):
            if node in rec_stack:
                # Found cycle
                cycle_start = path.index(node)
                cycles.append(path[cycle_start:] + [node])
                return
            
            if node in visited:
                return
                
            visited.add(node)
            rec_stack.add(node)
            
            for neighbor in self.import_graph.get(node, []):
                dfs(neighbor, path + [node])
            
            rec_stack.remove(node)
        
        for module in self.all_modules:
            if module not in visited:
                dfs(module, [])
        
        return cycles
    
    def get_dependency_order(self) -> List[str]:
        """Get topological sort order for safe migration."""
        in_degree = defaultdict(int)
        
        for module in self.all_modules:
            for dependency in self.import_graph.get(module, []):
                if dependency in self.all_modules:
                    in_degree[module] += 1
        
        queue = deque([module for module in self.all_modules if in_degree[module] == 0])
        result = []
        
        while queue:
            module = queue.popleft()
            result.append(module)
            
            for dependent in self.reverse_graph.get(module, []):
                in_degree[dependent] -= 1
                if in_degree[dependent] == 0:
                    queue.append(dependent)
        
        return result
    
    def generate_refactoring_plan(self) -> Dict:
        """Generate comprehensive refactoring plan."""
        
        # Proposed new structure
        file_moves = {}
        
        # Web UI files
        file_moves['web_ui.py'] = 'apps/web/app.py'
        file_moves['web_ui_config.py'] = 'apps/web/config.py'
        
        # Consolidate email functionality
        for file_path in self.python_files:
            if 'email_parsing/' in file_path:
                new_path = file_path.replace('email_parsing/', 'gmail/parsing/')
                file_moves[file_path] = new_path
            elif 'deduplication/' in file_path:
                new_path = file_path.replace('deduplication/', 'gmail/deduplication/')
                file_moves[file_path] = new_path
        
        # Distribute shared/ contents
        for file_path in self.python_files:
            if file_path.startswith('shared/'):
                if 'email' in file_path:
                    new_path = file_path.replace('shared/email/', 'gmail/utils/')
                    file_moves[file_path] = new_path
                elif 'utils' in file_path:
                    new_path = file_path.replace('shared/utils/', 'lib/utils/')
                    file_moves[file_path] = new_path
                else:
                    new_path = file_path.replace('shared/', 'lib/shared/')
                    file_moves[file_path] = new_path
        
        # Create services directory structure
        service_dirs = {
            'entity/': 'services/entity/',
            'pdf/': 'services/pdf/',
            'summarization/': 'services/summarization/',
            'cli/': 'services/cli/',
        }
        
        for old_prefix, new_prefix in service_dirs.items():
            for file_path in self.python_files:
                if file_path.startswith(old_prefix):
                    new_path = file_path.replace(old_prefix, new_prefix)
                    file_moves[file_path] = new_path
        
        # Generate import rewrite rules
        import_rewrites = {}
        for old_path, new_path in file_moves.items():
            old_module = str(Path(old_path).with_suffix('')).replace('/', '.')
            new_module = str(Path(new_path).with_suffix('')).replace('/', '.')
            
            if old_module.endswith('.__init__'):
                old_module = old_module[:-9]
            if new_module.endswith('.__init__'):
                new_module = new_module[:-9]
                
            import_rewrites[old_module] = new_module
        
        return {
            'file_moves': file_moves,
            'import_rewrites': import_rewrites,
            'circular_dependencies': self.find_circular_dependencies(),
            'dependency_order': self.get_dependency_order(),
            'all_imports': self.file_imports
        }
    
    def print_analysis(self):
        """Print comprehensive analysis."""
        plan = self.generate_refactoring_plan()
        
        print("\n=== LITIGATOR SOLO REFACTORING ANALYSIS ===\n")
        
        print(f"Total Python files: {len(self.python_files)}")
        print(f"Total internal modules: {len(self.all_modules)}")
        print(f"Total import relationships: {sum(len(deps) for deps in self.import_graph.values())}")
        
        print("\n=== PROPOSED FILE MOVES ===")
        for old, new in sorted(plan['file_moves'].items()):
            print(f"{old} -> {new}")
        
        print(f"\nTotal files to move: {len(plan['file_moves'])}")
        
        print("\n=== IMPORT REWRITE RULES ===")
        for old, new in sorted(plan['import_rewrites'].items()):
            print(f"{old} -> {new}")
        
        print(f"\nTotal import rewrites needed: {len(plan['import_rewrites'])}")
        
        print("\n=== CIRCULAR DEPENDENCIES ===")
        cycles = plan['circular_dependencies']
        if cycles:
            for i, cycle in enumerate(cycles, 1):
                print(f"Cycle {i}: {' -> '.join(cycle)}")
        else:
            print("No circular dependencies found!")
        
        print(f"\nTotal circular dependencies: {len(cycles)}")
        
        print("\n=== MIGRATION ORDER (First 20) ===")
        order = plan['dependency_order']
        for i, module in enumerate(order[:20], 1):
            print(f"{i}. {module}")
        if len(order) > 20:
            print(f"... and {len(order) - 20} more")
        
        # Save detailed analysis
        with open(self.project_root / 'refactoring_analysis.json', 'w') as f:
            # Convert sets to lists for JSON serialization
            json_plan = {
                'file_moves': plan['file_moves'],
                'import_rewrites': plan['import_rewrites'],
                'circular_dependencies': plan['circular_dependencies'],
                'dependency_order': plan['dependency_order'],
                'total_files': len(self.python_files),
                'total_modules': len(self.all_modules)
            }
            json.dump(json_plan, f, indent=2)
        
        print(f"\nDetailed analysis saved to: refactoring_analysis.json")

if __name__ == '__main__':
    project_root = sys.argv[1] if len(sys.argv) > 1 else '.'
    analyzer = ImportAnalyzer(project_root)
    analyzer.analyze_all_files()
    analyzer.print_analysis()