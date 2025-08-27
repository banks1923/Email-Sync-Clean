# Legal Document Search System

AI-powered search system with Legal BERT semantic understanding for legal document analysis.

> **CURRENT: Production Ready** - Working Gmail sync, keyword search, and semantic search capabilities

## STATUS: PRODUCTION BASELINE (2025-08-26) - WORKING

WORKING: **Gmail Sync v2.0**: Working with message-level deduplication and content reduction  
WORKING: **Keyword Search**: Fully operational hybrid search system  
WORKING: **Vector Service**: Qdrant connected with Legal BERT ready for embeddings  
WORKING: **Schema Compatibility**: All services aligned to v2.0 architecture  
WORKING: **Debug Logging**: Enabled system-wide for troubleshooting  
WORKING: **Database Health**: Email deduplication active, SQLite WAL mode optimized  
**NEW**: **Foreign Key Integrity**: Referential integrity enforced with CASCADE deletes (2025-08-26)  

## READY: Quick Start - PRODUCTION READY

### VALIDATE: Current Baseline (30 seconds)
```bash
# Quick system health check
tools/scripts/vsearch info

# Test keyword search (should return 5 lease-related results)
tools/scripts/vsearch search "lease" --limit 5

# Verify Gmail sync status
export LOG_LEVEL=DEBUG && python3 -m gmail.main
```

### Search Operations (Primary Use)
```bash
# Search across all content with keyword search (WORKING NOW)
tools/scripts/vsearch search "contract terms"

# Advanced search with filters
tools/scripts/vsearch search "contract terms" --type email --limit 10
tools/scripts/vsearch search "lease termination" --limit 5

# Enable semantic search (next step after baseline validation)
tools/scripts/vsearch ingest --emails  # Generate embeddings for semantic search

# Additional analysis tools
tools/scripts/vsearch legal process "case_id"
tools/scripts/vsearch intelligence smart-search "query"
```

### Document Processing
```bash
# Upload and process PDFs (with OCR support)
tools/scripts/vsearch upload document.pdf

# Batch process multiple PDFs
tools/scripts/vsearch upload /path/to/pdfs/

# Gmail sync (incremental)
python3 -m gmail.main
```

## Key Features

### AI-Powered Database Search
- **Semantic Search**: Legal BERT 1024D embeddings for context understanding
- **Database Storage**: SQLite with emails, PDFs, transcripts - **Chain integrity maintained**
- **Unified Search**: Search all content types in one database
- **Advanced Filters**: Date ranges, content types, and tag-based filtering
- **Flexible Dates**: Natural language dates ("last week", "3 days ago", "this month")
- **OCR Support**: Automatic text extraction from scanned PDFs
- **Batch Processing**: Bulk document operations
- **Gmail Sync**: Incremental sync with History API and content deduplication
- **Clean Architecture**: Simplified database-only system (analog removed)

### Search Intelligence
- **Smart Search**: Query preprocessing with abbreviation expansion and synonyms
- **Query Expansion**: "LLC" → "limited liability company", "Q1" → "first quarter"
- **Intelligent Ranking**: Entity relevance + recency scoring for better results
- **Document Similarity**: Find related documents using Legal BERT embeddings
- **Content Clustering**: DBSCAN clustering with configurable thresholds
- **Duplicate Detection**: SHA-256 hash for exact, cosine similarity for near-duplicates
- **Entity Caching**: TTL-based caching for entity extraction results
- **Auto-Summarization**: Integrated TF-IDF and TextRank summarization

### Document Intelligence
- **Automatic Summarization**: TF-IDF keywords and TextRank key sentences
- **Smart Processing**: PDFs get 5 sentences/15 keywords, emails get 3/10
- **Legal BERT Integration**: Semantic similarity for better sentence selection
- **Intelligence Schema**: Dedicated tables for summaries and metadata
- **Batch Operations**: Efficient processing of multiple documents
- **Production Ready**: Fully integrated with Gmail and PDF services

### Document Analysis & Relationships
- **Document Similarity**: Find related content using Legal BERT embeddings
- **Timeline Analysis**: Temporal relationships with automatic date extraction
- **Content Clustering**: Group similar documents using DBSCAN
- **Duplicate Detection**: Hash-based and similarity-based detection
- **Performance Caching**: Database-level caching system

