# Product Requirements Document: Import Ergonomics & Core Improvements

## Executive Summary

Refactor the Litigator Solo codebase to improve developer ergonomics, search capabilities, and data integrity while maintaining the project's core philosophy of simplicity and pragmatism. This refactor focuses on high-impact, low-complexity improvements that directly benefit the single-user legal research use case.

## Problem Statement

### Current Pain Points
1. **Import Verbosity**: Deep 3-4 level imports make code unnecessarily verbose
   - Example: `from infrastructure.documents.chunker.document_chunker import DocumentChunker`
   - Slows development and reduces readability

2. **Missing Metadata Tracking**: Database lacks critical fields for reproducibility
   - No tracking of embedding models used
   - No pipeline version tracking
   - No content hashing for deduplication

3. **Suboptimal Search**: Separate keyword and semantic search without fusion
   - No FTS5 implementation despite SQLite support
   - No reciprocal rank fusion (RRF) for hybrid search
   - Missing query logging for improvement analysis

4. **Timeline Limitations**: Incomplete UTC normalization and source linking
   - Missing raw timestamp preservation
   - No quote extraction for context
   - Limited filtering capabilities

## Goals & Non-Goals

### Goals
- **Simplify imports** to maximum 2 levels via public API re-exports
- **Add metadata fields** for pipeline reproducibility (emb_model, pipeline_rev)
- **Implement hybrid search** with FTS5 + embeddings using RRF
- **Enhance timeline** with proper UTC handling and source references
- **Add safety nets** via import validation and smoke tests

### Non-Goals
- NO enterprise features (Bates numbering, legal holds, content-addressed storage)
- NO complex migrations (dual-write, zero-downtime)
- NO breaking API changes
- NO over-abstraction or pattern complexity
- NO features for multi-user scenarios

## Technical Requirements

### 1. Import Ergonomics
**Requirement**: All public APIs accessible via 2-level imports maximum

**Implementation**:
- Add `__all__` exports to package `__init__.py` files
- Configure import-linter to enforce rules
- Create validation script for CI/pre-commit

**Success Criteria**:
- `from lib import SimpleDB` instead of `from lib.db import SimpleDB`
- `from services import PDFService` instead of `from services.pdf.wiring import get_pdf_service`
- Zero deep import violations in codebase

### 2. Database Schema Enhancement
**Requirement**: Track processing metadata without complexity

**New Fields for content_unified**:
```sql
sha256 TEXT UNIQUE           -- Content hash for deduplication
emb_model TEXT               -- Embedding model identifier
pipeline_rev TEXT            -- Git commit or version
ocr_engine TEXT              -- OCR engine if used
validation_status TEXT       -- Content validation state
quality_score REAL           -- Content quality metric
metadata TEXT                -- JSON metadata
embedding_generated INTEGER  -- Flag for embedding status
```

**Success Criteria**:
- All new content includes metadata fields
- Existing content migrated with defaults
- No performance degradation

### 3. Hybrid Search Implementation
**Requirement**: Combine keyword and semantic search effectively

**Components**:
- SQLite FTS5 virtual table for full-text search
- Reciprocal Rank Fusion (RRF) algorithm
- Per-source top-k limiting
- Query logging for analysis

**Algorithm**:
```python
def reciprocal_rank_fusion(keyword_results, semantic_results, k=60):
    """
    RRF formula: score = Σ(1 / (k + rank))
    where k=60 is the standard constant
    """
    scores = {}
    for rank, doc in enumerate(keyword_results, 1):
        scores[doc.id] = scores.get(doc.id, 0) + 1/(k + rank)
    for rank, doc in enumerate(semantic_results, 1):
        scores[doc.id] = scores.get(doc.id, 0) + 1/(k + rank)
    return sorted(scores.items(), key=lambda x: x[1], reverse=True)
```

**Success Criteria**:
- Search latency < 500ms for typical queries
- Improved relevance vs pure semantic search
- FTS5 index stays synchronized with content

### 4. Timeline Enhancement
**Requirement**: Proper temporal tracking for litigation

**Schema Updates**:
```sql
occurred_at_utc DATETIME  -- Normalized UTC timestamp
occurred_at_raw TEXT      -- Original string representation
tz TEXT                   -- Timezone identifier
source_ref TEXT           -- Link to source document/email
quote TEXT                -- Relevant text excerpt
```

**Success Criteria**:
- All timestamps dual-stored (UTC + raw)
- Timeline UI with party/source filters
- iCal export functionality

### 5. Quality Assurance
**Requirement**: Prevent regressions without overhead

**Components**:
- Import validation script (fail on deep imports)
- 5-10 E2E smoke tests
- Backup/restore automation
- Basic observability (structured logs, counters)

**Smoke Tests**:
1. Email ingestion → parsing → searchable
2. PDF upload → OCR → chunks → searchable
3. Hybrid search returns expected results
4. Timeline events properly ordered
5. All public API imports resolve

