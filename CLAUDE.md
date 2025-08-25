# Email Sync System - Development Guide

Clean architecture implementation with Legal BERT semantic search and simplified services.

> **For user documentation, see [README.md](README.md)**

<!-- ⚠️ CRITICAL CUSTOM INSTRUCTIONS - DO NOT MODIFY ⚠️ -->
<!-- REQUIRES 3X CONFIRMATION TO CHANGE THIS SECTION -->
<!-- PROTECTED WORKFLOW INSTRUCTIONS BELOW -->

 ------

## **CORE**: 

1. **Smooth is steady** steady is fast. 
2. Build it right, build it once. Build it fast, build it again. 
3. **PLAN** and investigate assumptions before finalizing 
4. **CLARIFY** - *STOP* If design choices or conflicts arise

Core Development Principles

## Anti-Patterns (NEVER DO)

- NO **Needless Complexity** unless *high ROI* and practical
- No **No Monster Files**: *IF* modular approach is best practices choice
- NO **Bandaids**: Fix it *right* unless time is a constraint
- NO **Redesign**: Without *USER Explicit approval* SAME for massive changes to files or functionality

## Good Patterns (ALWAYS DO)

- **Atomic Tasks** break tasks down into small steps
- **GREP** Libraries and extentions are your friend.
- **Single responsibility** Clean modular build
- *Read CLAUDE.md*:
- **Changelog.md**: Log all changes to changelog.md + update References across repo
- *Use TodoWrite*

## Guidelines (consider)
- **Best practices** Seperation of concerns, clean repo, clean code
- **Future proof**: no quick sloppy fix AND **Docstring/Documentation**
- *GREP* Libraries and extentions are your friend.
- *Organize* repo: scripts, tests, and configurables go: into proper directory.
- *Research* Best Practices, dependencies, tools, solutions, libraries, Etc.
- *Parallel* Use Subagents for grunt work, investigation, simple tasks.


<!-- END PROTECTED SECTION - DO NOT MODIFY WITHOUT 3X CONFIRMATION -->

> **For detailed API documentation, see [docs/SERVICES_API.md](docs/SERVICES_API.md)**
> **For MCP server documentation, see [docs/MCP_SERVERS.md](docs/MCP_SERVERS.md)**

## Current Architecture Status - PRODUCTION BASELINE (2025-08-25) ✅

- **Structure**: Flat Pythonic layout (no more `src/app/core/` nesting!)
- **Services**: 26,883 total lines (20,201 code lines) across 15 active services
- **Scripts**: 13 essential scripts (down from 35)
- **Documentation**: Consolidated to core files only
- **Testing**: Focus on real functionality, 89% less mocks

### 🎯 NEW PRODUCTION BASELINE (2025-08-25 3:05 PM)
- **Gmail Sync**: ✅ WORKING - 668 emails synced with v2.0 message-level deduplication  
- **Email Processing**: ✅ 302 unique messages from 393 occurrences (23% reduction)
- **Search System**: ✅ Keyword search fully functional, semantic search ready
- **Vector Store**: ✅ Qdrant connected (1024D Legal BERT embeddings ready)
- **Schema Compatibility**: ✅ All services aligned to v2.0 architecture
- **Debug Logging**: ✅ Enabled and working (`LOG_LEVEL=DEBUG`, `USE_LOGURU=true`)

### 📊 System Health (Current Metrics)
- **Content unified**: 668 records total
- **Email messages**: 663 email records  
- **Individual messages**: 302 unique messages
- **Message occurrences**: 393 total occurrences
- **Deduplication efficiency**: 23% content reduction
- **Vector dimensions**: 1024 (Legal BERT model)
- **Database status**: SQLite WAL mode, 64MB cache, healthy

- **Pipeline Status**: ✅ Working - Gmail sync + keyword search operational
- **Code Quality**: ✅ Major technical debt resolution completed (2025-08-22)
  - Type safety: 4 critical modules 100% or significantly improved
  - Complexity: 95% reduction in high-complexity functions
  - Dependencies: All packages updated, deprecations resolved

## 🚀 Quick Start (Development)

### Enable Vector Search (Required)
```bash
# Install Qdrant locally (no Docker required)
curl -L -o /tmp/qdrant.tar.gz https://github.com/qdrant/qdrant/releases/download/v1.15.3/qdrant-aarch64-apple-darwin.tar.gz
tar -xzf /tmp/qdrant.tar.gz -C /tmp
mkdir -p ~/bin && cp /tmp/qdrant ~/bin/qdrant

# Start Qdrant with local storage
cd /path/to/Email\ Sync
QDRANT__STORAGE__PATH=./qdrant_data ~/bin/qdrant &

# Verify connection
tools/scripts/vsearch info  # Should show "Vector Service: Connected"
```

