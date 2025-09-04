_This document outlines the core development principles, architecture, and guidelines for the Litigator Solo project._

# Legal Document Search System - Development Guide

Clean architecture implementation with Legal BERT semantic search and simplified services.

> **For user documentation, see [README.md](README.md)**

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
- *GREP* Libraries and extentions are your friend.
- Single responsibility: Clean modular build
- *Read CLAUDE.md*
- *Changelog.md*: Log all changes to changelog.md + update References across repo

## Guidelines (consider)
- **Future proof**: no quick sloppy fix AND **Docstring/Documentation**
- *Organize* repo: scripts, tests, and configurables go: into proper directory.
- *Research* Best Practices, dependencies, tools, solutions, libraries, Etc.
- *Parallel* Use Subagents for grunt work, investigation, simple tasks.


<!-- END PROTECTED SECTION - DO NOT MODIFY WITHOUT 3X CONFIRMATION -->

> **For detailed API documentation, see: docs/SERVICES_API.md**
> **For MCP server documentation, see: docs/MCP_SERVERS.md**

### Test Hooks (Patchable Factories)
To keep tests deterministic without deep mocks, we expose small factory seams:

- `infrastructure.mcp_servers.search_intelligence_mcp.get_search_intelligence_service()`
- `infrastructure.mcp_servers.legal_intelligence_mcp.get_legal_intelligence_service(db_path=None)`
- `legal_intelligence.main.get_knowledge_graph_service(db_path)` and `get_similarity_analyzer()`

Patch these with `unittest.mock.patch` in tests to inject controlled doubles. Defaults are minimal, production-safe implementations. Note: `search_smart` always invokes `_expand_query(query)` but only displays expanded terms when `use_expansion=True`.

## Current System Status

**Core Services Working**:
- Gmail sync with v2.0 message deduplication (420 emails processed)
- Semantic search fully operational via Qdrant
- Legal BERT embeddings with 1024D vectors
- Entity extraction with 97% email parsing coverage
- SQLite database with WAL mode, foreign key integrity
- **NEW**: Substantive text extraction with boilerplate stripping
- **NEW**: All DB access consolidated through SimpleDB
- **NEW**: Zero technical debt - all bandaid solutions removed

**Development State**:
- Clean flat architecture, no complex abstractions
- Email parsing pipeline stable and tested
- Chunk pipeline implemented (Task 25 complete)
- Debug logging enabled (`LOG_LEVEL=DEBUG`, `USE_LOGURU=true`)
- **NEW**: Pre-commit hooks prevent direct sqlite3 usage
- **NEW**: All services use direct function APIs (no service classes)

## READY: Quick Start (Development)

### Quick Development Setup
```bash
# Check system status
tools/scripts/vsearch info

# Test search (working now)
tools/scripts/vsearch search "lease" --limit 5

# Gmail sync when needed
python3 -m gmail.main

# Generate embeddings for semantic search
tools/scripts/vsearch ingest --emails
```

### Command Reference (Simplified Makefile + Direct CLI)

| Category | Command | Description |
|----------|---------|-------------|
| **Setup** | `make setup` | Complete setup from scratch |
| | `make install` | Install dependencies only |
| **Development** | `make test` | Run fast tests |
| | `make format` | Format code |
| | `make lint` | Check code quality |
| | `make fix` | Auto-fix common issues |
| | `make clean` | Clean up cache files |
| **System** | `make status` | Quick system health check |
| | `make diagnose` | Deep system diagnostic |
| | `make backup` | Backup your data |
| | `make reset` | Nuclear reset (when broken) |
| **Content** | `make search QUERY="terms"` | Search documents |
| | `make upload FILE="doc.pdf"` | Upload document |
| | `make sync` | Sync Gmail emails |
| **Advanced Search** | `tools/scripts/vsearch search "query"` | Basic search |
| | `tools/scripts/vsearch search "query" --type email --limit 10` | Filtered search |
| | `tools/scripts/vsearch info` | System status |
| **Advanced Ingestion** | `tools/scripts/vsearch ingest` | Process all content |
| | `tools/scripts/vsearch ingest --docs` | Process documents only |
| | `tools/scripts/vsearch upload document.pdf` | Single document |
| **Email Parsing** | `python3 scripts/parse_messages.py` | Parse emails with deduplication |
| | `python3 scripts/parse_messages.py --reset` | Fresh parse (clear resume state) |
| | `python3 scripts/backup_database.py create` | Backup before migration |
| | `python3 scripts/backup_database.py list` | List available backups |
| **Legal Intel** | `tools/scripts/vsearch legal process "24NNCV"` | Process case |
| | `tools/scripts/vsearch legal timeline "24NNCV"` | Generate timeline |
| **Search Intel** | `tools/scripts/vsearch intelligence smart-search "term"` | Smart search |
| | `tools/scripts/vsearch intelligence similarity doc_123` | Find similar |
| **Entities** | `tools/scripts/vsearch extract-entities --missing-only` | Extract entities |
| | `tools/scripts/vsearch entity-status` | Check status |
| **Verification** | `python3 scripts/verify_pipeline.py` | Full verification |
| | `python3 tests/test_email_parser.py` | Validate email parsing |

