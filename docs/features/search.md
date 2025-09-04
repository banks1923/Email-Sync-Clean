# Search API Documentation

## Overview

The search system provides semantic-only search using Legal BERT 1024-dimensional embeddings with Qdrant vector store. This is a pure semantic search architecture with no keyword search, no FTS, and no hybrid modes.

## Core API

### `search(query, limit=10, filters=None)`

Semantic vector search using Legal BERT embeddings.

```python
from search_intelligence import search

# Basic search
results = search("lease termination clause")

# Search with filters
results = search(
    "contract dispute",
    limit=5,
    filters={
        "source_type": "email_message",
        "date_range": {"start": "2024-01-01"}
    }
)
```

**Parameters:**
- `query` (str): Search query text
- `limit` (int): Maximum results to return (default: 10)
- `filters` (dict): Optional filters:
  - `source_type`: Filter by document type
  - `date_range`: Dict with 'start' and/or 'end' dates
  - `party`: Filter by party name
  - `tags`: Filter by tags (string or list)

**Returns:**
List of documents with semantic similarity scores.

### `find_literal(pattern, limit=50, fields=None)`

Find documents containing exact patterns. Use this for specific identifiers that need exact matching.

```python
from search_intelligence import find_literal

# Find BATES numbers
docs = find_literal("BATES-00123")

# Find section codes
docs = find_literal("§1983")

# Find email addresses
docs = find_literal("john.doe@example.com")
```

**Parameters:**
- `pattern` (str): Exact pattern to search for (SQL LIKE wildcards supported)
- `limit` (int): Maximum results (default: 50)
- `fields` (list): Fields to search in (default: ["body", "metadata"])

**Returns:**
List of documents containing the exact pattern.

## Configuration

The system is locked to the following configuration:
- **Collection**: `vectors_v2`
- **Embedding Model**: Legal BERT (pile-of-law/legalbert-large-1.7M-2)
- **Dimensions**: 1024
- **Distance Metric**: Cosine similarity

## Usage Examples

### CLI Usage

```bash
# Semantic search
tools/scripts/vsearch search "lease agreement" --limit 5

# Find exact patterns (coming soon in CLI)
tools/scripts/vsearch find-literal "BATES-00123"
```

### Python Usage

```python
from search_intelligence import search, find_literal, vector_store_available

# Check if vector store is available
if vector_store_available():
    # Semantic search for legal concepts
    results = search("breach of contract damages")
    
    for result in results:
        print(f"Title: {result['title']}")
        print(f"Score: {result['semantic_score']:.3f}")
        print(f"Content: {result['content'][:200]}...")
    
    # Find specific document by BATES number
    bates_docs = find_literal("BATES-2024-001")
    if bates_docs:
        print(f"Found document: {bates_docs[0]['title']}")
```

### MCP Server Usage

The MCP server exposes two tools:

1. **search_smart** - Semantic search
2. **find_literal** - Exact pattern matching

## Migration Guide

### From Old API

```python
# OLD - Don't use
from search_intelligence import get_search_intelligence_service
service = get_search_intelligence_service()
results = service.search(query, limit=10)

# NEW - Use this
from search_intelligence import search
results = search(query, limit=10)
```

### Deprecated Features

The following are deprecated and will be removed:
- `SearchIntelligenceService` class
- `get_search_intelligence_service()` function
- `semantic_search()` function (use `search()` instead)
- Query expansion (irrelevant for semantic embeddings)
- Mode selection (always semantic now)

## Performance Notes

- Semantic search requires embeddings to be generated for all content
- Initial embedding generation may take time for large datasets
- Once embedded, search is fast (typically < 100ms)
- No fallback to keyword search - vector store must be available

## Troubleshooting

### Vector Store Not Available

```bash
# Check if Qdrant is running
curl http://localhost:6333/collections

# Start Qdrant if needed
docker run -p 6333:6333 qdrant/qdrant
```

### No Results Found

1. Ensure content has been embedded:
```bash
tools/scripts/vsearch ingest --emails
```

2. Check vector store has data:
```python
from utilities.vector_store import get_vector_store
store = get_vector_store("vectors_v2")
print(f"Vectors in store: {store.count()}")
```

### Pattern Not Found

For exact patterns, ensure you're searching in the right fields:
```python
# Search in specific fields
results = find_literal(
    "BATES-123",
    fields=["body", "title", "metadata"]
)
```