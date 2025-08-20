# Email Sync System - Development Guide

Clean architecture implementation with Legal BERT semantic search and simplified services.

> **For user documentation, see [README.md](README.md)**

<!-- ⚠️ CRITICAL CUSTOM INSTRUCTIONS - DO NOT MODIFY ⚠️ -->
<!-- REQUIRES 3X CONFIRMATION TO CHANGE THIS SECTION -->
<!-- PROTECTED WORKFLOW INSTRUCTIONS BELOW -->

- **CORE**: PLAN,  Atomic steps, Always use todo list, web search best practices, 1orchestrationagent1.

## Core Development Principles

### Anti-Patterns (NEVER DO)
- **No Complex Hierarchies**: Simple agent classes
- **No Abstract Patterns**: Direct implementation
- **No Meta-Programming**: Keep it simple
- **No Long Context**: Break tasks into atomic steps

### Good Patterns (ALWAYS DO)
- **Read CLAUDE.md First**:  read project principles
- **Use TodoWrite**: Track all tasks with todo lists
- **Small Tasks**: Maximum context per task to prevent confusion
- **Changelog.md**: Log all changes to changelog
- **No breaking Repo**: ASK before Going off the rails
- **Remember**: The best code is no code. The second best is simple code that works.*
- **PLAN**
- **CLARIFY**


### Agent Workflow
1. **Read CLAUDE.md** - Understand project principles
2. **Create Todo List** - Break work into tiny tasks
3. **Execute Tasks** - One small task at a time

<!-- END PROTECTED SECTION - DO NOT MODIFY WITHOUT 3X CONFIRMATION -->

> **For detailed API documentation, see [docs/SERVICES_API.md](docs/SERVICES_API.md)**
> **For MCP server documentation, see [docs/MCP_SERVERS.md](docs/MCP_SERVERS.md)**

## Current Architecture Status

- **Structure**: Flat Pythonic layout (no more `src/app/core/` nesting!)
- **Clean Services**: 550 lines replacing 2000+ lines (75% reduction)
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
tools/scripts/vsearch transcribe audio.mp4

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
├── transcription/      # Audio/video transcription
├── entity/             # Entity extraction
├── summarization/      # Document summarization
├── search_intelligence/ # Unified search intelligence
├── knowledge_graph/    # Knowledge graph service
├── legal_intelligence/ # Legal analysis service
├── monitoring/         # Health monitoring
├── shared/             # Shared utilities & database

# Organized Utility Services
├── utilities/          # Organized utility services [NEW: Reorganized 2025-08-17]
│   ├── embeddings/     # Embedding service (Legal BERT)
│   ├── vector_store/   # Vector store service
│   ├── notes/          # Notes management
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

### Core Business Services
- **Gmail Service** (`gmail/`): Email sync with History API, 500+ emails/batch
- **PDF Service** (`pdf/`): Intelligent OCR detection, batch processing
- **Search Intelligence** (`search_intelligence/`): Smart search with query expansion
- **Legal Intelligence** (`legal_intelligence/`): Case analysis and timeline generation
- **Transcription** (`transcription/`): Audio/video processing with Whisper
- **Entity Extraction** (`entity/`): Legal NER with SpaCy
- **Summarization** (`summarization/`): TF-IDF + TextRank with Legal BERT
- **Knowledge Graph** (`knowledge_graph/`): Document relationships and similarity

### Utility Services
- **Embeddings** (`utilities/embeddings/`): Legal BERT 1024D vectors
- **Vector Store** (`utilities/vector_store/`): Qdrant wrapper with fallback
- **Notes** (`utilities/notes/`): Markdown notes with tags
- **Timeline** (`utilities/timeline/`): Chronological event tracking

### Infrastructure Services
- **MCP Servers** (`infrastructure/mcp_servers/`): Claude Desktop integration (2 active servers)
- **Pipelines** (`infrastructure/pipelines/`): Document processing workflows with HTML email cleaning
- **Documents** (`infrastructure/documents/`): Document lifecycle management

### Maintenance Utilities
- **Vector Maintenance** (`utilities/maintenance/vector_maintenance.py`): Unified vector operations
- **Schema Maintenance** (`utilities/maintenance/schema_maintenance.py`): Database schema operations

For detailed API documentation and usage examples, see **[docs/SERVICES_API.md](docs/SERVICES_API.md)**

## 🔧 MCP Server Integration

The system provides 40+ specialized tools through MCP servers:
- **Legal Intelligence MCP Server**: 6 legal analysis tools
- **Search Intelligence MCP Server**: 6 search and document intelligence tools
- **Sequential Thinking**: Structured problem-solving framework
- **Memory Server**: Persistent knowledge graph across sessions
- **Firecrawl**: Advanced web scraping capabilities
- **Qdrant**: Semantic memory and vector operations

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
- **Utilities**: utilities/embeddings/, utilities/vector_store/, utilities/notes/
- **Infrastructure**: infrastructure/pipelines/, infrastructure/documents/, infrastructure/mcp_servers/
- **Tools**: tools/cli/, tools/scripts/
- **shared/**: Shared utilities (keep minimal)
- **tests/**: All test files

## 📈 Performance Metrics

## 🎯 Philosophy

> Your system should be as simple as possible for YOUR needs.

This is a **single-user hobby project**, not enterprise software. Every line of code should justify its existence. If you can't explain what it does in one sentence, it's too complex.

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
- **[transcription/CLAUDE.md](transcription/CLAUDE.md)** - Audio transcription
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
