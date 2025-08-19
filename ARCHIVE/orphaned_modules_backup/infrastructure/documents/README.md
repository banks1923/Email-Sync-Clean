# Multi-Format Document Processing System

## Overview

Comprehensive document processing system supporting DOCX, TXT, MD, and PDF formats with full lifecycle management. Built following CLAUDE.md principles with simple, direct implementation.

## Features

### Supported Formats
- **PDF**: Full OCR support via existing PDF service
- **DOCX**: Microsoft Word documents with tables and metadata
- **TXT**: Plain text with automatic encoding detection
- **MD**: Markdown with YAML frontmatter support

### Document Lifecycle
```
[Raw] → [Staged] → [Processed] → [Export]
           ↓
     [Quarantine]
```

- **Raw**: Original untouched documents
- **Staged**: Pre-processed with standardized naming
- **Processed**: Extracted content in markdown format
- **Export**: Final processed documents
- **Quarantine**: Failed documents with error logs

## Installation

```bash
# Core functionality (TXT, MD)
pip install chardet pyyaml

# DOCX support
pip install python-docx

# Full PDF support (optional)
pip install PyPDF2 pdf2image pytesseract
```

## Quick Start

```python
from documents import DocumentPipeline

# Initialize pipeline
pipeline = DocumentPipeline(base_path="data", db_path="emails.db")

# Process single document
result = pipeline.process_document(
    Path("contract.docx"),
    case_name="SMITH_V_JONES",
    doc_type="CONTRACT"
)

# Process directory
results = pipeline.process_directory(
    "documents/inbox",
    case_name="JOHNSON_CASE",
    recursive=True
)

# Check statistics
stats = pipeline.get_pipeline_stats()
```

## Architecture

### Core Components

#### DocumentLifecycleManager
Manages folder structure and file movement through lifecycle stages.

```python
from documents import DocumentLifecycleManager

lifecycle = DocumentLifecycleManager("data")

# Move through stages
staged = lifecycle.move_to_staged(file_path)
processed = lifecycle.move_to_processed(staged)
exported = lifecycle.move_to_export(processed)

# Handle errors
lifecycle.quarantine_file(file_path, "Processing failed")
```

#### NamingConvention
Standardized naming for each lifecycle stage.

```python
from documents import NamingConvention

naming = NamingConvention()

# Stage-specific naming
staged = naming.staged_name(path, "CASE_NAME", "DOC_TYPE")
# Output: CASE_NAME_DOC_TYPE_20240115_document.pdf

processed = naming.processed_name(path, "md")
# Output: DOC_2024_0001.md

export = naming.export_name("DOC_2024_0001", "CASE", "TYPE")
# Output: DOC_2024_0001_CASE_TYPE_processed.md
```

#### FormatDetector
Automatic format detection using magic bytes and extensions.

```python
from documents import FormatDetector

detector = FormatDetector()

format_type = detector.detect_format(Path("file.docx"))
# Returns: 'docx'

is_supported = detector.is_supported_format(Path("file.pdf"))
# Returns: True
```

### Document Processors

Each format has a dedicated processor following the same interface:

```python
from documents.processors import TextProcessor, MarkdownProcessor, DocxProcessor

# Process any supported format
processor = TextProcessor()  # or MarkdownProcessor(), DocxProcessor()
result = processor.process(file_path)

# Result structure
{
    "success": True,
    "content": "Extracted text...",
    "metadata": {
        "filename": "document.txt",
        "encoding": "utf-8",
        "created_at": "2024-01-15T10:00:00",
        ...
    },
    "metrics": {
        "word_count": 500,
        "line_count": 50,
        ...
    },
    "format": "txt"
}
```

## Naming Conventions

### Staged Files
Format: `{CASE}_{TYPE}_{YYYYMMDD}_{OriginalName}`
Example: `SMITH_V_JONES_MOTION_20240115_document.pdf`

### Processed Files
Format: `DOC_{YYYY}_{NNNN}.{format}`
Example: `DOC_2024_0001.md`

