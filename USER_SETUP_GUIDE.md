# Email Sync System - User Setup Guide

🎯 **Get up and running in 5 minutes** - Complete setup guide for beginners.

## 📋 What You're Getting

This is an AI-powered document search system that:
- 🔍 **Searches** emails, PDFs, and documents with natural language
- 🧠 **Understands** context using Legal BERT AI 
- 📊 **Organizes** your documents automatically
- ⚡ **Finds** information instantly across all your content

## 🚀 Quick Setup (5 Minutes)

### Step 1: Install Python Dependencies
```bash
# Navigate to your project directory
cd /path/to/Email-Sync-Clean-Backup

# Install everything you need
make setup
```

### Step 2: Test Basic Functionality
```bash
# Test the system works
make test-basic

# Check system status
tools/scripts/vsearch info
```

### Step 3: Enable Vector Search (Optional but Recommended)
```bash
# Install and start Qdrant (vector database)
make install-qdrant

# Test vector search is working
make test-vector
```

### Step 4: Start Using the System
```bash
# Search your existing content
tools/scripts/vsearch search "important meeting"

# Upload a PDF to test
tools/scripts/vsearch upload document.pdf

# Check what's in your database
tools/scripts/vsearch info
```

## 📚 Essential Commands

### Daily Use Commands
```bash
# Search everything
make search QUERY="contract terms"

# Upload documents
make upload FILE="document.pdf"

# Sync Gmail (if configured)
make sync-gmail

# System health check
make health-check

# View recent activity
make recent-activity
```

### First-Time Setup Commands
```bash
# Complete setup from scratch
make first-time-setup

# Install all optional components
make install-all

# Configure Gmail sync (optional)
make setup-gmail

# Run full system test
make test-everything
```

### Maintenance Commands
```bash
# Clean up and optimize
make cleanup

# Update system components
make update-system

# Backup your data
make backup

# Check for issues
make diagnose
```

## 🛠️ Detailed Setup Instructions

### Requirements Check
```bash
# Check if you have Python 3.8+
python3 --version

# Check available memory (need 4GB+ for AI model)
make check-requirements
```

### Vector Search Setup (Recommended)
The system works without vector search, but it's much more powerful with it:

```bash
# Auto-install Qdrant locally (no Docker needed)
make install-qdrant

# Manual installation if auto-install fails
curl -L https://install.qdrant.io | bash
```

### Gmail Integration (Optional)
If you want to search your Gmail:

```bash
# Setup Gmail API credentials
make setup-gmail-auth

# Test Gmail connection
make test-gmail

# Sync recent emails
make sync-gmail-recent
```

## 🔍 Using the Search System

### Basic Search
```bash
# Simple text search
tools/scripts/vsearch search "meeting notes"

# Search with date filters
tools/scripts/vsearch search "contract" --since "last month"

# Search specific types
tools/scripts/vsearch search "invoice" --type pdf
```

### Advanced Search
```bash
# Multiple filters
tools/scripts/vsearch search "legal" --type email --since "2024-01-01" --tag urgent

# Fuzzy search for typos
tools/scripts/vsearch search "contrct" --fuzzy

# Search similar documents
tools/scripts/vsearch similar document_id_123
```

### Upload Documents
```bash
# Single PDF
tools/scripts/vsearch upload document.pdf

# Batch upload directory
tools/scripts/vsearch upload /path/to/documents/

# Upload with custom tags
tools/scripts/vsearch upload contract.pdf --tags "legal,contract,important"
```

## 📊 Understanding Your System

### System Information
```bash
# Complete system overview
tools/scripts/vsearch info

# Database statistics
make db-stats

# Performance metrics
make performance-stats
```

### Data Locations
- **Database**: `data/emails.db` (SQLite)
- **Documents**: `data/processed/` (PDFs, etc.)
- **Logs**: `logs/` (system activity)
- **Vector Data**: `qdrant_data/` (search index)

## 🚨 Troubleshooting

### Common Issues

#### "No search results"
```bash
# Check if documents are indexed
tools/scripts/vsearch info

# Reindex everything
make reindex-all
```

#### "Vector service not connected"
```bash
# Start Qdrant
make start-qdrant

# Check Qdrant status
make qdrant-status
```

#### "Permission errors"
```bash
# Fix file permissions
make fix-permissions

# Check disk space
make check-disk-space
```

#### "Out of memory errors"
```bash
# Check memory usage
make memory-check

# Use lightweight mode
export LIGHTWEIGHT_MODE=true
```

### Getting Help
```bash
# Show all available commands
make help

# Show search help
tools/scripts/vsearch --help

# Run system diagnostics
make diagnose

# Generate system report
make system-report
```

## 🎓 Next Steps

### Learn More
1. **Read the full documentation**: `README.md`
2. **Explore advanced features**: `docs/SERVICES_API.md`
3. **Set up automation**: Schedule regular Gmail syncs
4. **Customize search**: Add custom tags and filters

### Advanced Configuration
```bash
# Configure advanced settings
make configure-advanced

# Set up automated backups
make setup-backups

# Configure custom search aliases
make setup-search-aliases
```

### Performance Optimization
```bash
# Optimize database
make optimize-db

# Clean up old data
make cleanup-old-data

# Monitor performance
make monitor-performance
```

## 🔐 Security & Privacy

This system is designed for personal use:
- **Local-only**: All data stays on your computer
- **No cloud sync**: Unless you explicitly configure it
- **Encrypted storage**: Database can be encrypted
- **Privacy-first**: No telemetry or tracking

### Enable Encryption (Optional)
```bash
# Encrypt your database
make encrypt-database

# Set up secure backups
make setup-secure-backups
```

## 📈 Success Metrics

After setup, you should see:
- ✅ `tools/scripts/vsearch info` shows connected services
- ✅ Search returns relevant results
- ✅ Documents upload successfully
- ✅ Vector search provides semantic matching
- ✅ System responds quickly (< 2 seconds for searches)

## 🤝 Getting Support

If you run into issues:
1. **Check this guide** for common solutions
2. **Run diagnostics**: `make diagnose`
3. **Check logs**: `tail -f logs/latest.log`
4. **Review documentation**: `docs/` directory
5. **Test with minimal data** first

---

**🎯 Goal**: Have you searching your documents with AI in under 10 minutes!