### Command Reference

| Category | Command | Description |
|----------|---------|-------------|
| **Search** | `tools/scripts/vsearch search "query"` | Basic search |
| | `tools/scripts/vsearch search "query" --type email --limit 10` | Filtered search |
| | `tools/scripts/vsearch info` | System status |
| **Ingestion** | `tools/scripts/vsearch ingest` | Process all content |
| | `tools/scripts/vsearch ingest --docs` | Process documents only |
| | `tools/scripts/vsearch upload document.pdf` | Single document |
| **Quality** | `make cleanup` | Complete automated cleanup |
| | `make fix-all` | Auto-fix all issues |
| | `make check` | Quality checks |
| **System** | `make full-run` | Complete pipeline |
| | `make diag-wiring` | System diagnostic |
| | `make vector-smoke` | Quick validation |
| **Maintenance** | `make db-validate` | Schema integrity |
| | `make vector-sync` | Sync vectors |
| | `make maintenance-all` | All checks |
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
| | `make preflight-vector-parity` | Vector sync check |
| | `python3 tests/test_email_parser.py` | Validate email parsing |

For detailed command documentation, see [docs/SERVICES_API.md](docs/SERVICES_API.md)

## 🏗️ Clean Flat Architecture

### Project Structure (Clean Organized Architecture)

```
Email Sync/
# Core Business Services (Root Level)
├── gmail/              # Email service
├── pdf/                # PDF processing
├── entity/             # Entity extraction
├── summarization/      # Document summarization
├── search_intelligence/ # Unified search intelligence
├── knowledge_graph/    # Knowledge graph service
├── legal_intelligence/ # Legal analysis service
├── shared/             # Shared utilities & database

# Organized Utility Services
├── utilities/          # Organized utility services [NEW: Reorganized 2025-08-17]
│   ├── embeddings/     # Embedding service (Legal BERT)
│   ├── vector_store/   # Vector store service
│   ├── ~~notes/~~      # **REMOVED** - Migrated to document pipeline
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
- **New Files (Goal)**: Aim to keep files under 450 lines to prevent unmaintainable monster files.
- **Function Size (Goal)**: Try to keep functions ~30 lines for readability.
- **Rationale**: Keeps AI development focused and prevents monster files
These are guidance targets to prevent monster files; they are not hard caps.

##### Code Quality Achievements (2025-08-22) ✅
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
  - Multiple developers working on same areas

##### SimpleDB Specific (DOCUMENTED TRIGGERS)
**SimpleDB will remain as-is unless these specific triggers occur:**
1. **Need async/multiprocess writes** - Currently single-threaded is sufficient
2. **Sustained SQLITE_BUSY or p95 latency issues for 2+ weeks** - Currently zero lock issues
3. **Migration off SQLite to Postgres/Cloud SQL** - SQLite perfect for single-user
4. **Method count exceeds 60 or complexity exceeds agreed caps** - Currently 47 methods
5. **p95 write latency >2× baseline for 2 weeks OR busy_events >0.5% of writes** - Objective SLO

**SQLite Optimizations Applied (2025-08-19):**
- WAL mode enabled for better concurrency
- 64MB cache for batch operations
- NORMAL synchronous mode (safe for single-user)
- 5-second busy timeout for resilience
- Slow-query logging (>100ms)
- `db_maintenance()` method for WAL checkpointing after large batches

#### Other Hard Limits (ENFORCED)
- **Cyclomatic Complexity**: Maximum 10 per function
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


## 📊 Key Services Overview

<!-- AUTO-GENERATED SERVICE COUNTS - DO NOT EDIT BY HAND -->
<!-- Generated by make docs-audit - data from tools/docs/audit.py -->

| Service | Directory | Total Lines | Code Lines |
|---------|-----------|-------------|------------|
| Shared | `shared/` | 6,123 | 4,592 |
| PDF | `pdf/` | 3,523 | 2,642 |
| Knowledge Graph | `knowledge_graph/` | 2,839 | 2,129 |
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
| **TOTAL** | **All Services** | **24,713** | **18,528** |

<!-- END AUTO-GENERATED SERVICE COUNTS -->


For detailed service descriptions and APIs, see [docs/SERVICES_API.md](docs/SERVICES_API.md)

## 📊 Database Schema

### Core Architecture: Message-Level Deduplication (v2.0) ✅ PRODUCTION BASELINE
The system implements advanced message-level email deduplication with TEXT source_ids and full schema compatibility.

**Current Production Status (2025-08-25)**:
- **302 unique messages** from **393 occurrences** (23% deduplication efficiency)
- **668 total email records** in content_unified with source_type='email_message'  
- **Gmail sync**: Fully operational with v2.0 schema
- **Test Coverage**: 97%+ on email_parsing module, 34 tests passing
- **Schema fixes**: All tables compatible, semantic pipeline working

**Primary Tables:**

#### `content_unified` - Single Source of Truth
- `id` (INTEGER PRIMARY KEY) - Auto-generated ID
- `source_type` (TEXT) - Type: 'email_message', 'document', 'document_chunk'
- `source_id` (TEXT) - **NEW**: TEXT-based IDs (message_hash for emails, doc_uuid for documents)
- `title` (TEXT) - Document title or email subject
- `body` (TEXT) - Full text content
- `sha256` (TEXT UNIQUE) - Content hash for deduplication
- `ready_for_embedding` (BOOLEAN) - Flag for embedding pipeline
- `validation_status` (TEXT) - 'pending', 'validated', 'failed'
- Additional metadata columns for quality tracking

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

## 🔍 System Status Verification - CURRENT BASELINE ✅

**Current verified metrics (2025-08-25 3:05 PM):**

```bash
# ✅ PRODUCTION VERIFIED COUNTS
# Content unified: 668 records
# Email messages: 663 records  
# Individual messages: 302 unique
# Message occurrences: 393 total