### Performance & Caching
- **Three-Tier Architecture**: Memory → Database → File caching
- **Automatic Promotion**: Data moves to faster tiers when accessed
- **TTL Support**: Configurable expiration across all cache levels
- **Content Invalidation**: Automatic cache invalidation when content changes
- **Thread-Safe**: Full concurrency support

### ARCHITECTURE: Clean Architecture

```
User → CLI → Services → Data
              ↓
    ├── EmbeddingService (Legal BERT)
    ├── VectorStore (Qdrant)
    ├── SearchService (Hybrid search)
    ├── SearchIntelligence (Query expansion)
    ├── LegalIntelligence (Case analysis)
    ├── DocumentSummarizer (Auto-summarization)
    ├── CacheManager (Performance)
    └── SimpleDB (SQLite operations)
```

### Data Storage
```
data/
├── system_data/        # Main database and system files
│   └── emails.db       # SQLite database
└── Stoneman_dispute/   # Case-specific documents
    └── user_data/      # Document storage
```
- **SQLite Database**: All content stored in unified table
- **Email Deduplication**: Message-level processing
- **Foreign Key Integrity**: Referential integrity enforced

### Core Services
- **EmbeddingService**: Text-to-vector conversion using Legal BERT
- **VectorStore**: Qdrant vector operations (optional)
- **SearchService**: Search orchestration
- **SimpleDB**: Direct SQLite operations without abstractions

## PREREQUISITES

### Required
- Python 3.8+
- 4GB+ RAM (for Legal BERT model)

### Optional
- Qdrant vector database (for semantic search)
- Gmail API credentials (for email sync)
- FFmpeg (for audio processing)

## INSTALLATION

### 1. Clone Repository
```bash
git clone <repository-url>
cd "Email Sync"
```

### 2. Install Dependencies
```bash
pip install -r requirements.txt
```

### 3. Run the System
```bash
# Test search (works without any setup)
tools/scripts/vsearch search "test query"

# Check system status
tools/scripts/vsearch info
```

### 4. Optional: Enable Semantic Search
```bash
# Qdrant is installed locally - starts automatically
# No Docker required

# Semantic search works automatically when Qdrant is running
tools/scripts/vsearch search "legal contract"
```

## ARCHITECTURE: Details

### Core Services

#### EmbeddingService (`utilities/embeddings/`)
- Converts text to Legal BERT 1024D vectors
- Singleton pattern for model reuse
- Auto-detects device (MPS/CUDA/CPU)

#### VectorStore (`utilities/vector_store/`)
- Qdrant vector database operations
- Simple CRUD for vectors
- Optional - system works without it

#### SearchService (`search_intelligence/`)
- Orchestrates search across all services
- Combines semantic and keyword search
- Falls back gracefully when services unavailable

#### SimpleDB (`shared/simple_db.py`)
- Direct SQLite operations
- No ORM, no abstractions
- Just SQL that works

### Architecture Principles
- **Simple > Complex**: Direct function calls, no factories
- **Working > Perfect**: Practical solutions that work
- **Small Files**: Target 450 lines for new files; existing working files guided by functionality
- **Small Functions**: Maximum 30 lines per function
- **No Enterprise Patterns**: No dependency injection, no abstract classes

## DOCUMENTATION

### Primary Documentation
- **[README.md](README.md)** - User guide and quick start (this file)
- **[CLAUDE.md](CLAUDE.md)** - Development guide and architecture principles  
- **[CHANGELOG.md](CHANGELOG.md)** - Version history and project updates

### Developer References
- **[docs/SERVICES_API.md](docs/SERVICES_API.md)** - Complete API reference for all services
- **[docs/MCP_SERVERS.md](docs/MCP_SERVERS.md)** - MCP server integration and tools guide
- Code quality and cleanup tools (see Makefile commands)

### Service-Specific Documentation  
- **[gmail/CLAUDE.md](gmail/CLAUDE.md)** - Gmail service implementation details
- **[pdf/CLAUDE.md](pdf/CLAUDE.md)** - PDF processing and OCR functionality
- Audio transcription service (via document pipeline)
- Knowledge graph operations (via search intelligence)
- **[summarization/README.md](summarization/README.md)** - Document summarization engine

