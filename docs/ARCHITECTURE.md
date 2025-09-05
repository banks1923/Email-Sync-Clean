# Architecture Documentation

## Clean Flat Architecture

The system follows a clean, flat architecture with direct function calls and no unnecessary abstractions.

## Project Structure

```
Litigator_solo/
# Core Business Services (Root Level)
├── gmail/              # Email service
├── pdf/                # PDF processing
├── entity/             # Entity extraction
├── summarization/      # Document summarization
├── lib/                # Core business logic (unified interface)
│   ├── db.py           # Database operations (SimpleDB)
│   ├── search.py       # Semantic search & literal patterns
│   ├── embeddings.py   # Legal BERT embeddings
│   ├── vector_store.py # Qdrant vector operations
│   ├── validators.py   # Input validation layer
│   └── utilities/      # Helper functions
├── shared/             # Shared utilities & database

# Organized Utility Services
├── utilities/          # Organized utility services
│   ├── embeddings/     # Embedding service (Legal BERT)
│   ├── vector_store/   # Vector store service
│   └── timeline/       # Timeline service

# Infrastructure Services
├── infrastructure/     # Infrastructure services
│   ├── pipelines/      # Processing pipelines
│   ├── documents/      # Document management
│   │   ├── chunker/    # Document chunking logic
│   │   ├── quality/    # Quality scoring
│   │   └── processors/ # Format-specific processors
│   └── mcp_servers/    # MCP server implementations

# Development Tools
├── tools/              # Development and user tools
│   ├── cli/            # CLI handler modules
│   └── scripts/        # User-facing scripts
│
├── tests/             # Test suite
├── docs/              # Documentation
├── data/              # Data directories
│   ├── system_data/   # System files (database, cache, quarantine)
│   └── Stoneman_dispute/user_data/  # Case-specific document storage
└── .taskmaster/      # Task management system
```

## Architecture Principles

### Error Handling & Database Layer

The system uses **custom exceptions** for proper error handling instead of return codes:

```python
from shared.db.simple_db import SimpleDB
from shared.db.exceptions import TestDataBlockedException

try:
    db = SimpleDB()
    result = db.add_content("email", "Test Subject", "content")
except TestDataBlockedException as e:
    # Test data properly blocked with context
    logger.error(f"Blocked: {e.title}, type: {e.content_type}")
```

**Exception Types** (`shared/db/exceptions.py`):
- `TestDataBlockedException` - Test data patterns detected
- `ContentValidationError` - Content validation failures  
- `DuplicateContentError` - Duplicate content (if strict mode)

**Best Practices Applied**:
- Exceptions for errors, not return codes (no more "-1")
- Structured logging with loguru
- Exception context for debugging
- Proper exception propagation

### Input Validation Layer

The system implements comprehensive input validation at API boundaries:

**Validation Features** (`lib/validators.py`):
- **Parameter Validation**: Type coercion and bounds checking for all inputs
- **Query/Pattern**: Non-empty strings, control character removal, 1000 char limit
- **Limit Clamping**: Automatic bounds to 1-200 range
- **Filter Validation**: Field-specific rules with RFC3339 date format
- **Unicode Safe**: Preserves unicode while removing control characters

**API Integration**:
```python
from lib.search import search, find_literal

# Validation happens automatically at API boundary
results = search("query", limit=500)  # Limit auto-clamped to 200
results = find_literal("", limit=-5)  # Raises ValidationError

# Filters validated with specific rules
filters = {
    "date_from": "2024-01-01",  # RFC3339 format required
    "source_type": "email",      # Must be valid type
    "party": "John Doe"          # String length limits enforced
}
```

### File Size Guidelines
- **New Files**: Aim for <450 lines (prevents monster files)
- **Functions**: Target ~30 lines for readability
- **Existing Code**: Don't refactor working code without clear benefit

### Database Architecture
- **SQLite with WAL mode**: Perfect for single-user application
- **Foreign keys enforced**: Referential integrity via triggers
- **Performance optimized**: 64MB cache, 5s timeout, slow-query logging

### SimpleDB Specific Triggers

SimpleDB will remain as-is unless these specific triggers occur:
1. **Need async/multiprocess writes** - Currently single-threaded is sufficient
2. **Sustained SQLITE_BUSY or p95 latency issues for 2+ weeks** - Currently zero lock issues
3. **Migration off SQLite to Postgres/Cloud SQL** - SQLite perfect for single-user
4. **Method count exceeds 60 or complexity exceeds agreed caps** - Currently 47 methods
5. **p95 write latency >2× baseline for 2 weeks OR busy_events >0.5% of writes** - Objective SLO

### Other Hard Limits (ENFORCED)
- **Cyclomatic Complexity**: 10 per function
- **Service Independence**: No cross-service imports

### Good Patterns (ALWAYS DO)
- **Simple > Complex**: Direct function calls, no factories
- **Working > Perfect**: Solutions that work today
- **Direct > Indirect**: Import and use directly
- **Flat > Nested**: Keep nesting shallow

### Anti-Patterns (NEVER DO)
- **No Enterprise Patterns**: No dependency injection, abstract classes, or factories
- **No Over-Engineering**: This is a single-user hobby project
- **No Complex Routing**: Simple if/else for dispatch
- **No God Modules**: Each module has ONE purpose

## File Organization

- **Root level services**: gmail/, pdf/, entity/, summarization/
- **Core library**: lib/ (unified interface for db, search, embeddings, vector_store)
- **Utilities**: utilities/embeddings/, utilities/vector_store/
- **Infrastructure**: infrastructure/pipelines/, infrastructure/documents/, infrastructure/mcp_servers/
- **Tools**: tools/cli/, tools/scripts/
- **shared/**: Shared utilities (keep minimal)
- **tests/**: All test files
  - **infrastructure/database/**: SimpleDB tests (3 focused modules)
  - **integration/**: End-to-end workflow tests
  - **smoke/**: Quick system health checks

## Test Hooks (Patchable Factories)

To keep tests deterministic without deep mocks, we expose small factory seams:

- `infrastructure.mcp_servers.search_intelligence_mcp.get_search_intelligence_service()`
- `infrastructure.mcp_servers.legal_intelligence_mcp.get_legal_intelligence_service(db_path=None)`

Patch these with `unittest.mock.patch` in tests to inject controlled doubles. Defaults are minimal, production-safe implementations. Note: `search_smart` always invokes `_expand_query(query)` but only displays expanded terms when `use_expansion=True`.