# Quick status check
tools/scripts/vsearch info                       # System overview
tools/scripts/vsearch search "lease" --limit 3  # Test keyword search

# Database verification
sqlite3 data/system_data/emails.db "SELECT 'content_unified:' || COUNT(*) FROM content_unified UNION ALL SELECT 'email_messages:' || COUNT(*) FROM content_unified WHERE source_type='email_message' UNION ALL SELECT 'individual_messages:' || COUNT(*) FROM individual_messages UNION ALL SELECT 'message_occurrences:' || COUNT(*) FROM message_occurrences;"

# Gmail sync test (with debug logging)  
export LOG_LEVEL=DEBUG && export USE_LOGURU=true && python3 -m gmail.main

# Schema validation
sqlite3 data/system_data/emails.db ".schema document_summaries"  # Verify all columns present

# Full system health check
make diag-wiring
```

For detailed API documentation and usage examples, see **[docs/SERVICES_API.md](docs/SERVICES_API.md)**

## 🔄 Unified Ingestion Pipeline

**Manual ingestion for emails and documents through unified processing pipeline.**

- **Pipeline**: All content → `content_unified` table → vector embeddings → search
- **Features**: Duplicate detection (SHA256), recursive processing, manual triggers
- **File Types**: PDF (PyPDF2/OCR), DOCX, TXT, MD

```bash
tools/scripts/vsearch ingest --docs              # Process documents
tools/scripts/vsearch ingest --emails            # Process emails
tools/scripts/vsearch ingest --docs --dir /path  # Custom directory
```

## 🔧 MCP Server Integration

The system provides 2 active MCP servers for Claude Desktop with 12+ intelligence tools.

**Configuration**: `make mcp-status` | `make mcp-generate` | `make mcp-validate`

**Active Servers**:
- **Legal Intelligence**: 6 legal analysis tools (entity extraction, timeline, knowledge graph)
- **Search Intelligence**: 6 search tools (smart search, similarity, clustering)

For complete MCP documentation and tool details, see **[docs/MCP_SERVERS.md](docs/MCP_SERVERS.md)**

## 🔬 Entity Extraction System

**Unified entity extraction with quality filtering (95.3% quality score)**

- **Processing**: All content types through single pipeline with OCR garbage detection
- **Statistics**: 719 entities extracted, 685 high-quality (275 entities/second)
- **Entity Types**: PERSON, ORG, DATE, COURT, STATUTE, MONEY, LEGAL_CONCEPT

```bash
tools/scripts/vsearch extract-entities --missing-only  # Extract entities
tools/scripts/vsearch entity-status                    # Check status
tools/scripts/vsearch search-entities --entity-type PERSON --entity-value "Smith"
```

For complete documentation, see **[docs/ENTITY_EXTRACTION_INTEGRATION.md](docs/ENTITY_EXTRACTION_INTEGRATION.md)**

## 📝 Logging System

**Uses loguru for superior logging** - Config: `shared/loguru_config.py`

```python
from loguru import logger
logger.info("Message")  # Simple API, automatic rotation, structured logging
```

Environment: `LOG_LEVEL=INFO`, `USE_LOGURU=true`

## 🔍 System Verification

```bash
python3 scripts/verify_pipeline.py              # Complete pipeline verification
python3 scripts/verify_pipeline.py --json       # CI-friendly JSON output
python3 scripts/verify_pipeline.py --trace abc123  # Trace specific document
make preflight-vector-parity                    # Vector sync check
```

Runs 6 test suites: Preflight, Smoke, Integrity, Performance, Quarantine, Document Tracing.

For detailed verification documentation, see **[docs/PIPELINE_VERIFICATION.md](docs/PIPELINE_VERIFICATION.md)**

## 🧪 Testing & Validation

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
python3 -c "from shared.simple_db import SimpleDB; db = SimpleDB(); print('✅ DB working')"
```

