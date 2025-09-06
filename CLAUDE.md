_This document outlines the core development principles, architecture, and guidelines for the Litigator Solo project._

# Legal Document Search System - Development Guide

Clean architecture implementation with Legal BERT semantic search and simplified services.

> **Quick Links**: [User Guide](README.md) | [Commands](docs/COMMAND_REFERENCE.md) | [Database](docs/DATABASE_SCHEMA.md) | [API](docs/SERVICES_API.md)

<!-- WARNING: CRITICAL CUSTOM INSTRUCTIONS - DO NOT MODIFY -->
<!-- REQUIRES 3X CONFIRMATION TO CHANGE THIS SECTION -->
<!-- PROTECTED WORKFLOW INSTRUCTIONS BELOW -->

 ------

## **CORE**: 

1. *Smooth is steady* steady is fast. 
2. Build it right, build it once. Build it fast, build it again. 
3. *PLAN* and investigate assumptions 
4. **CLARIFY** - *STOP* If choices or conflicts arise

Core Development Principles

## Anti-Patterns (NEVER DO)

- NO **Needless Complexity** unless *high ROI* and practical
- No *No Monster Files*: *IF* best practices
- NO **Bandaids**: Fix it *right*
- NO **Redesign**: *USER Explicit approval*

## Good Patterns (ALWAYS DO)

- *Atomic Tasks* break todo small steps
- *GREP* Libraries and extensions are your friend.
- Single responsibility: Clean modular build
- *Read CLAUDE.md*
- *Changelog.md*: Log all changes to changelog.md + update References across repo

## Guidelines (consider)
- **Future proof**: no quick sloppy fix AND **Docstring/Documentation**
- *Organize* repo: scripts, tests, and configurables go: into proper directory.
- *Research* Best Practices, dependencies, tools, solutions, libraries, Etc.
- *Parallel* Use Subagents for grunt work, investigation, simple tasks.


<!-- END PROTECTED SECTION - DO NOT MODIFY WITHOUT 3X CONFIRMATION -->

> **Documentation**: [Services API](docs/SERVICES_API.md) | [MCP Servers](docs/MCP_SERVERS.md) | [Full Index](#documentation-index)

### Test Hooks (Patchable Factories)
To keep tests deterministic without deep mocks, we expose small factory seams:

- `infrastructure.mcp_servers.search_intelligence_mcp.get_search_intelligence_service()`
- `infrastructure.mcp_servers.legal_intelligence_mcp.get_legal_intelligence_service(db_path=None)`

Patch these with `unittest.mock.patch` in tests to inject controlled doubles. Defaults are minimal, production-safe implementations. Note: `search_smart` always invokes `_expand_query(query)` but only displays expanded terms when `use_expansion=True`.

## System Overview

Production-ready legal document search system with semantic search via Legal BERT embeddings and Qdrant vector database.

**Key Features:**
- Gmail sync with message deduplication
- Semantic and keyword search
- Entity extraction (PERSON, ORG, DATE, etc.)
- PDF processing and document chunking
- SQLite with foreign key integrity

> **For current system status and metrics, see [docs/SYSTEM_STATUS.md](docs/SYSTEM_STATUS.md)**

## Health Checks

```bash
# Quick health check
tools/scripts/vsearch admin health

# JSON output for monitoring
tools/scripts/vsearch admin health --json
```

> **For complete health check documentation, see [docs/SYSTEM_STATUS.md](docs/SYSTEM_STATUS.md)**

## Quick Start

```bash
# Setup
make ensure-qdrant
tools/scripts/vsearch info

# Daily workflow
python3 -m gmail.main                    # Sync emails
tools/scripts/vsearch ingest --emails    # Generate embeddings
tools/scripts/vsearch search "query"     # Search
```

> **See [docs/COMMAND_REFERENCE.md](docs/COMMAND_REFERENCE.md)** for all commands.

## Architecture

Clean flat architecture with direct function calls. No unnecessary abstractions.

> **See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)** for project structure and principles.


## Key Services

- **Core Library** (`lib/`): Database, search, embeddings, vector store
- **Gmail** (`gmail/`): Email sync and deduplication
- **PDF** (`pdf/`): Document processing
- **Entity** (`entity/`): Entity extraction
- **Infrastructure** (`infrastructure/`): Pipelines, documents, MCP servers

