# Command Reference Guide

## Quick Start Commands

```bash
# Start Qdrant vector database (if not running)
make ensure-qdrant
# Or use the script directly: ./scripts/shell/manage_qdrant.sh start

# Check system status
tools/scripts/vsearch info

# Test search (working now)
tools/scripts/vsearch search "lease" --limit 5

# Gmail sync when needed
python3 -m gmail.main

# Generate embeddings for semantic search
tools/scripts/vsearch ingest --emails

# Or use direct script for embedding generation
python3 scripts/data/generate_embeddings.py
```

## Complete Command Reference

### Setup Commands

| Command | Description |
|---------|-------------|
| `make setup` | Complete setup from scratch |
| `make install` | Install dependencies only |

### Development Commands

| Command | Description |
|---------|-------------|
| `make test` | Run fast tests |
| `make format` | Format code |
| `make lint` | Check code quality |
| `make fix` | Auto-fix common issues |
| `make clean` | Clean up cache files |
| `make cleanup` | Complete automated cleanup pipeline |
| `make fix-all` | Auto-fix all issues + advanced formatting |
| `make check` | Quality checks + tests (no modifications) |

### System Management

| Command | Description |
|---------|-------------|
| `make status` | Quick system health check |
| `make diagnose` | Deep system diagnostic |
| `make diag-wiring` | Full system diagnostic |
| `make backup` | Backup your data |
| `make reset` | Nuclear reset (when broken) |

### Qdrant Vector Database

| Command | Description |
|---------|-------------|
| `make ensure-qdrant` | Start Qdrant if not running |
| `make stop-qdrant` | Stop Qdrant database |
| `make restart-qdrant` | Restart Qdrant database |
| `make qdrant-status` | Check Qdrant status |
| `./scripts/shell/manage_qdrant.sh start` | Direct Qdrant start |
| `./scripts/shell/manage_qdrant.sh stop` | Direct Qdrant stop |

### Content Management

| Command | Description |
|---------|-------------|
| `make search QUERY="terms"` | Search documents |
| `make upload FILE="doc.pdf"` | Upload document |
| `make sync` | Sync Gmail emails |

### Advanced Search (vsearch CLI)

| Command | Description |
|---------|-------------|
| `tools/scripts/vsearch search "query"` | Basic search |
| `tools/scripts/vsearch search "query" --type email --limit 10` | Filtered search |
| `tools/scripts/vsearch info` | System status |
| `tools/scripts/vsearch search "lease" --limit 5` | Keyword search example |
| `tools/scripts/vsearch search "tenant rights" --limit 5` | Semantic search (after embeddings) |

### Ingestion Commands

| Command | Description |
|---------|-------------|
| `tools/scripts/vsearch ingest` | Process all content |
| `tools/scripts/vsearch ingest --docs` | Process documents only |
| `tools/scripts/vsearch ingest --emails` | Process emails only |
| `tools/scripts/vsearch ingest --docs --dir /path` | Custom directory |
| `tools/scripts/vsearch upload document.pdf` | Single document upload |

### Embedding Generation

| Command | Description |
|---------|-------------|
| `python3 scripts/data/generate_embeddings.py` | Generate all embeddings |
| `python3 scripts/data/generate_embeddings.py --stats` | Show embedding statistics |
| `python3 scripts/data/generate_embeddings.py --limit 100` | Process first 100 chunks |

### Email Processing

| Command | Description |
|---------|-------------|
| `python3 -m gmail.main` | Sync Gmail emails |
| `python3 scripts/parse_messages.py` | Parse emails with deduplication |
| `python3 scripts/parse_messages.py --reset` | Fresh parse (clear resume state) |
| `python3 scripts/backup_database.py create` | Backup before migration |
| `python3 scripts/backup_database.py list` | List available backups |
| `python3 scripts/parse_all_emails.py` | Parse all_emails.txt format |

### Legal Intelligence

| Command | Description |
|---------|-------------|
| `tools/scripts/vsearch legal process "24NNCV"` | Process case |
| `tools/scripts/vsearch legal timeline "24NNCV"` | Generate timeline |

### Search Intelligence

| Command | Description |
|---------|-------------|
| `tools/scripts/vsearch intelligence smart-search "term"` | Smart search with expansion |
| `tools/scripts/vsearch intelligence similarity doc_123` | Find similar documents |

### Entity Extraction

