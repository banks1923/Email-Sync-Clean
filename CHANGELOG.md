# Changelog

> Simple, practical changelog. See [archives](docs/changelog-archives/) for historical entries before August 2025.

## Recent Changes

### [2025-09-04] - Complete Technical Debt Elimination

#### Removed
- **BREAKING**: EmailStorage class completely deleted (was using direct sqlite3)
- **BREAKING**: SearchIntelligenceService class completely deleted
- All compatibility shims and deprecated functions removed from search_intelligence
- Service registry pattern removed as unused complexity

#### Changed
- **BREAKING**: All services now use direct function APIs (no service classes)
- GmailService refactored with inline database methods (no storage wrapper)
- Service locator returns dict of functions instead of service objects
- EnhancedPDFStorage refactored to use SimpleDB instead of direct sqlite3

#### Fixed
- All remaining direct sqlite3 usage eliminated from core services
- Import errors from deleted classes cleaned up
- Pre-commit hook prevents any new sqlite3.connect() usage

### [2025-09-04] - Database Consolidation & Substantive Text Support

#### Added
- Boilerplate stripping functionality in `shared/boilerplate_stripper.py`
- `substantive_text` column now populated with cleaned content for better embeddings
- Exact duplicate detection via SHA256 hashing of substantive text
- Pre-commit hook to prevent direct `sqlite3.connect()` usage outside SimpleDB

#### Changed
- **BREAKING**: All database access now routes through SimpleDB
- ~~EmailStorage refactored to delegate to SimpleDB (marked deprecated)~~ NOW DELETED
- Search results now prefer `substantive_text` over `body` field when available
- Embeddings pipeline updated to use `substantive_text` for better quality vectors

#### Fixed
- Consolidated scattered sqlite3 usage across quarantine_handler, vector_parity_check
- Removed 15+ direct database connections in ~~EmailStorage~~ gmail/main.py

### [2025-09-04] - Semantic-Only Search Refactor

#### Changed
- **BREAKING**: Removed all keyword/hybrid search - now pure semantic search only
- Simplified to 2-function API: `search()` for semantic, `find_literal()` for exact patterns
- Locked to vectors_v2 collection with Legal BERT 1024D embeddings

#### Removed
- SearchIntelligenceService complexity (deprecated with compatibility shims)
- Query expansion and synonym logic (irrelevant for embeddings)
- Environment variables: ENABLE_DYNAMIC_WEIGHTS, ENABLE_CHUNK_AGGREGATION

### [2025-09-04] - Test Factories for MCP Servers

#### Added
- Small patchable factories for tests: `get_search_intelligence_service()`, `get_legal_intelligence_service()`
- OCR optional via `OCR_DISABLED=true` environment variable

#### Changed
- `search_smart` always computes query expansion but only displays when `use_expansion=True`

### [2025-09-03] - Summarization Service Fix

#### Fixed
- Missing summaries for 420 emails - root cause was SimpleUploadProcessor
- Database foreign key constraints for proper referential integrity

#### Added
- `scripts/backfill_summaries.py` for batch processing historical data

### [2025-08-26] - Foreign Keys Enforced

#### Changed
- Enabled foreign key constraints for email messages in content_unified
- Email summaries exempt from FK constraints (source_type='email_summary')
- CASCADE DELETE enabled for automatic cleanup

### [2025-08-25] - Email Deduplication v2.0

#### Added
- Message-level deduplication reducing content by 70-80%
- Advanced boundary detection for parsing individual messages from threads
- Complete audit trail tracking where each message appears

#### Changed
- 302 emails processed with significant duplicate reduction

### [2025-08-23] - Configuration Alignment

#### Fixed
- Database path issues - all services now use `data/system_data/emails.db`
- 35+ files updated to use centralized Pydantic settings

#### Removed
- Legacy pipeline folders (raw/, staged/, processed/)

### [2025-08-22] - Entity Extraction System

#### Added
- Unified entity extraction across all content types
- Entity-based search and cross-document attribution

#### Changed
- 719 entities extracted with 95.3% quality after OCR garbage filtering

### [2025-08-22] - Code Quality Improvements

#### Fixed
- Type safety: 47% reduction in MyPy errors
- Complexity: 95% reduction in vsearch main() function

#### Changed
- All dependencies updated to latest stable versions
- Zero breaking changes during cleanup

## Quick Reference

### Search System
```bash
tools/scripts/vsearch search "query"        # Semantic search
tools/scripts/vsearch find-literal "BATES"  # Exact pattern match
```

### Entity Extraction
```bash
tools/scripts/vsearch extract-entities --missing-only
tools/scripts/vsearch entity-status
```

### Database
- Location: `data/system_data/emails.db`
- Schema: content_unified (main), individual_messages (dedupe), message_occurrences (audit)
- Foreign keys enforced for email_message type only

### MCP Servers
- Legal Intelligence: 6 tools for legal analysis
- Search Intelligence: 6 tools for search operations
- Both have patchable factories for testing

---

For older entries, see [archives](docs/changelog-archives/CHANGELOG-2025-pre-august.md)