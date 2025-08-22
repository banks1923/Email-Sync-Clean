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
- *Changelog.md*: Log all changes to changelog.md + update References across repo
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

## Current Architecture Status

- **Structure**: Flat Pythonic layout (no more `src/app/core/` nesting!)
- **Services**: 26,883 total lines (20,201 code lines) across 15 active services
- **Scripts**: 13 essential scripts (down from 35)
- **Documentation**: Consolidated to core files only
- **Testing**: Focus on real functionality, 89% less mocks
- **Pipeline Status**: ✅ Working (484 documents processed, export pipeline operational)

## 🚀 Quick Start (Development)

### Start Qdrant (Vector Search)
```bash
# Start Qdrant with local storage
cd /path/to/Email\ Sync
QDRANT__STORAGE__PATH=./qdrant_data ~/bin/qdrant &
```

### Core Commands
```bash
# Search (requires Qdrant — system is useless without it)
tools/scripts/vsearch search "query"

# Advanced search with filters
tools/scripts/vsearch search "query" --since "last week" --until "today"
tools/scripts/vsearch search "query" --type email --type pdf --limit 10
tools/scripts/vsearch search "query" --tag legal --tag contract --tag-logic AND

# System status
tools/scripts/vsearch info

# Upload and process
tools/scripts/vsearch upload document.pdf

# Code Quality & Cleanup
make cleanup                   # Complete automated code cleanup
make fix-all                  # Auto-fix all possible issues + format
make lint-all                 # Run both flake8 and ruff linters
make check                    # Comprehensive quality checks
make clean                    # Clean up caches and generated files

# System Operations
make full-run                 # Complete end-to-end system pipeline (Qdrant required)
make diag-wiring              # Full system diagnostic - validate wiring & efficiency
make vector-smoke             # Quick vector smoke test - upsert 50 points & run 2 searches

# Database & Vector Maintenance
make db-validate              # Validate database schema integrity
make vector-status            # Check vector store sync status
make vector-sync              # Sync missing vectors with database
make maintenance-all          # Run all maintenance checks

# Legal Intelligence commands
tools/scripts/vsearch legal process "24NNCV"
tools/scripts/vsearch legal timeline "24NNCV" -o timeline.json
tools/scripts/vsearch legal graph "24NNCV"

# Search Intelligence commands
tools/scripts/vsearch intelligence smart-search "contract attorney"
tools/scripts/vsearch intelligence similarity doc_123 --threshold 0.7
tools/scripts/vsearch intelligence cluster --threshold 0.8 -n 100

# Pipeline Verification & Diagnostics
python3 scripts/verify_pipeline.py              # Complete pipeline verification
python3 scripts/verify_pipeline.py --json       # CI-friendly JSON output
python3 scripts/verify_pipeline.py --since 24h  # Check recent processing activity
python3 scripts/verify_pipeline.py --trace a1b2c3d4  # Trace specific document

# Vector Parity Checks
make preflight-vector-parity                     # Check vector DB/Qdrant sync
python3 tools/preflight/vector_parity_check.py  # Standalone vector parity check
python3 tools/preflight.py                      # Full preflight system (includes vector parity)
```

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
├── data/              # Document processing pipeline
│   ├── raw/          # Incoming unprocessed documents
│   ├── staged/       # Documents being processed
│   ├── processed/    # Successfully processed documents
│   ├── quarantine/   # Failed processing documents
│   └── export/       # Documents ready for export
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
| shared | `shared/` | 4,705 | 3,484 |
| pdf | `pdf/` | 3,581 | 2,738 |
| knowledge_graph | `knowledge_graph/` | 2,829 | 2,195 |
| infrastructure/documents | `infrastructure/documents/` | 2,697 | 1,955 |
| infrastructure/pipelines | `infrastructure/pipelines/` | 2,673 | 1,947 |
| entity | `entity/` | 2,653 | 2,067 |
| gmail | `gmail/` | 1,886 | 1,414 |
| search_intelligence | `search_intelligence/` | 1,772 | 1,274 |
| infrastructure/mcp_servers | `infrastructure/mcp_servers/` | 1,598 | 1,229 |
| legal_intelligence | `legal_intelligence/` | 835 | 625 |
| summarization | `summarization/` | 502 | 360 |
| utilities/vector_store | `utilities/vector_store/` | 413 | 324 |
| utilities/timeline | `utilities/timeline/` | 388 | 317 |
| utilities/notes | `utilities/notes/` | 194 | 157 |
| utilities/embeddings | `utilities/embeddings/` | 157 | 115 |
| **TOTAL** | **All Services** | **26,883** | **20,201** |

