# Email Sync System - Development Guide

Clean architecture implementation with Legal BERT semantic search and simplified services.

> **For user documentation, see [README.md](README.md)**

<!-- ⚠️ CRITICAL CUSTOM INSTRUCTIONS - DO NOT MODIFY ⚠️ -->
<!-- REQUIRES 3X CONFIRMATION TO CHANGE THIS SECTION -->
<!-- PROTECTED WORKFLOW INSTRUCTIONS BELOW -->

- **CORE**: PLAN, Break task into atomic steps, Always use todo list, web search for best practices, 1orchestrationagent1 check work when done. Test and document changes.

## Core Development Principles

### Anti-Patterns (NEVER DO)
- **No Complex Hierarchies**: Simple agent classes
- **No Abstract Patterns**: Direct implementation
- **No Meta-Programming**: Keep it simple
- **No Long Context**: Break tasks into tiny chunks

### Good Patterns (ALWAYS DO)
- **Read CLAUDE.md First**: Every agent starts by reading project principles
- **Use TodoWrite**: Track all tasks with todo lists
- **Small Tasks**: Maximum context per task to prevent confusion
- **Changelog.md**: Log all changes to change log
- **Organized Repo**: Create files only when needed and do it in the correct location

### Agent Workflow
1. **Read CLAUDE.md** - Understand project principles
2. **Create Todo List** - Break work into tiny tasks
3. **Execute Tasks** - One small task at a time
4. **Write Logs** - Document all actions and decisions in logs folder
5. **QC Review** - QC Agent reviews and summarizes logs

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
- **Search Architecture**: ✅ Analog-first with graceful database fallback (2025-08-18)

## 🚀 Quick Start (Development)

### Core Commands
```bash
# Search (works with or without Qdrant)
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

# Legal Intelligence commands
tools/scripts/vsearch legal process "24NNCV"
tools/scripts/vsearch legal timeline "24NNCV" -o timeline.json
tools/scripts/vsearch legal graph "24NNCV"

# Search Intelligence commands
tools/scripts/vsearch intelligence smart-search "contract attorney"
tools/scripts/vsearch intelligence similarity doc_123 --threshold 0.7
tools/scripts/vsearch intelligence cluster --threshold 0.8 -n 100
```

### Optional: Enable Vector Search
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

**Major Update (2025-08-17)**: Directory reorganization completed:
- **53% reduction**: Root directory items reduced from 34 to 16
- **One-level nesting**: utilities/, infrastructure/, tools/ organize smaller services
- **Core services remain at root**: Main business logic stays easily accessible
- **Auto-updated imports**: 60+ import statements updated via Bowler AST transformations

### Architecture Principles

#### File Size Guidelines

##### For New Development (ENFORCED)
- **New Files**: Target under 450 lines to prevent AI-generated bloat
- **Function Size**: Maximum 30 lines per function
- **Rationale**: Keeps AI development focused and prevents monster files

##### For Existing Code (PRAGMATIC)
- **Core Infrastructure** (SimpleDB, main services): Size guided by functionality
- **Working Code Principle**: Don't refactor working code without clear benefit
- **Refactor Triggers**:
  - Maintenance difficulties
  - Clear functional separation opportunities
  - Multiple developers working on same areas

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

## 🔍 Search Architecture (Analog-First)

### Primary Search: Analog Database
- **Source**: Markdown files in `analog_db/` (39 documents)
- **Method**: Direct file-based semantic search with Legal BERT
- **Reliability**: Always available, no dependencies
- **Performance**: ~3 seconds for complex queries, 95%+ relevance

### Secondary Search: Database Enhancement  
- **Source**: SQLite `content` table (optional)
- **Method**: Structured search with preprocessing
- **Reliability**: Graceful fallback if unavailable
- **Performance**: Faster for large datasets when available

### Graceful Degradation
Following "Simple > Complex" principle from CLAUDE.md:
- Files are **source of truth** (reliable, always works)
- Database is **optional optimization** (faster when available)
- Search **never fails** due to database issues
- **Zero breaking changes** for existing functionality

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
- **MCP Servers** (`infrastructure/mcp_servers/`): Claude Desktop integration
- **Pipelines** (`infrastructure/pipelines/`): Document processing workflows with HTML email cleaning
- **Documents** (`infrastructure/documents/`): Document lifecycle management

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
- **Sensitive Data Filtering**: Passwords, tokens, emails automatically redacted in production
- **Error-Only Logs**: Separate error log file in production for critical issues
- **Diagnose Mode**: Disabled in production to prevent data leaks

## 🧪 Testing Philosophy

### Approach
- **Test Real Functionality**: Avoid mocks when possible
- **Simple Assertions**: Direct checks, not complex matchers
- **Integration > Unit**: Test workflows, not implementation

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
# Vector/Search may fail if Qdrant not running (expected)
```

## 🛠️ Development Tools

### Automated Code Cleanup
```bash
# One-command solutions (AI should use these first)
make cleanup        # Complete automated cleanup pipeline
make fix-all        # Auto-fix all issues + advanced formatting
make check          # Quality checks + tests (no modifications)
```

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
1. Run `tools/scripts/vsearch search "test"` - It works immediately
2. Optionally start Qdrant for semantic search

---

*Remember: The best code is no code. The second best is simple code that works.*

## Task Master AI Integration (Optional)

Task Master provides advanced task management for complex projects. When Task Master is installed and initialized in this project, its guidelines enhance the development workflow.

**If Task Master is active**: See `.taskmaster/CLAUDE.md` for Task Master-specific commands and workflows. Use `task-master init` to initialize when needed.

## Task Master AI Instructions
**Import Task Master's development workflow commands and guidelines, treat as if import is in the main CLAUDE.md file.**
@./.taskmaster/CLAUDE.md
