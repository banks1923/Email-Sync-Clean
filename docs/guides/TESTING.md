# Testing Guide - Email Sync System

## Quick Start - Simplified Commands

For daily development, use the streamlined make commands:

```bash
# Daily development workflow
make test           # Run fast tests
make format         # Format code
make lint           # Check code quality
make fix            # Auto-fix common issues
make clean          # Clean up cache files
```

## Complete Command Reference

### Essential Commands (Makefile v2.0)

| Command | Description | Usage |
|---------|-------------|-------|
| `make setup` | Complete setup from scratch | First-time setup |
| `make test` | Run fast tests (no slow AI tests) | Daily development |
| `make format` | Format code (black, isort, docformatter) | Before commits |
| `make lint` | Check code quality (flake8, ruff, mypy) | Quality checks |
| `make fix` | Auto-fix issues and format | Fix problems |
| `make clean` | Clean up cache files | Maintenance |
| `make status` | Quick system health check | Diagnostics |
| `make diagnose` | Deep system diagnostic | Troubleshooting |

### Advanced Testing (Direct CLI)

For more detailed testing, use pytest directly:

```bash
# Fast tests (excludes slow AI/integration tests)
pytest -c .config/pytest.ini -m "not slow" -v --tb=short

# Full test suite (including slow tests)
pytest -c .config/pytest.ini -v

# Specific test categories
pytest tests/test_search_intelligence.py -v      # Search tests
pytest tests/test_legal_intelligence.py -v      # Legal tests
pytest tests/test_email_parser.py -v            # Email parsing tests

# With coverage
pytest tests/ --cov=. --cov-report=html
```
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
make test-unit              # WORKING: 77 tests in 15s
make lint-fix               # WORKING: Auto-fix issues  
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

*For detailed API documentation, see [SERVICES_API.md](SERVICES_API.md)*# Test Coverage Analysis - Email Sync System
Generated: 2025-08-16

## Current Test Status

### Overall Metrics
- **Total Test Files**: 79
- **Tests Collected**: 445
- **Import Errors**: 26 (due to architecture refactoring)
- **Success Rate**: Cannot determine until import errors fixed

### Test Categories

#### 1. WORKING: Working Tests (23 files)
Tests that should be working with the new architecture:

##### Core Service Tests
- `test_imports.py` - Import validation
- `test_perf_decorator.py` - Performance decorator
- `test_vsearch_cli_output.py` - CLI output validation
- `test_interface_implementation.py` - Interface contracts

##### Intelligence Services
- `test_search_intelligence.py` - Search intelligence service
- `test_legal_intelligence.py` - Legal intelligence service
- `test_legal_intelligence_mcp.py` - Legal MCP server
- `test_intelligence_schema.py` - Intelligence database schema

##### Document Processing
- `test_summarization.py` - Document summarization
- `test_summarization_integration.py` - Summarization integration
- `test_timeline_extractor.py` - Timeline extraction
- `test_pipeline_orchestrator.py` - Pipeline orchestration

##### Knowledge Graph
- `test_knowledge_graph.py` - Knowledge graph service
- `test_legal_bert_integration.py` - Legal BERT integration
- `test_similarity_analyzer.py` - Similarity analysis
- `test_graph_queries.py` - Graph query operations

##### Caching System
- `test_cache_manager.py` - Cache manager
- `test_memory_cache.py` - Memory cache
- `test_file_cache.py` - File cache
- `test_database_cache.py` - Database cache

##### Utilities
- `test_logging_interop.py` - Logging interoperability
- `test_context_binding.py` - Context binding
- `shared_test_fixtures.py` - Shared test fixtures

#### 2.  Broken Tests (26 files with import errors)
Tests failing due to old architecture imports (`src.app.core.*`):

##### Integration Tests (Deprecated Structure)
- `tests/integration/legal/test_email_content_fix.py`
- `tests/integration/legal/test_fixed_processing.py`
- `tests/integration/legal/test_legal_metadata_vectors.py`
- `tests/integration/legal/test_legal_search.py`
- `tests/integration/test_optimization_validation.py`

##### PDF Service Tests (Need Updates)
- `tests/pdf_service/test_end_to_end_pipeline.py`
- `tests/pdf_service/test_large_pdf_handling.py`
- `tests/pdf_service/test_pdf_corruption_detection.py`
- `tests/pdf_service/test_pdf_database.py`
- `tests/pdf_service/test_pdf_service.py`

##### Gmail Service Tests (Need Updates)
- `tests/gmail_service/*` (10+ files)

##### Vector Service Tests (Need Updates)
- `tests/vector_service/*` (8+ files)

## Coverage Gaps Identified

### 1. Critical Missing Tests

#### MCP Servers
- [ ] Search Intelligence MCP Server (Task 10)
- [ ] Timeline MCP Server integration
- [ ] Entity extraction MCP Server
- [ ] Knowledge Graph MCP Server

#### New Services (Flat Architecture)
- [ ] `embeddings/` service tests
- [ ] `search/` service tests
- [ ] `vector_store/` service tests
- [ ] `entity/` service tests
- [ ] `notes/` service tests
- [ ] `monitoring/` service tests

