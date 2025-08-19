# 🚀 Get Started with Email Sync System

**Welcome to your personal email intelligence system!**

This guide will get you up and running in 10 minutes.

## ⚡ Super Quick Start

```bash
# 1. Run setup wizard (5 minutes)
tools/scripts/setup_wizard

# 2. Interactive first-run guide  
tools/scripts/first_run_guide

# 3. Start searching!
tools/scripts/vsearch search "your query"
```

**That's it!** Your system is ready to use.

---

## 🎯 What You Get

### 📧 **Smart Email Search**
- Find emails instantly: `vsearch search "contract"`
- Filter by date: `vsearch search "meeting" --since "last week"`
- Advanced intelligence: `vsearch intelligence smart-search "legal dispute"`

### 🧠 **AI-Powered Analysis**
- Duplicate detection: `vsearch dedup find`
- Legal case timelines: `vsearch legal timeline "case_name"`
- Document clustering: `vsearch intelligence cluster`

### 🔄 **Automated Processing**
- Sync thousands of emails: `tools/scripts/run_full_system`
- Real-time deduplication
- Automatic summarization

---

## 📋 Detailed Setup (if needed)

### Step 1: Gmail API Setup

**What you need:**
- Google account with Gmail
- 5 minutes to set up API access

**How to:**
1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create new project (or use existing)
3. Enable Gmail API
4. Create OAuth 2.0 credentials
5. Download as `credentials.json`

**Our wizard handles the rest!**

### Step 2: Choose Your Emails

You can sync:
- **All emails** - Complete Gmail backup
- **Specific senders** - Focus on important contacts
- **Smart filters** - Legal, business, personal categories

The setup wizard will ask what you prefer.

### Step 3: Optional Enhancements

**Vector Search (Qdrant)**
- Semantic search capabilities
- "Find emails similar to this"
- Enhanced duplicate detection

**Claude Desktop Integration**
- Specialized legal analysis tools
- Advanced search commands
- Document intelligence

**All optional - system works great without them!**

---

## 🚀 After Setup

### Your First Search
```bash
# Try these examples
vsearch search "maintenance"
vsearch search "contract" --type email
vsearch search "payment" --since "2024-01-01"
```

### System Management
```bash
# Check everything is working
vsearch health

# Full sync and processing
tools/scripts/run_full_system

# System information
vsearch info
```

### Advanced Features
```bash
# Find duplicates
vsearch dedup find --show-groups

# Legal analysis
vsearch legal process "case_name"

# Smart clustering
vsearch intelligence cluster
```

---

## 💡 Tips for Success

### 🎯 **Start Small**
- Sync 50-100 emails first
- Test search functionality
- Expand gradually

### 🔍 **Smart Searching**
- Use specific terms: "contract dispute" not "document"
- Try date filters: `--since "last month"`
- Combine filters: `--type email --tag legal`

### ⚙️ **Keep It Healthy**
- Run `vsearch health` weekly
- Use `make cleanup` monthly
- Monitor disk space

### 🔧 **When Things Go Wrong**
- Check `vsearch health --verbose`
- Look at logs in `logs/` directory
- Re-run setup wizard if needed

---

## 🆘 Quick Troubleshooting

### "Gmail authentication failed"
```bash
# Re-run setup
tools/scripts/setup_wizard

# Check credentials file exists
ls gmail/credentials.json
```

### "No search results"
```bash
# Check if emails synced
vsearch info

# Try broader search
vsearch search "" --limit 10
```

### "System slow"
```bash
# Check health
vsearch health

# Clean up
make cleanup
```

### "Setup wizard fails"
```bash
# Check Python version (need 3.9+)
python3 --version

# Install dependencies
pip install -r requirements.txt
```

---

## 📚 Learn More

- **[USER_GUIDE.md](USER_GUIDE.md)** - Complete user manual
- **[README.md](README.md)** - Technical documentation  
- **[CLAUDE.md](CLAUDE.md)** - Developer guide

### Quick Reference Commands
```bash
# Essential
vsearch search "query"              # Search
tools/scripts/run_full_system       # Full sync
vsearch info                        # System status

# Advanced  
vsearch dedup find                  # Find duplicates
vsearch legal process "case"        # Legal analysis
vsearch intelligence smart-search   # AI search

# Maintenance
vsearch health                      # Health check
make cleanup                        # Clean old data
tools/scripts/setup_wizard          # Re-setup
```

---

## 🎉 You're Ready!

Your email sync system is powerful yet simple:

1. **Run setup once** - `tools/scripts/setup_wizard`
2. **Search anytime** - `vsearch search "anything"`
3. **Sync regularly** - `tools/scripts/run_full_system`

**Happy searching! 🔍✨**

---

*Need help? Run `tools/scripts/first_run_guide` for an interactive tutorial!*