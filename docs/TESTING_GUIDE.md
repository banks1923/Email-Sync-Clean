# Testing Guide - Email Sync System

## Quick Start - Fast Testing

For daily development and CI/CD, use the categorized test commands:

```bash
# Fast unit tests (recommended for TDD)
make test-unit        # 77 tests in ~10-15 seconds

# System health checks
make test-smoke       # 22 tests in ~8 seconds

# Fast quality pipeline (CI/CD optimized)
make test-fast        # Unit + Integration tests

# Standard quality check
make check            # Format + Lint + Type-check + Fast tests
```

## Complete Command Reference

### Testing Commands

| Command | Description | Tests | Duration |
|---------|-------------|-------|----------|
| `make test-unit` | Unit tests (fast, isolated) | 77 | ~10-15s |
| `make test-smoke` | System health checks | 22 | ~8s |
| `make test-integration` | Cross-service tests | 1 | ~5s |
| `make test-slow` | Performance, AI models | Variable | Minutes |
| `make test-fast` | **CI/CD optimized pipeline** | 78 | ~15-20s |
| `make test` | Full test suite | 405 | 2+ minutes |
| `make test-coverage` | Tests with coverage report | 405 | 3+ minutes |

### Quality Commands

| Command | Description | Speed |
|---------|-------------|-------|
| `make check` | **Fast quality checks (recommended)** | ~1-2 minutes |
| `make check-full` | Comprehensive quality checks (all tests) | ~5+ minutes |
| `make lint-all` | Run all linters | ~10s |
| `make lint-fix` | Auto-fix linting issues | ~15s |
| `make type-check` | Type checking with mypy | ~10s |
| `make format-advanced` | Complete code formatting | ~30s |

### Utility Commands

| Command | Description |
|---------|-------------|
| `make cleanup` | Complete code cleanup pipeline |
| `make fix-all` | Auto-fix all possible issues |
| `make clean` | Clean caches and generated files |
| `make security-check` | Run security analysis |

## Test Categories

### Unit Tests (`@pytest.mark.unit`)
- **Purpose**: Fast, isolated tests
- **Count**: 77 tests
- **Duration**: 10-15 seconds
- **Use for**: TDD, local development, CI pre-checks
- **Includes**: Database operations, document processing, system health

### Integration Tests (`@pytest.mark.integration`)  
- **Purpose**: Cross-service functionality
- **Count**: 1 test
- **Duration**: ~5 seconds
- **Use for**: API interactions, service integration

### Slow Tests (`@pytest.mark.slow`)
- **Purpose**: Performance tests, AI model tests
- **Count**: Variable
- **Duration**: Minutes
- **Use for**: Performance validation, model accuracy
- **Includes**: Legal BERT tests, large-scale processing

### Smoke Tests (Directory-based)
- **Purpose**: System health verification
- **Count**: 22 tests  
- **Duration**: 8 seconds
- **Use for**: Deployment verification, environment checks

## Development Workflows

### Test-Driven Development (TDD)
```bash
# Write failing test
make test-unit              # Run fast tests to see failure

# Implement feature  
make test-unit              # Verify implementation

# Quick quality check
make check                  # Ensure no regressions
```

### Pre-Commit Workflow
```bash
# Before committing changes
make fix-all                # Auto-fix all issues
make check                  # Run fast quality pipeline
```

### CI/CD Pipeline
```bash
# Stage 1: Fast feedback (runs in ~20 seconds)
make test-fast

# Stage 2: Full validation (runs in parallel)
make test-slow              # Performance tests
make security-check         # Security validation
make test-coverage          # Coverage analysis
```

### Local Development
```bash
# Quick health check
make test-smoke

# Feature development
make test-unit

# Integration verification  
make test-integration

# Final validation
make check
```

## Test Execution Examples

### Fast Development Cycle
```bash
# Make code changes...
make test-unit              # ✅ 77 tests in 15s
make lint-fix               # ✅ Auto-fix issues  
git commit -m "feature: ..."
```

### Pre-Release Validation
```bash
make cleanup                # Clean up code
make check-full             # Full quality check
make test-coverage          # Coverage analysis
```

### Debugging Test Failures
```bash
# Run specific test category
make test-unit              # Check unit test health
make test-smoke             # Check system health
make test-integration       # Check service integration

# Individual pytest commands for debugging
pytest -m "unit" -v -k "test_name"
pytest tests/smoke/ -v -s
```

## Test Markers Reference

The test suite uses pytest markers for categorization:

```python
@pytest.mark.unit          # Fast, isolated tests
@pytest.mark.integration   # Cross-service tests  
@pytest.mark.slow          # Performance/AI tests
@pytest.mark.requires_auth # Authentication needed
@pytest.mark.requires_models # AI models needed
```

## Performance Metrics

| Test Category | Count | Typical Duration | Use Case |
|---------------|-------|------------------|----------|
| Unit | 77 | 10-15s | Daily development |
| Smoke | 22 | 8s | Health checks |
| Integration | 1 | 5s | Service validation |
| Fast Pipeline | 78 | 15-20s | CI/CD |
| Full Suite | 405 | 2+ minutes | Release validation |

## Tips for Efficient Testing

1. **Use `make test-unit` for TDD** - Fastest feedback loop
2. **Use `make test-smoke` for health checks** - Quick system validation
3. **Use `make test-fast` for CI/CD** - Optimal balance of speed and coverage
4. **Use `make check` instead of `make check-full`** for daily work
5. **Run `make test-slow` separately** - Don't block on performance tests
6. **Use specific markers** - `pytest -m "unit and not slow"` for custom combinations

## Troubleshooting

### Tests Taking Too Long
- Use `make test-unit` instead of `make test`
- Run `make test-slow` separately
- Check for infinite loops in failing tests

### Test Failures
- Start with `make test-smoke` to check system health
- Use `make test-unit` to isolate unit test issues
- Check database isolation if seeing data contamination

### CI/CD Optimization
- Use `make test-fast` for fast feedback
- Run comprehensive tests in parallel stages
- Cache dependencies and test databases

---

*For detailed API documentation, see [SERVICES_API.md](SERVICES_API.md)*