For detailed command documentation, see [docs/SERVICES_API.md](docs/SERVICES_API.md)

## ARCHITECTURE: Clean Flat Architecture

### Project Structure (Clean Organized Architecture)

```
Email Sync/
# Core Business Services (Root Level)
├── gmail/              # Email service
├── pdf/                # PDF processing
├── entity/             # Entity extraction
├── summarization/      # Document summarization
├── search_intelligence/ # Unified search intelligence
# knowledge_graph/ - functionality distributed across search_intelligence and utilities
├── legal_intelligence/ # Legal analysis service
├── shared/             # Shared utilities & database

# Organized Utility Services
├── utilities/          # Organized utility services [NEW: Reorganized 2025-08-17]
│   ├── embeddings/     # Embedding service (Legal BERT)
│   ├── vector_store/   # Vector store service
│   ├── notes/          # REMOVED - Migrated to document pipeline
│   └── timeline/       # Timeline service

# Infrastructure Services
├── infrastructure/     # Infrastructure services [NEW: Reorganized 2025-08-17]
│   ├── pipelines/      # Processing pipelines
│   ├── documents/      # Document management
│   └── mcp_servers/    # MCP server implementations

# Development Tools
├── tools/              # Development and user tools [NEW: Reorganized 2025-08-17]
│   ├── cli/            # CLI handler modules
│   └── scripts/        # User-facing scripts
│
├── tests/             # Test suite
├── docs/              # Documentation
│   ├── SERVICES_API.md               # Complete services API reference
│   ├── MCP_SERVERS.md                # MCP server integration guide
│   ├── AUTOMATED_CLEANUP.md          # Complete cleanup tool documentation
│   └── CLEANUP_QUICK_REFERENCE.md    # Quick reference for AI/developers
├── data/              # Data directories [UPDATED: 2025-08-23]
│   ├── system_data/   # System files (database, cache, quarantine)
│   └── Stoneman_dispute/user_data/  # Case-specific document storage
└── .taskmaster/      # Task management system
```

### Configuration Management (Centralized)

**All tool configurations are centralized in `.config/` directory:**

```
.config/
├── .coveragerc              # Coverage.py configuration
├── .flake8                  # Flake8 linting rules
├── .markdownlint.json      # Markdownlint documentation style rules
├── .mcpignore              # MCP server ignore patterns
├── .pre-commit-config.yaml # Pre-commit hooks configuration
├── .radon.cfg              # Radon complexity analysis configuration
├── mypy.ini                # MyPy type checking settings
├── pyrightconfig.json      # Pyright (VS Code) type checking
├── pytest.ini             # Pytest configuration
└── settings.py             # Centralized application settings (Pydantic)
```

**Tool Configuration Updates:**
- **Make commands**: All use `--config .config/[file]` syntax
- **PyProject.toml**: Contains consolidated tool settings where supported
- **External secrets**: Use `~/Secrets/.env` with direnv auto-loading via `.envrc`
- **Documentation linting**: `make docs-check` and `make docs-fix` for markdown quality
- **Complexity analysis**: `make complexity-check` and `make complexity-report` with radon

**Major Update (2025-08-23)**: Configuration alignment completed:
- **Database Path Alignment**: All services use `data/system_data/emails.db` via centralized `get_db_path()`
- **Legacy Pipeline Cleanup**: Removed automatic creation of unused `data/raw/`, `data/staged/`, `data/processed/` folders
- **User Data Standardization**: All services aligned to case-specific `data/Stoneman_dispute/user_data` path
- **Centralized Configuration**: 35+ files updated to use Pydantic settings instead of hardcoded paths
- **Clean Directory Structure**: No more stale database creation or unused pipeline directories

