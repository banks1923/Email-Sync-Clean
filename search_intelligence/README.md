# Search Intelligence Module

Unified search intelligence service that consolidates search, entity extraction, and document intelligence into a single, powerful interface.

## Overview

The Search Intelligence Module provides advanced search capabilities including:
- Query preprocessing and expansion with synonyms
- Intelligent ranking based on entity relevance and recency
- Document similarity analysis using Legal BERT embeddings
- Content clustering with DBSCAN algorithm
- Duplicate detection using hash and semantic methods
- Entity extraction with caching
- Automatic document summarization

## Installation

The module is already integrated into the Email Sync system. No additional installation required.

## Quick Start

```python
from search_intelligence import get_search_intelligence_service

# Initialize the service
intelligence = get_search_intelligence_service()

# Perform smart search
results = intelligence.smart_search_with_preprocessing(
    "contract attorney meeting",
    limit=10,
    use_expansion=True
)
```

## Core Features

### 1. Smart Search with Preprocessing

Automatically expands queries with synonyms and normalizes abbreviations:

```python
# Query: "LLC vs corp re: Q1"
# Expands to: "limited liability company versus corporation regarding first quarter"
results = intelligence.smart_search_with_preprocessing(
    "LLC vs corp re: Q1",
    limit=10,
    use_expansion=True
)
```

**Features:**
- Abbreviation expansion (LLC → limited liability company)
- Synonym matching (attorney → lawyer, counsel)
- Intelligent ranking with entity and recency boosts
- Result enhancement with summaries

### 2. Document Similarity Analysis

Find documents similar to a given document using Legal BERT embeddings:

```python
similar_docs = intelligence.analyze_document_similarity(
    doc_id="email_123",
    limit=10,
    threshold=0.7  # Minimum similarity score
)

# Returns documents with similarity scores
for doc in similar_docs:
    print(f"Document: {doc['id']}, Similarity: {doc['similarity_score']}")
```

### 3. Content Clustering

Group related documents using DBSCAN clustering:

```python
clusters = intelligence.cluster_similar_content(
    threshold=0.7,        # Similarity threshold
    content_type="email", # Optional filter
    limit=100,           # Max documents to cluster
    min_samples=2        # Min docs for a cluster
)

# View clusters
for cluster in clusters:
    print(f"Cluster {cluster['cluster_id']}: {cluster['size']} documents")
    print(f"Sample: {cluster['sample_title']}")
```

### 4. Duplicate Detection

Detect exact and near-duplicate documents:

```python
duplicates = intelligence.detect_duplicates(
    content_type="pdf",
    similarity_threshold=0.95  # For semantic duplicates
)

print(f"Found {len(duplicates['exact_duplicates'])} exact duplicate groups")
print(f"Found {len(duplicates['near_duplicates'])} near duplicate groups")
print(f"Total duplicate rate: {duplicates['duplicate_percentage']:.1f}%")
```

### 5. Entity Extraction with Caching

Extract and cache entities from documents:

```python
entities = intelligence.extract_and_cache_entities(
    doc_id="doc_456",
    force_refresh=False  # Use cache if available
)

# View entities by type
for entity_type, entity_list in entities['entities_by_type'].items():
    print(f"{entity_type}: {[e['text'] for e in entity_list]}")
```

### 6. Automatic Summarization

Generate document summaries with keywords:

```python
summary = intelligence.auto_summarize_document(
    doc_id="doc_789",
    max_sentences=3,
    max_keywords=10,
    cache=True
)

print(f"Summary: {summary['summary']}")
print(f"Keywords: {list(summary['keywords'].keys())}")
```

## Architecture

### Module Structure

```
search_intelligence/
├── __init__.py           # Module exports
├── main.py              # Core SearchIntelligenceService
├── similarity.py        # Document similarity and clustering
├── duplicate_detector.py # Duplicate detection algorithms
└── README.md            # This file
```

### Key Components

1. **SearchIntelligenceService** (main.py)
   - Central service orchestrating all intelligence features
   - Integrates with existing services (search, entity, summarization)
   - Implements caching and query processing

2. **DocumentSimilarityAnalyzer** (similarity.py)
   - Computes document similarity using Legal BERT
   - Provides pairwise similarity matrices
   - Manages vector retrieval and generation

3. **DocumentClusterer** (similarity.py)
   - DBSCAN clustering implementation
   - Groups documents by semantic similarity
   - Stores cluster relationships in database