<!-- END AUTO-GENERATED SERVICE COUNTS -->


### Core Business Services
- **Gmail Service** (`gmail/`): Email sync with History API, **advanced email parsing with individual message extraction**
- **PDF Service** (`pdf/`): Intelligent OCR detection, batch processing
- **Search Intelligence** (`search_intelligence/`): Smart search with query expansion
- **Legal Intelligence** (`legal_intelligence/`): Case analysis and timeline generation
- **Entity Extraction** (`entity/`): Legal NER with SpaCy
- **Summarization** (`summarization/`): TF-IDF + TextRank with Legal BERT
- **Knowledge Graph** (`knowledge_graph/`): Document relationships and similarity

### Utility Services
- **Embeddings** (`utilities/embeddings/`): Legal BERT 1024D vectors
- **Vector Store** (`utilities/vector_store/`): Qdrant wrapper with fallback
- ~~**Notes**~~ (`utilities/notes/`): **REMOVED** - Migrated to document pipeline for better search
- **Timeline** (`utilities/timeline/`): Chronological event tracking

### Infrastructure Services
- **MCP Servers** (`infrastructure/mcp_servers/`): Claude Desktop integration (2 active servers)
- **Pipelines** (`infrastructure/pipelines/`): Document processing workflows with HTML email cleaning
- **Documents** (`infrastructure/documents/`): Document lifecycle management

### Maintenance Utilities
- **Vector Maintenance** (`utilities/maintenance/vector_maintenance.py`): Unified vector operations
- **Schema Maintenance** (`utilities/maintenance/schema_maintenance.py`): Database schema operations

## 📊 Database Schema

### Primary Content Table: `content_unified`
The system uses a single unified content table for all document types:

**Table Structure:**
- `id` (TEXT PRIMARY KEY) - UUID for content
- `source_type` (TEXT) - Type of content: 'email', 'pdf', 'upload', 'transcript', **'email_message'**
- `source_id` (TEXT) - Original document/email ID
- `title` (TEXT) - Document title or email subject
- `body` (TEXT) - Full text content
- `created_at` (TIMESTAMP) - When content was added
- `ready_for_embedding` (BOOLEAN) - Flag for embedding pipeline
- `sha256` (TEXT) - Document hash for deduplication (includes sender/date for email_message evidence preservation)
- Additional metadata columns for specific content types

**Advanced Email Processing (2025-08-22):**
- **Individual Message Extraction**: Email threads are parsed to extract individual quoted messages
- **Legal Evidence Preservation**: Duplicate harassment signatures stored separately for evidence
- **Thread Reconstruction**: Messages maintain thread_id relationships for chronological timeline analysis
- **Pattern Detection**: Automated detection of harassment patterns (anonymous signatures, ignored messages)

**Current Status (Verify with Commands):**
- ⚠️ Migration in progress - run `make db-stats` for current counts
- Run `sqlite3 data/emails.db "SELECT 'content:' || COUNT(*) FROM content UNION ALL SELECT 'content_unified:' || COUNT(*) FROM content_unified"` to check migration status
- Run `make diag-wiring` to verify system health

## 🔍 System Status Verification

**Never trust documentation numbers. Always verify current state:**

