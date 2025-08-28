_This document outlines the development principles and implementation details for the PDF service._

# PDF Service

PDF processing with OCR support, text extraction, and job queue integration.

## Architecture Principles

### Hard Limits
- **File Size**: Target 450 lines for new files; existing working files guided by functionality
- **Function Size**: Maximum 30 lines per function
- **Service Independence**: No imports from other services
- **Single Responsibility**: Each file has one clear purpose

### Anti-Patterns (NEVER DO)
- **No Singletons**: Direct instantiation is fine
- **No Factories**: Use if/else for 2-3 choices
- **No Abstract Base Classes**: Unless Python stdlib requires it
- **No Dependency Injection**: Just import and use
- **No Manager of Managers**: One level of management max
- **No Complex Patterns**: This is a hobby project for ONE user

### Good Patterns
- **Simple Functions**: Input → Process → Output
- **Direct Imports**: `from module import function`
- **Flat Structure**: Avoid deep nesting
- **Clear Names**: `extract_pdf_text()` not `PDFProcessingPipelineFactory`

## Status
Production-ready with integrated OCR pipeline and batch processing.

## Quick Commands

```bash
# Upload and process PDFs (with automatic OCR detection)
scripts/vsearch upload document.pdf              # Single PDF
scripts/vsearch upload pdfs/                     # Directory batch
scripts/vsearch upload pdfs/ -n 20               # Limited batch

# Check PDF processing stats
scripts/vsearch info                             # Shows OCR vs text extraction counts

# Search across PDFs and emails
scripts/vsearch search "legal contract terms"    # Unified search
```

## Modular Architecture

### Core Service
- **PDFService** (`main.py`) - Main service interface with OCR integration (232 lines)

### OCR Pipeline Components (Integrated)
- **OCRCoordinator** (`ocr/ocr_coordinator.py`) - Pipeline orchestration (120 lines)
  - Intelligent PDF type detection (text vs scanned)
  - Automatic OCR processing when needed
  - Confidence scoring and quality metrics
  - Falls back to text extraction for text-based PDFs

### Storage & Database
- **PDFDatabase** (`pdf_database.py`) - SQLite storage with deduplication
- **PDFProcessor** (`pdf_processor.py`) - Basic text extraction
- **EnhancedPDFProcessor** (`pdf_processor_enhanced.py`) - OCR-enabled processing
- **EnhancedPDFStorage** (`pdf_storage_enhanced.py`) - Legal metadata support

### Pipeline Integration
- **PDFVectorPipeline** - Transactional PDF→Vector processing (archived - needs refactor)

## Pipeline Features

### OCR Detection & Processing
- **Automatic Detection**: Identifies scanned vs text PDFs
- **Quality Checks**: Minimum text length validation
- **Image Enhancement**: Contrast, sharpening, noise reduction
- **Confidence Scoring**: OCR quality metrics

### Transactional Safety
- **Atomic Operations**: All-or-nothing processing
- **Rollback Support**: Failed operations don't leave partial data
- **Duplicate Prevention**: SHA-256 based deduplication
- **State Tracking**: Processing status in unified_content table

## API

```python
from pdf.main import PDFService

# Direct service usage (OCR integrated)
service = PDFService()

# Single PDF upload (automatic OCR if needed)
result = service.upload_single_pdf("document.pdf")
# Returns: {"success": True, "chunks_processed": 118, "file_name": "document.pdf"}

# Batch directory upload
result = service.upload_directory("/path/to/pdfs/", limit=20)
# Returns: {"success": True, "results": {...}, "total_processed": 20}

# Get stats including OCR metrics
stats = service.get_pdf_stats()
# Returns extraction method breakdown, OCR confidence scores, etc.

# Health check
health = service.health_check()
# Returns: {"healthy": True, "database": "connected", ...}
```

## Database Schema

### Documents Table
- Chunked text (900 chars each with overlap)
- File metadata (hash, size, path)
- Processing timestamps
- Legal metadata (JSON field)
- Extraction method tracking
- OCR confidence scores

### Unified Content Table
- Cross-content type storage
- Vector processing status
- Source tracking
- Transactional integrity

### Jobs Table
- Job queue management
- Priority and retry tracking
- Error messages
- Processing timestamps

## Legal Metadata Extraction

Automatically extracts:
- Case numbers (multiple formats)
- Court names and jurisdictions
- Document types (Motion, Complaint, Order, etc.)
- Filing/hearing/service dates
- Party names using NER
- Attorney information with bar numbers
- Legal deadlines based on document type

## Testing

```bash
# All PDF tests
pytest tests/pdf_service/

# OCR pipeline tests
pytest tests/test_ocr_pipeline.py

# Integration tests
pytest tests/integration/ -k pdf

# PDF service tests
pytest tests/pdf_service/
```

### Test Coverage
- Unit tests for each OCR component
- Integration tests for full pipeline
- Mock and real PDF processing tests
- Job queue reliability tests
- Transactional safety tests

## Recent Updates

### OCR Integration (Jan 2025)
- **Automatic Detection**: PDFService now automatically detects scanned vs text PDFs
- **Integrated Processing**: OCR seamlessly integrated into main upload flow
- **Smart Fallback**: Uses pypdf2 for text PDFs, Tesseract for scanned
- **Production Ready**: Successfully processes real legal documents (LA Court case example)

### Performance Improvements (Jan 2025)
- **Batch Operations**: High-performance bulk inserts via SimpleDB
- **Deduplication**: SHA-256 based duplicate prevention
- **Concurrency Control**: Semaphore-based upload limiting
- **Progress Tracking**: Optional callbacks for long operations

### Architecture Simplification (Jan 2025)
- **Flat Structure**: Moved from nested to root-level services
- **Clean Integration**: OCR coordinator directly in PDFService
- **Reduced Complexity**: 75% less code while maintaining functionality
- **Better Metrics**: Enhanced stats with OCR confidence tracking