#!/usr/bin/env python3
"""
Dependency Mapper - Find the real architectural issues in your codebase.
Reveals circular dependencies, orphaned modules, and broken import chains.
"""

import ast
import json
from pathlib import Path
from typing import Dict, Set, List, Tuple
from collections import defaultdict

class DependencyMapper:
    def __init__(self, root_path: str = "."):
        self.root = Path(root_path).resolve()
        self.dependencies: Dict[str, Set[str]] = defaultdict(set)
        self.reverse_deps: Dict[str, Set[str]] = defaultdict(set)
        self.module_files: Dict[str, Path] = {}
        self.broken_imports: List[Tuple[str, str, str]] = []
        self.circular_deps: List[List[str]] = []
        self.external_deps: Set[str] = set()
        
    def scan_codebase(self):
        """Scan all Python files and build dependency graph."""
        print("🔍 Scanning codebase...")
        py_files = list(self.root.rglob("*.py"))
        
        # Skip venv, node_modules, etc
        py_files = [f for f in py_files if not any(
            skip in f.parts for skip in [
                'venv', '.venv', 'node_modules', '__pycache__', 
                '.git', 'build', 'dist', '.tox', 'migrations'
            ]
        )]
        
        print(f"Found {len(py_files)} Python files")
        
        for file_path in py_files:
            self._analyze_file(file_path)
            
    def _analyze_file(self, file_path: Path):
        """Analyze imports in a single file."""
        module_name = self._path_to_module(file_path)
        self.module_files[module_name] = file_path
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                tree = ast.parse(f.read(), filename=str(file_path))
                
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        self._add_dependency(module_name, alias.name, file_path)
                        
                elif isinstance(node, ast.ImportFrom):
                    if node.module:
                        # Handle relative imports
                        if node.level > 0:
                            base = module_name.rsplit('.', node.level)[0] if node.level > 0 else module_name
                            full_module = f"{base}.{node.module}" if node.module else base
                        else:
                            full_module = node.module
                        self._add_dependency(module_name, full_module, file_path)
                        
        except Exception:
            # Syntax errors or encoding issues
            pass
            
    def _path_to_module(self, file_path: Path) -> str:
        """Convert file path to module name."""
        try:
            relative = file_path.relative_to(self.root)
            parts = list(relative.parts[:-1]) + [relative.stem]
            
            # Remove __init__ from module names
            if parts[-1] == '__init__':
                parts = parts[:-1]
                
            return '.'.join(parts)
        except ValueError:
            return str(file_path.stem)
            
    def _add_dependency(self, from_module: str, to_module: str, file_path: Path):
        """Add a dependency relationship."""
        # Check if it's an external dependency
        if not to_module.startswith(('gmail', 'pdf', 'transcription', 'entity', 
                                     'search_intelligence', 'knowledge_graph', 
                                     'legal_intelligence', 'shared', 'utilities',
                                     'infrastructure', 'tools', 'tests')):
            if not to_module.startswith(('sys', 'os', 'json', 'typing', 're', 
                                        'collections', 'pathlib', 'datetime')):
                self.external_deps.add(to_module)
            return
            
        self.dependencies[from_module].add(to_module)
        self.reverse_deps[to_module].add(from_module)
        
        # Check if import is broken (module doesn't exist)
        if not self._module_exists(to_module):
            self.broken_imports.append((from_module, to_module, str(file_path)))
            
    def _module_exists(self, module_name: str) -> bool:
        """Check if a module actually exists in the codebase."""
        # Check exact match
        if module_name in self.module_files:
            return True
            
        # Check if it's a submodule of an existing module
        parts = module_name.split('.')
        for i in range(len(parts), 0, -1):
            partial = '.'.join(parts[:i])
            if partial in self.module_files:
                return True
                
        # Check if it's a directory with __init__.py
        module_path = self.root / module_name.replace('.', '/')
        if module_path.is_dir() and (module_path / '__init__.py').exists():
            return True
            
        return False
        
    def find_circular_dependencies(self):
        """Find all circular dependency chains."""
        print("\n🔄 Finding circular dependencies...")
        visited = set()
        
        for module in self.dependencies:
            if module not in visited:
                path = []
                if self._has_cycle(module, visited, path, set()):
                    self.circular_deps.append(path)
                    
    def _has_cycle(self, module: str, visited: Set[str], path: List[str], 
                   rec_stack: Set[str]) -> bool:
        """DFS to detect cycles."""
        visited.add(module)
        rec_stack.add(module)
        path.append(module)
        
        for neighbor in self.dependencies.get(module, []):
            if neighbor not in visited:
                if self._has_cycle(neighbor, visited, path, rec_stack):
                    return True
            elif neighbor in rec_stack:
                # Found cycle
                cycle_start = path.index(neighbor)
                self.circular_deps.append(path[cycle_start:] + [neighbor])
                
        path.pop()
        rec_stack.remove(module)
        return False
        
    def find_orphaned_modules(self) -> List[str]:
        """Find modules with no incoming dependencies (except main/test files)."""
        orphaned = []
        
        for module in self.module_files:
            # Skip test files and main entry points
            if ('test' in module or module.endswith('__main__') or 
                module.endswith('main') or 'conftest' in module):
                continue
                
            # Check if anything imports this module
            if module not in self.reverse_deps or not self.reverse_deps[module]:
                orphaned.append(module)
                
        return orphaned
        
    def find_god_modules(self, threshold: int = 10) -> List[Tuple[str, int]]:
        """Find modules that too many others depend on."""
        god_modules = []
        
        for module, dependents in self.reverse_deps.items():
            if len(dependents) >= threshold:
                god_modules.append((module, len(dependents)))
                
        return sorted(god_modules, key=lambda x: x[1], reverse=True)
        
    def find_layer_violations(self) -> List[Tuple[str, str]]:
        """Find dependencies that violate architectural layers."""
        violations = []
        
        # Define architectural layers (higher layers shouldn't import lower)
        layers = {
            'shared': 0,
            'utilities': 1,
            'infrastructure': 2,
            'gmail': 3,
            'pdf': 3,
            'transcription': 3,
            'entity': 3,
            'search_intelligence': 4,
            'knowledge_graph': 4,
            'legal_intelligence': 4,
            'tools': 5,
            'tests': 6
        }
        
        for from_module, deps in self.dependencies.items():
            from_layer = self._get_layer(from_module, layers)
            
            for to_module in deps:
                to_layer = self._get_layer(to_module, layers)
                
                # Lower layers shouldn't import higher layers
                if from_layer < to_layer:
                    violations.append((from_module, to_module))
                    
        return violations
        
    def _get_layer(self, module: str, layers: Dict[str, int]) -> int:
        """Get the architectural layer of a module."""
        for layer_name, level in layers.items():
            if module.startswith(layer_name):
                return level
        return 999  # Unknown layer
        
    def generate_report(self):
        """Generate comprehensive dependency report."""
        print("\n" + "="*60)
        print("📊 DEPENDENCY ANALYSIS REPORT")
        print("="*60)
        
        # Broken imports
        if self.broken_imports:
            print(f"\n❌ BROKEN IMPORTS ({len(self.broken_imports)} found)")
            print("-" * 40)
            for from_mod, to_mod, file_path in self.broken_imports[:10]:
                print(f"  {from_mod} → {to_mod}")
                print(f"    in {file_path}")
            if len(self.broken_imports) > 10:
                print(f"  ... and {len(self.broken_imports) - 10} more")
                
        # Circular dependencies
        if self.circular_deps:
            print(f"\n🔄 CIRCULAR DEPENDENCIES ({len(self.circular_deps)} cycles)")
            print("-" * 40)
            for cycle in self.circular_deps[:5]:
                print(f"  {' → '.join(cycle[:5])}")
                if len(cycle) > 5:
                    print(f"    ... {len(cycle) - 5} more in cycle")
                    
        # Orphaned modules
        orphaned = self.find_orphaned_modules()
        if orphaned:
            print(f"\n🏝️ ORPHANED MODULES ({len(orphaned)} found)")
            print("-" * 40)
            for module in orphaned[:10]:
                file_path = self.module_files.get(module, "unknown")
                print(f"  {module}")
                print(f"    {file_path}")
            if len(orphaned) > 10:
                print(f"  ... and {len(orphaned) - 10} more")
                
        # God modules
        god_modules = self.find_god_modules()
        if god_modules:
            print("\n👑 GOD MODULES (too many dependents)")
            print("-" * 40)
            for module, count in god_modules[:5]:
                print(f"  {module}: {count} dependents")
                
        # Layer violations
        violations = self.find_layer_violations()
        if violations:
            print(f"\n🚫 LAYER VIOLATIONS ({len(violations)} found)")
            print("-" * 40)
            for from_mod, to_mod in violations[:10]:
                print(f"  {from_mod} → {to_mod}")
            if len(violations) > 10:
                print(f"  ... and {len(violations) - 10} more")
                
        # External dependencies
        if self.external_deps:
            print(f"\n📦 EXTERNAL DEPENDENCIES ({len(self.external_deps)} packages)")
            print("-" * 40)
            for dep in sorted(list(self.external_deps))[:20]:
                print(f"  {dep}")
            if len(self.external_deps) > 20:
                print(f"  ... and {len(self.external_deps) - 20} more")
                
        # Summary statistics
        print("\n📈 STATISTICS")
        print("-" * 40)
        print(f"  Total modules: {len(self.module_files)}")
        print(f"  Total dependencies: {sum(len(deps) for deps in self.dependencies.values())}")
        print(f"  Average dependencies per module: {sum(len(deps) for deps in self.dependencies.values()) / max(len(self.module_files), 1):.1f}")
        
        # Most connected modules
        connectivity = [(m, len(self.dependencies.get(m, [])) + len(self.reverse_deps.get(m, []))) 
                       for m in self.module_files]
        connectivity.sort(key=lambda x: x[1], reverse=True)
        
        print("\n🔗 MOST CONNECTED MODULES")
        print("-" * 40)
        for module, connections in connectivity[:5]:
            out_deps = len(self.dependencies.get(module, []))
            in_deps = len(self.reverse_deps.get(module, []))
            print(f"  {module}: {connections} total ({out_deps} out, {in_deps} in)")
            
    def export_json(self, output_file: str = "dependency_map.json"):
        """Export dependency data as JSON for visualization."""
        data = {
            "modules": list(self.module_files.keys()),
            "dependencies": {k: list(v) for k, v in self.dependencies.items()},
            "reverse_dependencies": {k: list(v) for k, v in self.reverse_deps.items()},
            "broken_imports": self.broken_imports,
            "circular_dependencies": self.circular_deps,
            "orphaned_modules": self.find_orphaned_modules(),
            "god_modules": self.find_god_modules(),
            "layer_violations": self.find_layer_violations(),
            "external_dependencies": list(self.external_deps)
        }
        
        with open(output_file, 'w') as f:
            json.dump(data, f, indent=2)
        print(f"\n💾 Exported dependency map to {output_file}")


def main():
    print("🗺️ Email Sync Dependency Mapper")
    print("=" * 60)
    
    mapper = DependencyMapper()
    mapper.scan_codebase()
    mapper.find_circular_dependencies()
    mapper.generate_report()
    mapper.export_json()
    
    print("\n✅ Analysis complete!")
    print("Review dependency_map.json for full details")


if __name__ == "__main__":
    main()