```bash
# Check record counts across tables
make db-stats

# Check migration status  
sqlite3 data/emails.db "SELECT 'OLD content:' || COUNT(*) FROM content UNION ALL SELECT 'NEW content_unified:' || COUNT(*) FROM content_unified UNION ALL SELECT 'embeddings:' || COUNT(*) FROM embeddings"

# Check embedding coverage (includes email_message type for individual messages)
sqlite3 data/emails.db "SELECT source_type, COUNT(*) FROM content_unified GROUP BY source_type"

# Test advanced email parsing capabilities
python3 test_advanced_parsing.py     # Test parsing with subset
python3 test_full_integration.py     # Full integration test

# System health check
make diag-wiring
```

For detailed API documentation and usage examples, see **[docs/SERVICES_API.md](docs/SERVICES_API.md)**

## 🔧 MCP Server Integration

**Clean Architecture MCP Servers (2025-08-22 Update)**

The system provides unified MCP servers with flexible path resolution and centralized configuration management.

### Configuration Management

**Centralized MCP Configuration**: `infrastructure/mcp_config/`
- **Secure API key loading** from `~/Secrets/.env` (no hardcoded secrets)
- **Pydantic validation** with graceful fallback to dataclasses
- **Unified generation** for both Claude Code (.mcp.json) and Claude Desktop
- **Automatic server detection** based on available API keys

**Configuration Commands:**
```bash
# Show configuration status and API key counts
make mcp-status

# Generate .mcp.json for Claude Code
make mcp-generate

# Generate Claude Desktop configuration  
make mcp-generate-claude

# Validate all MCP servers exist and can start
make mcp-validate

# Preview configuration without writing files
make mcp-preview

# Remove generated configuration files
make mcp-clean
```

### Active Servers
- **Legal Intelligence MCP Server** (`legal_intelligence_mcp.py`): 6 comprehensive legal analysis tools
  - Entity extraction with Legal BERT + spaCy
  - Case timeline generation and gap analysis  
  - Knowledge graph relationships for legal cases
  - Document analysis with harassment pattern detection
  - Case tracking with deadline and procedural analysis
  - Cross-case relationship discovery
  
- **Search Intelligence MCP Server** (`search_intelligence_mcp.py`): 6 advanced search tools
  - Smart search with query preprocessing and expansion
  - Document similarity analysis with configurable thresholds
  - Entity extraction from documents or raw text
  - Document summarization with keyword extraction
  - Document clustering for pattern analysis
  - Batch processing operations

### Configuration-Driven Architecture
- **Secure Environment Loading**: API keys from ~/Secrets/.env via direnv
- **Flexible Path Resolution**: Uses Pydantic config system with graceful fallback
- **Direct Service Imports**: No factory injection complexity (follows Clean Architecture)
- **Legal Evidence Support**: Full integration with advanced email parsing system
- **Error Resilience**: Graceful degradation when dependencies unavailable
- **Security Validation**: Automatic file permission checks and warnings

### Other MCP Integrations
- **Sequential Thinking**: Structured problem-solving framework
- **Memory Server**: Persistent knowledge graph across sessions  
- **Task Master AI**: Advanced task management (conditional on API keys)
- **Filesystem**: File operations for Claude Code
- **Puppeteer**: Browser automation (Claude Desktop only)

For complete MCP server documentation, see **[docs/MCP_SERVERS.md](docs/MCP_SERVERS.md)**

## 📝 Logging System (Loguru)

The Email Sync system now uses **loguru** for superior logging capabilities (migrated Aug 17, 2025):

### Benefits for Developers
- **Simpler API**: Just `from loguru import logger` and use `logger.info()`
- **Better Debugging**: Automatic exception catching with full stack traces
- **Structured Logging**: Built-in JSON serialization for log analysis
- **Automatic Rotation**: Logs rotate at 500MB, compress to .zip after 10 days
- **Context Tracking**: Use `logger.bind()` to add context to all subsequent logs
- **Thread-Safe**: No configuration needed for concurrent operations
- **Color Output**: Beautiful, readable logs in development

