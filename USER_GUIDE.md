# 📧 Email Sync System - User Guide

> **Your Personal Email Intelligence System**

Transform your Gmail into a searchable, intelligent knowledge base with AI-powered analysis and semantic search.

## 🚀 Quick Start (5 minutes)

### Step 1: Initial Setup
```bash
# Clone and enter the project
cd "Email Sync"

# Run the interactive setup wizard
tools/scripts/setup_wizard
```

The wizard will guide you through:
- Gmail API authentication
- Email filter configuration  
- Optional vector search setup
- First sync test

### Step 2: First Run
```bash
# Interactive first-run guide
tools/scripts/first_run_guide
```

### Step 3: Start Using!
```bash
# Search your emails
tools/scripts/vsearch search "maintenance"

# Full system sync
tools/scripts/run_full_system

# System status
tools/scripts/vsearch info
```

## 🎯 What Can You Do?

### 🔍 **Smart Search**
```bash
# Basic search
vsearch search "contract dispute"

# Filter by email type
vsearch search "payment" --type email

# Date-based search  
vsearch search "meeting" --since "last week" --until "today"

# Advanced semantic search (if Qdrant installed)
vsearch intelligence smart-search "legal document review"
```

### 📊 **Email Intelligence**
```bash
# Find duplicate emails
vsearch dedup find --show-groups

# Compare two emails
vsearch dedup compare email1_id email2_id

# Legal case analysis
vsearch legal process "24NNCV06082"

# Generate timeline
vsearch legal timeline "case_name" -o timeline.json
```

### 🔄 **System Management**
```bash
# Full sync with processing
tools/scripts/run_full_system

# Health check
vsearch health --verbose

# System information
vsearch info
```

## 📚 Key Features

### ✅ **What's Included**
- **Gmail Sync**: Automatic email synchronization with deduplication
- **Smart Search**: Keyword and semantic search across all content
- **Legal Analysis**: Case timeline generation and document analysis
- **Duplicate Detection**: Find exact and near-duplicate content
- **AI Integration**: MCP servers for Claude Desktop
- **Batch Processing**: Handle thousands of emails efficiently

### 🎨 **Search Capabilities**
- **Content Types**: emails, PDFs, transcripts, notes
- **Date Filtering**: "last week", "2024-01-01", "yesterday"
- **Type Filtering**: `--type email`, `--type pdf`
- **Tag Support**: `--tag legal --tag contract`
- **Similarity Search**: Find related documents
- **Fuzzy Matching**: Near-duplicate detection

### 🧠 **Intelligence Features**
- **Query Expansion**: Automatic search term enhancement
- **Document Clustering**: Group similar content
- **Entity Extraction**: Identify legal entities, dates, amounts
- **Summarization**: AI-powered document summaries
- **Timeline Generation**: Chronological case analysis

## 🛠️ Configuration

### Gmail Filters
Edit `gmail/config.py` to customize which emails to sync:

```python
self.preferred_senders = [
    "important@company.com",
    "legal@lawfirm.com",
    # Add your important contacts
]
```

### Search Behavior
- **Default limit**: 10 results
- **Similarity threshold**: 80% for duplicates
- **Batch size**: 50 emails per sync chunk

### Optional Components
- **Qdrant**: Vector database for semantic search
- **MCP Servers**: Claude Desktop integration
- **Background Processing**: Automatic summarization

## 🔧 Troubleshooting

### Common Issues

**Gmail Authentication Failed**
```bash
# Re-run setup wizard
tools/scripts/setup_wizard

# Check credentials file
ls gmail/credentials.json

# Test connection
python3 -c "from gmail.oauth import GmailAuth; print(GmailAuth().get_credentials())"
```

**Search Returns No Results**
```bash
# Check database
vsearch info

# Verify sync
tools/scripts/run_full_system

# Try broader search
vsearch search "" --limit 5
```

**Slow Performance**
```bash
# Check system health
vsearch health

# Clean old data
make cleanup

# Rebuild index
vsearch dedup index
```

