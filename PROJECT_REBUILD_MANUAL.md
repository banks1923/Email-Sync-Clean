# Email Sync System - Complete Rebuild Manual

**Target Audience**: Developers who need to rebuild this project from scratch  
**Complexity Level**: Intermediate to Advanced  
**Time Estimate**: 4-6 weeks for complete rebuild  
**Prerequisites**: Python, SQLite, basic ML/embeddings knowledge

---

## Table of Contents

1. [Executive Summary](#executive-summary)
2. [Current System Analysis](#current-system-analysis)
3. [Architectural Lessons Learned](#architectural-lessons-learned)
4. [Clean Slate Design](#clean-slate-design)
5. [Implementation Roadmap](#implementation-roadmap)
6. [Critical Gotchas & Solutions](#critical-gotchas--solutions)
7. [Testing Strategy](#testing-strategy)
8. [Deployment & Operations](#deployment--operations)

---

## Executive Summary

### What This System Does
A **document search and analysis system** that:
- Syncs emails from Gmail API
- Processes PDF documents with OCR
- Generates semantic embeddings using Legal BERT
- Provides AI-powered search across all content
- Extracts entities and creates timelines
- Supports legal document analysis

### Why Rebuild Is Needed
The current system suffers from **architectural fragmentation**:
- **Dual content storage** (Gmail→content table, PDF→content_unified table)
- **Configuration-code mismatches** (768D config vs 1024D actual embeddings)
- **Uncoordinated services** (each works independently)
- **Manual coordination** required between working subsystems
- **Tech debt** accumulated from incremental development

### Rebuild Goals
1. **Unified Architecture**: Single content model, consistent patterns
2. **Fail-Fast Pipeline**: Clear error handling, early failure detection
3. **Single Command Operation**: `make rebuild && make full-run` should work
4. **Maintainable Codebase**: Clear service boundaries, dependency injection
5. **Production Ready**: Monitoring, logging, recovery procedures

---

## Current System Analysis

### What Works (Preserve These Patterns)

#### 1. **Service Single Responsibility** ✅
```python
# Current services already have good boundaries
GmailService: Only email ingestion
PDFService: Only PDF processing  
EmbeddingService: Only vector generation
SearchService: Only search operations
```

#### 2. **Sophisticated Automation** ✅
```bash
# These automation systems work well
scripts/backfill_embeddings.py       # Processes 997 pending embeddings
utilities/semantic_pipeline.py       # Full enrichment pipeline
make vector-sync                     # Qdrant synchronization
tools/scripts/vsearch semantic       # CLI automation
```

#### 3. **Robust Data Layer** ✅
```python
# SimpleDB provides solid foundation
- WAL mode for concurrency
- Proper foreign key constraints  
- Migration tracking system
- Batch operations (1000+ records/sec)
```

#### 4. **Legal BERT Integration** ✅
```python
# Working 1024-dimensional embeddings
Model: pile-of-law/legalbert-large-1.7M-2
Performance: 7.8s per document, 0.007s per query
Quality: Semantic search across 585 documents
```

### What's Broken (Fix in Rebuild)

#### 1. **Architectural Fragmentation** ❌
```
Gmail Service → content table (UUID IDs)
PDF Service → content_unified table (Integer IDs)  
Search Service → Queries both tables
Vector Service → Only works with content_unified
```

#### 2. **Configuration Chaos** ❌
```python
# config/settings.py
embedding_model = "nlpaueb/legal-bert-base-uncased"  # 768D
embedding_dimension = 768

# utilities/embeddings/embedding_service.py  
model_name = "pile-of-law/legalbert-large-1.7M-2"  # 1024D
dimensions = 1024
```

#### 3. **Manual Coordination Required** ❌
```bash
# Current workflow requires manual steps
1. Sync emails with Gmail
2. Manually run backfill script  
3. Manually sync vectors
4. Manually check health
```

#### 4. **No Fail-Fast Behavior** ❌
- Services continue running with partial failures
- No early error detection
- Silent failures in embedding generation
- No coordinated health checks

---

## Architectural Lessons Learned

### Key Insights from Analysis

#### 1. **Coordination > Reconstruction**
The services aren't fundamentally broken - they lack coordination:
- Each service works well independently
- The automation systems are sophisticated
- Data integrity is maintained
- **Problem**: Services don't work together seamlessly

#### 2. **Configuration Must Drive Code**
Current system has config-code drift:
- Configuration files are ignored
- Hard-coded values in services
- No validation of config consistency
- **Solution**: Config-first design with runtime validation

#### 3. **Single Content Model Required**
Dual table system creates complexity:
- Search has to query multiple tables
- Vector system only works with one table
- Embedding generation is inconsistent
- **Solution**: One content table, one ID system, one processing flow

#### 4. **Pipeline Should Be Atomic**
Current system allows partial failures:
- Documents can be ingested but not embedded
- Embeddings can exist without vectors in Qdrant
- No transactional guarantees
- **Solution**: All-or-nothing processing pipeline

### Design Principles for Rebuild

#### 1. **Configuration-First Architecture**
```python
# Everything driven by validated configuration
@dataclass
class SystemConfig:
    embedding_model: str
    embedding_dimension: int
    database_path: str
    vector_store_url: str
    
    def __post_init__(self):
        self.validate()  # Fail fast on invalid config
```

#### 2. **Unified Content Model**
```python
# Single content representation
@dataclass
class Content:
    id: UUID                    # Universal identifier
    source_type: ContentType    # email, pdf, upload
    title: str
    body: str
    metadata: dict
    content_hash: str          # SHA256 deduplication
    processing_state: ProcessingState
    created_at: datetime
```

#### 3. **Atomic Processing Pipeline**
```python
# All-or-nothing processing
class ContentProcessor:
    def process(self, content: Content) -> ProcessingResult:
        with self.transaction():
            self.normalize_content(content)
            self.generate_embedding(content)  
            self.store_vector(content)
            self.extract_entities(content)
            # If any step fails, rollback all
```

#### 4. **Dependency Injection**
```python
# Testable, configurable services
class EmailIngestionService:
    def __init__(self, 
                 config: SystemConfig,
                 content_repo: ContentRepository,
                 processor: ContentProcessor):
        self.config = config
        self.content_repo = content_repo
        self.processor = processor
```

---

## Clean Slate Design

### System Architecture

```
┌─ Configuration Layer ─────────────────────────────┐
│  SystemConfig (single source of truth)           │
└───────────────────────────────────────────────────┘
                           │
┌─ Ingestion Layer ─────────────────────────────────┐
│  EmailIngestionService   PDFIngestionService      │
│  DocumentIngestionService                         │
└───────────────────────────────────────────────────┘
                           │
┌─ Processing Pipeline ─────────────────────────────┐
│  ContentNormalizer                                │
│  EmbeddingGenerator                               │  
│  EntityExtractor                                  │
│  VectorStorer                                     │
└───────────────────────────────────────────────────┘
                           │
┌─ Storage Layer ───────────────────────────────────┐
│  ContentRepository  VectorRepository              │
│  MetadataRepository                               │
└───────────────────────────────────────────────────┘
                           │
┌─ Query Layer ─────────────────────────────────────┐
│  SearchService  VectorSearchService               │
│  ContentRetrievalService                          │
└───────────────────────────────────────────────────┘
```

### Database Schema

```sql
-- Single unified content table
CREATE TABLE content (
    id TEXT PRIMARY KEY,                    -- UUID
    source_type TEXT NOT NULL,              -- 'email', 'pdf', 'upload'
    source_id TEXT NOT NULL,                -- Original source identifier
    title TEXT NOT NULL,
    body TEXT NOT NULL,
    content_hash TEXT UNIQUE NOT NULL,      -- SHA256 for deduplication
    metadata TEXT NOT NULL,                 -- JSON metadata
    processing_state TEXT DEFAULT 'pending', -- 'pending', 'processing', 'completed', 'failed'
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Processing pipeline tracking
CREATE TABLE processing_log (
    id TEXT PRIMARY KEY,
    content_id TEXT NOT NULL,
    processor_name TEXT NOT NULL,
    status TEXT NOT NULL,                   -- 'started', 'completed', 'failed'
    result_data TEXT,                       -- JSON results
    error_message TEXT,
    started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP,
    FOREIGN KEY (content_id) REFERENCES content(id)
);

-- Embeddings (one-to-one with content)
CREATE TABLE embeddings (
    content_id TEXT PRIMARY KEY,
    model_name TEXT NOT NULL,
    embedding_vector BLOB NOT NULL,
    dimension INTEGER NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (content_id) REFERENCES content(id)
);

-- Entities extracted from content
CREATE TABLE entities (
    id TEXT PRIMARY KEY,
    content_id TEXT NOT NULL,
    entity_type TEXT NOT NULL,
    entity_value TEXT NOT NULL,
    confidence REAL NOT NULL,
    start_pos INTEGER,
    end_pos INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (content_id) REFERENCES content(id)
);

-- Configuration tracking
CREATE TABLE system_config (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### Service Interfaces

```python
# Core service contracts
class ContentIngestionService(Protocol):
    def ingest(self, source_data: Any) -> List[Content]:
        """Convert source data to Content objects"""

class ContentProcessor(Protocol):
    def process(self, content: Content) -> ProcessingResult:
        """Process content through full pipeline"""

class ContentRepository(Protocol):
    def save(self, content: Content) -> UUID:
        """Store content, return ID"""
    
    def get(self, content_id: UUID) -> Content:
        """Retrieve content by ID"""
    
    def search(self, query: str) -> List[Content]:
        """Search content by text"""

class VectorRepository(Protocol):
    def store(self, content_id: UUID, vector: np.ndarray) -> bool:
        """Store vector for content"""
    
    def search(self, vector: np.ndarray, limit: int) -> List[SimilarityResult]:
        """Find similar vectors"""
```

---

## Implementation Roadmap

### Phase 1: Foundation (Week 1)

#### 1.1 Project Structure
```
email_sync_v2/
├── config/
│   ├── __init__.py
│   ├── settings.py         # SystemConfig with validation
│   └── defaults.py         # Default configuration values
├── core/
│   ├── __init__.py
│   ├── models.py           # Content, ProcessingResult data models
│   ├── interfaces.py       # Service protocols/interfaces
│   └── exceptions.py       # Custom exception hierarchy
├── ingestion/
│   ├── __init__.py
│   ├── email_service.py    # EmailIngestionService
│   ├── pdf_service.py      # PDFIngestionService
│   └── document_service.py # DocumentIngestionService
├── processing/
│   ├── __init__.py
│   ├── pipeline.py         # ContentProcessor implementation
│   ├── normalizer.py       # ContentNormalizer
│   ├── embeddings.py       # EmbeddingGenerator
│   ├── entities.py         # EntityExtractor
│   └── vectors.py          # VectorStorer
├── storage/
│   ├── __init__.py
│   ├── content_repo.py     # ContentRepository implementation
│   ├── vector_repo.py      # VectorRepository implementation
│   ├── metadata_repo.py    # MetadataRepository implementation
│   └── database.py         # Database connection and migrations
├── query/
│   ├── __init__.py
│   ├── search_service.py   # SearchService
│   ├── vector_search.py    # VectorSearchService
│   └── retrieval.py        # ContentRetrievalService
├── cli/
│   ├── __init__.py
│   ├── commands.py         # CLI command implementations
│   └── main.py             # Main CLI entry point
├── tests/
│   ├── unit/               # Unit tests for each service
│   ├── integration/        # Integration tests
│   └── fixtures/           # Test data and mocks
├── migrations/
│   ├── 001_initial_schema.sql
│   └── migrate.py          # Migration runner
├── docker/
│   ├── Dockerfile
│   ├── docker-compose.yml
│   └── qdrant.yml          # Qdrant configuration
├── scripts/
│   ├── setup.sh            # Initial setup script
│   ├── full_run.py         # End-to-end pipeline runner
│   └── migrate_old_data.py # Migration from current system
├── config.yaml             # Main configuration file
├── requirements.txt
├── Makefile               # Build and operation commands
└── README.md              # Setup and usage instructions
```

#### 1.2 Core Models
```python
# core/models.py
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Dict, Any, Optional
from uuid import UUID

class ContentType(Enum):
    EMAIL = "email"
    PDF = "pdf"  
    UPLOAD = "upload"

class ProcessingState(Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"

@dataclass
class Content:
    id: UUID
    source_type: ContentType
    source_id: str
    title: str
    body: str
    content_hash: str
    metadata: Dict[str, Any]
    processing_state: ProcessingState
    created_at: datetime
    updated_at: Optional[datetime] = None
    
    def __post_init__(self):
        if self.updated_at is None:
            self.updated_at = self.created_at

@dataclass
class ProcessingResult:
    success: bool
    content_id: UUID
    processor_name: str
    result_data: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None
    processing_time_ms: Optional[int] = None
```

#### 1.3 Configuration System
```python
# config/settings.py
import os
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional
import yaml

@dataclass
class DatabaseConfig:
    path: str = "data/emails.db"
    connection_pool_size: int = 5
    busy_timeout_ms: int = 5000
    
    def validate(self):
        db_path = Path(self.path)
        if not db_path.parent.exists():
            db_path.parent.mkdir(parents=True, exist_ok=True)

@dataclass  
class EmbeddingConfig:
    model_name: str = "pile-of-law/legalbert-large-1.7M-2"
    dimension: int = 1024
    batch_size: int = 32
    device: str = "auto"  # auto, cpu, cuda, mps
    
    def validate(self):
        if self.dimension not in [768, 1024]:
            raise ValueError(f"Unsupported dimension: {self.dimension}")
        if self.batch_size < 1 or self.batch_size > 256:
            raise ValueError(f"Invalid batch_size: {self.batch_size}")

@dataclass
class VectorConfig:
    qdrant_url: str = "http://localhost:6333"
    collection_name: str = "email_sync"
    timeout_seconds: int = 60
    batch_size: int = 100
    
    def validate(self):
        if not self.qdrant_url.startswith(("http://", "https://")):
            raise ValueError(f"Invalid Qdrant URL: {self.qdrant_url}")

@dataclass
class GmailConfig:
    credentials_path: str = ".config/credentials.json"
    token_path: str = ".config/token.json"
    batch_size: int = 50
    max_results: int = 500
    preferred_senders: List[str] = None
    
    def __post_init__(self):
        if self.preferred_senders is None:
            self.preferred_senders = []
    
    def validate(self):
        creds_path = Path(self.credentials_path)
        if not creds_path.exists():
            raise FileNotFoundError(f"Gmail credentials not found: {creds_path}")

@dataclass
class SystemConfig:
    database: DatabaseConfig
    embedding: EmbeddingConfig  
    vector: VectorConfig
    gmail: GmailConfig
    
    @classmethod
    def from_file(cls, config_path: str = "config.yaml") -> "SystemConfig":
        """Load configuration from YAML file"""
        if not Path(config_path).exists():
            # Create default config file
            default_config = cls.default()
            default_config.save_to_file(config_path)
            return default_config
            
        with open(config_path) as f:
            data = yaml.safe_load(f)
            
        return cls(
            database=DatabaseConfig(**data.get("database", {})),
            embedding=EmbeddingConfig(**data.get("embedding", {})),
            vector=VectorConfig(**data.get("vector", {})),
            gmail=GmailConfig(**data.get("gmail", {}))
        )
    
    @classmethod
    def default(cls) -> "SystemConfig":
        """Create default configuration"""
        return cls(
            database=DatabaseConfig(),
            embedding=EmbeddingConfig(),
            vector=VectorConfig(),
            gmail=GmailConfig()
        )
    
    def validate(self):
        """Validate all configuration sections"""
        self.database.validate()
        self.embedding.validate()
        self.vector.validate()
        self.gmail.validate()
    
    def save_to_file(self, config_path: str):
        """Save configuration to YAML file"""
        import dataclasses
        
        def to_dict(obj):
            if dataclasses.is_dataclass(obj):
                return {k: to_dict(v) for k, v in dataclasses.asdict(obj).items()}
            return obj
            
        data = to_dict(self)
        with open(config_path, 'w') as f:
            yaml.dump(data, f, default_flow_style=False)
```

### Phase 2: Core Services (Week 2)

#### 2.1 Content Repository
```python
# storage/content_repo.py
import sqlite3
import json
import hashlib
from datetime import datetime
from typing import List, Optional
from uuid import UUID, uuid4

from core.models import Content, ContentType, ProcessingState
from core.interfaces import ContentRepository

class SQLiteContentRepository(ContentRepository):
    def __init__(self, db_path: str):
        self.db_path = db_path
        self._ensure_schema()
    
    def save(self, content: Content) -> UUID:
        """Store content, return ID"""
        if content.id is None:
            content.id = uuid4()
            
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT OR REPLACE INTO content 
                (id, source_type, source_id, title, body, content_hash, 
                 metadata, processing_state, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                str(content.id),
                content.source_type.value,
                content.source_id,
                content.title,
                content.body,
                content.content_hash,
                json.dumps(content.metadata),
                content.processing_state.value,
                content.created_at.isoformat(),
                content.updated_at.isoformat()
            ))
            
        return content.id
    
    def get(self, content_id: UUID) -> Optional[Content]:
        """Retrieve content by ID"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            row = conn.execute(
                "SELECT * FROM content WHERE id = ?", 
                (str(content_id),)
            ).fetchone()
            
        if not row:
            return None
            
        return Content(
            id=UUID(row["id"]),
            source_type=ContentType(row["source_type"]),
            source_id=row["source_id"],
            title=row["title"],
            body=row["body"],
            content_hash=row["content_hash"],
            metadata=json.loads(row["metadata"]),
            processing_state=ProcessingState(row["processing_state"]),
            created_at=datetime.fromisoformat(row["created_at"]),
            updated_at=datetime.fromisoformat(row["updated_at"])
        )
    
    def search(self, query: str, limit: int = 100) -> List[Content]:
        """Search content by text"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute("""
                SELECT * FROM content 
                WHERE title LIKE ? OR body LIKE ?
                ORDER BY updated_at DESC
                LIMIT ?
            """, (f"%{query}%", f"%{query}%", limit)).fetchall()
            
        return [self._row_to_content(row) for row in rows]
    
    def get_by_hash(self, content_hash: str) -> Optional[Content]:
        """Get content by hash (for deduplication)"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            row = conn.execute(
                "SELECT * FROM content WHERE content_hash = ?",
                (content_hash,)
            ).fetchone()
            
        return self._row_to_content(row) if row else None
    
    def update_processing_state(self, content_id: UUID, state: ProcessingState):
        """Update processing state"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                UPDATE content 
                SET processing_state = ?, updated_at = ?
                WHERE id = ?
            """, (
                state.value,
                datetime.now().isoformat(),
                str(content_id)
            ))
    
    def _row_to_content(self, row) -> Content:
        """Convert database row to Content object"""
        return Content(
            id=UUID(row["id"]),
            source_type=ContentType(row["source_type"]),
            source_id=row["source_id"],
            title=row["title"],
            body=row["body"],
            content_hash=row["content_hash"],
            metadata=json.loads(row["metadata"]),
            processing_state=ProcessingState(row["processing_state"]),
            created_at=datetime.fromisoformat(row["created_at"]),
            updated_at=datetime.fromisoformat(row["updated_at"])
        )
    
    def _ensure_schema(self):
        """Create database schema if it doesn't exist"""
        with sqlite3.connect(self.db_path) as conn:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS content (
                    id TEXT PRIMARY KEY,
                    source_type TEXT NOT NULL,
                    source_id TEXT NOT NULL,
                    title TEXT NOT NULL,
                    body TEXT NOT NULL,
                    content_hash TEXT UNIQUE NOT NULL,
                    metadata TEXT NOT NULL,
                    processing_state TEXT DEFAULT 'pending',
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );
                
                CREATE INDEX IF NOT EXISTS idx_content_source_type 
                ON content(source_type);
                
                CREATE INDEX IF NOT EXISTS idx_content_processing_state 
                ON content(processing_state);
                
                CREATE INDEX IF NOT EXISTS idx_content_created_at 
                ON content(created_at);
                
                CREATE TABLE IF NOT EXISTS processing_log (
                    id TEXT PRIMARY KEY,
                    content_id TEXT NOT NULL,
                    processor_name TEXT NOT NULL,
                    status TEXT NOT NULL,
                    result_data TEXT,
                    error_message TEXT,
                    started_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    completed_at TEXT,
                    FOREIGN KEY (content_id) REFERENCES content(id)
                );
            """)
```

#### 2.2 Processing Pipeline
```python
# processing/pipeline.py
import time
from typing import List, Dict, Any
from uuid import UUID
from loguru import logger

from core.models import Content, ProcessingResult, ProcessingState
from core.interfaces import ContentProcessor
from storage.content_repo import ContentRepository
from processing.normalizer import ContentNormalizer
from processing.embeddings import EmbeddingGenerator
from processing.entities import EntityExtractor
from processing.vectors import VectorStorer

class AtomicContentProcessor(ContentProcessor):
    """Processes content through full pipeline atomically"""
    
    def __init__(self,
                 content_repo: ContentRepository,
                 normalizer: ContentNormalizer,
                 embedding_generator: EmbeddingGenerator,
                 entity_extractor: EntityExtractor,
                 vector_storer: VectorStorer):
        self.content_repo = content_repo
        self.processors = [
            normalizer,
            embedding_generator,
            entity_extractor,
            vector_storer
        ]
    
    def process(self, content: Content) -> ProcessingResult:
        """Process content through all stages, fail fast on any error"""
        start_time = time.time()
        
        try:
            # Mark as processing
            self.content_repo.update_processing_state(
                content.id, ProcessingState.PROCESSING
            )
            
            # Run each processor
            for processor in self.processors:
                processor_start = time.time()
                
                try:
                    result = processor.process(content)
                    if not result.success:
                        raise ProcessingError(
                            f"{processor.__class__.__name__} failed: {result.error_message}"
                        )
                    
                    processor_time = (time.time() - processor_start) * 1000
                    logger.debug(
                        f"{processor.__class__.__name__} completed for {content.id} "
                        f"in {processor_time:.1f}ms"
                    )
                    
                except Exception as e:
                    # Mark as failed and re-raise
                    self.content_repo.update_processing_state(
                        content.id, ProcessingState.FAILED
                    )
                    raise ProcessingError(
                        f"{processor.__class__.__name__} failed: {str(e)}"
                    ) from e
            
            # Mark as completed
            self.content_repo.update_processing_state(
                content.id, ProcessingState.COMPLETED
            )
            
            total_time = (time.time() - start_time) * 1000
            
            return ProcessingResult(
                success=True,
                content_id=content.id,
                processor_name="AtomicContentProcessor",
                processing_time_ms=int(total_time)
            )
            
        except Exception as e:
            total_time = (time.time() - start_time) * 1000
            
            return ProcessingResult(
                success=False,
                content_id=content.id,
                processor_name="AtomicContentProcessor",
                error_message=str(e),
                processing_time_ms=int(total_time)
            )

class ProcessingError(Exception):
    """Exception raised during content processing"""
    pass
```

### Phase 3: Ingestion Services (Week 3)

#### 3.1 Email Ingestion
```python
# ingestion/email_service.py
import hashlib
from datetime import datetime
from typing import List, Dict, Any
from uuid import uuid4

from core.models import Content, ContentType, ProcessingState
from core.interfaces import ContentIngestionService
from config.settings import GmailConfig

class EmailIngestionService(ContentIngestionService):
    """Single responsibility: fetch emails and create Content objects"""
    
    def __init__(self, gmail_config: GmailConfig):
        self.config = gmail_config
        self.gmail_api = self._init_gmail_api()
    
    def ingest(self, max_results: int = None) -> List[Content]:
        """Fetch emails from Gmail and convert to Content objects"""
        max_results = max_results or self.config.max_results
        
        # Get email data from Gmail API
        email_data = self._fetch_emails(max_results)
        
        # Convert to Content objects
        content_objects = []
        for email in email_data:
            content = self._email_to_content(email)
            content_objects.append(content)
            
        return content_objects
    
    def _fetch_emails(self, max_results: int) -> List[Dict[str, Any]]:
        """Fetch emails from Gmail API"""
        # Implementation details for Gmail API integration
        # Similar to current GmailService but focused only on fetching
        pass
    
    def _email_to_content(self, email_data: Dict[str, Any]) -> Content:
        """Convert Gmail email data to Content object"""
        # Create content hash for deduplication
        content_text = f"{email_data.get('subject', '')}{email_data.get('body', '')}"
        content_hash = hashlib.sha256(content_text.encode('utf-8')).hexdigest()
        
        return Content(
            id=uuid4(),
            source_type=ContentType.EMAIL,
            source_id=email_data['message_id'],
            title=email_data.get('subject', 'No Subject'),
            body=email_data.get('body', ''),
            content_hash=content_hash,
            metadata={
                'sender': email_data.get('sender'),
                'recipient': email_data.get('recipient'),
                'datetime_utc': email_data.get('datetime_utc'),
                'thread_id': email_data.get('thread_id'),
                'labels': email_data.get('labels', [])
            },
            processing_state=ProcessingState.PENDING,
            created_at=datetime.now()
        )
    
    def _init_gmail_api(self):
        """Initialize Gmail API client"""
        # Implementation for Gmail API setup
        pass
```

### Phase 4: CLI & Orchestration (Week 4)

#### 4.1 Main CLI
```python
# cli/main.py
import click
from pathlib import Path
import sys

from config.settings import SystemConfig
from cli.commands import (
    setup_command,
    ingest_command,
    process_command,
    search_command,
    status_command,
    full_run_command
)

@click.group()
@click.option('--config', default='config.yaml', help='Configuration file path')
@click.pass_context
def cli(ctx, config):
    """Email Sync System v2 - Clean Architecture"""
    
    # Load and validate configuration
    try:
        system_config = SystemConfig.from_file(config)
        system_config.validate()
        ctx.obj = system_config
    except Exception as e:
        click.echo(f"❌ Configuration error: {e}", err=True)
        sys.exit(1)

@cli.command()
@click.pass_context
def setup(ctx):
    """Initial system setup"""
    setup_command(ctx.obj)

@cli.command()
@click.option('--source', type=click.Choice(['gmail', 'pdf', 'upload']), 
              required=True, help='Content source to ingest from')
@click.option('--max-results', type=int, help='Maximum items to ingest')
@click.pass_context
def ingest(ctx, source, max_results):
    """Ingest content from source"""
    ingest_command(ctx.obj, source, max_results)

@cli.command()
@click.option('--content-id', help='Process specific content ID')
@click.option('--all-pending', is_flag=True, help='Process all pending content')
@click.pass_context  
def process(ctx, content_id, all_pending):
    """Process content through pipeline"""
    process_command(ctx.obj, content_id, all_pending)

@cli.command()
@click.argument('query')
@click.option('--limit', default=10, help='Maximum results to return')
@click.pass_context
def search(ctx, query, limit):
    """Search content"""
    search_command(ctx.obj, query, limit)

@cli.command()
@click.pass_context
def status(ctx):
    """Show system status"""
    status_command(ctx.obj)

@cli.command()
@click.option('--max-emails', default=100, help='Maximum emails to sync')
@click.option('--max-pdfs', default=50, help='Maximum PDFs to process')
@click.pass_context
def full_run(ctx, max_emails, max_pdfs):
    """Run complete pipeline: ingest → process → verify"""
    full_run_command(ctx.obj, max_emails, max_pdfs)

if __name__ == '__main__':
    cli()
```

#### 4.2 Full Run Command
```python
# cli/commands.py
import time
from typing import List
from loguru import logger

from config.settings import SystemConfig
from ingestion.email_service import EmailIngestionService
from ingestion.pdf_service import PDFIngestionService
from processing.pipeline import AtomicContentProcessor
from storage.content_repo import SQLiteContentRepository
from query.search_service import SearchService

def full_run_command(config: SystemConfig, max_emails: int, max_pdfs: int):
    """Execute full pipeline with fail-fast behavior"""
    
    logger.info("🚀 Starting full system pipeline")
    start_time = time.time()
    
    try:
        # Initialize services
        content_repo = SQLiteContentRepository(config.database.path)
        processor = create_processor(config, content_repo)
        search_service = SearchService(config, content_repo)
        
        # Step 1: Ingest emails
        logger.info(f"📧 Ingesting up to {max_emails} emails...")
        email_service = EmailIngestionService(config.gmail)
        email_content = email_service.ingest(max_emails)
        
        logger.info(f"✅ Ingested {len(email_content)} emails")
        
        # Step 2: Ingest PDFs
        logger.info(f"📄 Ingesting up to {max_pdfs} PDFs...")
        pdf_service = PDFIngestionService(config)
        pdf_content = pdf_service.ingest(max_pdfs)
        
        logger.info(f"✅ Ingested {len(pdf_content)} PDFs")
        
        # Step 3: Store all content
        all_content = email_content + pdf_content
        for content in all_content:
            content_repo.save(content)
            
        logger.info(f"💾 Stored {len(all_content)} content items")
        
        # Step 4: Process all content
        logger.info("🔄 Processing all content through pipeline...")
        processed = 0
        failed = 0
        
        for content in all_content:
            result = processor.process(content)
            if result.success:
                processed += 1
            else:
                failed += 1
                logger.warning(f"❌ Failed to process {content.id}: {result.error_message}")
                
        logger.info(f"✅ Processed {processed} items, {failed} failed")
        
        # Step 5: Verify search functionality
        logger.info("🔍 Verifying search functionality...")
        test_queries = ["contract", "email", "legal"]
        
        for query in test_queries:
            results = search_service.search(query, limit=5)
            logger.info(f"  Query '{query}': {len(results)} results")
            
        # Step 6: Generate report
        total_time = time.time() - start_time
        logger.info("=" * 60)
        logger.info("📊 PIPELINE COMPLETE")
        logger.info(f"⏱️  Total time: {total_time:.1f}s")
        logger.info(f"📥 Content ingested: {len(all_content)}")
        logger.info(f"✅ Successfully processed: {processed}")
        logger.info(f"❌ Failed: {failed}")
        logger.info("=" * 60)
        
        if failed > 0:
            logger.warning(f"⚠️  {failed} items failed processing")
            return 1
        else:
            logger.success("🎉 All content processed successfully!")
            return 0
            
    except Exception as e:
        logger.error(f"❌ Pipeline failed: {e}")
        return 1

def create_processor(config: SystemConfig, content_repo: SQLiteContentRepository) -> AtomicContentProcessor:
    """Create configured content processor"""
    from processing.normalizer import ContentNormalizer
    from processing.embeddings import EmbeddingGenerator
    from processing.entities import EntityExtractor
    from processing.vectors import VectorStorer
    
    normalizer = ContentNormalizer()
    embedding_generator = EmbeddingGenerator(config.embedding)
    entity_extractor = EntityExtractor()
    vector_storer = VectorStorer(config.vector)
    
    return AtomicContentProcessor(
        content_repo=content_repo,
        normalizer=normalizer,
        embedding_generator=embedding_generator,
        entity_extractor=entity_extractor,
        vector_storer=vector_storer
    )
```

---

## Critical Gotchas & Solutions

### 1. **Embedding Model Consistency** 🔥

#### Problem
Current system has config-code mismatch (768D vs 1024D embeddings).

#### Solution
```python
# Enforce config-code consistency
class EmbeddingGenerator:
    def __init__(self, config: EmbeddingConfig):
        self.config = config
        self.model = self._load_model()
        
        # CRITICAL: Validate model matches config
        actual_dim = self.model.get_sentence_embedding_dimension()
        if actual_dim != config.dimension:
            raise ConfigurationError(
                f"Model dimension {actual_dim} doesn't match "
                f"config dimension {config.dimension}"
            )
```

### 2. **Database Migration Strategy** 🔥

#### Problem
Need to migrate 1001 existing documents (420 emails + 581 PDFs) without data loss.

#### Solution
```python
# scripts/migrate_old_data.py
class DataMigrator:
    def migrate_all(self):
        """Migrate all data with rollback capability"""
        
        # 1. Backup existing database
        self.create_backup()
        
        # 2. Migrate content table (Gmail data)
        email_results = self.migrate_content_table()
        
        # 3. Migrate content_unified table (PDF data)  
        pdf_results = self.migrate_content_unified_table()
        
        # 4. Migrate existing embeddings
        embedding_results = self.migrate_embeddings()
        
        # 5. Verify migration
        if not self.verify_migration():
            self.rollback()
            raise MigrationError("Migration verification failed")
            
        return MigrationResults(
            emails_migrated=email_results.count,
            pdfs_migrated=pdf_results.count,
            embeddings_migrated=embedding_results.count
        )
```

### 3. **Vector Store Synchronization** 🔥

#### Problem
Current system has 403 emails missing from Qdrant vector store.

#### Solution
```python
# processing/vectors.py
class VectorStorer:
    def process(self, content: Content) -> ProcessingResult:
        """Store vector with atomicity guarantees"""
        
        try:
            # 1. Generate vector ID deterministically
            vector_id = self._generate_vector_id(content.id)
            
            # 2. Store in database first
            self._store_embedding_db(content.id, embedding)
            
            # 3. Store in Qdrant second
            self._store_embedding_qdrant(vector_id, embedding, content.metadata)
            
            # 4. Verify both stores have the data
            if not self._verify_vector_stored(content.id, vector_id):
                raise VectorStoreError("Vector verification failed")
                
            return ProcessingResult(success=True, content_id=content.id)
            
        except Exception as e:
            # Cleanup on failure
            self._cleanup_partial_storage(content.id, vector_id)
            raise
```

### 4. **Fail-Fast Configuration Validation** 🔥

#### Problem
System continues running with invalid configuration.

#### Solution
```python
# Validate everything at startup
def main():
    try:
        config = SystemConfig.from_file("config.yaml")
        config.validate()  # Fail fast on invalid config
        
        # Test all external dependencies
        test_qdrant_connection(config.vector.qdrant_url)
        test_gmail_credentials(config.gmail.credentials_path)
        test_database_connection(config.database.path)
        test_embedding_model(config.embedding.model_name)
        
    except Exception as e:
        logger.error(f"❌ Startup validation failed: {e}")
        sys.exit(1)
        
    # Only proceed if everything validates
    run_pipeline(config)
```

### 5. **Memory Management for Large Batches** 🔥

#### Problem
Processing 1000+ documents can exhaust memory.

#### Solution
```python
# Use streaming processing
class BatchProcessor:
    def process_all_pending(self, batch_size: int = 50):
        """Process all pending content in manageable batches"""
        
        while True:
            # Get next batch
            batch = self.content_repo.get_pending(limit=batch_size)
            if not batch:
                break
                
            # Process batch
            for content in batch:
                try:
                    self.processor.process(content)
                except Exception as e:
                    logger.warning(f"Failed to process {content.id}: {e}")
                    
            # Explicit garbage collection
            import gc
            gc.collect()
```

---

## Testing Strategy

### Unit Tests
```python
# tests/unit/test_content_repository.py
import pytest
from uuid import uuid4
from datetime import datetime

from core.models import Content, ContentType, ProcessingState
from storage.content_repo import SQLiteContentRepository

class TestSQLiteContentRepository:
    @pytest.fixture
    def repo(self, tmp_path):
        db_path = tmp_path / "test.db"
        return SQLiteContentRepository(str(db_path))
    
    @pytest.fixture
    def sample_content(self):
        return Content(
            id=uuid4(),
            source_type=ContentType.EMAIL,
            source_id="test_message_123",
            title="Test Email",
            body="This is test content",
            content_hash="abc123",
            metadata={"sender": "test@example.com"},
            processing_state=ProcessingState.PENDING,
            created_at=datetime.now()
        )
    
    def test_save_and_get_content(self, repo, sample_content):
        # Save content
        content_id = repo.save(sample_content)
        assert content_id == sample_content.id
        
        # Retrieve content
        retrieved = repo.get(content_id)
        assert retrieved is not None
        assert retrieved.title == sample_content.title
        assert retrieved.body == sample_content.body
        
    def test_deduplication_by_hash(self, repo, sample_content):
        # Save content twice with same hash
        repo.save(sample_content)
        
        duplicate = Content(
            id=uuid4(),  # Different ID
            source_type=sample_content.source_type,
            source_id="different_id", 
            title="Different Title",
            body=sample_content.body,  # Same body
            content_hash=sample_content.content_hash,  # Same hash
            metadata={},
            processing_state=ProcessingState.PENDING,
            created_at=datetime.now()
        )
        
        existing = repo.get_by_hash(sample_content.content_hash)
        assert existing is not None
        assert existing.id == sample_content.id  # Original, not duplicate
```

### Integration Tests
```python
# tests/integration/test_full_pipeline.py
import pytest
from config.settings import SystemConfig
from cli.commands import full_run_command

class TestFullPipeline:
    @pytest.fixture
    def test_config(self, tmp_path):
        return SystemConfig(
            database=DatabaseConfig(path=str(tmp_path / "test.db")),
            embedding=EmbeddingConfig(model_name="sentence-transformers/all-MiniLM-L6-v2", dimension=384),
            vector=VectorConfig(qdrant_url="http://localhost:6333"),
            gmail=GmailConfig(credentials_path="tests/fixtures/fake_credentials.json")
        )
    
    def test_full_pipeline_integration(self, test_config, monkeypatch):
        # Mock external services
        monkeypatch.setattr("ingestion.email_service.EmailIngestionService._fetch_emails", 
                           lambda self, max_results: self._get_mock_emails())
        
        # Run full pipeline
        result = full_run_command(test_config, max_emails=5, max_pdfs=0)
        
        # Verify success
        assert result == 0
        
        # Verify content was stored and processed
        content_repo = SQLiteContentRepository(test_config.database.path)
        all_content = content_repo.search("", limit=100)
        assert len(all_content) > 0
        
        # Verify processing completed
        completed_content = [c for c in all_content if c.processing_state == ProcessingState.COMPLETED]
        assert len(completed_content) > 0
```

---

## Deployment & Operations

### Docker Setup
```dockerfile
# Dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    sqlite3 \
    tesseract-ocr \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create data directory
RUN mkdir -p data logs

# Expose CLI
ENTRYPOINT ["python", "-m", "cli.main"]
```

```yaml
# docker-compose.yml
version: '3.8'

services:
  email-sync:
    build: .
    volumes:
      - ./data:/app/data
      - ./logs:/app/logs
      - ./config.yaml:/app/config.yaml
    depends_on:
      - qdrant
    environment:
      - LOG_LEVEL=INFO
    
  qdrant:
    image: qdrant/qdrant:latest
    ports:
      - "6333:6333"
    volumes:
      - qdrant_data:/qdrant/storage
    
volumes:
  qdrant_data:
```

### Makefile Operations
```makefile
# Makefile
.PHONY: build install test lint clean setup full-run

# Development
install:
	pip install -r requirements.txt
	pip install -r requirements-dev.txt

test:
	pytest tests/ -v --cov=. --cov-report=html

lint:
	flake8 .
	black --check .
	mypy .

format:
	black .
	isort .

# Operations  
build:
	docker build -t email-sync:latest .

setup:
	python -m cli.main setup

full-run:
	python -m cli.main full-run

status:
	python -m cli.main status

# Database operations
migrate:
	python scripts/migrate_old_data.py

backup:
	cp data/emails.db data/emails.db.backup.$(shell date +%Y%m%d_%H%M%S)

# Monitoring
health-check:
	python -m cli.main status | grep -q "✅" || exit 1

clean:
	find . -type f -name "*.pyc" -delete
	find . -type d -name "__pycache__" -delete
	rm -rf .coverage htmlcov/
```

### Monitoring & Alerting
```python
# monitoring/health_check.py
from dataclasses import dataclass
from typing import List
import time

@dataclass
class HealthCheckResult:
    service: str
    status: str  # "healthy", "degraded", "failed"
    response_time_ms: int
    message: str

class SystemHealthChecker:
    def check_all(self) -> List[HealthCheckResult]:
        """Run all health checks"""
        results = []
        
        # Database health
        results.append(self._check_database())
        
        # Qdrant health
        results.append(self._check_qdrant())
        
        # Embedding model health
        results.append(self._check_embedding_model())
        
        # Gmail API health
        results.append(self._check_gmail_api())
        
        return results
    
    def _check_database(self) -> HealthCheckResult:
        start = time.time()
        try:
            with sqlite3.connect(self.config.database.path) as conn:
                conn.execute("SELECT COUNT(*) FROM content").fetchone()
            
            return HealthCheckResult(
                service="database",
                status="healthy",
                response_time_ms=int((time.time() - start) * 1000),
                message="Database accessible"
            )
        except Exception as e:
            return HealthCheckResult(
                service="database",
                status="failed", 
                response_time_ms=int((time.time() - start) * 1000),
                message=f"Database error: {e}"
            )
```

---

## Summary

This manual provides a complete rebuild strategy that addresses all the architectural issues identified in the audit:

### ✅ **Problems Solved**
1. **Unified Architecture** - Single content model, consistent patterns
2. **Configuration Consistency** - Config-driven design with validation
3. **Fail-Fast Pipeline** - Atomic processing with early error detection
4. **Single Responsibility** - Clear service boundaries with dependency injection
5. **Maintainable Codebase** - Clean architecture, comprehensive testing

### 📋 **Implementation Checklist**
- [ ] Phase 1: Foundation (Week 1)
- [ ] Phase 2: Core Services (Week 2) 
- [ ] Phase 3: Ingestion Services (Week 3)
- [ ] Phase 4: CLI & Orchestration (Week 4)
- [ ] Data Migration (Week 5)
- [ ] Testing & Validation (Week 6)
- [ ] Documentation & Deployment (Week 7)

### 🎯 **Success Criteria**
- Single command setup: `make setup`
- Single command operation: `make full-run`
- Zero configuration drift
- Fail-fast error handling
- Complete test coverage
- Production monitoring

This rebuild manual captures all lessons learned and provides a path to sustainable, clean architecture while preserving the sophisticated functionality that already works in the current system.