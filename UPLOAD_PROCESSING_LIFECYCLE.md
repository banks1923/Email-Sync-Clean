# Upload Processing Lifecycle & File Management

## Overview

This document explains how uploaded files are processed through the Email Sync system, from initial upload to final storage and export.

## Upload Processing Workflow

### 1. File Upload Entry Points

#### CLI Upload Command
```bash
tools/scripts/vsearch upload document.pdf
```
- Uses `tools/scripts/cli/upload_handler.py`
- Calls `DataPipelineOrchestrator.add_to_raw()` with `copy=True`
- Original file remains in place, copy moves to `data/raw/`

#### Directory Upload
```bash
tools/scripts/vsearch upload /path/to/documents --limit 50
```
- Batch processes multiple files
- Each file copied to `data/raw/` with timestamp suffix if duplicate names

### 2. Pipeline Stages & Directory Structure

```
data/
├── raw/           # Initial upload landing (temporary)
├── staged/        # Validated and ready for processing
├── processed/     # Successfully processed with metadata
├── quarantine/    # Failed processing (manual review needed)
└── export/        # Prepared for external systems
```

### 3. File Lifecycle Flow

```
[Upload] → raw/ → [Validation] → staged/ → [Processing] → processed/
                       ↓                         ↓
                   quarantine/              [Export] → export/
                   (on error)
```

## Processing Pipeline Details

### Stage 1: Raw Ingestion (`data/raw/`)

**Purpose**: Initial file landing zone
- Files copied from user locations (originals preserved)
- Filename collision handling with timestamps
- No processing occurs at this stage
- Files wait for pipeline processing

**File Naming**: 
- Preserves original filename
- Adds timestamp suffix for duplicates: `document_20250821_150034.pdf`

### Stage 2: Validation & Staging (`data/staged/`)

**Purpose**: Validated files ready for processing
- File format validation
- Basic security checks
- Metadata extraction preparation
- Queue for content processing

**Processing Triggers**:
```bash
# Process staged files
tools/scripts/vsearch process-uploads
```

### Stage 3: Content Processing (`data/processed/`)

**Purpose**: Extracted content with intelligence
- Text extraction (OCR for scanned PDFs)
- HTML cleaning for emails
- Chunk management for large documents
- Metadata generation with `.meta.json` files

**Database Storage**:
- Content stored in `content_unified` table
- Embeddings generated and stored in Qdrant
- Document intelligence extracted (entities, summaries)

### Stage 4: Error Handling (`data/quarantine/`)

**Purpose**: Failed processing requiring manual review
- Files that couldn't be processed
- Error logs stored as `.error.json` files
- Manual intervention required

**Common Quarantine Reasons**:
- Corrupted PDF files
- Unsupported file formats
- OCR failures
- Parsing errors

## File Metadata & Tracking

### Database Schema Integration

#### Content Unified Table
```sql
CREATE TABLE content_unified (
    id INTEGER PRIMARY KEY,
    source_type TEXT,           -- 'pdf', 'email', 'upload'
    source_id INTEGER,
    title TEXT,
    body TEXT,                  -- Full extracted content
    created_at TEXT,
    ready_for_embedding INTEGER,
    sha256 TEXT,               -- File hash for deduplication
    chunk_index INTEGER        -- For multi-chunk documents
);
```

#### Document Chunks (for large files)
- Large PDFs split into chunks for processing
- Each chunk gets unique `chunk_index` (0, 1, 2...)
- Same SHA256 hash links all chunks to original document
- Export system combines chunks back into complete documents

### Metadata Files

#### Processing Metadata (`.meta.json`)
```json
{
  "pipeline_id": "uuid",
  "original_path": "/path/to/original/file.pdf",
  "processed_path": "/data/processed/file_clean.txt", 
  "stage": "processed",
  "created_at": "2025-08-21T15:00:00Z",
  "file_type": "pdf",
  "processing_steps": {
    "validation": "complete",
    "text_extraction": "complete", 
    "chunking": "complete",
    "embedding": "complete"
  }
}
```

