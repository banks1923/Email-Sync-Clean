# Changelog

> Simple, practical changelog. See [archives](docs/changelog-archives/) for historical entries before August 2025.

## Recent Changes

### [2025-09-04] - Improved Error Handling with Custom Exceptions

#### Added
- **Custom Exception Classes**: Created `shared/db/exceptions.py` with proper exception hierarchy
  - `TestDataBlockedException` for blocked test data
  - `ContentValidationError` for validation failures
  - `DuplicateContentError` for duplicate detection (if strict mode)

#### Changed
- **Error Handling Best Practices**: Guardrails now raise exceptions instead of returning "-1"
  - Test data blocking raises `TestDataBlockedException` with context
  - Proper exception propagation for better error handling upstream
  - Maintains structured logging with warnings and debug info

#### Technical Details
- Exceptions carry context (title, content_type) for better debugging
- Compatible with existing try-catch blocks in calling code
- Follows Python best practices: exceptions for errors, not return codes

### [2025-09-04] - Email Chunking Bug Fix & HTML Email Cleanup

#### Fixed
- **Email-to-Document Pipeline Crossover**: Fixed critical bug where emails were being chunked as documents
  - Root cause: `test_chunk_pipeline.py` incorrectly used `source_types=["email_message"]`
  - 148 bogus document chunks created from HTML emails (all cleaned)
  - Added multiple guardrails to prevent recurrence

#### Changed
- **ChunkPipeline defaults**: Changed from `["email_message"]` to `["document"]`
- **Pipeline guardrails**: Added explicit blocking of email_message and email_summary types
- **SQL constraints**: Query now excludes email types with `NOT IN` clause
- **Import fix**: Fixed `shared/ingestion/simple_file_processor.py` import path

#### Removed
- **144 HTML emails**: Cleaned all HTML-formatted emails from database
- **148 document chunks**: Removed all incorrectly chunked email data
- **Data cleanup**: Both content_unified and individual_messages tables cleaned

#### Technical Details
- Guardrails prevent emails from entering document chunking pipeline
- Warning logs if email_message type is attempted in chunk pipeline
- Database now clean: 276 plain text emails, 0 HTML emails, 0 chunks
- Killed lingering vsearch chunk-ingest process using old code

### [2025-09-04] - PDF Upload Service Restoration

#### Fixed
- **PDF Upload Processing**: Fixed broken import in `shared/ingestion/simple_upload_processor.py`
  - Changed `from .simple_db import SimpleDB` to `from shared.db.simple_db import SimpleDB`
  - Removed broken PDFService instantiation fallback (missing required constructor arguments)
- **Entity Processing**: Fixed broken import in `shared/processors/unified_entity_processor.py`
  - Changed `from .simple_db import SimpleDB` to `from shared.db.simple_db import SimpleDB`
- **PDF Extraction Flow**: Simplified PDF processing to work optimally with external OCR workflow
  - Primary: OCR extraction via `pdf.wiring.build_pdf_service()` (for complex/image PDFs)
  - Fallback: PyPDF2 direct text extraction (for searchable PDFs from external OCR)
  - Compatible with user's external PDF OCR processing pipeline

#### Technical Details
- SimpleUploadProcessor now instantiates correctly and processes all file types
- PDF service builds successfully with all components (ContentQualityScorer found)
- External OCR workflow supported: searchable PDFs → PyPDF2 extraction → database storage
- Maintains internal OCR capabilities as fallback for complex processing needs

### [2025-09-04] - Documentation Reality Alignment

#### Fixed
- **Documentation-Reality Drift**: Aligned all documentation with actual codebase
- Removed fictional service references from CLAUDE.md and SERVICES_API.md
- Fixed audit.py to stop looking for non-existent services (knowledge_graph, notes, legal_intelligence)
- Fixed preflight.py imports for non-existent KnowledgeGraphService
- Updated entity extraction docs to use actual EntityService methods