**Major Update (2025-08-17)**: Directory reorganization completed:
- **53% reduction**: Root directory items reduced from 34 to 16
- **One-level nesting**: utilities/, infrastructure/, tools/ organize smaller services
- **Core services remain at root**: Main business logic stays easily accessible
- **Auto-updated imports**: 60+ import statements updated via Bowler AST transformations

### Architecture Principles

#### File Size Guidelines

##### For New Development (GOALS, NOT ENFORCED)
- *New Files (Goal)*: Aim to keep files under 450 lines to prevent unmaintainable monster files.
- *Function Size (Goal)*: Try to keep functions ~30 lines for readability.
- *Rationale*: Keeps AI development focused and prevents monster files
These are guidance targets to prevent monster files; they are not hard caps.

##### Code Quality Achievements (2025-08-22) - COMPLETED
- **Type Safety**: Critical modules now properly type-annotated with modern Python syntax
- **Complexity Reduction**: High-complexity functions refactored following clean architecture
- **Function Compliance**: All new extracted functions under 30 lines (goal achieved)
- **Dependency Health**: All packages current, deprecation warnings resolved

##### For Existing Code (PRAGMATIC)
- **Core Infrastructure** (SimpleDB, main services): Size guided by functionality
- **Working Code Principle**: Don't refactor working code without clear benefit
- **Refactor Triggers**:
  - Maintenance difficulties
  - Clear functional separation opportunities

##### SimpleDB Specific (DOCUMENTED TRIGGERS)
**SimpleDB will remain as-is unless these specific triggers occur:**
1. **Need async/multiprocess writes** - Currently single-threaded is sufficient
2. **Sustained SQLITE_BUSY or p95 latency issues for 2+ weeks** - Currently zero lock issues
3. **Migration off SQLite to Postgres/Cloud SQL** - SQLite perfect for single-user
4. **Method count exceeds 60 or complexity exceeds agreed caps** - Currently 47 methods
5. **p95 write latency >2× baseline for 2 weeks OR busy_events >0.5% of writes** - Objective SLO

**SQLite Optimizations Applied (2025-08-19, Updated 2025-08-26):**
- WAL mode enabled for better concurrency
- 64MB cache for batch operations
- NORMAL synchronous mode (safe for single-user)
- 5-second busy timeout for resilience
- Slow-query logging (>100ms)
- `db_maintenance()` method for WAL checkpointing after large batches
- **Foreign Keys ENFORCED** (2025-08-26): Referential integrity active via triggers
  - Only applies to `source_type='email_message'` records
  - Email summaries (`source_type='email_summary'`) exempt from FK constraints
  - CASCADE DELETE enabled for automatic cleanup
  - Migration tool: `scripts/enable_foreign_keys_comprehensive.py`

#### Other Hard Limits (ENFORCED)
- **Cyclomatic Complexity**: 10 per function
- **Service Independence**: No cross-service imports

#### Good Patterns (ALWAYS DO)
- **Simple > Complex**: Direct function calls, no factories
- **Working > Perfect**: Solutions that work today
- **Direct > Indirect**: Import and use directly
- **Flat > Nested**: Keep nesting shallow

#### Anti-Patterns (NEVER DO)
- **No Enterprise Patterns**: No dependency injection, abstract classes, or factories
- **No Over-Engineering**: This is a single-user hobby project
- **No Complex Routing**: Simple if/else for dispatch
- **No God Modules**: Each module has ONE purpose


## STATUS: Key Services Overview

<!-- AUTO-GENERATED SERVICE COUNTS - DO NOT EDIT BY HAND -->
<!-- Generated by make docs-audit - data from tools/docs/audit.py -->

| Service | Directory | Total Lines | Code Lines |
|---------|-----------|-------------|------------|
| Shared | `shared/` | 6,123 | 4,592 |
| PDF | `pdf/` | 3,523 | 2,642 |
| Entity | `entity/` | 2,661 | 1,995 |
| Infrastructure/Documents | `infrastructure/documents/` | 1,993 | 1,494 |
| Gmail | `gmail/` | 1,883 | 1,412 |
| Search Intelligence | `search_intelligence/` | 1,797 | 1,347 |
| Infrastructure/MCP | `infrastructure/mcp_servers/` | 1,589 | 1,191 |
| Legal Intelligence | `legal_intelligence/` | 837 | 627 |
| Summarization | `summarization/` | 499 | 374 |
| Utilities/Vector Store | `utilities/vector_store/` | 413 | 309 |
| Utilities/Timeline | `utilities/timeline/` | 399 | 299 |
| Utilities/Embeddings | `utilities/embeddings/` | 157 | 117 |
| **TOTAL** | **All Services** | **21,874** | **16,399** |

