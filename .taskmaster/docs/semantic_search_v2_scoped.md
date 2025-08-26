# Semantic Search v2 Enhancement - SCOPED TO EXISTING PROJECT

## PROJECT BASELINE - CURRENT STATE (2025-08-26)

**EXISTING WORKING SYSTEM:**
- **Gmail Sync**: Working with v2.0 message-level deduplication  
- **Email Processing**: Working - 663 items ready for embedding, 23 already embedded
- **Search System**: Working - Keyword search via tools/scripts/vsearch
- **Vector Store**: Working - Qdrant connected, utilities/vector_store/ service active
- **Schema**: Working - content_unified table with embedding_generated columns
- **Infrastructure**: Working - utilities/embeddings/, search_intelligence/, shared/simple_db.py

**EXISTING ARCHITECTURE PATTERNS:**
- **Database**: SQLite + SimpleDB (no ORM, no Alembic)
- **Configuration**: config/settings.py with Pydantic
- **Logging**: loguru (shared/loguru_config.py)
- **CLI Tools**: tools/scripts/vsearch for all operations
- **Testing**: tests/ directory, Make commands, pytest
- **Services**: Flat architecture - gmail/, pdf/, search_intelligence/, etc.

## ENHANCEMENT GOALS - v2 PIPELINE

**ADD TO EXISTING SYSTEM:**
1. **Token-based chunking** for better content segmentation
2. **Quality scoring** to filter low-value chunks  
3. **Document-level retrieval** with RRF aggregation
4. **Feature flags** to toggle between v1/v2 search
5. **Batch migration** tools for historical content

**INTEGRATION REQUIREMENTS:**
- Use existing utilities/embeddings/ service (no new embedding endpoints)
- Enhance existing search_intelligence/ (no new FastAPI modules)
- Work with existing SimpleDB patterns (no SQLAlchemy/Alembic)
- Follow existing CLI patterns (extend tools/scripts/vsearch)
- Use existing test infrastructure (tests/ directory)

## TECHNICAL IMPLEMENTATION

### 1. Document Chunking Enhancement
**Goal**: Replace simple splitting with token-aware chunking
**Integration**: New chunker/ module, integrated via utilities/semantic_pipeline.py
**Dependencies**: tiktoken, spacy (add to existing requirements)

### 2. Quality Scoring System  
**Goal**: Filter chunks below quality threshold (≥0.35)
**Integration**: New quality/ module, used in chunking pipeline
**Dependencies**: scipy, numpy (already available)

### 3. Schema Evolution
**Goal**: Support chunk-level embeddings if needed
**Integration**: Extend SimpleDB with content_embeddings table if required
**Method**: Direct SQL operations, no migrations framework

### 4. Pipeline Integration
**Goal**: Wire chunker → quality → embeddings → vectors
**Integration**: Extend existing utilities/semantic_pipeline.py
**Storage**: Use existing Qdrant via utilities/vector_store/, new vectors_v2 collection

### 5. Enhanced Retrieval
**Goal**: Document-level RRF with chunk aggregation  
**Integration**: Enhance existing search_intelligence/main.py
**Interface**: Extend tools/scripts/vsearch with new flags

### 6. Feature Flags
**Goal**: Toggle between v1/v2 pipelines safely
**Integration**: Extend config/settings.py, add CLI flags to vsearch
**Storage**: Simple environment variables + JSON config

### 7. Migration Tools
**Goal**: Batch process 663 ready items into v2 pipeline
**Integration**: New scripts/batch_reembed.py following existing patterns
**Monitoring**: loguru logging, progress tracking

### 8. Quality Monitoring
**Goal**: Compare v1 vs v2 search quality
**Integration**: tests/evaluation/ directory, Make commands
**Interface**: CLI-based evaluation, CSV/Markdown reports

### 9. Deployment Readiness
**Goal**: Safe cutover procedures for single-user system
**Integration**: Simple monitoring scripts, feature flag toggles
**Method**: Manual testing procedures, backup/rollback scripts

## SUCCESS CRITERIA

**Technical Metrics:**
- Process 663 ready items through v2 pipeline
- p95 search latency < 200ms  
- Quality score filtering removes low-value content
- RRF improves search relevance vs v1

**Integration Requirements:**
- All existing functionality continues working
- Feature flags allow instant rollback to v1
- New components use existing service patterns
- CLI tools remain primary interface