> **For detailed service descriptions and metrics, see [docs/SERVICES_API.md](docs/SERVICES_API.md)**

## DATABASE: Schema Overview

The system uses SQLite with advanced message-level deduplication and foreign key constraints.

**Primary Tables:**
- `content_unified` - Single source of truth for all content
- `individual_messages` - Unique email messages
- `message_occurrences` - Email audit trail
- `document_summaries` - Document summaries
- `entities` - Extracted entities

**Metadata Fields:**
- `sha256` - Deduplication
- `embedding_generated` - Track vectors
- `quality_score` - Filter quality
- `is_validated` - Verification status

```bash
make db.migrate  # Apply migration
make db.verify   # Verify schema
```

> **For complete database schema documentation, see [docs/DATABASE_SCHEMA.md](docs/DATABASE_SCHEMA.md)**

## VERIFICATION: System Health

```bash
# Quick health check
tools/scripts/vsearch info

# Full system diagnostic
make diag-wiring

# Health with details
python -m cli admin health --deep
```

> **For detailed API documentation, see [docs/SERVICES_API.md](docs/SERVICES_API.md)**


## MCP Servers

2 active servers: Legal Intelligence & Search Intelligence (12+ tools)

> **See [docs/MCP_SERVERS.md](docs/MCP_SERVERS.md)**




## Testing

```bash
python3 scripts/verify_pipeline.py
pytest tests/
```

> **See [docs/TESTING_GUIDE.md](docs/TESTING_GUIDE.md)**



## PHILOSOPHY

> Your system should be as simple as possible for YOUR needs.

This is a **single-user project**, important use case, not for profit, not enterprise software.

### Core Values
1. **Working code > Perfect abstractions**
2. **Direct solutions > Clever patterns**
3. **Less code > More features**
4. **Today's solution > Tomorrow's possibility**

## DOCUMENTATION: Index

### Primary Documentation
- **[README.md](README.md)** - User guide and quick start
- **[CLAUDE.md](CLAUDE.md)** - Development guide (this file)
- **[CHANGELOG.md](CHANGELOG.md)** - Version history and updates

### Core References
- **[docs/DATABASE_SCHEMA.md](docs/DATABASE_SCHEMA.md)** - Complete database schema documentation
- **[docs/COMMAND_REFERENCE.md](docs/COMMAND_REFERENCE.md)** - All CLI commands and usage
- **[docs/TESTING_GUIDE.md](docs/TESTING_GUIDE.md)** - Comprehensive testing guide
- **[docs/CONFIGURATION.md](docs/CONFIGURATION.md)** - Configuration management
- **[docs/SYSTEM_STATUS.md](docs/SYSTEM_STATUS.md)** - Current system status and health
- **[docs/SERVICES_API.md](docs/SERVICES_API.md)** - Complete services API reference
- **[docs/MCP_SERVERS.md](docs/MCP_SERVERS.md)** - MCP server integration guide

### System Documentation
- **[docs/ENTITY_EXTRACTION_INTEGRATION.md](docs/ENTITY_EXTRACTION_INTEGRATION.md)** - Entity extraction system guide
- **[docs/DIAGNOSTIC_SYSTEM.md](docs/DIAGNOSTIC_SYSTEM.md)** - System diagnostic tools and troubleshooting
- **[docs/PIPELINE_VERIFICATION.md](docs/PIPELINE_VERIFICATION.md)** - Pipeline verification documentation
- **[docs/CLEANUP_QUICK_REFERENCE.md](docs/CLEANUP_QUICK_REFERENCE.md)** - Quick cleanup reference

### Service-Specific Documentation
- **[gmail/CLAUDE.md](gmail/CLAUDE.md)** - Gmail service implementation
- **[pdf/CLAUDE.md](pdf/CLAUDE.md)** - PDF processing details
- **[summarization/README.md](summarization/README.md)** - Document summarization


---

*Remember: The best code is no code. The second best is simple code that works.*


## Task Master AI Integration

> **See [.taskmaster/CLAUDE.md](.taskmaster/CLAUDE.md)** for Task Master commands and workflows.

**Import Task Master's development workflow commands and guidelines:**
@./.taskmaster/CLAUDE.md
