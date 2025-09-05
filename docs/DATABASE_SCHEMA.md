# Database Schema Documentation

## Core Architecture: Message-Level Deduplication (v2.0)

The system implements advanced message-level email deduplication with TEXT source_ids and full schema compatibility.

## Current Production Status (2025-08-25)

- **Email deduplication**: Significant reduction in duplicate content from email threads
- **Gmail sync**: Fully operational with v2.0 schema
- **Test Coverage**: 97%+ on email_parsing module, comprehensive test suite
- **Schema compatibility**: All tables compatible, semantic pipeline working

## Primary Tables

### `content_unified` - Single Source of Truth

| Column | Type | Description |
|--------|------|-------------|
| `id` | INTEGER PRIMARY KEY | Auto-generated ID |
| `source_type` | TEXT | Type: 'email_message', 'email_summary', 'document', 'document_chunk' |
| `source_id` | TEXT | TEXT-based IDs (message_hash for emails, doc_uuid for documents) |
| `title` | TEXT | Document title or email subject |
| `body` | TEXT | Full text content |
| `sha256` | TEXT UNIQUE | Content hash for deduplication |
| `ready_for_embedding` | BOOLEAN | Flag for embedding pipeline |
| `validation_status` | TEXT | 'pending', 'validated', 'failed' |
| `quality_score` | REAL | Quality metric for content |
| `metadata` | TEXT | JSON metadata |

**Notes:**
- Added 'email_summary' type for summaries without FK constraints (2025-08-26)
- Foreign Key: Conditional - only enforced for `source_type='email_message'` via triggers

### `individual_messages` - Unique Email Messages

| Column | Type | Description |
|--------|------|-------------|
| `message_hash` | TEXT PRIMARY KEY | SHA256 of normalized content |
| `content` | TEXT | Full message text |
| `subject` | TEXT | Message subject line |
| `sender_email` | TEXT | Sender's email address |
| `recipients` | TEXT | JSON array of recipients |
| `date_sent` | TIMESTAMP | When message was sent |
| `message_id` | TEXT UNIQUE | Email Message-ID header |
| `thread_id` | TEXT | Thread identifier for reconstruction |
| `content_type` | TEXT | 'original', 'reply', 'forward' |

### `message_occurrences` - Audit Trail

| Column | Type | Description |
|--------|------|-------------|
| `id` | INTEGER PRIMARY KEY | Auto-generated ID |
| `message_hash` | TEXT | Links to individual_messages |
| `email_id` | TEXT | Original email file where seen |
| `position_in_email` | INTEGER | Order within the email |
| `context_type` | TEXT | 'original', 'quoted', 'forwarded' |
| `quote_depth` | INTEGER | Number of > markers |

### `document_summaries` - Document Summaries

| Column | Type | Description |
|--------|------|-------------|
| `id` | INTEGER PRIMARY KEY | Auto-generated ID |
| `document_id` | TEXT | Foreign key to documents |
| `summary_type` | TEXT | Type of summary |
| `summary` | TEXT | Summary text |
| `metadata` | TEXT | JSON metadata |
| `created_at` | TIMESTAMP | Creation timestamp |
| `updated_at` | TIMESTAMP | Last update timestamp |

### `entities` - Extracted Entities

| Column | Type | Description |
|--------|------|-------------|
| `id` | INTEGER PRIMARY KEY | Auto-generated ID |
| `source_id` | INTEGER | Foreign key to content |
| `entity_type` | TEXT | PERSON, ORG, DATE, COURT, etc. |
| `entity_value` | TEXT | Extracted entity text |
| `confidence` | REAL | Extraction confidence score |
| `context` | TEXT | Surrounding context |
| `metadata` | TEXT | JSON metadata |

## SQLite Optimizations (2025-08-19, Updated 2025-08-26)

- **WAL mode** enabled for better concurrency
- **64MB cache** for batch operations
- **NORMAL synchronous mode** (safe for single-user)
- **5-second busy timeout** for resilience
- **Slow-query logging** (>100ms)
- **`db_maintenance()`** method for WAL checkpointing after large batches
- **Foreign Keys ENFORCED** (2025-08-26): Referential integrity active via triggers
  - Only applies to `source_type='email_message'` records
  - Email summaries (`source_type='email_summary'`) exempt from FK constraints
  - CASCADE DELETE enabled for automatic cleanup
  - Migration tool: `scripts/enable_foreign_keys_comprehensive.py`

## Email Processing Pipeline (v2.0 - 2025-08-25)

- **Message-Level Deduplication**: Parse individual messages from threads, hash each uniquely
- **TEXT Source IDs**: Flexible string-based IDs replace INTEGER constraints
- **Advanced Parsing**: Boundary detection for forwards, replies, nested quotes
- **Legal Integrity**: Foreign key constraints with CASCADE for evidence preservation
- **Audit Trail**: Complete tracking of where each message appears across emails
- **70-80% Content Reduction**: Eliminates duplicate quoted/forwarded content

## Migration Tools

- `scripts/parse_messages.py` - Batch processor for email parsing
- `scripts/parse_all_emails.py` - Parser for all_emails.txt format
- `scripts/backup_database.py` - Backup/restore with integrity checks
- `email_parsing/message_deduplicator.py` - Advanced parsing service (97% coverage)

## Test Coverage

- `tests/test_email_parser.py` - Unit tests (16 tests)
- `tests/test_email_integration.py` - Integration tests (4 tests)
- `tests/test_email_coverage.py` - Edge case tests (18 tests)

## Semantic Pipeline (Restored 2025-08-25)

- `utilities/semantic_pipeline.py` - Complete orchestration system (443 lines)
- `infrastructure/pipelines/service_orchestrator.py` - Pipeline coordination
- `scripts/backfill_semantic.py` - Batch semantic processing
- `scripts/setup_semantic_schema.py` - Schema setup utility
- `scripts/test_semantic_pipeline.py` - Testing framework
- `scripts/verify_semantic_wiring.py` - Verification tools
- `tests/test_semantic_pipeline_comprehensive.py` - Full test suite

## Schema Verification Commands

```bash
# View all tables
sqlite3 data/system_data/emails.db ".tables"

# Check content_unified structure
sqlite3 data/system_data/emails.db ".schema content_unified"

# Verify foreign key status
sqlite3 data/system_data/emails.db "PRAGMA foreign_keys;"

# Count records by type
sqlite3 data/system_data/emails.db "
SELECT source_type, COUNT(*) as count 
FROM content_unified 
GROUP BY source_type;"

# Check for duplicates
sqlite3 data/system_data/emails.db "
SELECT sha256, COUNT(*) as count 
FROM content_unified 
GROUP BY sha256 
HAVING count > 1;"
```