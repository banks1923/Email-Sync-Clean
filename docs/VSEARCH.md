# 🤖 AI-Powered Database Search CLI (`scripts/vsearch`)

## Overview
The `scripts/vsearch` command provides an AI-powered database search interface that uses Legal BERT semantic understanding with SQLite database storage for intelligent document discovery.

## 🧠 How It Works

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
scripts/vsearch info

# Process emails for AI search (required first time)
scripts/vsearch process -n 50

# Search with natural language
scripts/vsearch search "water damage problems"
scripts/vsearch search "financial planning meeting"
scripts/vsearch search "urgent attention needed"
```

## Commands

### `scripts/vsearch search "query"`
AI-powered database search with semantic similarity and keyword matching.

```bash
# Natural language queries
scripts/vsearch search "password reset issues"
scripts/vsearch search "property maintenance problems"
scripts/vsearch search "budget planning discussions"

# With custom result limit
scripts/vsearch search "server errors" --limit 10

# With advanced filters
scripts/vsearch search "contract" --since "last month" --until "today"
scripts/vsearch search "meeting" --type email --type pdf
scripts/vsearch search "legal" --tag urgent --tag important --tag-logic AND
```

**Output Format:**
```
🤖 AI-Powered Search for: 'water damage'
🔍 Running database search...
✅ Found 3 matches

=== 🔍 Database Search Results ===

--- 📧 Result 1 (Score: 0.924) ---
Title: Re: Water Damage Report
From: john@example.com
Date: 2024-03-15
Preview: Following up on the water damage incident from last week...

--- 📧 Result 2 (Score: 0.889) ---
Title: Property Maintenance - Urgent
From: manager@property.com
Date: 2024-03-10
Preview: Water damage detected in unit 102, immediate attention required...
```

### `scripts/vsearch info`
Display comprehensive system information.

```bash
scripts/vsearch info
```

**Output:**
```
📊 System Information
====================
📁 Database Statistics:
  Total emails: 45
  Total PDFs: 5
  Total transcripts: 2
  Total content: 52

🧠 Vector Service:
  Status: ✅ Connected
  Collection: email_vectors
  Dimensions: 1024

🤖 Embedding Service:
  Model: pile-of-law/legalbert-large-1.7M-2
  Dimensions: 1024
  Device: cuda (GPU acceleration)
```

### `scripts/vsearch process`
Process unembedded content for semantic search.

```bash
# Process all new content
scripts/vsearch process

# Process specific content type
scripts/vsearch process --type email -n 100
scripts/vsearch process --type pdf -n 20
```

### `scripts/vsearch embed`
Generate embeddings for specific content types.

```bash
# Generate embeddings for emails
scripts/vsearch embed email -n 50

# Generate embeddings for PDFs
scripts/vsearch embed pdf -n 10
```

### `scripts/vsearch upload`
Upload and process PDF documents.

```bash
# Upload single PDF
scripts/vsearch upload document.pdf

# Upload directory of PDFs
scripts/vsearch upload /path/to/pdfs/
```

### `scripts/vsearch transcribe`
Transcribe audio/video files.

```bash
# Transcribe audio file
scripts/vsearch transcribe meeting.mp4

# Transcribe with metadata
scripts/vsearch transcribe interview.wav --metadata '{"speaker": "John Doe"}'
```

### `scripts/vsearch timeline`
View chronological timeline of content.

```bash
# View recent timeline
scripts/vsearch timeline -n 20

# Filter by content type
scripts/vsearch timeline --types email pdf -n 50

# Date range filtering
scripts/vsearch timeline --start 2024-01-01 --end 2024-03-31
```

### `scripts/vsearch note`
Create searchable notes.

```bash
# Create a note
scripts/vsearch note "Meeting Notes" "Discussion about Q1 goals" --tags business quarterly

# Create note with metadata
scripts/vsearch note "Legal Review" "Contract review findings" --tags legal contract
```

## Advanced Features

### 🔍 Search Intelligence
- **Query Expansion**: Automatically expands abbreviations (LLC → Limited Liability Company)
- **Synonym Matching**: Finds related terms for better coverage
- **Entity Recognition**: Identifies and weights important names/organizations
- **Duplicate Detection**: Automatically removes duplicate results

### 📊 Performance Metrics
- **Vector Search**: ~0.5-2 seconds per query
- **Keyword Fallback**: ~0.1-0.3 seconds per query
- **Batch Processing**: 100+ emails/second
- **Database Operations**: 2000+ records/second

### 🛡️ Reliability Features
- **Automatic Fallback**: Switches to keyword search if vector service unavailable
- **Error Recovery**: Graceful handling of service failures
- **Cache Management**: Automatic caching for frequently accessed content
- **Health Monitoring**: Built-in health checks for all services

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
# Check if content is processed
scripts/vsearch info

# Process content if needed
scripts/vsearch process
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
# Increase batch size for processing
scripts/vsearch process --batch-size 100

# Use GPU acceleration (if available)
export CUDA_VISIBLE_DEVICES=0
```

## Architecture

### System Components
```
User Query → vsearch CLI → Search Intelligence Service
                                    ↓
                         ┌─────────────────────┐
                         │   Database Search   │
                         │   (SQLite + BERT)   │
                         └─────────────────────┘
                                    ↓
                         ┌─────────────────────┐
                         │   Result Ranking    │
                         │   & Deduplication   │
                         └─────────────────────┘
```

### Data Flow
1. User provides natural language query
2. Query preprocessed with expansion and synonyms
3. Legal BERT generates query embedding
4. Vector similarity search in database
5. Results ranked by relevance and recency
6. Duplicates removed, formatted output

## Best Practices

### Search Tips
- Use natural language queries for best results
- Include context words for better matching
- Use filters to narrow results
- Check `info` command to verify content is indexed

### Performance Tips
- Process content in batches for efficiency
- Use GPU acceleration when available
- Enable caching for frequent queries
- Monitor system health regularly

---

*Updated: 2025-08-19 - Analog system removed, database-only operation*