<!-- END AUTO-GENERATED SERVICE COUNTS -->


For detailed service descriptions and APIs, see [docs/SERVICES_API.md](docs/SERVICES_API.md)

## DATABASE: Schema

### Core Architecture: Message-Level Deduplication (v2.0) - PRODUCTION BASELINE
The system implements advanced message-level email deduplication with TEXT source_ids and full schema compatibility.

**Current Production Status (2025-08-25)**:
- **Email deduplication**: Significant reduction in duplicate content from email threads
- **Gmail sync**: Fully operational with v2.0 schema
- **Test Coverage**: 97%+ on email_parsing module, comprehensive test suite
- **Schema compatibility**: All tables compatible, semantic pipeline working

**Primary Tables:**

#### `content_unified` - Single Source of Truth
- `id` (INTEGER PRIMARY KEY) - Auto-generated ID
- `source_type` (TEXT) - Type: 'email_message', 'email_summary', 'document', 'document_chunk'
  - **NEW (2025-08-26)**: Added 'email_summary' type for summaries without FK constraints
- `source_id` (TEXT) - TEXT-based IDs (message_hash for emails, doc_uuid for documents, various for summaries)
- `title` (TEXT) - Document title or email subject
- `body` (TEXT) - Full text content
- `sha256` (TEXT UNIQUE) - Content hash for deduplication
- `ready_for_embedding` (BOOLEAN) - Flag for embedding pipeline
- `validation_status` (TEXT) - 'pending', 'validated', 'failed'
- `quality_score` (REAL) - Quality metric for content
- `metadata` (TEXT) - JSON metadata
- **Foreign Key**: Conditional - only enforced for `source_type='email_message'` via triggers

#### `individual_messages` - Unique Email Messages
- `message_hash` (TEXT PRIMARY KEY) - SHA256 of normalized content
- `content` (TEXT) - Full message text
- `subject` (TEXT) - Message subject line
- `sender_email` (TEXT) - Sender's email address
- `recipients` (TEXT) - JSON array of recipients
- `date_sent` (TIMESTAMP) - When message was sent
- `message_id` (TEXT UNIQUE) - Email Message-ID header
- `thread_id` (TEXT) - Thread identifier for reconstruction
- `content_type` (TEXT) - 'original', 'reply', 'forward'

#### `message_occurrences` - Audit Trail
- `id` (INTEGER PRIMARY KEY)
- `message_hash` (TEXT) - Links to individual_messages
- `email_id` (TEXT) - Original email file where seen
- `position_in_email` (INTEGER) - Order within the email
- `context_type` (TEXT) - 'original', 'quoted', 'forwarded'
- `quote_depth` (INTEGER) - Number of > markers

**Email Processing Pipeline (v2.0 - 2025-08-25):**
- **Message-Level Deduplication**: Parse individual messages from threads, hash each uniquely
- **TEXT Source IDs**: Flexible string-based IDs replace INTEGER constraints
- **Advanced Parsing**: Boundary detection for forwards, replies, nested quotes
- **Legal Integrity**: Foreign key constraints with CASCADE for evidence preservation
- **Audit Trail**: Complete tracking of where each message appears across emails
- **70-80% Content Reduction**: Eliminates duplicate quoted/forwarded content

**Migration Tools:**
- `scripts/parse_messages.py` - Batch processor for email parsing
- `scripts/parse_all_emails.py` - Parser for all_emails.txt format
- `scripts/backup_database.py` - Backup/restore with integrity checks
- `email_parsing/message_deduplicator.py` - Advanced parsing service (97% coverage)
- `tests/test_email_parser.py` - Unit tests (16 tests)
- `tests/test_email_integration.py` - Integration tests (4 tests)
- `tests/test_email_coverage.py` - Edge case tests (18 tests)

**Semantic Pipeline (Restored 2025-08-25):**
- `utilities/semantic_pipeline.py` - Complete orchestration system (443 lines)
- `infrastructure/pipelines/service_orchestrator.py` - Pipeline coordination
- `scripts/backfill_semantic.py` - Batch semantic processing
- `scripts/setup_semantic_schema.py` - Schema setup utility
- `scripts/test_semantic_pipeline.py` - Testing framework  
- `scripts/verify_semantic_wiring.py` - Verification tools
- `tests/test_semantic_pipeline_comprehensive.py` - Full test suite

## VERIFICATION: System Status - CURRENT BASELINE

**Current verified status (2025-08-25 3:05 PM):**

