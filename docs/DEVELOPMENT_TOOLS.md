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
                print(f"WORKING: Fixed: {filepath}")
                
        except Exception as e:
            print(f" Error in {filepath}: {e}")

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
- Enforcing consistent code patterns# Recommended Additional Dependencies

##  Code Quality & Analysis

### Already Have WORKING:
- ruff, black, isort (formatting/linting)
- mypy (type checking)
- bandit (security)
- flake8 (style)
- pytest (testing)
- vulture (dead code) - installed separately

### Should Consider Adding CURRENT:

#### 1. **Coverage Analysis**
```bash
pip install coverage-badge  # Generate coverage badges
pip install diff-cover      # Coverage for only changed code
```
- Shows coverage on PRs/commits
- Focuses on new code quality

#### 2. **Complexity Analysis**
```bash
pip install radon           # Code complexity metrics
pip install xenon           # Complexity monitoring with thresholds
```
- Cyclomatic complexity tracking
- Maintainability index
- Enforces max complexity limits

#### 3. **Documentation**
```bash
pip install interrogate     # Docstring coverage checker
pip install mkdocs          # Generate documentation site
pip install mkdocs-material # Beautiful Material theme
```
- Ensures all functions are documented
- Auto-generates docs from code

#### 4. **Performance Profiling**
```bash
pip install py-spy          # Sampling profiler (no code changes needed)
pip install memory-profiler # Line-by-line memory usage
pip install scalene         # CPU + GPU + memory profiler
```
- Find performance bottlenecks
- Memory leak detection
- Real-time profiling

#### 5. **Dependency Management**
```bash
pip install pip-audit       # Security vulnerabilities in dependencies
pip install pipdeptree      # Visualize dependency tree
pip install pip-autoremove  # Remove unused dependencies
```
- Security scanning
- Clean dependency management
- Conflict detection

## READY: Development Productivity

### Should Consider Adding CURRENT:

#### 6. **Development Tools**
```bash
pip install ipdb            # Better Python debugger
pip install rich            # Beautiful terminal output
pip install typer           # Modern CLI building (better than argparse)
pip install python-Levenshtein  # Fast string similarity (for search)
```
- Enhanced debugging experience
- Better CLI output formatting
- Improved search capabilities

#### 7. **Async & Parallel Processing**
```bash
pip install aiofiles        # Async file operations
pip install asyncpg         # Async PostgreSQL (future migration)
pip install concurrent-log-handler  # Thread-safe logging
```
- Better async support
- Prepared for scaling

#### 8. **Data Validation**
```bash
pip install pydantic        # Data validation using Python type annotations
pip install marshmallow     # Object serialization/deserialization
```
- Runtime type validation
- API data validation
- Config validation

## STATUS: Monitoring & Observability

### Should Consider Adding CURRENT:

#### 9. **Logging & Monitoring**
```bash
pip install structlog       # Structured logging
pip install sentry-sdk      # Error tracking and monitoring
pip install prometheus-client  # Metrics export
```
- Better log analysis
- Error tracking in production
- Performance metrics

#### 10. **Database Tools**
```bash
pip install alembic         # Database migrations
pip install sqlalchemy      # ORM (if moving from raw SQL)
pip install dataset         # Simple database toolkit
```
- Schema versioning
- Migration management
- Database abstraction

## TESTING: Testing Enhancements

### Should Consider Adding CURRENT:

#### 11. **Advanced Testing**
```bash
pip install hypothesis      # Property-based testing
pip install faker           # Generate fake data for tests
pip install freezegun       # Mock datetime for tests
pip install responses       # Mock HTTP responses
pip install pytest-benchmark  # Benchmark tests
pip install pytest-timeout  # Timeout long-running tests
```
- Generate test cases automatically
- Better test data
- Performance regression testing

#### 12. **Code Quality CI/CD**
```bash
pip install tox             # Test across Python versions
pip install nox             # Modern tox alternative
pip install commitizen      # Conventional commits
pip install pre-commit-hooks  # Additional pre-commit checks
```
- Multi-environment testing
- Standardized commits
- Automated checks

##  Security Enhancements

### Should Consider Adding CURRENT:

#### 13. **Security Tools**
```bash
pip install detect-secrets  # Detect secrets in code
pip install cryptography    # Encryption support
pip install python-jose     # JWT tokens
```
- Prevent credential leaks
- Secure data handling
- Authentication tokens

##  Recommended Installation Groups

### Minimal Quality Enhancement
```bash
pip install coverage-badge diff-cover radon interrogate pip-audit
```

### Development Productivity
```bash
pip install ipdb rich typer pydantic structlog
```

### Testing Enhancement
```bash
pip install hypothesis faker freezegun pytest-benchmark
```

### Full Stack (All Recommended)
```bash
# Create requirements-enhanced.txt with all recommendations
pip install -r requirements-enhanced.txt
```

## CURRENT: Top 5 Priorities for Your Project

Based on your Email Sync system with legal document processing:

1. **pydantic** - Data validation for legal metadata
2. **structlog** - Better logging for audit trails
3. **interrogate** - Ensure all code is documented
4. **py-spy** - Profile performance bottlenecks
5. **pip-audit** - Security scanning for dependencies

##  Update Makefile

Add new commands to your Makefile:
```makefile
complexity-check: ## Check code complexity
 radon cc . -s -nb
 xenon . --max-absolute B --max-modules A --max-average A

doc-coverage: ## Check documentation coverage
 interrogate -vv .

security-audit: ## Audit dependencies for vulnerabilities
 pip-audit
 detect-secrets scan

profile: ## Profile the application
 py-spy record -o profile.svg -- python scripts/vsearch search "test"

deps-tree: ## Show dependency tree
 pipdeptree --graph-output png > dependencies.png
```

##  Pre-commit Config Update

Add to `.pre-commit-config.yaml`:
```yaml
repos:
  - repo: https://github.com/econchick/interrogate
    rev: 1.5.0
    hooks:
      - id: interrogate
        args: [--fail-under=80]

  - repo: https://github.com/Yelp/detect-secrets
    rev: v1.4.0
    hooks:
      - id: detect-secrets
        args: ['--baseline', '.secrets.baseline']
```

##  Implementation Strategy

1. **Start Small**: Add 2-3 tools at a time
2. **Test Integration**: Ensure they work with your workflow
3. **Document Usage**: Update README with new commands
4. **Team Training**: If working with others, document conventions
5. **CI/CD Integration**: Add to GitHub Actions or other CI

##  Quick Wins

These will have immediate impact:
```bash
# Install these first
pip install rich pydantic interrogate pip-audit

# Run these commands
interrogate -vv .  # See documentation coverage
pip-audit          # Check security vulnerabilities
```

Your codebase is already well-structured. These tools will help maintain and improve quality as it grows!
