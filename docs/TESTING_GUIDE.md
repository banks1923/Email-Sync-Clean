# Testing Guide

## Testing Philosophy

- **Test Real Functionality**: Avoid mocks when possible
- **Integration > Unit**: Test workflows, not implementation details
- **Comprehensive Verification**: Use `verify_pipeline.py` for full system validation
- **Fast Feedback**: Quick smoke tests before deep validation

## Test Organization

```
tests/
├── infrastructure/
│   └── database/           # SimpleDB tests (52 tests)
│       ├── test_simple_db_core.py        # Core CRUD/search
│       ├── test_simple_db_intelligence.py # Intelligence features
│       └── test_simple_db_performance.py  # Performance tests
├── services/
│   └── search/            # Search service tests
├── integration/           # End-to-end workflow tests
├── smoke/                # Quick health checks
├── test_email_parser.py  # Email parsing unit tests (16 tests)
├── test_email_integration.py  # Email integration (4 tests)
├── test_email_coverage.py     # Email edge cases (18 tests)
├── test_validators.py         # Input validation (222 tests)
├── simple_mcp_validation.py   # MCP validation
└── run_mcp_tests.py          # All MCP tests
```

## Essential Test Commands

### Quick Validation (< 1 minute)
```bash
# Verify core services are working
python3 -c "from lib.db import SimpleDB; db = SimpleDB(); print('✅ DB working')"
python3 -c "from lib.search import search; print('✅ Search working')"
python3 -c "from lib.embeddings import get_embedding_service; print('✅ Embeddings working')"

# Quick smoke test
python3 scripts/verify_pipeline.py --quick
```

### System Validation
```bash
# Full pipeline verification (comprehensive)
python3 scripts/verify_pipeline.py

# CI-friendly JSON output
python3 scripts/verify_pipeline.py --json

# Trace specific document through pipeline
python3 scripts/verify_pipeline.py --trace abc123

# Vector sync verification
make preflight-vector-parity
```

### Database Tests
```bash
# All SimpleDB tests (52 tests)
pytest tests/infrastructure/database/

# Specific test categories
pytest tests/infrastructure/database/test_simple_db_core.py      # CRUD operations
pytest tests/infrastructure/database/test_simple_db_intelligence.py  # Advanced features
pytest tests/infrastructure/database/test_simple_db_performance.py   # Performance

# Run with coverage
pytest tests/infrastructure/database/ --cov=shared.db --cov-report=html
```

### Email Processing Tests
```bash
# Email parser unit tests (16 tests)
python3 tests/test_email_parser.py

# Email integration tests (4 tests)
python3 tests/test_email_integration.py

# Email edge cases (18 tests)
python3 tests/test_email_coverage.py

# All email tests with coverage (97%+ coverage)
coverage run -m pytest tests/test_email*.py
coverage report
coverage html  # Generate HTML report
```

### Input Validation Tests
```bash
# All validation tests (222 tests)
pytest tests/test_validators.py

# Run only fuzz tests
pytest tests/test_validators.py -k fuzz

# Test specific edge cases
pytest tests/test_validators.py::TestEdgeCases

# Run with verbose output
pytest tests/test_validators.py -v

# Check validation coverage
pytest tests/test_validators.py --cov=lib.validators
```

### MCP Server Tests
```bash
# Basic MCP validation
python3 tests/simple_mcp_validation.py

# Complete MCP test suite
python3 tests/run_mcp_tests.py

# Test MCP parameter mapping
python3 tests/services/search/test_search_intelligence_mcp.py
```

### Integration Tests
```bash
# End-to-end workflows
pytest tests/integration/

# Search integration
pytest tests/integration/test_search_integration.py

# Pipeline integration
pytest tests/integration/test_pipeline_integration.py
```

## Test Coverage

### Current Coverage Stats
- **SimpleDB**: 52 tests across 3 modules (95%+ coverage)
- **Email Parsing**: 34 tests with 97% coverage
- **Input Validation**: 222 tests with 92% coverage
- **Integration Tests**: MCP parameter mapping and workflows
- **System Tests**: Full pipeline validation via `verify_pipeline.py`

### Generate Coverage Reports
```bash
# Install coverage tool
pip install coverage

# Run all tests with coverage
coverage run -m pytest tests/

# Generate terminal report
coverage report

# Generate HTML report
coverage html
open htmlcov/index.html  # View in browser

# Check specific module coverage
coverage run -m pytest tests/infrastructure/database/
coverage report --include="shared/db/*"
```