### Configuration
- **Main config**: `shared/loguru_config.py`
- **Environment variables**:
  - `LOG_LEVEL`: DEBUG, INFO, WARNING, ERROR (default: INFO)
  - `ENVIRONMENT`: Set to 'production' for production safety
  - `USE_LOGURU`: Set to 'false' to fallback to standard logging

### For Rookie Developers
```python
# OLD WAY (confusing)
import logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
logger.info("Message")

# NEW WAY (simple with loguru)
from loguru import logger
logger.info("Message")
```

### Production Safety
- **Security**: Not a focus — private hobby project in private git. Do not spend effort on redaction or enterprise security here.

## 🔍 Pipeline Verification System

### Comprehensive Verification Suite

The Email Sync system includes a comprehensive verification system for end-to-end pipeline validation:

```bash
# Complete pipeline health check
python3 scripts/verify_pipeline.py

# CI integration (returns proper exit codes)
python3 scripts/verify_pipeline.py --json --strict

# Performance analysis with time windows
python3 scripts/verify_pipeline.py --since 24h

# Trace specific document through pipeline (multi-chunk example)
python3 scripts/verify_pipeline.py --trace ec69f22c
```

### Test Suite Components

**1. Preflight Test** - Environment & Schema Validation
- ✅ Database schema version and required tables
- ✅ Required columns in documents table (`sha256`, `char_count`, etc.)
- ✅ Qdrant vector database connectivity
- ✅ Missing dependency detection
- ✅ **Vector Parity Check**: Database vs Qdrant sync validation with delta thresholds

**2. Smoke Test** - End-to-End Chain Verification
- ✅ Complete chain: documents → content_unified → embeddings
- ✅ Exact SQL joins with deterministic ordering
- ✅ Real document processing verification
- ✅ **Multi-chunk document analysis**: Chunk count, total characters, chunk distribution
- ✅ **Document vs Chunk metrics**: Distinguishes unique documents from document chunks

**3. Integrity Test** - Data Consistency Validation
- ✅ Orphaned content detection (content without documents)
- ✅ Orphaned embeddings detection (embeddings without content)
- ✅ Processed documents without content normalization
- ✅ Duplicate content detection per source
- ✅ Quarantine statistics and retry analysis

**4. Performance Test** - Processing Metrics Analysis
- ✅ Document processing rates and character counts
- ✅ Embedding generation statistics
- ✅ Time window filtering (`--since 30m`, `--since 24h`, `--since 7d`)

**5. Quarantine Test** - Recovery System Validation
- ✅ Failed document analysis and retry logic
- ✅ Permanent failure detection (3+ attempts)
- ✅ Recovery handler availability

**6. Document Tracing** - Full Pipeline Inspection
- ✅ **Enhanced chunk hierarchy display**: Shows all chunks per document with tree structure
- ✅ **SHA256 prefix resolution**: Handles multi-chunk documents with DISTINCT resolution
- ✅ **Complete document lifecycle tracing**: From chunks → content_unified → embeddings
- ✅ **Content mapping clarification**: Explains content_unified represents full document text
- ✅ **All embeddings returned**: Not just first match, with model and timestamp info

### Exit Codes for CI Integration

- `0`: All tests passed
- `1`: Tests failed (or warnings with `--strict`)
- `2`: Configuration error
- `3`: Schema/environment mismatch
- `4`: Transient error (retry possible)

### JSON Mode for Automation

```bash
# Silent operation for CI pipelines
python3 scripts/verify_pipeline.py --json

# Example output:
{"status":"WARN","chain":false,"orphans":1,"dup_content":0,"docs_24h":12,"emb_24h":12}
```

### Document Processing Verification

