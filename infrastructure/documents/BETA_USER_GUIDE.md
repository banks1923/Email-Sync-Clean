# Email Sync Beta Test User Guide

Welcome to the Email Sync System Beta Test! This guide will help you get started with testing the AI-powered search system.

## Quick Start

### 1. System Requirements
- **Operating System**: macOS, Linux, or Windows with WSL
- **Python**: 3.8 or higher
- **Memory**: 4GB RAM minimum (for Legal BERT model)
- **Disk Space**: 2GB free (1.3GB for model download on first run)

### 2. First Run Setup

When you run the system for the first time, it will:
1. Download the Legal BERT model (1.3GB) - this is a one-time download
2. Initialize the SQLite database
3. Create data pipeline directories
4. Start in keyword search mode (vector search optional)

### 3. Basic Commands

#### Search for Content
```bash
# Simple search across all content
scripts/vsearch search "contract terms"

# Search with date filters
scripts/vsearch search "meeting notes" --since "last week"
scripts/vsearch search "invoice" --since "2024-01-01" --until "2024-06-30"

# Search by content type
scripts/vsearch search "important" --type email
scripts/vsearch search "agreement" --type pdf

# Search with tags
scripts/vsearch search "urgent" --tag legal --tag priority
```

#### Process Documents
```bash
# Upload a single PDF
scripts/vsearch upload document.pdf

# Upload multiple PDFs from a directory
scripts/vsearch upload /path/to/documents/

# The system automatically:
# - Detects if OCR is needed for scanned PDFs
# - Extracts text and metadata
# - Generates summaries (5 sentences, 15 keywords)
# - Creates searchable content
```

#### Sync Gmail (Optional)
```bash
# First time setup (opens browser for authentication)
scripts/vsearch sync-gmail

# Subsequent syncs (incremental, only new emails)
scripts/vsearch sync-gmail

# The system automatically:
# - Deduplicates emails
# - Extracts metadata
# - Generates summaries (3 sentences, 10 keywords)
```

#### System Information
```bash
# Check system status
scripts/vsearch info

# View help
scripts/vsearch --help
```

## Key Features to Test

### 1. Smart Search
The system uses AI to understand your search intent:
- **Query Expansion**: "LLC" automatically searches for "limited liability company"
- **Semantic Search**: Finds related concepts, not just keyword matches
- **Entity Recognition**: Identifies people, organizations, dates, and legal terms

### 2. Document Intelligence
- **Automatic Summarization**: Every document gets AI-generated summaries
- **Entity Extraction**: Identifies key people, organizations, and dates
- **Relationship Discovery**: Finds connections between documents

### 3. Advanced Filtering
- **Natural Language Dates**: Use "yesterday", "last week", "3 days ago"
- **Multiple Filters**: Combine date, type, and tag filters
- **Tag Logic**: Use AND/OR logic for tag combinations

## Beta Test Scenarios

### Scenario 1: Document Upload and Search
1. Upload a PDF document:
   ```bash
   scripts/vsearch upload test_document.pdf
   ```
2. Search for content from the document:
   ```bash
   scripts/vsearch search "keywords from document"
   ```
3. Try semantic search for related concepts

### Scenario 2: Email Search (if using Gmail)
1. Sync your emails:
   ```bash
   scripts/vsearch sync-gmail
   ```
2. Search with filters:
   ```bash
   scripts/vsearch search "meeting" --since "last month" --type email
   ```

### Scenario 3: Intelligence Features
1. Find similar documents:
   ```bash
   # After uploading multiple documents
   scripts/vsearch search "main topic" --limit 5
   ```
2. The system will show related documents based on content similarity

## Monitoring Your Test

### Check System Health
```bash
# Run the monitoring script
python scripts/beta_monitor.py --report

# For continuous monitoring (runs every 60 seconds)
python scripts/beta_monitor.py --continuous
```

### Performance Expectations
- **Search Response**: Should be under 2 seconds
- **PDF Processing**: 5-10 seconds per document
- **Email Sync**: ~50 emails per minute
- **Memory Usage**: Should stay under 500MB

## Troubleshooting

### Issue: Search returns no results
**Solution**: Check if content is indexed:
```bash
scripts/vsearch info  # Shows content counts
```

### Issue: Slow search performance
**Solution**: System may be using keyword search. To enable faster semantic search:
1. Install Qdrant (optional): See main README
2. Restart the search to use vector search

### Issue: PDF upload fails
**Possible causes**:
- PDF may be corrupted
- Insufficient permissions
- Check `data/quarantine/` for failed files

### Issue: High memory usage
**Solution**: This is normal during model loading. Memory usage should stabilize after initial load.

## Providing Feedback

### What We Need to Know
1. **Search Accuracy**: Are you finding what you're looking for?
2. **Performance**: Are operations fast enough?
3. **Ease of Use**: Is the system intuitive?
4. **Errors**: Any crashes or unexpected behavior?
5. **Feature Requests**: What's missing that you need?

### How to Report Issues
1. **Collect Information**:
   - What command did you run?
   - What was the expected result?
   - What actually happened?
   - Any error messages?

2. **Check Logs**:
   - Look at `beta_monitor.log` for system logs
   - Include relevant log entries in your report

3. **Submit Feedback**:
   - Email: [beta-feedback@example.com]
   - GitHub Issues: [repository-url]/issues
   - Include your `beta_monitor_report.md` if possible

## Advanced Features (Optional)

### Enable Semantic Search
For better search results, you can enable vector-based semantic search:

1. Install Qdrant locally (no Docker needed):
   ```bash
   # See main README for installation instructions
   ```

2. The system will automatically detect and use Qdrant when available

### Use MCP Tools in Claude Desktop
If you're using Claude Desktop, the system provides advanced tools:
- Legal intelligence analysis
- Document relationship mapping
- Timeline generation
- Entity extraction

## Safety and Privacy

### Your Data
- All data stays local on your machine
- No external services except optional Gmail API
- Database stored in local SQLite file
- Vectors stored locally in Qdrant (if enabled)

### Backup
Your data is stored in:
- `email_sync.db` - Main database
- `data/` - Document pipeline
- `qdrant_data/` - Vector embeddings (if enabled)

Back up these directories to preserve your data.

## Known Limitations

1. **First Run**: Initial model download takes time (1.3GB)
2. **Memory**: Requires 4GB RAM for Legal BERT model
3. **OCR**: Large scanned PDFs may take longer to process
4. **Batch Limits**: Email sync processes 500 emails at a time

## Getting Help

### Quick Help
```bash
# Command help
scripts/vsearch --help

# Specific command help
scripts/vsearch search --help
```

### Documentation
- This guide: `BETA_USER_GUIDE.md`
- Full documentation: `README.md`
- Architecture details: `CLAUDE.md`

### Support
- Check `BETA_TEST_CHECKLIST.md` for test scenarios
- Run `python scripts/beta_monitor.py --report` for system health
- Submit issues via GitHub or email

## Thank You!

Thank you for participating in the Email Sync beta test. Your feedback is invaluable in making this system better. We appreciate your time and effort in testing these features.

Happy searching! 🚀