```bash
# PRODUCTION VERIFICATION

# Quick status check
tools/scripts/vsearch info                       # System overview
tools/scripts/vsearch search "lease" --limit 3  # Test keyword search

# Database verification
sqlite3 data/system_data/emails.db "SELECT 'content_unified total:' || COUNT(*) FROM content_unified UNION ALL SELECT 'email_messages:' || COUNT(*) FROM content_unified WHERE source_type='email_message';"

# Gmail sync test (with debug logging)  
export LOG_LEVEL=DEBUG && export USE_LOGURU=true && python3 -m gmail.main

# Schema validation
sqlite3 data/system_data/emails.db ".schema document_summaries"  # Verify all columns present

# Full system health check
make diag-wiring
```

For detailed API documentation and usage examples, see **docs/SERVICES_API.md**

## PIPELINE: Unified Ingestion

**Manual ingestion for emails and documents through unified processing pipeline.**

- **Pipeline**: All content → `content_unified` table → vector embeddings → search
- **Features**: Duplicate detection (SHA256), recursive processing, manual triggers
- **File Types**: PDF (PyPDF2/OCR), DOCX, TXT, MD

```bash
tools/scripts/vsearch ingest --docs              # Process documents
tools/scripts/vsearch ingest --emails            # Process emails
tools/scripts/vsearch ingest --docs --dir /path  # Custom directory
```

## TOOLS: MCP Server Integration

The system provides 2 active MCP servers for Claude Desktop with 12+ intelligence tools.

**Configuration**: `make mcp-status` | `make mcp-generate` | `make mcp-validate`

**Active Servers**:
- **Legal Intelligence**: 6 legal analysis tools (entity extraction, timeline, document analysis)
- **Search Intelligence**: 6 search tools (smart search, similarity, clustering)

For complete MCP documentation and tool details, see **[docs/MCP_SERVERS.md](docs/MCP_SERVERS.md)**

## 🔬 Entity Extraction System

**Entity extraction across all content types**

- **Processing**: Unified pipeline with OCR garbage detection
- **Entity Types**: PERSON, ORG, DATE, COURT, STATUTE, MONEY, LEGAL_CONCEPT
- **Current**: 719 entities extracted from processed content

```bash
tools/scripts/vsearch extract-entities --missing-only  # Extract entities
tools/scripts/vsearch entity-status                    # Check status
tools/scripts/vsearch search-entities --entity-type PERSON --entity-value "Smith"
```

For complete documentation, see **[docs/ENTITY_EXTRACTION_INTEGRATION.md](docs/ENTITY_EXTRACTION_INTEGRATION.md)**

## LOGGING: System

**Uses loguru for superior logging** - Config: `shared/loguru_config.py`

```python
from loguru import logger
logger.info("Message")  # Simple API, automatic rotation, structured logging
```

Environment: `LOG_LEVEL=INFO`, `USE_LOGURU=true`

## VERIFICATION: System

```bash
python3 scripts/verify_pipeline.py              # Complete pipeline verification
python3 scripts/verify_pipeline.py --json       # CI-friendly JSON output
python3 scripts/verify_pipeline.py --trace abc123  # Trace specific document
make preflight-vector-parity                    # Vector sync check
```

Runs 6 test suites: Preflight, Smoke, Integrity, Performance, Quarantine, Document Tracing.

For detailed verification documentation, see **[docs/PIPELINE_VERIFICATION.md](docs/PIPELINE_VERIFICATION.md)**

## TESTING: Testing & Validation

### Testing Philosophy
- **Test Real Functionality**: Avoid mocks when possible
- **Integration > Unit**: Test workflows, not implementation
- **Comprehensive Verification**: Use `verify_pipeline.py` for full system validation

### Test Commands
```bash
# System validation
python3 scripts/verify_pipeline.py              # Full pipeline verification
make preflight-vector-parity                    # Vector sync check

# Email deduplication tests (v2.0)
python3 tests/test_email_parser.py              # Unit tests (16 tests)
python3 tests/test_email_integration.py         # Integration tests (4 tests)
python3 tests/test_email_coverage.py            # Edge cases (18 tests)
coverage run -m pytest tests/test_email*.py     # Coverage report (97%+)

# MCP & other tests
python3 tests/simple_mcp_validation.py          # MCP validation
python3 tests/run_mcp_tests.py                  # All MCP tests

# Quick service test
python3 -c "from shared.simple_db import SimpleDB; db = SimpleDB(); print('WORKING: DB working')"
```

