#!/usr/bin/env python3
"""
LibCST-based import refactoring tool for Litigator Solo microservice architecture.
Performs comprehensive import transformations with precise AST manipulation.
"""

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Dict, List, Optional, Set, Union

import libcst as cst
from libcst import metadata


class ImportRewriter(cst.CSTTransformer):
    """LibCST transformer for rewriting imports according to refactoring plan."""
    
    def __init__(self, import_mapping: Dict[str, str]):
        self.import_mapping = import_mapping
        self.changes_made = []
        
    def leave_ImportFrom(self, original_node: cst.ImportFrom, updated_node: cst.ImportFrom) -> cst.ImportFrom:
        """Transform 'from X import Y' statements."""
        if updated_node.module is None:
            return updated_node
            
        # Get the module name as string
        module_name = self._get_module_name(updated_node.module)
        if not module_name:
            return updated_node
            
        # Check for direct mapping
        if module_name in self.import_mapping:
            new_module_name = self.import_mapping[module_name]
            new_module = self._create_module_node(new_module_name)
            self.changes_made.append(f"from {module_name} -> from {new_module_name}")
            return updated_node.with_changes(module=new_module)
        
        # Check for partial mappings (e.g., shared.utils -> lib.utils)
        for old_prefix, new_prefix in self.import_mapping.items():
            if module_name.startswith(old_prefix + '.') or module_name == old_prefix:
                new_module_name = module_name.replace(old_prefix, new_prefix, 1)
                new_module = self._create_module_node(new_module_name)
                self.changes_made.append(f"from {module_name} -> from {new_module_name}")
                return updated_node.with_changes(module=new_module)
                
        return updated_node
    
    def leave_Import(self, original_node: cst.Import, updated_node: cst.Import) -> cst.Import:
        """Transform 'import X' statements."""
        new_names = []
        changed = False
        
        for name in updated_node.names:
            if isinstance(name, cst.ImportAlias):
                module_name = self._get_module_name(name.name)
                if module_name and module_name in self.import_mapping:
                    new_module_name = self.import_mapping[module_name]
                    new_name_node = self._create_module_node(new_module_name)
                    new_alias = name.with_changes(name=new_name_node)
                    new_names.append(new_alias)
                    self.changes_made.append(f"import {module_name} -> import {new_module_name}")
                    changed = True
                else:
                    # Check for partial mappings
                    found_mapping = False
                    for old_prefix, new_prefix in self.import_mapping.items():
                        if module_name and (module_name.startswith(old_prefix + '.') or module_name == old_prefix):
                            new_module_name = module_name.replace(old_prefix, new_prefix, 1)
                            new_name_node = self._create_module_node(new_module_name)
                            new_alias = name.with_changes(name=new_name_node)
                            new_names.append(new_alias)
                            self.changes_made.append(f"import {module_name} -> import {new_module_name}")
                            changed = True
                            found_mapping = True
                            break
                    if not found_mapping:
                        new_names.append(name)
            else:
                new_names.append(name)
        
        if changed:
            return updated_node.with_changes(names=new_names)
        return updated_node
    
    def _get_module_name(self, node: Union[cst.Attribute, cst.Name]) -> Optional[str]:
        """Extract module name from CST node."""
        if isinstance(node, cst.Name):
            return node.value
        elif isinstance(node, cst.Attribute):
            parts = []
            current = node
            while isinstance(current, cst.Attribute):
                parts.append(current.attr.value)
                current = current.value
            if isinstance(current, cst.Name):
                parts.append(current.value)
                return '.'.join(reversed(parts))
        return None
    
    def _create_module_node(self, module_name: str) -> Union[cst.Name, cst.Attribute]:
        """Create CST node for module name."""
        parts = module_name.split('.')
        if len(parts) == 1:
            return cst.Name(parts[0])
        
        # Build nested attribute access
        result = cst.Name(parts[0])
        for part in parts[1:]:
            result = cst.Attribute(value=result, attr=cst.Name(part))
        return result