### Export Files
Format: `{DocID}_{CASE}_{TYPE}_processed.md`
Example: `DOC_2024_0001_SMITH_V_JONES_MOTION_processed.md`

### Quarantine Files
Format: `{YYYYMMDD_HHMMSS}_{ERROR}_{OriginalName}`
Example: `20240115_143022_CORRUPT_document.pdf`

## Database Integration

Documents are automatically stored in the unified content database:

```python
# Stored in SimpleDB with metadata
{
    "content_type": "document",
    "title": "Contract Agreement",
    "content": "Full extracted text...",
    "metadata": {
        "format": "docx",
        "doc_id": "DOC_2024_0001",
        "author": "John Doe",
        "created": "2024-01-15",
        "word_count": 1500,
        ...
    }
}
```

## Error Handling

### Automatic Quarantine
Failed documents are automatically moved to quarantine with error logs:

```
data/quarantine/
├── 20240115_143022_CORRUPT_document.pdf
└── 20240115_143022_CORRUPT_document.pdf.error
```

### Error Recovery
```python
# Retry failed documents
for file in lifecycle.list_files("quarantine"):
    if "CORRUPT" not in file:
        # Retry processing
        result = pipeline.process_document(
            lifecycle.get_file_path("quarantine", file)
        )
```

## Format-Specific Features

### Text Files (TXT)
- Automatic encoding detection (UTF-8, ASCII, Latin-1, etc.)
- Line ending normalization
- Special format detection (logs, CSV-like, code)

### Markdown Files (MD)
- YAML frontmatter parsing
- Structure analysis (headings, links, tables, code blocks)
- Plain text conversion
- Link and heading extraction

### Word Documents (DOCX)
- Table extraction
- Header/footer extraction
- Document properties (author, creation date, etc.)
- Style analysis
- Comment extraction (limited)

### PDF Files
- Full OCR support via PDF service
- Text/scanned detection
- Legal metadata extraction
- Confidence scoring
- **NEW**: Direct PDF-to-markdown conversion via DocumentConverter

## Testing

```bash
# Run all document processing tests
pytest tests/document_processing/

# Run specific processor tests
pytest tests/document_processing/test_document_processors.py::TestTextProcessor
pytest tests/document_processing/test_document_processors.py::TestMarkdownProcessor
pytest tests/document_processing/test_document_processors.py::TestDocxProcessor
```

## CLI Integration

```bash
# Process documents via vsearch
scripts/vsearch process-docs /path/to/documents --case "SMITH_V_JONES"

# Check pipeline stats
scripts/vsearch doc-stats
```

## Performance

### Processing Speed
- TXT: ~1000 docs/minute
- MD: ~800 docs/minute
- DOCX: ~100 docs/minute
- PDF: ~20 docs/minute (with OCR)

### Memory Usage
- Base: ~50MB
- Per processor: ~20MB
- Large DOCX: Up to 200MB
- PDF with OCR: Up to 500MB

## Configuration

### Folder Structure
```python
# Custom base path
pipeline = DocumentPipeline(base_path="/custom/path")

# Folder layout
/custom/path/
├── raw/        # Original files
├── staged/     # Renamed files
├── processed/  # Markdown output
├── export/     # Final documents
└── quarantine/ # Failed files
```

### Processor Settings
```python
# Custom encoding for text files
processor = TextProcessor()
processor.supported_encodings = ['utf-8', 'cp1252', 'shift-jis']

# Custom DPI for PDF OCR
from pdf.ocr import OCRCoordinator
ocr = OCRCoordinator(dpi=400)
```

## Best Practices

1. **Batch Processing**: Process documents in batches of 100-500
2. **Case Organization**: Use consistent case names for related documents
3. **Error Review**: Regularly check quarantine folder
4. **Backup Raw Files**: Keep originals in separate backup
5. **Monitor Stats**: Track success/failure rates

## Troubleshooting

### Common Issues

**"Unsupported format"**
- Check file extension is in supported list
- Verify file is not corrupted
- Try renaming with correct extension

