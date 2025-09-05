# Legal Document Search System

AI-powered search system with Legal BERT semantic understanding for legal document analysis. This is a single-user system that prioritizes working code over perfect abstractions.

> CURRENT: Production baseline — Gmail sync, true hybrid search with RRF, and semantic-only mode.

## STATUS: PRODUCTION BASELINE (2025-08-26)

*   **Gmail Sync v2.0**: Working with message-level deduplication and content reduction
*   **Hybrid Search**: True RRF hybrid search (semantic + keyword) with explainability
*   **Vector Service**: Qdrant connected with Legal BERT ready for embeddings
*   **Schema Compatibility**: All services aligned to v2.0 architecture
*   **Database Health**: Email deduplication active, SQLite WAL mode optimized
*   **Foreign Key Integrity**: Referential integrity enforced with CASCADE deletes

## Core Workflows

This section provides a quick reference to the most essential commands for daily use. For a complete list of all commands, see the [auto-generated Command Reference](docs/COMMAND_REFERENCE.md).

### System Operations
```bash
# Check system health and status
make status

# Run the full diagnostic suite
make diagnose

# Run fast tests (no slow AI tests)
make test
```

### Content Operations
```bash
# Search across all content (hybrid default)
make search QUERY="contract terms"

# Upload and process a document
make upload FILE="/path/to/your/document.pdf"

# Sync emails incrementally
make sync
```

### Development & Maintenance
```bash
# Auto-fix common code quality issues
make fix

# Format all code
make format

# Clean up cache files
make clean
```

## Project Philosophy & Architecture

The system follows a clean, flat architecture with direct function calls and no unnecessary abstractions.

### Guiding Principles
*   **Simple > Complex**: Direct function calls, no factories.
*   **Working > Perfect**: Practical solutions that work today.
*   **Direct > Indirect**: Import and use directly.
*   **Flat > Nested**: Keep nesting shallow.
*   **Small Files**: Aim for <450 lines for new files.
*   **Small Functions**: Target ~30 lines for readability.

### Anti-Patterns (NEVER DO)
*   **No Enterprise Patterns**: No dependency injection, abstract classes, or factories.
*   **No Over-Engineering**: This is a single-user hobby project.
*   **No Complex Routing**: Simple if/else for dispatch.
*   **No God Modules**: Each module has ONE purpose.

### Core Services
*   **`gmail/`, `pdf/`, `entity/`, `summarization/`**: Root-level, single-purpose business services.
*   **`lib/`**: Core business logic (database, search, embeddings). This is the unified interface.
*   **`shared/`**: Utilities and database code shared across services. Keep minimal.
*   **`tools/`**: CLI scripts and other user-facing tools.
*   **`tests/`**: All test files.

For the complete, up-to-date project structure, you can use the `tree` command or your IDE.

### Database
*   **Engine**: SQLite with WAL mode for single-user performance.
*   **Integrity**: Foreign keys are enforced.
*   **Error Handling**: Uses custom exceptions (`shared/db/exceptions.py`) instead of return codes for clarity.

## Task Management & Agentic Workflow
This project's development is managed by `Task Master`, a tool for planning and executing development tasks, often with AI agents. For full details on this workflow, see [AGENTS.md](AGENTS.md).

## Testing
*   **Run fast tests**: `make test`
*   **Run all tests (including slow AI tests)**: `make test-all`
*   **Test files**: Located in `tests/`. Test files mirror the structure of the service they are testing.
*   **Test Hooks**: To keep tests deterministic, small factory seams are exposed for patching (e.g., `get_search_intelligence_service()`). See the bottom of the old `docs/ARCHITECTURE.md` for details if needed.

## Full Command Reference
For a complete, exhaustive list of all available commands and their descriptions, please see the **[Full Command Reference](docs/COMMAND_REFERENCE.md)**, which is automatically generated from the `Makefile`.