class FileRefactorer:
    """Main refactoring orchestrator."""
    
    def __init__(self, project_root: str, dry_run: bool = False):
        self.project_root = Path(project_root)
        self.dry_run = dry_run
        self.changes_log = []
        
        # Load refactoring plan
        with open(self.project_root / 'refactoring_analysis.json') as f:
            self.plan = json.load(f)
        
    def create_target_directories(self):
        """Create all target directories for file moves."""
        directories_to_create = set()
        
        for target_path in self.plan['file_moves'].values():
            target_dir = Path(target_path).parent
            if target_dir != Path('.'):
                directories_to_create.add(target_dir)
        
        for dir_path in sorted(directories_to_create):
            full_path = self.project_root / dir_path
            if not self.dry_run:
                full_path.mkdir(parents=True, exist_ok=True)
                print(f"Created directory: {dir_path}")
            else:
                print(f"[DRY RUN] Would create directory: {dir_path}")
    
    def move_files(self):
        """Move files to new locations."""
        for old_path, new_path in self.plan['file_moves'].items():
            old_full = self.project_root / old_path
            new_full = self.project_root / new_path
            
            if old_full.exists():
                if not self.dry_run:
                    # Move file
                    new_full.parent.mkdir(parents=True, exist_ok=True)
                    old_full.rename(new_full)
                    print(f"Moved: {old_path} -> {new_path}")
                else:
                    print(f"[DRY RUN] Would move: {old_path} -> {new_path}")
            else:
                print(f"WARNING: File not found: {old_path}")
    
    def rewrite_imports_in_file(self, file_path: Path) -> bool:
        """Rewrite imports in a single file."""
        if not file_path.exists():
            return False
            
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                source_code = f.read()
            
            # Parse with libcst
            tree = cst.parse_expression(source_code) if source_code.strip().startswith('(') else cst.parse_module(source_code)
            
            # Transform imports
            transformer = ImportRewriter(self.plan['import_rewrites'])
            new_tree = tree.visit(transformer)
            
            if transformer.changes_made:
                new_source = new_tree.code
                
                if not self.dry_run:
                    with open(file_path, 'w', encoding='utf-8') as f:
                        f.write(new_source)
                    print(f"Rewrote imports in: {file_path.relative_to(self.project_root)}")
                    for change in transformer.changes_made:
                        print(f"  - {change}")
                else:
                    print(f"[DRY RUN] Would rewrite imports in: {file_path.relative_to(self.project_root)}")
                    for change in transformer.changes_made:
                        print(f"  - {change}")
                
                self.changes_log.extend(transformer.changes_made)
                return True
                
        except Exception as e:
            print(f"Error processing {file_path}: {e}")
            
        return False
    
    def rewrite_all_imports(self):
        """Rewrite imports in all Python files."""
        python_files = list(self.project_root.glob('**/*.py'))
        python_files = [f for f in python_files if '__pycache__' not in str(f) and '.cache' not in str(f)]
        
        print(f"\nRewriting imports in {len(python_files)} Python files...")
        
        files_changed = 0
        for file_path in python_files:
            if self.rewrite_imports_in_file(file_path):
                files_changed += 1
        
        print(f"\nImport rewriting complete. {files_changed} files modified.")
    
    def cleanup_empty_directories(self):
        """Remove empty directories left after moving files."""
        directories_to_check = [
            'shared', 'email_parsing', 'deduplication', 'cli', 'entity', 'pdf', 'summarization'
        ]
        
        for dir_name in directories_to_check:
            dir_path = self.project_root / dir_name
            if dir_path.exists() and dir_path.is_dir():
                try:
                    # Check if directory is empty (ignoring __pycache__)
                    contents = [item for item in dir_path.iterdir() if item.name != '__pycache__']
                    if not contents:
                        if not self.dry_run:
                            import shutil
                            shutil.rmtree(dir_path)
                            print(f"Removed empty directory: {dir_name}")
                        else:
                            print(f"[DRY RUN] Would remove empty directory: {dir_name}")
                except Exception as e:
                    print(f"Error removing directory {dir_name}: {e}")
    
    def create_init_files(self):
        """Create __init__.py files in new directory structures."""
        init_dirs = [
            'apps', 'apps/web', 'services', 'services/cli', 'services/entity',
            'services/entity/extractors', 'services/entity/processors', 'services/pdf',
            'services/summarization', 'gmail/parsing', 'gmail/deduplication', 'gmail/utils',
            'lib/utils'
        ]
        
        for dir_path in init_dirs:
            init_file = self.project_root / dir_path / '__init__.py'
            if not self.dry_run:
                init_file.parent.mkdir(parents=True, exist_ok=True)
                if not init_file.exists():
                    init_file.write_text('"""Package initialization file."""\n')
                    print(f"Created: {init_file.relative_to(self.project_root)}")
            else:
                print(f"[DRY RUN] Would create: {dir_path}/__init__.py")
    
    def generate_migration_script(self):
        """Generate a script to perform the complete migration."""
        script_path = self.project_root / 'perform_migration.py'
        
        script_content = f'''#!/usr/bin/env python3
"""
Generated migration script for Litigator Solo refactoring.
Run this script to perform the complete refactoring.
"""

import os
import sys
import json
import shutil
from pathlib import Path

def main():
    project_root = Path(__file__).parent
    print("Starting Litigator Solo refactoring migration...")
    
    # File moves
    file_moves = {json.dumps(self.plan['file_moves'], indent=2)}
    
    # Create target directories
    print("\\n1. Creating target directories...")
    directories = set()
    for target in file_moves.values():
        directories.add(Path(target).parent)
    
    for dir_path in sorted(directories):
        if dir_path != Path('.'):
            full_path = project_root / dir_path
            full_path.mkdir(parents=True, exist_ok=True)
            print(f"   Created: {{dir_path}}")
    
    # Move files
    print("\\n2. Moving files...")
    for old_path, new_path in file_moves.items():
        old_full = project_root / old_path
        new_full = project_root / new_path
        
        if old_full.exists():
            shutil.move(str(old_full), str(new_full))
            print(f"   Moved: {{old_path}} -> {{new_path}}")
        else:
            print(f"   WARNING: File not found: {{old_path}}")
    
    # Create __init__.py files
    print("\\n3. Creating __init__.py files...")
    init_dirs = [
        'apps', 'apps/web', 'services', 'services/cli', 'services/entity',
        'services/entity/extractors', 'services/entity/processors', 'services/pdf',
        'services/summarization', 'gmail/parsing', 'gmail/deduplication', 'gmail/utils',
        'lib/utils'
    ]
    
    for dir_path in init_dirs:
        init_file = project_root / dir_path / '__init__.py'
        if not init_file.exists():
            init_file.write_text('"""Package initialization file."""\\n')
            print(f"   Created: {{init_file.relative_to(project_root)}}")
    
    print("\\n4. Import rewriting...")
    print("   Run: python3 refactor_imports.py --rewrite-only")
    
    print("\\nMigration complete! Next steps:")
    print("1. Run tests to verify functionality")
    print("2. Update any remaining imports manually")
    print("3. Remove empty directories if desired")

if __name__ == '__main__':
    main()
'''
        
        if not self.dry_run:
            with open(script_path, 'w') as f:
                f.write(script_content)
            os.chmod(script_path, 0o755)
            print(f"Generated migration script: {script_path.name}")
        else:
            print(f"[DRY RUN] Would generate migration script: {script_path.name}")
    
    def run_complete_refactoring(self):
        """Run the complete refactoring process."""
        print("=== LITIGATOR SOLO MICROSERVICE REFACTORING ===\n")
        
        print("Phase 1: Directory Setup")
        self.create_target_directories()
        
        print("\nPhase 2: File Movement")  
        self.move_files()
        
        print("\nPhase 3: Initialize Packages")
        self.create_init_files()
        
        print("\nPhase 4: Import Rewriting")
        self.rewrite_all_imports()
        
        print("\nPhase 5: Cleanup")
        self.cleanup_empty_directories()
        
        print("\nRefactoring complete!")
        print(f"Total import changes: {len(self.changes_log)}")
        
        # Write summary
        summary_path = self.project_root / 'refactoring_summary.txt'
        if not self.dry_run:
            with open(summary_path, 'w') as f:
                f.write("LITIGATOR SOLO REFACTORING SUMMARY\n")
                f.write("==================================\n\n")
                f.write(f"Files moved: {len(self.plan['file_moves'])}\n")
                f.write(f"Import changes: {len(self.changes_log)}\n\n")
                f.write("Import Changes:\n")
                for change in self.changes_log:
                    f.write(f"  - {change}\n")
            print(f"Summary written to: {summary_path.name}")

def main():
    parser = argparse.ArgumentParser(description='Refactor Litigator Solo to microservice architecture')
    parser.add_argument('--dry-run', action='store_true', help='Show what would be done without making changes')
    parser.add_argument('--rewrite-only', action='store_true', help='Only rewrite imports, skip file moves')
    parser.add_argument('--generate-script', action='store_true', help='Generate migration script only')
    parser.add_argument('--project-root', default='.', help='Project root directory')
    
    args = parser.parse_args()
    
    refactorer = FileRefactorer(args.project_root, args.dry_run)
    
    if args.generate_script:
        refactorer.generate_migration_script()
    elif args.rewrite_only:
        print("Rewriting imports only...")
        refactorer.rewrite_all_imports()
    else:
        refactorer.run_complete_refactoring()

if __name__ == '__main__':
    main()