> **For developers**: Start with [CLAUDE.md](CLAUDE.md) for core principles, then refer to [docs/SERVICES_API.md](docs/SERVICES_API.md) for detailed API documentation.

## PROJECT: Structure

```
Email Sync/
# Core Business Services (Root Level - Reorganized 2025-08-17)
├── gmail/                   # Email service with History API sync
├── pdf/                     # PDF processing with intelligent OCR
├── transcription/           # Audio/video transcription with Whisper
├── entity/                  # Named entity recognition (Legal NER)
├── summarization/           # Document summarization (TF-IDF + TextRank)
├── search_intelligence/     # Unified search with query expansion
├── knowledge_graph/         # Document relationships and similarity
├── legal_intelligence/      # Legal case analysis and timelines
├── monitoring/              # Health monitoring and metrics
├── shared/                  # Shared utilities and SimpleDB

# Organized Utility Services
├── utilities/               # Reorganized utility services
│   ├── embeddings/          # Legal BERT 1024D embeddings
│   ├── vector_store/        # Qdrant wrapper with fallback
│   # notes/ removed - migrated to document pipeline
│   └── timeline/            # Chronological event tracking

# Infrastructure Services  
├── infrastructure/          # Infrastructure and processing
│   ├── pipelines/           # Document processing pipelines
│   ├── documents/           # Document lifecycle management
│   └── mcp_servers/         # MCP server implementations

# Development Tools
├── tools/                   # Development and user tools
│   ├── cli/                 # CLI handler modules
│   └── scripts/             # User-facing scripts (vsearch, etc.)

# Documentation & Testing
├── docs/                    # Focused documentation
│   ├── SERVICES_API.md      # Complete API reference
│   ├── MCP_SERVERS.md       # MCP integration guide
│   └── AUTOMATED_CLEANUP.md # Code quality tools
├── tests/                   # Test suite (integration focused)
├── data/                    # Data storage (system_data/, case files)
└── .taskmaster/             # Task management system
```

## WORKFLOWS: Common Operations

### Setup & Development (Simplified Make Commands)
```bash
# Complete setup from scratch
make setup          # Install everything and get started

# Daily development
make test           # Run fast tests
make format         # Format code
make lint           # Check code quality
make fix            # Auto-fix common issues
make clean          # Clean up cache files
```

### System Operations
```bash
# System health and diagnostics
make status         # Quick system health check
make diagnose       # Deep system diagnostic (when broken)
make backup         # Backup your data
make reset          # Nuclear reset (use with caution)
```

### Content Operations
```bash
# Search documents
make search QUERY="lease termination"    # Search with specific terms
make search QUERY="contract terms"       # Example search

# Upload and sync
make upload FILE="document.pdf"          # Upload single document
make sync                                # Sync Gmail emails
```

### Advanced Search (Direct CLI)
```bash
# Basic search
tools/scripts/vsearch search "important meeting"

# Search with filters
tools/scripts/vsearch search "contract" --type email --limit 10
tools/scripts/vsearch search "lease" --limit 5

# Legal analysis
tools/scripts/vsearch legal process "case_id"
tools/scripts/vsearch intelligence smart-search "query"
```

### Advanced Document Processing (Direct CLI)
```bash
# Upload single PDF (automatic OCR if needed)
tools/scripts/vsearch upload document.pdf

# Batch upload directory of PDFs
tools/scripts/vsearch upload /path/to/legal/documents/

# Check processing stats
tools/scripts/vsearch info  # Shows OCR vs text extraction counts

# Generate embeddings for semantic search
tools/scripts/vsearch ingest --emails

# Search documents
tools/scripts/vsearch search "contract clause"
```



## TESTING