### Test Coverage
- **Email Parsing** (v2.0): 97%+ coverage, 34 tests total
  - `tests/test_email_parser.py` - Core functionality (16 tests)
  - `tests/test_email_integration.py` - End-to-end workflows (4 tests)
  - `tests/test_email_coverage.py` - Edge cases & error conditions (18 tests)
- **Unit Tests**: `tests/unit/` - Query expansion, parameter validation
- **Integration Tests**: `tests/integration/` - MCP parameter mapping
- **System Tests**: `scripts/verify_pipeline.py` - Full pipeline validation

For detailed testing documentation, see **[docs/PIPELINE_VERIFICATION.md](docs/PIPELINE_VERIFICATION.md)**

## 🛠️ Development Tools

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

For complete cleanup documentation: **[docs/AUTOMATED_CLEANUP.md](docs/AUTOMATED_CLEANUP.md)**

## 📋 Development Guidelines

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
- **Utilities**: utilities/embeddings/, utilities/vector_store/, ~~utilities/notes/~~ (removed)
- **Infrastructure**: infrastructure/pipelines/, infrastructure/documents/, infrastructure/mcp_servers/
- **Tools**: tools/cli/, tools/scripts/
- **shared/**: Shared utilities (keep minimal)
- **tests/**: All test files

## 📈 Performance Metrics

## 🎯 Philosophy

> Your system should be as simple as possible for YOUR needs.

This is a **single-user project**, important use case, not for profit, not enterprise software.

### Core Values
1. **Working code > Perfect abstractions**
2. **Direct solutions > Clever patterns**
3. **Less code > More features**
4. **Today's solution > Tomorrow's possibility**

## 📚 Documentation Index

### Primary Documentation
- **[README.md](README.md)** - User guide and quick start
- **[CLAUDE.md](CLAUDE.md)** - Development guide (this file)
- **[CHANGELOG.md](CHANGELOG.md)** - Version history and updates

### Detailed References
- **[docs/SERVICES_API.md](docs/SERVICES_API.md)** - Complete services API reference
- **[docs/MCP_SERVERS.md](docs/MCP_SERVERS.md)** - MCP server integration guide
- **[docs/ENTITY_EXTRACTION_INTEGRATION.md](docs/ENTITY_EXTRACTION_INTEGRATION.md)** - Entity extraction system guide **UPDATED**
- **[docs/DIAGNOSTIC_SYSTEM.md](docs/DIAGNOSTIC_SYSTEM.md)** - System diagnostic tools and troubleshooting
- **[docs/AUTOMATED_CLEANUP.md](docs/AUTOMATED_CLEANUP.md)** - Code cleanup tools
- **[docs/CLEANUP_QUICK_REFERENCE.md](docs/CLEANUP_QUICK_REFERENCE.md)** - Quick cleanup reference

### Service-Specific Documentation
- **[gmail/CLAUDE.md](gmail/CLAUDE.md)** - Gmail service implementation
- **[pdf/CLAUDE.md](pdf/CLAUDE.md)** - PDF processing details
- **[knowledge_graph/CLAUDE.md](knowledge_graph/CLAUDE.md)** - Knowledge graph API
- **[summarization/README.md](summarization/README.md)** - Document summarization

## 🚀 Next Steps - FROM PRODUCTION BASELINE ✅

### CURRENT STATUS: Production Ready with Keyword Search
✅ **Gmail sync working**  
✅ **Keyword search operational**  
✅ **Vector service connected**  
⏳ **Semantic search ready** (needs embedding generation)

### Immediate Next Actions
1. **Enable Semantic Search**: `tools/scripts/vsearch ingest --emails` - Generate embeddings for 668 emails
2. **Test Both Search Types**: 
   - Keyword: `tools/scripts/vsearch search "lease" --limit 5`
   - Semantic: `tools/scripts/vsearch search "tenant rights" --limit 5` (after embeddings)

### Daily Production Workflow
```bash
# Quick health check (30 seconds)
tools/scripts/vsearch info

# Gmail sync (as needed)
export LOG_LEVEL=DEBUG && python3 -m gmail.main

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
