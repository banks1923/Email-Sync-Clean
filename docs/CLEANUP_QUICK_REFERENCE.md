# Cleanup Quick Reference

## Essential Commands

```bash
# One-command solutions (AI should use these first)
make cleanup        # Complete automated cleanup pipeline
make fix-all        # Auto-fix all possible issues + format
make check          # Quality checks + tests (no modifications)
```

## Step-by-Step Cleanup

```bash
# 1. Fix linting issues
make lint-fix

# 2. Advanced code formatting
make format-advanced

# 3. Fix documentation
make docs-fix

# 4. Verify everything works
make check
```

## Specific Tools

| Command | Purpose | Safe? |
|---------|---------|-------|
| `make lint-all` | Show all linting issues | ✅ Read-only |
| `make lint-fix` | Auto-fix linting issues | ⚠️ Modifies files |
| `make type-check` | Run MyPy type checking | ✅ Read-only |
| `make docs-check` | Check markdown style | ✅ Read-only |
| `make docs-fix` | Fix markdown issues | ⚠️ Modifies files |
| `make complexity-check` | Analyze code complexity | ✅ Read-only |

## Quick Quality Check

```bash
# Before committing - comprehensive check
make check

# Fast check for CI/CD
make test-fast
```

## Configuration Files

- `.config/.flake8` - Linting rules
- `.config/mypy.ini` - Type checking
- `.config/.markdownlint.json` - Docs style
- `pyproject.toml` - Tool settings

## Emergency Reset

```bash
# Clean all caches and generated files
make clean

# Start fresh
git checkout -- .
make setup
```

---

*Quick reference for AI agents and developers working on the Email Sync system.*