### Running Tests
```bash
# Run all working tests (skip deprecated)
python3 -m pytest tests/ -k "not integration and not pdf_service and not gmail_service and not vector_service"

# Run specific test categories
python3 -m pytest tests/test_search_intelligence.py -v      # Search intelligence
python3 -m pytest tests/test_legal_intelligence.py -v        # Legal intelligence
python3 -m pytest tests/test_cache_manager.py -v            # Caching system
python3 -m pytest tests/test_mcp_integration.py -v          # MCP servers
python3 -m pytest tests/test_knowledge_graph.py -v          # Knowledge graph

# Run with coverage report
python3 -m pytest tests/ --cov=. --cov-report=html
# View coverage: open htmlcov/index.html

# Run only passing tests (quick validation)
python3 -m pytest tests/ -m "not broken" --tb=short
```

### Test Coverage Status
- **Total Tests**: 445 collected (26 with import errors to fix)
- **Working Tests**: ~419 tests passing
- **Test Categories**:
  - WORKING: Intelligence Services (search, legal, MCP)
  - WORKING: Caching System (memory, file, database)
  - WORKING: Knowledge Graph & Embeddings
  - WORKING: Document Processing (summarization, timeline)
  - WARNING: Legacy tests need import updates (pdf_service, gmail_service)

### Quick Service Validation
```bash
# Test core services are working
python3 -c "
from embeddings import get_embedding_service
from shared.simple_db import SimpleDB
from search import get_search_service
from caching import get_global_cache_manager

# Test embeddings
emb = get_embedding_service()
vec = emb.encode('test')
print(f'WORKING: Embeddings: {len(vec)} dimensions')

# Test database
db = SimpleDB()
stats = db.get_content_stats()
print(f'WORKING: Database: {stats}')

# Test search
search = get_search_service()
print('WORKING: Search service initialized')

# Test caching
cache = get_global_cache_manager()
cache.set('test_key', {'data': 'test'})
result = cache.get('test_key')
print(f'WORKING: Cache: {result}')
"
```

### Adding New Tests
```bash
# Create test file following naming convention
tests/test_<service_name>.py

# Use provided fixtures
from tests.shared_test_fixtures import *

# Run your new test
python3 -m pytest tests/test_<service_name>.py -v
```

### Integration Test Files
- `tests/test_mcp_integration.py` - MCP server integration tests
- `tests/test_core_services_integration.py` - Core service integration tests
- `tests/TEST_COVERAGE_ANALYSIS.md` - Comprehensive coverage analysis

## TROUBLESHOOTING

### Semantic Search Not Working
```bash
# Qdrant is installed locally - check if it's running
# No Docker required

# Verify connection
scripts/vsearch info  # Should show "Vector Service: Connected"
```

### Import Errors
```bash
# Ensure Python path is set
export PYTHONPATH=/path/to/Email-Sync:$PYTHONPATH
```

### Model Download
First run downloads Legal BERT (~1.3GB). This is one-time only.

## PERFORMANCE

### Architecture Benefits
- **Simplified Structure**: Clean, flat organization
- **Reduced Complexity**: Focused, single-purpose modules
- **Maintainability**: Clear service boundaries and responsibilities
- **Performance**: Direct operations without abstraction overhead

### Resource Usage
- **Memory**: 2-4GB typical (model loaded once)
- **Disk**: ~2GB for model + your data
- **CPU**: Minimal except during embedding generation

## PROJECT: Status

### Current Features
- **Search Intelligence**: Query preprocessing, expansion, and intelligent ranking
- **Document Intelligence**: Automatic summarization with TF-IDF and TextRank
- **Legal Intelligence**: Legal case analysis tools via MCP
- **Performance Optimization**: Multi-tier caching system
- **Document Pipeline**: Automated processing and ingestion
- **Timeline Extraction**: Temporal relationship analysis

See `.taskmaster/` for detailed development status.

## CONTRIBUTING

This is a personal project focused on simplicity. Contributions should:
- Follow the "Simple > Complex" philosophy
- Keep new files under 450 lines; don't refactor working large files unnecessarily
- Keep functions under 30 lines
- Avoid enterprise patterns
- Include tests for new features

## LICENSE

[Your License Here]

## ACKNOWLEDGMENTS

- Legal BERT model by Pile of Law
- Qdrant vector database
- OpenAI Whisper for transcription

---

**Philosophy**: Your system should be as simple as possible for YOUR needs. This is a single-user system that prioritizes working code over perfect abstractions.