4. **DuplicateDetector** (duplicate_detector.py)
   - SHA-256 hashing for exact duplicates
   - Cosine similarity for semantic duplicates
   - Multiple removal strategies (keep first/last/newest)

## Configuration

### Query Expansion

The service includes predefined synonyms for legal and business terms:

```python
# Default synonyms (automatically applied)
{
    "contract": ["agreement", "deal", "arrangement"],
    "attorney": ["lawyer", "counsel", "solicitor"],
    "payment": ["transaction", "transfer", "remittance"],
    # ... more synonyms
}
```

### Abbreviations

Common abbreviations are automatically expanded:

```python
# Default abbreviations
{
    "llc": "limited liability company",
    "inc": "incorporated",
    "q1": "first quarter",
    # ... more abbreviations
}
```

### Caching

- **TTL**: 1 hour default for cached relationships
- **Storage**: In-memory cache + database persistence
- **Invalidation**: Automatic based on TTL

## Performance Considerations

### Clustering Performance
- **Small datasets** (<100 docs): <1 second
- **Medium datasets** (100-1000 docs): 2-10 seconds
- **Large datasets** (1000+ docs): Consider batching

### Similarity Computation
- **Single document**: <100ms with cached embeddings
- **Batch processing**: ~1 second per 10 documents
- **Embedding generation**: ~200ms per document

### Duplicate Detection
- **Hash-based**: O(n) time, instant for <10,000 docs
- **Semantic**: O(n²) comparisons, use sampling for large sets

## Advanced Usage

### Custom Query Expansion

```python
# Add custom synonyms
intelligence.synonyms["proprietary"] = ["confidential", "private", "restricted"]

# Add custom abbreviations
intelligence.abbreviations["nda"] = "non-disclosure agreement"
```

### Batch Processing

```python
# Process multiple documents
doc_ids = ["doc1", "doc2", "doc3", "doc4", "doc5"]

# Find all similarities
for doc_id in doc_ids:
    similar = intelligence.analyze_document_similarity(doc_id)
    print(f"{doc_id}: {len(similar)} similar documents")
```

### Integration with Other Services

```python
# Combine with entity search
results = intelligence.smart_search_with_preprocessing("John Doe contract")

# Extract entities from results
for result in results[:5]:
    entities = intelligence.extract_and_cache_entities(result['id'])
    print(f"Document {result['id']} has {entities['total_entities']} entities")
```

## Error Handling

The service includes graceful fallbacks:

```python
try:
    results = intelligence.smart_search_with_preprocessing("query")
except Exception as e:
    # Falls back to basic search if preprocessing fails
    print(f"Search failed: {e}")
```

## Testing

Run tests with:

```bash
python3 -m pytest tests/test_search_intelligence.py -v
```

## API Reference

### SearchIntelligenceService

#### Methods

- `smart_search_with_preprocessing(query, limit=10, use_expansion=True, filters=None)`
- `analyze_document_similarity(doc_id, limit=10, threshold=0.7)`
- `cluster_similar_content(threshold=0.7, content_type=None, limit=100, min_samples=2)`
- `detect_duplicates(doc_ids=None, content_type=None, similarity_threshold=0.95)`
- `extract_and_cache_entities(doc_id, force_refresh=False)`
- `auto_summarize_document(doc_id, text=None, max_sentences=3, max_keywords=10, cache=True)`
- `get_stats()`

### Utility Functions

- `get_search_intelligence_service(collection="emails")` - Get singleton instance
- `cluster_similar_content(...)` - Standalone clustering function
- `detect_all_duplicates(...)` - Standalone duplicate detection

## Dependencies

- **embeddings**: Legal BERT embedding service
- **vector_store**: Qdrant vector storage
- **search**: Base search service
- **entity**: Entity extraction service
- **summarization**: Document summarization engine
- **shared.simple_db**: Database operations
- **sklearn**: DBSCAN clustering and similarity metrics
- **numpy**: Numerical operations

## Limitations

1. **File sizes exceed limits**: main.py (729 lines) exceeds 450 line limit
2. **Requires Qdrant**: Some features degrade without vector store
3. **Memory usage**: Large clustering operations can use significant RAM
4. **Processing time**: Semantic operations scale quadratically

## Future Improvements

- [ ] Split main.py into smaller modules
- [ ] Add more language support for query expansion
- [ ] Implement incremental clustering
- [ ] Add GPU acceleration for embeddings
- [ ] Expand abbreviation dictionary
- [ ] Add custom similarity metrics

## Support

For issues or questions, see the main [Email Sync documentation](../README.md) or [CLAUDE.md](../CLAUDE.md).