### Test Coverage
- **Email Parsing**: Comprehensive test suite with 34 tests
- **Integration Tests**: MCP parameter mapping and workflows
- **System Tests**: Full pipeline validation via `verify_pipeline.py`
- **Coverage Focus**: Email parsing at 97%, integration over unit tests

For detailed testing documentation, see **[docs/PIPELINE_VERIFICATION.md](docs/PIPELINE_VERIFICATION.md)**

## TOOLS: Development Tools

### Automated Code Cleanup
```bash
make cleanup        # Complete automated cleanup pipeline
make fix-all        # Auto-fix all issues + advanced formatting
make check          # Quality checks + tests (no modifications)
```

### Additional Tools
- **LibCST**: Large-scale Python refactoring - See [docs/CODE_TRANSFORMATION_TOOLS.md](docs/CODE_TRANSFORMATION_TOOLS.md)
- **SonarQube**: IDE quality analysis (`SonarSource.sonarlint-vscode`)
- **Commands**: `make sonar-check`, `make sonar-fix`, `make sonar-report`

For cleanup tools: Use `make cleanup` and `make fix-all` commands

## GUIDELINES: Development

### Adding Features
1. **Check if it already exists** - We have a lot already
2. **Keep it simple** - Can it be done in 30 lines?
3. **Use existing services** - Don't create new abstractions
4. **Test with real operations** - Avoid mocks

### Code Style
```python
# GOOD: Simple and direct
def search(query):
    db = SimpleDB()
    return db.search_content(query)

# BAD: Over-engineered
class SearchFactory:
    def create_search_handler(self):
        return AbstractSearchHandler()
```

### File Organization
- **Root level services**: gmail/, pdf/, search_intelligence/, legal_intelligence/
- **Utilities**: utilities/embeddings/, utilities/vector_store/ (utilities/notes/ removed)
- **Infrastructure**: infrastructure/pipelines/, infrastructure/documents/, infrastructure/mcp_servers/
- **Tools**: tools/cli/, tools/scripts/
- **shared/**: Shared utilities (keep minimal)
- **tests/**: All test files

## PERFORMANCE: Metrics

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

### Detailed References
- **[docs/SERVICES_API.md](docs/SERVICES_API.md)** - Complete services API reference
- **[docs/MCP_SERVERS.md](docs/MCP_SERVERS.md)** - MCP server integration guide
- **[docs/ENTITY_EXTRACTION_INTEGRATION.md](docs/ENTITY_EXTRACTION_INTEGRATION.md)** - Entity extraction system guide **UPDATED**
- **[docs/DIAGNOSTIC_SYSTEM.md](docs/DIAGNOSTIC_SYSTEM.md)** - System diagnostic tools and troubleshooting
- Code cleanup tools (via Make commands)
- **[docs/CLEANUP_QUICK_REFERENCE.md](docs/CLEANUP_QUICK_REFERENCE.md)** - Quick cleanup reference

### Service-Specific Documentation
- **[gmail/CLAUDE.md](gmail/CLAUDE.md)** - Gmail service implementation
- **[pdf/CLAUDE.md](pdf/CLAUDE.md)** - PDF processing details
- Document similarity and clustering (via search intelligence service)
- **[summarization/README.md](summarization/README.md)** - Document summarization

## NEXT: Steps - FROM PRODUCTION BASELINE

### CURRENT STATUS: Production Ready with Keyword Search
WORKING: **Gmail sync working**  
WORKING: **Keyword search operational**  
WORKING: **Vector service connected**  
⏳ **Semantic search ready** (needs embedding generation)

### Immediate Next Actions
1. **Enable Semantic Search**: `tools/scripts/vsearch ingest --emails` - Generate embeddings for all emails
2. **Test Both Search Types**: 
   - Keyword: `tools/scripts/vsearch search "lease" --limit 5`
   - Semantic: `tools/scripts/vsearch search "tenant rights" --limit 5` (after embeddings)

### Daily Production Workflow
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

---

*Remember: The best code is no code. The second best is simple code that works.*

## Task Master AI Integration (Optional)

Task Master provides advanced task management for complex projects. When Task Master is installed and initialized in this project, its guidelines enhance the development workflow.

**If Task Master is active**: See `.taskmaster/CLAUDE.md` for Task Master-specific commands and workflows. Use `task-master init` to initialize when needed.

## Task Master AI Instructions
**Import Task Master's development workflow commands and guidelines, treat as if import is in the main CLAUDE.md file.**
@./.taskmaster/CLAUDE.md