The verification system confirms support for:
- ✅ **Text-based PDFs**: Fast PyPDF2 extraction
- ✅ **Scanned PDFs**: Tesseract OCR with automatic detection  
- ✅ **Legal Documents**: Court filings, contracts, judgments
- ✅ **Mixed Content**: Automatic text vs OCR detection
- ✅ **Multi-chunk Documents**: Large documents split into chunks with proper indexing
- ✅ **Pipeline Stages**: Raw → Staged → Processing → Storage → Embeddings

### Multi-Chunk Document Architecture

The system supports large documents through intelligent chunking:

```
Document: large-file.pdf (SHA256: abc123...)
├── Chunk 0: abc123..._0 (chunk_index: 0, chars: 2,500)
├── Chunk 1: abc123..._1 (chunk_index: 1, chars: 2,400)
└── Chunk 2: abc123..._2 (chunk_index: 2, chars: 1,800)
    ↓
Content Unified: ID=5 (represents full document text from all chunks)
    ↓  
Embeddings: ID=12 (1024D Legal BERT vector for complete document)
```

**Key Features:**
- **Chunk Indexing**: Each chunk has `chunk_index` (0, 1, 2...) and unique `chunk_id`
- **SHA256 Consistency**: All chunks share the same `sha256` hash for the original document
- **Content Unification**: One `content_unified` entry represents the complete document text
- **Single Embedding**: One embedding per document (not per chunk) for semantic search
- **Tracing Support**: `--trace <sha_prefix>` shows complete hierarchy for debugging

## 🧪 Testing Philosophy

### Approach
- **Test Real Functionality**: Avoid mocks when possible
- **Simple Assertions**: Direct checks, not complex matchers
- **Integration > Unit**: Test workflows, not implementation
- **Comprehensive Verification**: Use `verify_pipeline.py` for full system validation

### Quick Test
```python
# Test clean services work
from utilities.embeddings import get_embedding_service
from utilities.vector_store import get_vector_store
from search_intelligence import get_search_intelligence_service
from shared.simple_db import SimpleDB

# All should initialize without errors
emb = get_embedding_service()
db = SimpleDB()
search = get_search_intelligence_service()
# Vector/Search will fail if Qdrant is not running (by design)
```

### Pipeline Verification
```bash
# Comprehensive system validation
python3 scripts/verify_pipeline.py

# Expected output: 6 tests (preflight, observability, smoke, integrity, performance, quarantine)
# Status: PASS (green), WARN (yellow), FAIL (red)
```

## 🔍 Vector Parity Check System

The Email Sync system includes a comprehensive vector parity checking system to ensure the Qdrant vector database stays in sync with the main SQLite database.

### Components

**Vector Parity Check Script** (`tools/preflight/vector_parity_check.py`)
- Compares database expected vs Qdrant actual vector counts
- Enforces zero-vector guard unless `ALLOW_EMPTY_COLLECTION=true`
- JSON output with detailed diagnostics
- Configurable delta thresholds for warnings vs failures

### Environment Variables

```bash
APP_DB_PATH=data/emails.db              # Database path (default)
VSTORE_URL=http://localhost:6333        # Qdrant URL (or VSTORE_HOST/VSTORE_PORT)
VSTORE_API_KEY=...                      # Optional Qdrant API key
VSTORE_COLLECTION=emails                # Collection name (default)
ALLOW_EMPTY_COLLECTION=false            # Allow zero vectors (default: false)
EXPECTED_DIM=1024                       # Expected vector dimensions
DELTA_THRESHOLD=50                      # Warn vs fail threshold for sync delta
```

### Usage Examples

```bash
# Standalone vector parity check
make preflight-vector-parity

# Full preflight system (includes vector parity)
python3 tools/preflight.py

# Custom configuration
APP_DB_PATH=custom.db DELTA_THRESHOLD=10 python3 tools/preflight/vector_parity_check.py
```

### Exit Codes

- **0**: All checks passed (perfect sync)
- **1**: Warning (small delta within threshold)
- **2**: Failure (connection issues, large delta, or zero-vector violation)

### Integration

