# 🤖 AI-Powered Database Search CLI (`python -m cli`)

## Overview
The `python -m cli` command provides an AI-powered database search interface that uses Legal BERT semantic understanding with SQLite database storage for intelligent document discovery.

Note: This replaces the legacy `tools/scripts/vsearch` command, which now acts as a wrapper to the new modular CLI.

##  How It Works

### Database-Centric Architecture
1. **Semantic Search**: Uses Legal BERT Large model (1024D) to understand query meaning
2. **Database Storage**: All content stored in SQLite database (52+ documents)
3. **Natural Language**: Accepts plain English queries like "water damage issues"
4. **High Accuracy**: Achieves 0.88-0.94 similarity scores for relevant matches

### AI Model Details
- **Model**: `pile-of-law/legalbert-large-1.7M-2` (Legal domain optimized)
- **Dimensions**: 1024-dimensional embeddings
- **Processing**: Local inference, no API costs
- **Performance**: ~2-3 seconds per query including model loading

## Quick Start

```bash
# Check system status
python -m cli admin health

# Search (hybrid default: semantic + keyword)
python -m cli search "water damage problems" --why
python -m cli search "financial planning meeting"
python -m cli search "urgent attention needed" --limit 10

# Alternative entry (wrapper for compatibility)
tools/scripts/vsearch admin health
tools/scripts/vsearch search "water damage"
```

## Commands

### `python -m cli search` - Search Operations
AI-powered search with hybrid retrieval (default) and semantic-only/literal modes.

```bash
# Hybrid search (default)
python -m cli search "password reset issues"           # hybrid default
python -m cli search "property maintenance problems" --limit 10 --why
python -m cli search hybrid "budget planning discussions"

# Literal pattern search (exact matches)
python -m cli search literal "BATES001"
python -m cli search literal "john@example.com" --limit 20

# Legacy wrapper syntax (still supported)
tools/scripts/vsearch search semantic "contract disputes"
```

**Output Format (hybrid):**
```
🔎 Hybrid Search for: 'water damage'
✅ Found 3 results

===  Database Search Results ===

1. [email_message] Re: Water Damage Report
   Semantic score: 0.924
   Why: semantic:0.92; keyword:'water damage'
   Preview: Following up on the water damage incident from last week...

---  Result 2 (Score: 0.889) ---
Title: Property Maintenance - Urgent
From: manager@property.com
Date: 2024-03-10
Preview: Water damage detected in unit 102, immediate attention required...
```

### `python -m cli admin` - System Information & Health
Display comprehensive system information and health checks.

```bash
# Basic health check
python -m cli admin health

# Health check with JSON output
python -m cli admin health --json

# Deep health check (slower, more thorough)
python -m cli admin health --deep

# Aliases
python -m cli admin info      # alias for health
python -m cli admin doctor    # alias for health
```

**Output:**
```
System Health:
==========
Overall: healthy

DB -> healthy
  Path: /Users/.../emails.db
  Content count: 52

EMBEDDINGS -> healthy
  Model: pile-of-law/legalbert-large-1.7M-2 (loaded=true)
  Dimension: 1024

VECTOR -> healthy
  Endpoint: localhost:6333
  Collection: email_vectors (exists=true)
```

### `python -m cli embed` - Embedding Operations
Generate and manage embeddings for content.

```bash
# Build embeddings for all content
python -m cli embed build

# Reindex existing embeddings
python -m cli embed reindex

# Show embedding statistics
python -m cli embed stats
```

### `python -m cli db` - Database Administration
Database maintenance and administration operations.

```bash
# Run database migrations
python -m cli db migrate

# Backup database
python -m cli db backup

# Restore from backup
python -m cli db restore

# Vacuum/optimize database
python -m cli db vacuum
```

### `python -m cli index` - Index Operations
Manage search indexes and content indexing.

```bash
# Add content to search index
python -m cli index add

# Reindex all content
python -m cli index reindex

# Prune stale index entries
python -m cli index prune
```

### `python -m cli view` - Rich Search Results Viewer
Pretty display of search results with optional interactivity.

```bash
# Basic rich view of search results
python -m cli view "water damage" --limit 10

# Interactive viewer with full content preview
python -m cli view "contract terms" --limit 20 --interactive
```

## Advanced Features

### Search Behavior
- **Hybrid default**: Semantic vectors + lightweight keyword lane (tiny legal abbreviation map). Use `--why` to see reasons.
- **Semantic-only mode**: `python -m cli search semantic "query"` for pure embeddings.
- **Literal search**: `python -m cli search literal "BATES-12345"` for exact identifiers/citations.

### STATUS: Performance Metrics
- **Vector Search**: ~0.5–2 seconds per query (depends on model warmup)
- **Keyword Lane**: ~0.1–0.3 seconds per query
- **Batch Processing**: 100+ emails/second
- **Database Operations**: 2000+ records/second

### Reliability
- **Fail-fast**: If the vector store is unavailable, hybrid returns an error (no silent keyword-only fallback). Check `admin health`.
- **Health Monitoring**: Built-in health checks for DB, embeddings, and vector store.

## Troubleshooting

### Common Issues

**Vector Service Not Available:**
```bash
# Check if Qdrant is running
docker ps | grep qdrant

# Start Qdrant if needed
docker run -d -p 6333:6333 qdrant/qdrant
```

**No Results Found:**
```bash
# Check if content is processed and indexed
python -m cli admin health

# Check embedding statistics
python -m cli embed stats

# Reindex content if needed
python -m cli index reindex
```

**Model Loading Slow:**
```bash
# Pre-load model in background
python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('nlpaueb/legal-bert-base-uncased')"
```

## Configuration

### Environment Variables
```bash
# Set default search limit
export VSEARCH_LIMIT=10

# Disable vector search (keyword only)
export VSEARCH_KEYWORD_ONLY=1

# Set model device (cpu/cuda)
export VSEARCH_DEVICE=cuda
```

### Performance Tuning
```bash
# Optimize database
python -m cli db vacuum

# Rebuild embeddings if performance degrades
python -m cli embed reindex

# Use GPU acceleration (if available)
export CUDA_VISIBLE_DEVICES=0
```

## Architecture

### System Components
```
User Query → python -m cli → CLI Router (search/admin/embed/db/index/view)
                                    ↓
                         
                            Search Service   
                            (lib.search)
                         
                                    ↓
                         
                            Database + Vector Store    
                            (SQLite + Qdrant + BERT)   
                         
                                    ↓
                         
                            Result Ranking & Display    
                            
```

### Data Flow
1. User provides natural language query
2. Hybrid default: semantic vectors + lightweight keyword lane (tiny legal abbreviation map)
3. Legal BERT generates query embedding
4. Vector similarity search (Qdrant) + keyword matches (SQLite)
5. Results merged and displayed (optional `--why` explains matches)

## Best Practices

### Search Tips
- Use natural language queries for semantic search
- Use literal search for exact patterns (BATES IDs, email addresses)
- Try the interactive view mode for detailed content exploration
- Check `python -m cli admin health` to verify system status

### Performance Tips
- Use `python -m cli db vacuum` to optimize database performance
- Use GPU acceleration when available (CUDA_VISIBLE_DEVICES=0)
- Monitor system health with `python -m cli admin health --deep`
- Rebuild embeddings if search quality degrades

---

*Updated: 2025-09-04 - Documentation aligned with modular CLI implementation (python -m cli)*
