# Automated Code Cleanup Documentation

## Overview

The Email Sync system includes comprehensive automated cleanup tools to maintain code quality and consistency.

## Available Commands

### Quick Commands
```bash
make cleanup        # Complete automated cleanup pipeline
make fix-all        # Auto-fix all possible issues + format
make check          # Quality checks + tests (no modifications)
```

### Individual Tools
```bash
make lint-fix       # Auto-fix linting issues where possible
make format-advanced # Advanced formatting with all cleanup tools
make docs-fix       # Auto-fix markdown documentation issues
```

## Tools Used

- **autoflake**: Remove unused imports and variables
- **pyupgrade**: Upgrade Python syntax to modern standards
- **docformatter**: Format docstrings consistently
- **isort**: Sort and organize imports
- **black**: Format Python code
- **ruff**: Modern Python linter with auto-fix
- **markdownlint**: Markdown documentation linting

## Configuration

All tool configurations are centralized in the `.config/` directory:

- `.config/.flake8` - Flake8 linting rules
- `.config/mypy.ini` - MyPy type checking settings
- `.config/pytest.ini` - Pytest configuration
- `.config/.markdownlint.json` - Markdown style rules
- `.config/.coveragerc` - Coverage.py configuration

## CI Integration

The cleanup tools integrate with:
- Pre-commit hooks
- Make targets for development workflows
- Documentation audit system

## Best Practices

1. Run `make check` before committing changes
2. Use `make cleanup` for comprehensive code improvements
3. Address linting issues promptly to prevent drift
4. Review auto-generated changes before committing

---

*This is a generated stub. The actual cleanup system is implemented through Make targets and configuration files.*
