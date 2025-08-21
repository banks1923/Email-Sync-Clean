# Code Transformation Tools Documentation

## Overview

This document outlines recommended tools and techniques for large-scale Python code transformations in the Email Sync system.

## Recommended Tool: LibCST

**LibCST** is the recommended tool for large-scale Python refactoring as it preserves formatting and comments perfectly.

### Installation
```bash
pip install libcst
```

### Common Use Cases

#### Import Statement Updates
```python
# Example: Update import paths after reorganization
import libcst as cst
from libcst import matchers as m

# Transform imports from old structure to new structure
old_import = "from src.app.core.services import gmail"
new_import = "from gmail import main"
```

#### Function/Variable Renaming
```python
# Rename functions across the codebase while preserving context
class RenameVisitor(cst.CSTTransformer):
    def leave_Name(self, original_node, updated_node):
        if updated_node.value == "old_function_name":
            return updated_node.with_changes(value="new_function_name")
        return updated_node
```

#### Class Refactoring
```python
# Move methods between classes or update class hierarchies
# while maintaining all formatting and comments
```

### Alternative Tools

#### Bowler (Facebook's Tool)
```bash
# Good for query-based transformations
bowler query "src/**/*.py" "import gmail.main" --select="import_stmt"
```

#### AST-based Tools
- **ast** module - Basic AST manipulation
- **astor** - AST to source code conversion
- **astunparse** - Another AST unparsing tool

### Best Practices

1. **Always backup code** before large transformations
2. **Test incrementally** - apply changes to small subsets first
3. **Preserve comments and formatting** - use LibCST over basic AST tools
4. **Validate syntax** after transformations
5. **Run tests** to ensure functional correctness

### Integration with Email Sync

The Email Sync system has used code transformation tools for:

- Directory reorganization (2025-08-17)
- Import path updates after service moves
- Function signature updates across services
- Configuration centralization

### Example Transformation Scripts

```python
#!/usr/bin/env python3
"""
Example transformation script using LibCST
"""
import libcst as cst
from pathlib import Path

def transform_imports(source_code: str) -> str:
    """Transform old import paths to new structure."""
    tree = cst.parse_expression(source_code)
    
    class ImportTransformer(cst.CSTTransformer):
        def leave_ImportFrom(self, original_node, updated_node):
            # Transform import paths here
            pass
    
    transformer = ImportTransformer()
    new_tree = tree.visit(transformer)
    return new_tree.code

# Apply to all Python files
for py_file in Path('.').rglob('*.py'):
    with open(py_file, 'r') as f:
        content = f.read()
    
    transformed = transform_imports(content)
    
    with open(py_file, 'w') as f:
        f.write(transformed)
```

### Safety Measures

1. **Git tracking** - ensure all changes are tracked
2. **Syntax validation** - parse each transformed file
3. **Test execution** - run test suite after transformations
4. **Manual review** - inspect a sample of changes before applying to all files

---

*This is a stub document. Actual transformation scripts are located in `tools/codemods/`.*
