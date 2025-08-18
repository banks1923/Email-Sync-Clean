# Document Processing Pipeline

## Overview
Comprehensive document lifecycle management system that processes documents through structured stages: raw → staged → processed → quarantine/export.

## Architecture

### Pipeline Stages
1. **Raw**: Initial document ingestion point
2. **Staged**: Active processing and transformation
3. **Processed**: Completed with intelligence extracted
4. **Quarantine**: Failed documents requiring manual intervention
5. **Export**: Final output preparation for external systems

### Key Components

#### PipelineOrchestrator (`orchestrator.py`)
- **Purpose**: Manages document lifecycle and stage transitions
- **Lines**: ~500
- **Key Methods**:
  - `generate_pipeline_id()`: Creates unique document identifiers
  - `move_to_stage()`: Transitions documents between stages
  - `process_raw_document()`: Initiates processing from raw stage
  - `process_staged_document()`: Applies intelligence extraction
  - `quarantine_document()`: Handles processing failures
  - `export_document()`: Prepares final output

#### Document Processors (`processors.py`)
- **Purpose**: Type-specific document processing
- **Lines**: ~300
- **Processors**:
  - `EmailProcessor`: Handles email parsing and metadata extraction with HTML cleaning
  - `PDFProcessor`: Processes PDF text with artifact cleanup
  - `TranscriptionProcessor`: Formats audio/video transcriptions
- **Factory**: `get_processor(document_type)` returns appropriate processor

#### HTML Content Cleaning (`document_exporter.py` + `shared/html_cleaner.py`)
- **Purpose**: Clean HTML email content for readable markdown export
- **Features**:
  - Automatic HTML tag removal and text extraction
  - Email metadata extraction (sender, subject, date)
  - Intelligent content type detection (only cleans email content)
  - Preserves important content while removing styling artifacts
  - HTML entity decoding (`&lt;` → `<`, `&amp;` → `&`)
  - Email thread cleanup (removes quoted content and boilerplate)

#### Unified Formats (`formats.py`)
- **Purpose**: Consistent document representation
- **Lines**: ~200
- **Formatters**:
  - `MarkdownFormatter`: Creates Markdown with YAML frontmatter
  - `JSONCompanionFormatter`: Generates structured metadata files
  - `UnifiedDocumentFormatter`: Combines both formats

#### Document Intelligence (`intelligence.py`)
- **Purpose**: Extract insights from documents
- **Lines**: ~250
- **Features**:
  - Summary extraction (TF-IDF + TextRank)
  - Entity recognition (persons, organizations, dates, etc.)
  - Relationship building (similarity, references, temporal)
  - Database integration for persistence

## Usage Examples

### Basic Pipeline Usage
```python
from pipelines import get_pipeline_orchestrator

# Initialize orchestrator
orchestrator = get_pipeline_orchestrator()

# Generate pipeline ID for new document
pipeline_id = orchestrator.generate_pipeline_id()

# Save document to raw stage
orchestrator.save_document_to_stage(
    content="Document content here",
    filename="document.txt",
    stage='raw',
    pipeline_id=pipeline_id,
    metadata={'content_type': 'text'}
)

# Process through pipeline
orchestrator.process_raw_document(pipeline_id, 'email')
orchestrator.process_staged_document(pipeline_id)
orchestrator.export_document(pipeline_id, 'both')
```

### Document Processing
```python
from pipelines.processors import get_processor

# Get appropriate processor
processor = get_processor('email')

# Validate document
is_valid, error_msg = processor.validate(content, metadata)

# Process document
if is_valid:
    processed_content, updated_metadata = processor.process(content, metadata)
```

### HTML Email Cleaning
```python
from infrastructure.pipelines.document_exporter import DocumentExporter
from shared.html_cleaner import clean_html_content, extract_email_content

# Clean raw HTML email content
html_email = '''
<div>From: john@example.com</div>
<div>Subject: Legal Notice</div>
<p style="margin:0in;">Important legal content here</p>
<blockquote>Previous email quoted</blockquote>
'''

# Extract clean content and metadata
cleaned_content, email_metadata = extract_email_content(html_email)
# Returns: metadata = {'sender': 'john@example.com', 'subject': 'Legal Notice'}
# Returns: cleaned_content = 'Important legal content here'

# Export with DocumentExporter (automatically detects and cleans HTML emails)
exporter = DocumentExporter()
email_dict = {
    'content_id': 'email-123',
    'content_type': 'email',  # Triggers HTML cleaning
    'title': 'Legal Email',
    'content': html_email,
    'created_time': '2025-08-17T10:00:00',
    'metadata': {}
}

markdown_result = exporter.format_as_markdown(email_dict)
# Produces clean markdown with extracted metadata in YAML frontmatter
```

### Intelligence Extraction
```python
from pipelines.intelligence import DocumentIntelligence

intelligence = DocumentIntelligence()

# Extract all intelligence
intel_data = intelligence.extract_all(text, metadata)

# Individual extraction
summary = intelligence.extract_summary(text, max_sentences=5)
entities = intelligence.extract_entities(text)
relationships = intelligence.build_relationships(content_id, text, metadata)
```