The vector parity check is automatically included in:
- **Preflight System**: `python3 tools/preflight.py` 
- **Makefile Targets**: `make preflight-vector-parity`
- **CI Pipelines**: JSON output mode for automation

## 🛠️ Development Tools

### Automated Code Cleanup
```bash
# One-command solutions (AI should use these first)
make cleanup        # Complete automated cleanup pipeline
make fix-all        # Auto-fix all issues + advanced formatting
make check          # Quality checks + tests (no modifications)
```

### Code Transformation Tools
- **LibCST**: Recommended for large-scale Python refactoring (import fixes, renaming)
  - Preserves formatting and comments perfectly
  - See **[docs/CODE_TRANSFORMATION_TOOLS.md](docs/CODE_TRANSFORMATION_TOOLS.md)** for usage

### SonarQube for IDE (Code Quality Analysis)
Real-time code quality and security analysis directly in your IDE. Catches bugs, vulnerabilities, and code smells as you type.

#### Installation
```bash
# VS Code: Install from marketplace
# Extension ID: SonarSource.sonarlint-vscode
# Or search "SonarQube for IDE" in VS Code Extensions

# Command-line analysis (requires sonarlint-cli)
make sonar-check       # Run SonarLint analysis on entire codebase
make sonar-fix         # Auto-fix issues where possible
make sonar-report      # Generate HTML quality report
```

#### What It Catches
- **Security**: Hardcoded credentials, SQL injection, unsafe deserialization
- **Bugs**: Null pointers, resource leaks, unreachable code
- **Code Smells**: Complexity > 10, duplicate code, long functions > 30 lines
- **Python-specific**: PEP8 violations, unused imports, mutable defaults
- **Project-specific**: Validates our architecture principles (no god modules, simple patterns)

#### Configuration
Project rules are defined in `.sonarlint/` directory:
- Connected to our linting standards (flake8, ruff)
- Enforces our 450-line file limit for new code
- Validates our flat architecture principles

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
- **[docs/DIAGNOSTIC_SYSTEM.md](docs/DIAGNOSTIC_SYSTEM.md)** - System diagnostic tools and troubleshooting
- **[docs/AUTOMATED_CLEANUP.md](docs/AUTOMATED_CLEANUP.md)** - Code cleanup tools
- **[docs/CLEANUP_QUICK_REFERENCE.md](docs/CLEANUP_QUICK_REFERENCE.md)** - Quick cleanup reference

### Service-Specific Documentation
- **[gmail/CLAUDE.md](gmail/CLAUDE.md)** - Gmail service implementation
- **[pdf/CLAUDE.md](pdf/CLAUDE.md)** - PDF processing details
- **[knowledge_graph/CLAUDE.md](knowledge_graph/CLAUDE.md)** - Knowledge graph API
- **[summarization/README.md](summarization/README.md)** - Document summarization

## 🚀 Next Steps

### For Users
1. **Health Check**: `make diag-wiring` - Validates all system components (30 seconds)
2. **Full Pipeline**: `make full-run` - Complete email sync with vector operations (2-3 minutes)  
3. **Quick Test**: `make vector-smoke` - Fast validation of core functionality (10 seconds)

### Production Workflow
```bash
# Morning routine
make diag-wiring    # Validate system health before work

# Development cycle  
make check          # Code quality validation
make full-run       # Integration testing

# Maintenance
make maintenance-all # Clean up and optimize system
```

---

*Remember: The best code is no code. The second best is simple code that works.*

## Task Master AI Integration (Optional)

Task Master provides advanced task management for complex projects. When Task Master is installed and initialized in this project, its guidelines enhance the development workflow.

**If Task Master is active**: See `.taskmaster/CLAUDE.md` for Task Master-specific commands and workflows. Use `task-master init` to initialize when needed.

## Task Master AI Instructions
**Import Task Master's development workflow commands and guidelines, treat as if import is in the main CLAUDE.md file.**
@./.taskmaster/CLAUDE.md