#### Changed
- **KNOWLEDGE_GRAPH.md**: Marked as "NOT IMPLEMENTED" with clear status
- **Service counts**: Updated CLAUDE.md totals to reflect legal_intelligence removal
- **Test paths**: Removed references to non-existent test files in audit.py

### [2025-09-04] - Fixed Embedding Generation Script

#### Fixed
- Replaced deprecated shim in `scripts/data/generate_embeddings.py` with functional implementation
- Script now properly uses `BatchEmbeddingProcessor` from v2 pipeline infrastructure
- Integrates with Legal BERT embeddings and Qdrant vectors_v2 collection

#### Added
- `--stats` flag to show embedding statistics (chunks needing embeddings)
- `--dry-run` mode for testing without storing embeddings
- `--batch-size` and `--min-quality` configuration options
- Comprehensive help with usage examples

#### Technical Details
- Works with `content_unified` table for document chunks
- Processes 148 chunks ready for embedding (quality scores: 0.561-0.925)
- Follows project philosophy: uses existing services directly, no unnecessary abstractions

### [2025-09-04] - Legal Intelligence Service Removal

#### Removed
- **BREAKING**: Removed `legal_intelligence/` directory entirely (837 lines)
- Eliminated unnecessary orchestration layer that violated project philosophy

#### Changed  
- Refactored MCP server (`legal_intelligence_mcp.py`) to use services directly
- Refactored CLI handler (`legal_handler.py`) to call services directly
- Both now import: `EntityService`, `SimpleDB`, `TimelineService` directly
- Moved useful logic (legal doc patterns, case processing) into consumers

#### Fixed
- Missing `extract_legal_entities()` method that was causing MCP server failures
- Database path alignment: changed from `data/emails.db` to `data/system_data/emails.db`

### [2025-09-04] - Legal CLI Handler Refactor

#### Changed  
- **BREAKING**: Refactored `legal_handler.py` to remove dependency on `legal_intelligence` service
- Now uses underlying services directly: `EntityService`, `SimpleDB`, `TimelineService`, `get_document_summarizer`
- All CLI functions (`process_legal_case`, `generate_legal_timeline`, etc.) maintain same interface
- Moved legal intelligence logic directly into CLI helper functions

#### Technical Details
- Eliminated intermediate service layer for cleaner, more direct implementation
- All 6 CLI commands working unchanged with same output format
- Helper functions (`_get_case_documents`, `_extract_case_entities`, etc.) implemented as module-level functions
- Simplified document similarity calculation using Jaccard similarity
- Follows project philosophy of "Simple > Complex" and "Direct > Indirect"

### [2025-09-04] - Legal Intelligence MCP Refactor

#### Changed  
- **BREAKING**: Refactored `legal_intelligence_mcp.py` to remove dependency on `legal_intelligence` service
- Now uses underlying services directly: `EntityService`, `SimpleDB`, `TimelineService`
- Moved all legal document patterns and logic directly into MCP handlers
- Preserved patchable factory pattern for tests compatibility

#### Technical Details
- Eliminated intermediate service layer for better maintainability
- All 6 MCP tool functions (`legal_extract_entities`, `legal_timeline_events`, etc.) working unchanged
- Maintained same output format and functionality
- Helper functions (`_get_case_documents`, `_identify_document_types`, etc.) moved directly into MCP file

### [2025-09-04] - Chunking System Migration & Cleanup

#### Changed
- Document chunker moved from `src/chunker/` to `infrastructure/documents/chunker/`
- Quality scorer moved from `src/quality/` to `infrastructure/documents/quality/`
- All imports updated using LibCST automated refactoring (7 files)
- Removed sys.path manipulation hacks from quality_score.py

#### Removed
- Deleted non-standard `src/` directory (now empty)
- Removed unused `email_thread_processor` import from documents module

#### Technical Details
- Used LibCST codemod for safe automated import updates
- Preserved circular dependency between chunker and quality modules (working code)
- All tests pass after migration

### [2025-09-04] -  Technical Debt Elimination

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