**"Processing failed"**
- Check quarantine folder for error details
- Verify required libraries installed
- Check file permissions

**"No processor for format"**
- Install format-specific dependencies
- For DOCX: `pip install python-docx`
- For PDF: Ensure PDF service is available

## New Features (August 2025)

### DocumentConverter
**Direct PDF-to-markdown conversion with YAML frontmatter**

```python
from infrastructure.documents.document_converter import get_document_converter

# Convert single PDF to markdown
converter = get_document_converter()
result = converter.convert_pdf_to_markdown(
    pdf_path=Path("contract.pdf"),
    output_path=Path("contract.md")
)

# Batch convert directory
batch_result = converter.convert_directory(
    directory_path=Path("pdfs/"),
    output_dir=Path("markdown/"),
    recursive=True
)
```

**Features:**
- Automatic OCR detection and processing
- Comprehensive YAML frontmatter metadata
- Content cleaning and formatting
- SHA-256 hash calculation
- Legal metadata extraction
- Batch processing support
- 23 comprehensive tests

**Metadata Generated:**
```yaml
---
title: document_name
original_filename: document.pdf
file_hash: sha256_hash
file_size_mb: 1.23
page_count: 10
extraction_method: ocr|pypdf2
ocr_required: true|false
ocr_confidence: 0.95
processed_at: 2025-08-17T20:00:00
document_type: pdf
legal_metadata:
  case_number: "24NNCV001234"
---
```

## Future Enhancements

- [ ] RTF support
- [ ] ODT support
- [ ] Excel/CSV with table extraction
- [ ] Email formats (EML, MSG)
- [ ] Image OCR integration
- [ ] Parallel processing
- [ ] Web UI for document management

## API Reference

### EmailThreadProcessor (NEW)

**Convert Gmail threads to chronological markdown files**

```python
from infrastructure.documents.processors import get_email_thread_processor

# Initialize processor
processor = get_email_thread_processor()

# Process single thread
result = processor.process_thread(
    thread_id="gmail_thread_id_123",
    include_metadata=True,
    save_to_db=True
)

# Process multiple threads by query
batch_result = processor.process_threads_by_query(
    query="from:important@client.com",
    max_threads=20,
    include_metadata=True
)
```

**Features:**
- Gmail thread fetching and parsing
- Chronological message sorting
- HTML content cleaning
- Large thread splitting (>100 emails)
- Cross-reference links between parts
- YAML frontmatter metadata
- Analog database integration

**Methods:**
- `process_thread(thread_id, include_metadata, save_to_db)` - Process single thread
- `process_threads_by_query(query, max_threads, include_metadata)` - Batch process threads
- `validate_setup()` - Check processor dependencies

### DocumentConverter (NEW)

**Methods:**
- `convert_pdf_to_markdown(pdf_path, output_path, include_metadata)` - Convert single PDF
- `convert_directory(directory_path, output_dir, recursive)` - Batch convert directory
- `validate_setup()` - Check converter dependencies

### DocumentPipeline

**Methods:**
- `process_document(file_path, case_name, doc_type)` - Process single document
- `process_directory(directory_path, case_name, doc_type, recursive)` - Process directory
- `get_pipeline_stats()` - Get processing statistics

### DocumentLifecycleManager

**Methods:**
- `move_to_staged(file_path, new_name)` - Move to staged
- `move_to_processed(file_path, new_name)` - Move to processed
- `move_to_export(file_path, new_name)` - Move to export
- `quarantine_file(file_path, error_msg)` - Move to quarantine
- `get_folder_stats()` - Get folder statistics
- `list_files(stage)` - List files in stage

### NamingConvention

**Methods:**
- `raw_name(path)` - Keep original name
- `staged_name(path, case, type)` - Generate staged name
- `processed_name(path, format)` - Generate processed name
- `export_name(doc_id, case, type)` - Generate export name
- `quarantine_name(path, error)` - Generate quarantine name
- `validate_name(filename, stage)` - Validate naming convention

---

*Built following CLAUDE.md principles - Simple, Direct, Functional*
