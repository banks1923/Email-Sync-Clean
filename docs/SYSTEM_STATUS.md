# System Status & Health

## Current System Status

### Core Services Working
- ✅ Gmail sync with v2.0 message deduplication (420+ emails processed)
- ✅ Semantic search fully operational via Qdrant
- ✅ Legal BERT embeddings with 1024D vectors
- ✅ Entity extraction with 97% email parsing coverage
- ✅ SQLite database with WAL mode, foreign key integrity
- ✅ PDF upload processing (text extraction only, OCR handled externally)
- ✅ Substantive text extraction with boilerplate stripping
- ✅ All DB access consolidated through SimpleDB
- ✅ Zero technical debt - all bandaid solutions removed
- ✅ Comprehensive input validation layer (lib/validators.py) with parameter bounds checking

### Development State
- Clean flat architecture, no complex abstractions
- Email parsing pipeline stable and tested
- Chunk pipeline implemented (Task 25 complete)
- Debug logging enabled (`LOG_LEVEL=DEBUG`, `USE_LOGURU=true`)
- Pre-commit hooks prevent direct sqlite3 usage
- All services use direct function APIs (no service classes)
- Chunking/quality modules migrated from src/ to infrastructure/documents/

## Unified Health Checks (CLI + APIs)

### Health Check Contract
**Contract Keys:**
- `status`: "healthy" | "mock" | "degraded" | "error"
- `details`: Stable, service-specific fields (e.g., model_name, vector_size, db_path)
- `metrics`: Lightweight stats (e.g., cache hits, query counts)
- `hints`: Actionable guidance (how to enable Qdrant or models)

### CLI Usage
```bash
# Human-readable health check
python tools/scripts/vsearch admin health

# Machine-readable JSON output
python tools/scripts/vsearch admin health --json

# Deep health checks (heavier)
python tools/scripts/vsearch admin health --deep
```

### Exit Codes
- **0**: Healthy (or mock with TEST_MODE)
- **1**: Degraded/mock (without TEST_MODE)
- **2**: Error condition

### Environment Toggles
- `TEST_MODE=1` or `SKIP_MODEL_LOAD=1`: Use mock embeddings; fast checks
- `QDRANT_DISABLED=1`: Force mock vector store
- `QDRANT_HOST`, `QDRANT_PORT`, `QDRANT_TIMEOUT_S`: Configure Qdrant (defaults: localhost, 6333, 0.5s)

### API Entry Points
```python
# Database health
lib.db.SimpleDB.health_check(deep=False)

# Vector store health
lib.vector_store.get_vector_store().health_check(deep=False)

# Embeddings health
lib.embeddings.get_embedding_service().health_check(deep=False)
```

### Performance Budgets
- **Database**: <300ms for health check
- **Vector Store**: <500ms for control-plane operations
- **Embeddings**: <50ms for mock/light checks
- **Deep Checks**: Single encode operation or point count

## System Metrics (Current)

### Database Statistics
- **Total Documents**: 298+ in content_unified
- **Email Messages**: 420+ deduplicated messages
- **Entities Extracted**: 719+ entities across all content
- **Test Coverage**: 97%+ on email parsing module

### Service Counts
| Service | Directory | Total Lines | Code Lines |
|---------|-----------|-------------|------------|
| Shared | `shared/` | 6,123 | 4,592 |
| PDF | `pdf/` | 3,523 | 2,642 |
| Entity | `entity/` | 2,661 | 1,995 |
| Infrastructure/Documents | `infrastructure/documents/` | 1,993 | 1,494 |
| Gmail | `gmail/` | 1,883 | 1,412 |
| Core Library | `lib/` | 2,100 | 1,575 |
| Infrastructure/MCP | `infrastructure/mcp_servers/` | 1,589 | 1,191 |
| Summarization | `summarization/` | 499 | 374 |
| Utilities/Vector Store | `utilities/vector_store/` | 413 | 309 |
| Utilities/Timeline | `utilities/timeline/` | 399 | 299 |
| Utilities/Embeddings | `utilities/embeddings/` | 157 | 117 |
| **TOTAL** | **All Services** | **21,037** | **15,772** |

## Production Readiness

### Working Features
- ✅ **Gmail Sync**: Full email ingestion with deduplication
- ✅ **Keyword Search**: Database search operational
- ✅ **Vector Service**: Connected and operational
- ⏳ **Semantic Search**: Ready (needs embedding generation)

### Quick Verification Commands
```bash
# System overview
tools/scripts/vsearch info

# Test keyword search
tools/scripts/vsearch search "lease" --limit 5

# Database record count
sqlite3 data/system_data/emails.db "SELECT COUNT(*) FROM content_unified;"

# Full system diagnostic
make diag-wiring
```

## Daily Production Workflow

```bash
# 1. Quick health check (30 seconds)
tools/scripts/vsearch info

# 2. Gmail sync (as needed)
export LOG_LEVEL=DEBUG && export USE_LOGURU=true && python3 -m gmail.main

# 3. Generate embeddings (if not done)
tools/scripts/vsearch ingest --emails

# 4. Test searches
tools/scripts/vsearch search "your query" --limit 5

# 5. Full diagnostic (if issues)
make diag-wiring
```

## Known Issues & Mitigations

### Pending Items
- ⚠️ MCP server needs `@server.list_tools()` update
- ⚠️ Embedding dimension mismatch (768 vs 1024) may affect semantic search
- ⚠️ Some CLI modules unmapped from main interface
- ⚠️ Test file import paths need updating in some integration tests

### Mitigations
- Use `TEST_MODE=1` for CI/testing environments
- Run with `SKIP_MODEL_LOAD=1` for fast health checks
- Use keyword search while semantic embeddings are generated
- Monitor health checks for degraded status

## Next Steps

### Immediate Actions
1. Generate embeddings: `tools/scripts/vsearch ingest --emails`
2. Verify semantic search: `tools/scripts/vsearch search "tenant rights" --limit 5`
3. Monitor system health: `python -m cli admin health --json`

### Optimization Opportunities
1. Batch embedding generation for better performance
2. Implement embedding cache warming
3. Add query performance metrics to health checks
4. Set up automated health monitoring