#### Error Tracking (`.error.json`)
```json
{
  "timestamp": "2025-08-21T15:00:00Z",
  "from_stage": "staged",
  "error": "PDF parsing failed",
  "filename": "document.pdf",
  "attempts": 2,
  "stack_trace": "..."
}
```

## Bates Numbering & Legal Document Conventions

### Current Implementation
- **Content ID**: Sequential database ID (1, 2, 3...)
- **File Naming**: `{source_type}_{content_id:04d}_{title}.txt`
- **Examples**: 
  - `pdf_0042_Contract_Agreement.txt`
  - `email_0157_Legal_Notice.txt`

### Bates Number Integration (Roadmap)
- **Prefix Support**: Configurable case prefixes (e.g., `CASE2024_`)
- **Sequential Numbering**: `CASE2024_000001`, `CASE2024_000002`
- **Document Families**: Link related documents (email + attachments)
- **Metadata Preservation**: Original filename + Bates number tracking

## Export & External Integration

### Improved Export System (`export_text_documents_improved.py`)

#### Features
- **Chunk Consolidation**: Combines PDF chunks into complete documents
- **HTML Cleaning**: Removes email formatting artifacts
- **Organized Structure**: Separates emails, PDFs, uploads into subdirectories
- **Metadata Headers**: Each file includes processing information

#### Directory Structure
```
/target/export/directory/
├── emails/        # Clean email text files
├── pdfs/          # Combined PDF text content
└── uploads/       # User-uploaded document text
```

#### File Format
```
Document ID: 42
Source Type: pdf
Title: Contract Agreement
Created: 2025-08-21T15:00:00Z
SHA256: abc123...
Chunk Info: combined_3_chunks
Content Length: 15,247 characters

================================================================================

[Clean extracted text content here...]
```

## Configuration & Customization

### Pipeline Settings
- **Batch Sizes**: Configurable processing limits
- **Retention Policies**: How long to keep files in each stage
- **Error Thresholds**: When to move files to quarantine
- **Export Formats**: Markdown, JSON, or plain text

### Service Integration
- **SimpleDB**: Primary content storage
- **Qdrant**: Vector embeddings for semantic search
- **Legal BERT**: Document intelligence extraction
- **Timeline Service**: Chronological organization

## Monitoring & Maintenance

### Health Checks
```bash
# Check pipeline status
tools/scripts/vsearch pipeline-status

# Verify system health  
python3 scripts/verify_pipeline.py

# Check quarantine files
ls -la data/quarantine/
```

### Maintenance Tasks

#### Daily
- Monitor quarantine directory for failed files
- Check processing logs for errors
- Verify vector database sync

#### Weekly  
- Archive old processed files
- Clean up export directory after confirmation
- Review and retry quarantine files

#### Monthly
- Analyze processing metrics
- Optimize pipeline performance
- Update file retention policies

## Security & Data Integrity

### File Handling
- **Original Preservation**: User files never modified
- **Copy-Based Processing**: All processing on copies
- **SHA256 Verification**: Content integrity checking
- **Quarantine Isolation**: Failed files isolated safely

### Access Control
- **Local Processing**: All processing happens locally
- **No External Uploads**: No automatic cloud uploads
- **User Control**: User decides what gets processed and exported

## Integration Points

### MCP Server Access
- **Legal Intelligence**: Document analysis and case building
- **Search Intelligence**: Semantic search across all content  
- **Pipeline Status**: Real-time processing monitoring

### CLI Integration
```bash
# Complete workflow
tools/scripts/vsearch upload document.pdf
tools/scripts/vsearch process-uploads  
tools/scripts/vsearch search "contract terms"
```

## Performance Characteristics

### Processing Speed
- **Text Files**: ~1000 docs/minute
- **PDFs (text)**: ~100 docs/minute  
- **PDFs (OCR)**: ~20 docs/minute
- **Emails**: ~500 docs/minute

### Storage Requirements
- **Original Files**: Preserved in user locations
- **Processed Content**: ~2-3x original size (with metadata)
- **Vector Embeddings**: ~4KB per document (1024D vectors)

---

This lifecycle ensures reliable, traceable document processing while preserving originals and providing multiple export formats for legal and analytical use.