### Document Formatting
```python
from pipelines.formats import get_document_formatter

formatter = get_document_formatter()

# Format document with intelligence
formatted = formatter.format_document(
    pipeline_id=pipeline_id,
    title="Document Title",
    content=content,
    metadata=metadata,
    intelligence=intel_data
)

# Save formatted documents
saved_files = formatter.save_formatted_document(
    pipeline_id=pipeline_id,
    output_dir='data/processed',
    formatted_content=formatted
)
```

## Metadata Structure

### Pipeline Metadata (.meta.json)
```json
{
  "pipeline_id": "uuid",
  "stage": "raw|staged|processed|quarantine|export",
  "created_at": "2025-08-16T12:00:00Z",
  "updated_at": "2025-08-16T12:05:00Z",
  "content_type": "email|pdf|transcription",
  "original_filename": "document.pdf",
  "processing_steps": {
    "validation": "complete",
    "text_extraction": "complete",
    "intelligence_extraction": "in_progress"
  },
  "errors": [],
  "warnings": []
}
```

### Markdown Output Format
```markdown
---
pipeline_id: uuid
title: Document Title
date: 2025-08-16
content_type: email
tags: [legal, contract]
summary: Brief document summary
---

# Document Title

Full processed content...
```

### JSON Companion Format
```json
{
  "pipeline_id": "uuid",
  "generated_at": "2025-08-16T12:00:00Z",
  "intelligence": {
    "summary": {
      "summary_text": "...",
      "tf_idf_keywords": {"legal": 0.8},
      "textrank_sentences": ["Key sentence"]
    },
    "entities": {
      "persons": ["John Doe"],
      "organizations": ["ABC Corp"],
      "dates": ["2025-08-16"]
    },
    "relationships": [
      {"to": "doc_id", "type": "similar_to", "confidence": 0.85}
    ]
  },
  "embeddings": {
    "model": "legal-bert",
    "vector_id": "qdrant-uuid"
  }
}
```

## Error Handling

### Quarantine Process
1. Document validation fails or processing error occurs
2. Document moved to `/quarantine/` with error metadata
3. Error details logged in `.meta.json`
4. Manual review required for recovery

### Error Metadata
```json
{
  "quarantined_at": "2025-08-16T12:00:00Z",
  "quarantined_from": "staged",
  "error_info": {
    "error": "validation_failed",
    "message": "PDF extraction failed",
    "stack_trace": "...",
    "attempts": 3
  },
  "partial_results": {...}
}
```

## Integration Points

### Service Integration
- **Gmail Service**: Email ingestion via `integrate_gmail()`
- **PDF Service**: PDF processing via `integrate_pdf()`
- **Transcription Service**: Audio/video via `integrate_transcription()`
- **Search Service**: Vector embeddings and indexing
- **SimpleDB**: Metadata and intelligence storage

### CLI Integration
- `vsearch ingest`: Central ingestion command
- `vsearch process`: Process documents through pipeline
- `vsearch export`: Export processed documents

## Performance Characteristics

### Processing Speed
- **Document validation**: <100ms
- **Text processing**: ~500ms per document
- **Intelligence extraction**: 1-2 seconds
- **Full pipeline**: 2-5 seconds per document

### Resource Usage
- **Memory**: <50MB per document
- **Disk**: 2-3x original document size (with metadata)
- **CPU**: Single-threaded processing

## Testing

### Test Coverage
- 11 comprehensive tests in `test_pipeline_orchestrator.py`
- Tests cover:
  - Folder structure creation
  - Document lifecycle transitions
  - Metadata tracking
  - Error quarantine
  - Format generation
  - Processor validation

### Running Tests
```bash
python3 -m pytest tests/test_pipeline_orchestrator.py -v
```

## Future Enhancements

### Planned Features
- Batch processing optimization
- Parallel document processing
- Advanced duplicate detection
- Image/OCR support
- Real-time processing notifications
- Web dashboard for monitoring

### Integration Opportunities
- Legal Intelligence module integration
- Search Intelligence module integration
- MCP server for pipeline management
- Automated workflow triggers
- External system webhooks

## Best Practices

### Document Ingestion
1. Always generate pipeline_id first
2. Validate documents before processing
3. Preserve original files in raw stage
4. Track all metadata changes

### Error Recovery
1. Check quarantine regularly
2. Analyze error patterns
3. Implement retry logic for transient failures
4. Manual review for critical documents

### Performance Optimization
1. Batch similar document types
2. Cache intelligence extraction results
3. Use appropriate processors for each type
4. Monitor stage transition times

## Architecture Principles

### Simplicity
- Direct implementation, no abstractions
- Single responsibility per component
- Maximum 450 lines per file
- Clear stage transitions

### Reliability
- Fail-safe quarantine mechanism
- Metadata tracking at every stage
- Idempotent operations
- Error isolation

### Extensibility
- Pluggable processors
- Flexible metadata schema
- Multiple output formats
- Service integration ready