## Implementation Plan

### Phase 1: Foundation (Day 1)
1. Create import re-exports in `__init__.py` files
2. Add import-linter configuration
3. Create validation script
4. Update pyproject.toml with rules

### Phase 2: Database (Day 1-2)
1. Create migration script for metadata fields
2. Update Makefile with db.migrate command
3. Add db.verify for schema validation
4. Test backup/restore cycle

### Phase 3: Search (Day 2-3)
1. Create FTS5 migration and indexes
2. Implement RRF fusion algorithm
3. Update search module with hybrid option
4. Add query logging

### Phase 4: Timeline (Day 3)
1. Enhance timeline_events schema
2. Create timeline UI component
3. Add filtering capabilities
4. Implement iCal export

### Phase 5: Safety (Day 3-4)
1. Write E2E smoke tests
2. Set up CI integration
3. Document in CHANGELOG.md
4. Create rollback procedures

## Technical Specifications

### Import Rules (import-linter)
```ini
[importlinter]
root_package = .
include_external_packages = False

[contract:1]
name = No deep imports
type = forbidden
source_modules = 
    services
    lib
    infrastructure
forbidden_modules =
    *.*.* 
```

### Migration Strategy
```bash
# Safe migration pattern
make db.backup
python3 lib/migrations/migrate.py --dry-run
python3 lib/migrations/migrate.py
make db.verify
```

### FTS5 Configuration
```sql
-- Optimized for legal text
CREATE VIRTUAL TABLE content_unified_fts USING fts5(
    content_id UNINDEXED,
    title,
    body,
    substantive_text,
    tokenize = 'porter unicode61',
    content = 'content_unified',
    content_rowid = 'id'
);
```

## Testing Strategy

### Unit Tests
- Import validation: All re-exports resolve
- RRF algorithm: Correct score calculation
- Migration: Schema changes applied correctly

### Integration Tests
- Search: Keyword + semantic fusion works
- Timeline: UTC conversion accurate
- Database: Constraints enforced

### E2E Smoke Tests
- Complete workflows from ingest to search
- Performance benchmarks met
- No regressions in existing features

## Risk Mitigation

### Risks & Mitigations
1. **Migration failure**: Atomic transactions, pre-migration backup
2. **Import breaking**: Maintain old paths during transition
3. **Search degradation**: A/B test results, keep pure semantic option
4. **FTS5 sync issues**: Triggers to maintain consistency

### Rollback Plan
```bash
# Complete rollback procedure
make db.restore
git checkout HEAD~1
make clean
make install
```

## Success Metrics

### Quantitative
- Import depth: 100% ≤ 2 levels
- Search latency: < 500ms p95
- Test coverage: > 80% for new code
- Migration success: Zero data loss
- Smoke tests: 100% pass rate

### Qualitative
- Developer experience improved (fewer keystrokes)
- Search results more relevant
- Timeline more useful for case analysis
- System more maintainable

## Dependencies

### Required Libraries
- `import-linter`: Import rule enforcement
- `libcst`: AST manipulation (already used)
- SQLite 3.32+: FTS5 support (already available)

### Existing Systems
- Qdrant: Vector store (no changes)
- Legal BERT: Embeddings (no changes)
- Gmail sync: No changes required

## Constraints

### Technical Constraints
- Single-user architecture (no concurrency concerns)
- SQLite database (no PostgreSQL features)
- Python 3.11+ requirement

### Resource Constraints
- 4-day implementation window
- Single developer
- Maintain existing functionality

## Documentation Requirements

### Updates Required
- CHANGELOG.md: All changes documented
- README.md: New import patterns
- CLAUDE.md: Updated best practices
- Migration guide for existing data

## Approval & Sign-off

This PRD follows the core principles:
- **Build it right, build it once**: No technical debt
- **Simple > Complex**: No enterprise patterns
- **Working code > Perfect abstractions**: Pragmatic solutions
- **Direct solutions > Clever patterns**: Straightforward implementation

## Appendix: Code Examples

### Before: Deep Imports
```python
from infrastructure.documents.chunker.document_chunker import DocumentChunker
from services.gmail.deduplication.near_duplicate_detector import NearDuplicateDetector
from lib.db import SimpleDB
```

### After: Clean Imports
```python
from infrastructure import DocumentChunker
from services.gmail import NearDuplicateDetector
from lib import SimpleDB
```

### Hybrid Search Usage
```python
from lib import hybrid_search

results = hybrid_search(
    query="motion for summary judgment deadline",
    limit=20,
    mode="rrf"  # or "keyword_only", "semantic_only"
)
```

---

*This PRD represents a pragmatic, high-impact refactor that respects the project's philosophy while delivering meaningful improvements to developer experience and system capabilities.*