| Command | Description |
|---------|-------------|
| `tools/scripts/vsearch extract-entities --missing-only` | Extract entities from unprocessed content |
| `tools/scripts/vsearch entity-status` | Check extraction status |
| `tools/scripts/vsearch search-entities --entity-type PERSON --entity-value "Smith"` | Search for specific entities |

### Export Commands

| Command | Description |
|---------|-------------|
| `python3 tools/scripts/export_documents.py` | Export all documents to text files |
| `python3 tools/scripts/export_documents.py --content-type email` | Export emails only |
| `python3 tools/scripts/export_documents.py --output-dir /path` | Custom export directory |

### Verification & Testing

| Command | Description |
|---------|-------------|
| `python3 scripts/verify_pipeline.py` | Full pipeline verification |
| `python3 scripts/verify_pipeline.py --json` | CI-friendly JSON output |
| `python3 scripts/verify_pipeline.py --trace abc123` | Trace specific document |
| `make preflight-vector-parity` | Vector sync check |
| `python3 tests/test_email_parser.py` | Validate email parsing |

### Test Suites

| Command | Description |
|---------|-------------|
| `pytest tests/infrastructure/database/` | All 52 SimpleDB tests |
| `pytest tests/infrastructure/database/test_simple_db_core.py` | Core CRUD/search tests |
| `pytest tests/infrastructure/database/test_simple_db_intelligence.py` | Intelligence tests |
| `pytest tests/infrastructure/database/test_simple_db_performance.py` | Performance tests |
| `pytest tests/test_validators.py` | 222 validation tests |
| `pytest tests/test_validators.py -k fuzz` | Run fuzz tests only |
| `pytest tests/test_validators.py::TestEdgeCases` | Test edge cases |
| `python3 tests/test_email_parser.py` | Unit tests (16 tests) |
| `python3 tests/test_email_integration.py` | Integration tests (4 tests) |
| `python3 tests/test_email_coverage.py` | Edge cases (18 tests) |
| `coverage run -m pytest tests/test_email*.py` | Coverage report (97%+) |

### MCP Server Management

| Command | Description |
|---------|-------------|
| `make mcp-status` | Check MCP server status |
| `make mcp-generate` | Generate MCP configuration |
| `make mcp-validate` | Validate MCP configuration |
| `python3 tests/simple_mcp_validation.py` | MCP validation |
| `python3 tests/run_mcp_tests.py` | All MCP tests |

### Health Checks (CLI + API)

| Command | Description |
|---------|-------------|
| `python tools/scripts/vsearch admin health` | Human-readable health check |
| `python tools/scripts/vsearch admin health --json` | Machine-readable JSON output |
| `python tools/scripts/vsearch admin health --deep` | Deep health checks |
| `python -m cli admin health` | Alternative CLI entry |
| `python -m cli admin health --json` | JSON health output |

### Quick Service Test

```bash
# Test database connection
python3 -c "from lib.db import SimpleDB; db = SimpleDB(); print('WORKING: DB working')"

# Test search import
python3 -c "from lib.search import search; print('✅ lib.search works')"

# Test embeddings
python3 -c "from lib.embeddings import get_embedding_service; print('✅ embeddings work')"

# Test vector store
python3 -c "from lib.vector_store import get_vector_store; print('✅ vector store works')"
```

## Daily Production Workflow

```bash
# Quick health check (30 seconds)
tools/scripts/vsearch info

# Gmail sync (as needed)
export LOG_LEVEL=DEBUG && export USE_LOGURU=true && python3 -m gmail.main

# Search testing
tools/scripts/vsearch search "your query" --limit 5

# Full system diagnostic (if issues)
make diag-wiring
```

## Environment Variables

### Core Settings
- `LOG_LEVEL`: INFO, DEBUG, WARNING, ERROR
- `USE_LOGURU`: true/false for enhanced logging
- `PYTHONPATH`: Set to project root
- `MCP_STORAGE_DIR`: data/sequential_thinking

### Test/Mock Settings
- `TEST_MODE=1`: Use mock services
- `SKIP_MODEL_LOAD=1`: Skip model loading
- `QDRANT_DISABLED=1`: Force mock vector store

### Qdrant Configuration
- `QDRANT_HOST`: Default localhost
- `QDRANT_PORT`: Default 6333
- `QDRANT_TIMEOUT_S`: Default 0.5
- `QDRANT__STORAGE__PATH`: ./qdrant_data
- `QDRANT__LOG__PATH`: ./logs/qdrant.log

## Exit Codes

- **0**: Healthy or TEST_MODE with mock
- **1**: Degraded/mock without TEST_MODE
- **2**: Error condition