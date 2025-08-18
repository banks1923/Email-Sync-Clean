# Document Processing Pipeline - Data Directory Structure

This directory contains the structured data flow for the Email Sync document processing pipeline.

## Directory Structure

```
data/
├── raw/           # Incoming documents before processing
├── staged/        # Documents validated and ready for processing
├── processed/     # Successfully processed documents
├── quarantine/    # Problematic documents requiring manual review
└── export/        # Documents prepared for external use
```

## Data Flow

```
[New Document] → raw/ → [Validation] → staged/ → [Processing] → processed/
                            ↓                          ↓
                        quarantine/               [Export Ready] → export/
                        (on error)
```

## Directory Purposes

### `/raw/`
- **Purpose**: Initial landing zone for all incoming documents
- **Sources**: Email attachments, PDF uploads, transcriptions, API imports
- **Retention**: Temporary - files move to staged/ after validation
- **File Types**: All supported formats (PDF, DOCX, TXT, MP3, MP4, etc.)

### `/staged/`
- **Purpose**: Validated documents awaiting processing
- **Pre-conditions**: File format verified, virus scanned, metadata extracted
- **Processing Queue**: FIFO (First In, First Out) by default
- **File Types**: Only validated, supported formats

### `/processed/`
- **Purpose**: Successfully processed documents with extracted content
- **Contents**: Original files + generated outputs (Markdown, JSON, embeddings)
- **Organization**: Subdirectories by date (YYYY-MM-DD) for easy archival
- **Retention**: Long-term storage (configurable archival policy)

### `/quarantine/`
- **Purpose**: Documents that failed processing or validation
- **Reasons**: Corrupted files, unsupported formats, OCR failures, parsing errors
- **Review**: Manual intervention required
- **Metadata**: Error logs and processing attempts stored alongside files

### `/export/`
- **Purpose**: Documents prepared for external systems or backup
- **Formats**: Standardized outputs (Markdown + YAML frontmatter, JSON)
- **Use Cases**: API exports, backup archives, third-party integrations
- **Cleanup**: Periodic cleanup after successful export confirmation

## File Naming Conventions

### Standardized Naming Pattern
```
{timestamp}_{source}_{type}_{hash[:8]}.{ext}

Example: 20250115_gmail_pdf_a3f8c9d2.pdf
```

- **timestamp**: ISO 8601 format (YYYYMMDD_HHMMSS)
- **source**: Origin system (gmail, upload, api, manual)
- **type**: Content type (email, pdf, transcript, note)
- **hash**: First 8 characters of SHA-256 hash for deduplication
- **ext**: Original file extension

## Processing Pipeline Integration

### Supported Processing Workflows

1. **Email Processing** (gmail/ service)
   - Emails with attachments → raw/
   - Extracted attachments → staged/
   - Processed content → processed/

2. **PDF Processing** (pdf/ service)
   - Uploaded PDFs → raw/
   - OCR candidates → staged/
   - Extracted text → processed/

3. **Transcription Processing** (transcription/ service)
   - Audio/video files → raw/
   - Validated media → staged/
   - Transcribed text → processed/

4. **Document Intelligence** (Coming Soon)
   - Processed documents → Intelligence Engine
   - Summaries, entities, relationships → processed/
   - Enriched metadata → export/

## Automation Scripts

### Process Documents
```bash
scripts/vsearch ingest --source raw --batch-size 10
```

### Check Pipeline Status
```bash
scripts/vsearch pipeline-status
```

### Retry Quarantined Files
```bash
scripts/vsearch retry-quarantine --max-attempts 3
```

### Export Processed Documents
```bash
scripts/vsearch export --format markdown --since "last week"
```

## Configuration

Pipeline settings are managed through environment variables and configuration files:

- **Retention Policies**: Configure in `shared/simple_db.py`
- **Processing Limits**: Set batch sizes and timeouts
- **File Type Filters**: Define supported formats
- **Error Thresholds**: Quarantine rules and retry limits

## Monitoring

### Health Checks
- Directory permissions and space availability
- Processing queue depth
- Quarantine size and age
- Export backlog

### Metrics
- Documents processed per hour
- Average processing time by type
- Error rates and quarantine reasons
- Storage utilization trends

## Security Considerations

- Files in raw/ are untrusted until validated
- Staged files have passed security scanning
- Processed files are considered safe
- Quarantine may contain malicious files - handle with care
- Export files are sanitized for external consumption

## Maintenance

### Daily Tasks
- Monitor quarantine/ for files requiring attention
- Check processing logs for errors

### Weekly Tasks
- Archive old processed files
- Clean up export/ after confirmation
- Review and retry quarantine files

### Monthly Tasks
- Analyze processing metrics
- Optimize pipeline performance
- Update file retention policies

## Integration Points

This data pipeline integrates with:
- **Legal Intelligence Module**: Analyzes processed documents
- **Search Intelligence Module**: Indexes content for search
- **Knowledge Graph**: Builds relationships from processed data
- **MCP Servers**: Provides API access to pipeline status

---

For more information, see the main [CLAUDE.md](../CLAUDE.md) documentation.