#### Document Pipeline (Task 14)
- [ ] Pipeline stage transitions (raw → staged → processed)
- [ ] Quarantine handling
- [ ] Export system tests
- [ ] Document validation tests

#### CLI Handlers
- [ ] `scripts/cli/search_handler.py`
- [ ] `scripts/cli/upload_handler.py`
- [ ] `scripts/cli/process_handler.py`
- [ ] `scripts/cli/info_handler.py`
- [ ] `scripts/cli/intelligence_handler.py`
- [ ] `scripts/cli/legal_handler.py`

### 2. Integration Tests Needed

#### End-to-End Workflows
- [ ] Complete document ingestion (upload → process → search)
- [ ] Legal case analysis workflow
- [ ] Email sync and processing
- [ ] PDF OCR and text extraction
- [ ] Transcription pipeline

#### Cross-Service Integration
- [ ] Search + Intelligence + Embeddings
- [ ] Legal Intelligence + Knowledge Graph
- [ ] Timeline + Entity Extraction
- [ ] Caching layers interaction

### 3. Performance Tests Needed

- [ ] Batch processing performance
- [ ] Embedding generation speed
- [ ] Search query performance
- [ ] Cache hit/miss ratios
- [ ] Database query optimization

## Priority Fix List

### Phase 1: Fix Import Errors (Immediate)
1. Update all `src.app.core.*` imports to new flat structure
2. Update PDF service test imports
3. Update Gmail service test imports
4. Update Vector service test imports

### Phase 2: Add Critical Tests (High Priority)
1. MCP server integration tests
2. New flat architecture service tests
3. Document pipeline tests
4. CLI handler tests

### Phase 3: Integration Tests (Medium Priority)
1. End-to-end workflow tests
2. Cross-service integration tests
3. Performance benchmarks

## Test Execution Strategy

### Local Testing
```bash
# Run all tests
python3 -m pytest tests/ -v

# Run specific category
python3 -m pytest tests/test_search_intelligence.py -v

# Run with coverage
python3 -m pytest tests/ --cov=. --cov-report=html

# Run only working tests (skip broken)
python3 -m pytest tests/ -k "not integration and not pdf_service and not gmail_service and not vector_service"
```

### Patching Factories for Legal Intelligence

Some tests need to replace heavyweight services with light doubles. The Legal Intelligence module exposes two small, patchable factory functions you can override in tests:

- `legal_intelligence.main.get_knowledge_graph_service(db_path)`
- `legal_intelligence.main.get_similarity_analyzer()`

Example with `unittest.mock.patch`:

```python
from unittest.mock import Mock, patch

with patch("legal_intelligence.main.get_knowledge_graph_service") as mock_kg,
     patch("legal_intelligence.main.get_similarity_analyzer") as mock_sim:
    mock_kg.return_value = Mock(add_node=Mock(return_value={"success": True}),
                                add_edge=Mock(return_value={"success": True}))
    mock_sim.return_value = Mock(similarity=lambda a, b: 0.9)

    from legal_intelligence import get_legal_intelligence_service
    svc = get_legal_intelligence_service(db_path)
    # run tests using svc
```

Notes:
- The default factories return a minimal in-memory graph and a simple similarity helper suitable for lightweight integration tests.
- Patching these functions avoids reaching into private internals and keeps tests deterministic.

### CI/CD Testing
```yaml
# GitHub Actions workflow
- name: Run tests
  run: |
    python3 -m pytest tests/ --tb=short
    python3 -m pytest tests/ --cov=. --cov-report=xml
```

## Estimated Coverage

### Current (with broken tests)
- **Line Coverage**: ~35-40% (estimated)
- **Function Coverage**: ~30% (estimated)
- **Branch Coverage**: ~25% (estimated)

### Target After Fixes
- **Line Coverage**: 70%+
- **Function Coverage**: 80%+
- **Branch Coverage**: 60%+

## Action Items

1. **Immediate**: Fix 26 import errors in existing tests
2. **Week 1**: Add tests for new flat architecture services
3. **Week 2**: Add MCP server integration tests
4. **Week 3**: Add end-to-end workflow tests
5. **Ongoing**: Maintain 70%+ coverage for new code

## Test Infrastructure Improvements

### Recommended Tools
- `pytest-cov` - Coverage reporting WORKING: (installed)
- `pytest-mock` - Better mocking support WORKING: (installed)
- `pytest-benchmark` - Performance testing WORKING: (installed)
- `pytest-asyncio` - Async test support WORKING: (installed)
- `tox` - Multi-environment testing (consider adding)
- `hypothesis` - Property-based testing WORKING: (installed)

### Test Organization
```
tests/
 unit/           # Pure unit tests
 integration/    # Integration tests
 e2e/           # End-to-end tests
 performance/   # Performance benchmarks
 fixtures/      # Shared test data
 mocks/         # Mock implementations
```

## Conclusion

The test suite needs significant updates to match the new flat architecture. While we have 445 tests collected, 26 are failing due to import errors from the old nested structure. Priority should be:

1. Fix existing test imports (Quick win)
2. Add tests for new services (Critical coverage)
3. Add integration tests (Quality assurance)
4. Maintain ongoing coverage targets (Long-term health)

The good news is that core intelligence services, caching, and knowledge graph tests are working, providing a solid foundation to build upon.
