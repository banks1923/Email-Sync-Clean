# Pipeline Verification System

Complete guide to the Email Sync pipeline verification and testing infrastructure.

## Overview

The Email Sync system includes comprehensive verification for end-to-end pipeline validation through `scripts/verify_pipeline.py`.

## Test Suite Components

### 1. Preflight Test - Environment & Schema Validation
- ✅ Database schema version and required tables
- ✅ Required columns in documents table (`sha256`, `char_count`, etc.)
- ✅ Qdrant vector database connectivity
- ✅ Missing dependency detection
- ✅ **Vector Parity Check**: Database vs Qdrant sync validation with delta thresholds

### 2. Smoke Test - End-to-End Chain Verification
- ✅ Complete chain: documents → content_unified → embeddings
- ✅ Exact SQL joins with deterministic ordering
- ✅ Real document processing verification
- ✅ **Multi-chunk document analysis**: Chunk count, total characters, chunk distribution
- ✅ **Document vs Chunk metrics**: Distinguishes unique documents from document chunks

### 3. Integrity Test - Data Consistency Validation
- ✅ Orphaned content detection (content without documents)
- ✅ Orphaned embeddings detection (embeddings without content)
- ✅ Processed documents without content normalization
- ✅ Duplicate content detection per source
- ✅ Quarantine statistics and retry analysis

### 4. Performance Test - Processing Metrics Analysis
- ✅ Document processing rates and character counts
- ✅ Embedding generation statistics
- ✅ Time window filtering (`--since 30m`, `--since 24h`, `--since 7d`)

### 5. Quarantine Test - Recovery System Validation
- ✅ Failed document analysis and retry logic
- ✅ Permanent failure detection (3+ attempts)
- ✅ Recovery handler availability

### 6. Document Tracing - Full Pipeline Inspection
- ✅ **Enhanced chunk hierarchy display**: Shows all chunks per document with tree structure
- ✅ **SHA256 prefix resolution**: Handles multi-chunk documents with DISTINCT resolution
- ✅ **Complete document lifecycle tracing**: From chunks → content_unified → embeddings
- ✅ **Content mapping clarification**: Explains content_unified represents full document text
- ✅ **All embeddings returned**: Not just first match, with model and timestamp info

## Exit Codes for CI Integration

- `0`: All tests passed
- `1`: Tests failed (or warnings with `--strict`)
- `2`: Configuration error
- `3`: Schema/environment mismatch
- `4`: Transient error (retry possible)

## Usage Examples

```bash
# Complete pipeline health check
python3 scripts/verify_pipeline.py

# CI integration with JSON output
python3 scripts/verify_pipeline.py --json --strict

# Performance analysis with time windows
python3 scripts/verify_pipeline.py --since 24h

# Trace specific document through pipeline
python3 scripts/verify_pipeline.py --trace ec69f22c
```

## JSON Mode for Automation

```bash
# Silent operation for CI pipelines
python3 scripts/verify_pipeline.py --json

# Example output:
{"status":"WARN","chain":false,"orphans":1,"dup_content":0,"docs_24h":12,"emb_24h":12}
```

## Document Processing Verification

The verification system confirms support for:
- ✅ **Text-based PDFs**: Fast PyPDF2 extraction
- ✅ **Scanned PDFs**: Tesseract OCR with automatic detection  
- ✅ **Legal Documents**: Court filings, contracts, judgments
- ✅ **Mixed Content**: Automatic text vs OCR detection
- ✅ **Multi-chunk Documents**: Large documents split into chunks with proper indexing
- ✅ **Pipeline Stages**: Raw → Staged → Processing → Storage → Embeddings

## Multi-Chunk Document Architecture

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

## Vector Parity Check System

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