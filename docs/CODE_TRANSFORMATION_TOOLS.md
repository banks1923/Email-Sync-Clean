# Code Transformation Tools

## LibCST - Large-Scale Python Refactoring

LibCST (Concrete Syntax Trees) is the recommended tool for large-scale Python code transformations in the Email Sync project. It preserves formatting, comments, and whitespace while making AST-based changes.

### Installation

```bash
pip install libcst
# or
pip install -r requirements-dev.txt
```

### Why LibCST over other tools?

| Tool | Pros | Cons | Use Case |
|------|------|------|----------|
| **LibCST** | Preserves formatting perfectly, modern & maintained, powerful visitor pattern | Steeper learning curve | Large-scale refactoring, import fixes |
| **Bowler** | Built on LibCST, simpler API | Less maintained, limited features | Simple renaming tasks |
| **ast** | Built-in Python, simple | Loses formatting and comments | Analysis only, not modification |
| **2to3/lib2to3** | Battle-tested | Python 2→3 focused, deprecated | Legacy migrations |
| **rope** | Powerful refactoring | Complex setup, slower | IDE-level refactoring |

### Example: Fix Broken Imports

```python
import libcst as cst
from typing import Sequence

class ImportFixer(cst.CSTTransformer):
    """Fix common import issues in the codebase."""
    
    def leave_ImportFrom(self, original_node: cst.ImportFrom, 
                        updated_node: cst.ImportFrom) -> cst.ImportFrom:
        """Transform broken import statements."""
        
        # Fix shared.simple_db imports
        if updated_node.module and updated_node.module.value == "shared.simple_db":
            # Change to: from shared.simple_db import SimpleDB
            return updated_node.with_changes(
                module=cst.Attribute(
                    value=cst.Name("shared"),
                    attr=cst.Name("simple_db")
                ),
                names=cst.ImportStar() if isinstance(updated_node.names, cst.ImportStar)
                       else [cst.ImportAlias(name=cst.Name("SimpleDB"))]
            )
        
        return updated_node

# Apply the transformation
def fix_imports_in_file(filepath: str):
    with open(filepath, 'r') as f:
        source = f.read()
    
    module = cst.parse_module(source)
    modified = module.visit(ImportFixer())
    
    with open(filepath, 'w') as f:
        f.write(modified.code)
```

### Common Patterns

#### 1. Find and Replace Imports
```python
# Replace all occurrences of an import
class ReplaceImport(cst.CSTTransformer):
    def leave_ImportFrom(self, original_node, updated_node):
        if updated_node.module and updated_node.module.value == "old.module":
            return updated_node.with_changes(
                module=cst.parse_expression("new.module")
            )
        return updated_node
```

#### 2. Add Missing Imports
```python
# Add an import if it doesn't exist
class AddImport(cst.CSTTransformer):
    def leave_Module(self, original_node, updated_node):
        # Check if import exists
        has_import = any(
            isinstance(stmt, cst.ImportFrom) and 
            stmt.module and stmt.module.value == "typing"
            for stmt in updated_node.body
        )
        
        if not has_import:
            # Add at the top after other imports
            new_import = cst.ImportFrom(
                module=cst.Name("typing"),
                names=[cst.ImportAlias(name=cst.Name("Optional"))]
            )
            return updated_node.with_changes(
                body=[new_import, *updated_node.body]
            )
        return updated_node
```

#### 3. Rename Functions/Classes
```python
# Rename all occurrences of a function
class RenameFunction(cst.CSTTransformer):
    def leave_Name(self, original_node, updated_node):
        if updated_node.value == "old_function_name":
            return updated_node.with_changes(value="new_function_name")
        return updated_node
```

### Running LibCST on Multiple Files