## Continuous Integration

### Pre-commit Checks
```bash
# Run all pre-commit hooks
pre-commit run --all-files

# Run specific hooks
pre-commit run black --all-files
pre-commit run flake8 --all-files
pre-commit run mypy --all-files
```

### CI Environment Variables
```bash
# For fast CI runs
export TEST_MODE=1           # Use mock services
export SKIP_MODEL_LOAD=1     # Skip model loading
export QDRANT_DISABLED=1     # Use mock vector store

# Run tests in CI mode
TEST_MODE=1 pytest tests/
```

### GitHub Actions Workflow
```yaml
name: Tests
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    env:
      TEST_MODE: 1
      SKIP_MODEL_LOAD: 1
    steps:
      - uses: actions/checkout@v2
      - uses: actions/setup-python@v2
      - run: pip install -r requirements.txt
      - run: pytest tests/
```

## Performance Testing

### Benchmark Commands
```bash
# Database performance
python3 tests/infrastructure/database/test_simple_db_performance.py

# Search performance
python3 scripts/benchmark_search.py

# Embedding generation speed
python3 scripts/data/generate_embeddings.py --benchmark
```

### Load Testing
```bash
# Bulk insert test
python3 tests/performance/test_bulk_insert.py

# Concurrent read test
python3 tests/performance/test_concurrent_reads.py

# Vector search performance
python3 tests/performance/test_vector_search.py
```

## Debugging Failed Tests

### Verbose Output
```bash
# Run with detailed output
pytest tests/ -vv

# Show print statements
pytest tests/ -s

# Stop on first failure
pytest tests/ -x

# Enter debugger on failure
pytest tests/ --pdb
```

### Specific Test Isolation
```bash
# Run single test file
pytest tests/test_validators.py

# Run single test class
pytest tests/test_validators.py::TestValidation

# Run single test method
pytest tests/test_validators.py::TestValidation::test_query_validation
```

### Environment Debugging
```bash
# Check environment
python3 -c "import sys; print(sys.path)"
python3 -c "from lib.db import SimpleDB; print(SimpleDB().get_db_path())"

# Verify database schema
sqlite3 data/system_data/emails.db ".schema"

# Check Qdrant status
curl http://localhost:6333/collections
```

## Test Writing Guidelines

### Good Test Structure
```python
def test_search_with_filters():
    """Test that search properly applies filters."""
    # Arrange
    db = SimpleDB()
    test_data = create_test_data()
    
    # Act
    results = search("query", filters={"type": "email"})
    
    # Assert
    assert len(results) > 0
    assert all(r["type"] == "email" for r in results)
```

### Test Naming Conventions
- `test_<what>_<condition>_<expected>`: e.g., `test_search_with_empty_query_returns_empty`
- Use descriptive names that explain the test purpose
- Group related tests in classes

### Test Data Management
- Use fixtures for shared test data
- Clean up after tests (use try/finally or pytest fixtures)
- Avoid hardcoded paths - use `tempfile` or fixtures
- Use TEST_MODE environment variable for safe testing

## Troubleshooting

### Common Issues

**Import Errors**
```bash
# Fix Python path
export PYTHONPATH="${PYTHONPATH}:$(pwd)"

# Verify imports
python3 -c "from lib.search import search"
```

**Database Lock Errors**
```bash
# Check for locked database
lsof data/system_data/emails.db

# Reset database (careful!)
make reset-test-db
```

**Qdrant Connection Errors**
```bash
# Check Qdrant status
make qdrant-status

# Restart Qdrant
make restart-qdrant

# Use mock for testing
QDRANT_DISABLED=1 pytest tests/
```

## Test Maintenance

### Regular Tasks
1. Run full test suite before commits
2. Update tests when changing functionality
3. Monitor test coverage trends
4. Remove obsolete tests
5. Refactor slow tests

### Test Review Checklist
- [ ] Tests are independent (no order dependencies)
- [ ] Tests clean up after themselves
- [ ] Tests use appropriate assertions
- [ ] Tests have descriptive names
- [ ] Tests cover edge cases
- [ ] Tests run quickly (< 0.1s per unit test)

## Resources

- [Pytest Documentation](https://docs.pytest.org/)
- [Coverage.py Documentation](https://coverage.readthedocs.io/)
- [Python Testing Best Practices](https://realpython.com/pytest-python-testing/)
- Project-specific: [docs/PIPELINE_VERIFICATION.md](PIPELINE_VERIFICATION.md)