### Log Files
Check `logs/` directory for detailed error information:
```bash
# View recent logs
tail -f logs/gmail_service_$(date +%Y%m%d).log

# Search for errors
grep -i error logs/*.log
```

### Reset Setup
```bash
# Remove configuration
rm gmail/token.json .first_run_progress.json

# Re-run setup
tools/scripts/setup_wizard
```

## 📈 Advanced Usage

### Automation
```bash
# Add to crontab for daily sync
0 9 * * * cd /path/to/Email\ Sync && tools/scripts/run_full_system

# Background processing
nohup tools/scripts/run_full_system > sync.log 2>&1 &
```

### Integration
```bash
# Export search results
vsearch search "contract" --json > results.json

# Batch operations
vsearch dedup remove --threshold 0.95 --force

# Legal workflow
vsearch legal process "case_id" --format json
```

### Claude Desktop Integration
If you have Claude Desktop, the system provides specialized tools:
- **Legal Intelligence**: Case analysis and timeline generation
- **Search Intelligence**: Advanced search and clustering
- **Sequential Thinking**: Structured problem-solving

## 📊 Performance & Limits

### What to Expect
- **Sync Speed**: ~50 emails/minute
- **Search Speed**: <500ms for keyword search
- **Database Size**: ~30MB per 1000 emails
- **Memory Usage**: <200MB during processing

### Gmail API Limits
- **Daily quota**: 1 billion quota units
- **Per-minute**: 250 quota units/user
- **Typical usage**: ~1-2 units per email

### Storage Requirements
- **Database**: ~30KB per email
- **Logs**: ~1MB per day
- **Vector index**: ~4KB per document (if using Qdrant)

## 🆘 Getting Help

### Self-Help Resources
1. **Quick Reference**: Run `tools/scripts/first_run_guide` to generate
2. **System Status**: `vsearch health --verbose`
3. **Documentation**: Check `docs/` directory
4. **Logs**: Review `logs/` for errors

### Diagnostic Commands
```bash
# Complete system check
vsearch health

# Database integrity
sqlite3 emails.db "PRAGMA integrity_check;"

# Gmail connection test
python3 -c "from gmail.main import GmailService; s=GmailService(); print(s.gmail_api.get_profile())"

# Dependencies check
pip list | grep -E "(torch|transformers|loguru|qdrant)"
```

### Recovery Procedures
```bash
# Backup database
cp emails.db emails.db.backup

# Reset and restore
tools/scripts/setup_wizard
# Re-sync emails will automatically skip duplicates

# Clean restart
rm -rf qdrant_data/ logs/ .first_run_progress.json
tools/scripts/setup_wizard
```

## 🎉 Tips & Best Practices

### Efficient Searching
- Use specific terms: "contract review" vs "document"
- Combine filters: `--type email --since "last month"`
- Try semantic search for concept matching
- Use date ranges for large datasets

### Email Management
- Configure sender filters to focus on important emails
- Run daily syncs to stay current
- Use duplicate detection to clean up your database
- Export important findings to markdown

### Performance Optimization
- Install Qdrant for faster semantic search
- Run cleanup regularly: `make cleanup`
- Use batch operations for large changes
- Monitor system health: `vsearch health`

---

## 📜 Quick Command Reference

```bash
# Essential Commands
vsearch search "query"              # Search content
tools/scripts/run_full_system       # Complete sync & processing
vsearch info                        # System status

# Advanced Search
vsearch intelligence smart-search "query"   # AI-enhanced search
vsearch dedup find --show-groups           # Find duplicates
vsearch legal process "case_id"            # Legal analysis

# System Management  
vsearch health                      # Health check
make cleanup                        # Clean old data
tools/scripts/setup_wizard          # Re-run setup

# Help
vsearch --help                      # All commands
tools/scripts/first_run_guide       # Interactive tutorial
```

**Happy searching! 🔍✨**