```python
import os
from pathlib import Path

def transform_codebase(transformer_class, file_pattern="*.py"):
    """Apply a LibCST transformer to all matching files."""
    
    for filepath in Path(".").rglob(file_pattern):
        # Skip virtual environments and caches
        if any(skip in str(filepath) for skip in 
               ['venv', '__pycache__', '.git', 'node_modules']):
            continue
            
        try:
            with open(filepath, 'r') as f:
                source = f.read()
            
            module = cst.parse_module(source)
            modified = module.visit(transformer_class())
            
            if module.code != modified.code:
                with open(filepath, 'w') as f:
                    f.write(modified.code)
                print(f"✅ Fixed: {filepath}")
                
        except Exception as e:
            print(f"❌ Error in {filepath}: {e}")

# Usage
transform_codebase(ImportFixer)
```

### Integration with Email Sync Workflow

1. **Dependency Analysis**: Use `dependency_mapper.py` to find issues
2. **Create Transformer**: Write LibCST transformer for the specific issue
3. **Test on Sample**: Test transformer on a few files first
4. **Run on Codebase**: Apply to entire codebase
5. **Verify**: Run tests and linters to ensure correctness

### Best Practices

1. **Always backup before large transformations**
   ```bash
   git add -A && git commit -m "Backup before LibCST transformation"
   ```

2. **Test transformers on sample files first**
   ```python
   # Test on one file before running on entire codebase
   fix_imports_in_file("test_file.py")
   ```

3. **Use matchers for complex patterns**
   ```python
   import libcst.matchers as m
   
   # Match specific import patterns
   if m.matches(node, m.ImportFrom(module=m.Name("shared"))):
       # Handle shared module imports
   ```

4. **Preserve metadata and comments**
   ```python
   # LibCST preserves these by default, but be careful with
   # with_changes() to not accidentally remove them
   ```

### Real-World Example: Email Sync Import Cleanup

This actual codemod was used to fix 107 broken imports in the Email Sync project:

```python
import libcst as cst
import re

class EmailSyncImportFixer(cst.CSTTransformer):
    """Fix all broken imports identified by dependency analysis."""
    
    # Map of broken imports to correct imports
    IMPORT_FIXES = {
        r"shared\.simple_db": "from shared.simple_db import SimpleDB",
        r"gmail\.main": "from gmail import get_gmail_service",
        r"pdf\.main": "from pdf import get_pdf_service",
        r"entity\.main": "from entity import get_entity_service",
        # ... more mappings
    }
    
    def leave_ImportFrom(self, original_node, updated_node):
        if not updated_node.module:
            return updated_node
            
        module_str = self._get_module_string(updated_node.module)
        
        for pattern, replacement in self.IMPORT_FIXES.items():
            if re.match(pattern, module_str):
                # Parse the replacement and return new node
                new_import = cst.parse_statement(replacement)
                return new_import
                
        return updated_node
    
    def _get_module_string(self, module):
        """Convert module node to string for matching."""
        if isinstance(module, cst.Name):
            return module.value
        elif isinstance(module, cst.Attribute):
            return f"{self._get_module_string(module.value)}.{module.attr.value}"
        return ""
```

### Debugging LibCST Transformations

```python
# Enable verbose mode to see what's being transformed
import libcst as cst

# Print the tree structure
module = cst.parse_module("from shared.simple_db import *")
print(module)  # Shows the CST structure

# Use the interactive matcher
from libcst import matchers as m
print(m.findall(module, m.ImportFrom()))  # Find all imports

# Test transformations step by step
transformer = ImportFixer()
result = module.visit(transformer)
print(result.code)  # See the transformed code
```

### Resources

- [LibCST Documentation](https://libcst.readthedocs.io/)
- [LibCST Codemods Tutorial](https://libcst.readthedocs.io/en/latest/codemods_tutorial.html)
- [LibCST Matchers Guide](https://libcst.readthedocs.io/en/latest/matchers_tutorial.html)

---

**Note**: LibCST is particularly powerful for the Email Sync project's needs:
- Fixing import statements after directory restructuring
- Renaming services and factory functions
- Adding type hints systematically
- Removing dead code while preserving formatting
- Enforcing consistent code patterns