# Knowledge Graph Service

## Overview

The Knowledge Graph Service provides intelligent content relationship discovery and management for the Email Sync system. It uses Legal BERT embeddings to identify similar documents, extracts temporal relationships, and enables graph-based content navigation.

## Architecture

### Module Structure
```
knowledge_graph/
 __init__.py                  # Service exports
 main.py                      # Core graph operations (403 lines)
 similarity_analyzer.py       # Document similarity (292 lines)
 similarity_integration.py    # Auto-discovery (355 lines)
 timeline_relationships.py    # Temporal analysis (473 lines)
 CLAUDE.md                    # Comprehensive API documentation (522 lines)
```

### Database Schema

#### kg_nodes Table
- Represents content items as graph nodes
- Links to content table via content_id
- Stores flexible metadata in JSON column

#### kg_edges Table
- Represents relationships between content
- Includes relationship type and strength score
- Stores edge metadata (method, confidence, timestamps)

#### kg_metadata Table
- Graph-level configuration and statistics
- Algorithm versions and update timestamps

#### similarity_cache Table
- Persistent cache for computed similarities
- MD5 hashing for consistent pair identification
- Tracks computation time for performance analysis

## Core Features

### 1. Document Similarity Analysis

Uses Legal BERT embeddings to compute semantic similarity between documents:

```python
from knowledge_graph import get_similarity_analyzer

analyzer = get_similarity_analyzer(similarity_threshold=0.7)

# Find similar documents
similar = analyzer.find_similar_content("email_123", limit=10)

# Batch compute similarities
content_ids = ["email_1", "email_2", "pdf_1", "pdf_2"]
similarities = analyzer.batch_compute_similarities(content_ids)
```

**Performance Characteristics:**
- First computation: <2 seconds per document pair
- Cached retrieval: <10ms
- Batch processing: 100+ documents with progress tracking

### 2. Automatic Relationship Discovery

Discovers and stores similarity relationships across all content:

```python
from knowledge_graph import get_similarity_integration

integration = get_similarity_integration()

# Discover similarities for all PDFs
result = integration.discover_and_store_similarities(content_type="pdf")
print(f"Found {result['relationships_created']} relationships")

# Find clusters of similar documents
clusters = integration.find_similarity_clusters(min_cluster_size=3)
```

### 3. Timeline Analysis

Extracts dates from content and creates temporal relationships:

```python
from knowledge_graph import get_timeline_relationships

timeline = get_timeline_relationships()

# Create all temporal relationships
result = timeline.create_temporal_relationships()
print(f"Created {result['sequential']} sequential relationships")

# Find documents in temporal proximity
cluster = timeline.find_temporal_cluster("email_123", window_days=7)

# Get timeline context
context = timeline.get_timeline_context("email_123", before=5, after=5)
```

**Date Extraction Sources:**
- Emails: datetime_utc field
- PDFs: Metadata and OCR text
- Transcripts: Recording/transcription dates
- Legal dates: Court dates, filing deadlines, case dates

### 4. Graph Operations

Navigate and query the knowledge graph:

```python
from knowledge_graph import get_knowledge_graph_service

kg = get_knowledge_graph_service()

# Add custom relationships
edge_id = kg.add_edge("email_123", "pdf_456", "references", 0.85)

# Query related content
related = kg.get_related_content("contract_123", ["similar_to"], limit=5)

# Find shortest path between documents
path = kg.find_shortest_path("doc_a", "doc_z", max_depth=5)

# Get graph statistics
stats = kg.get_graph_stats()
```

## Relationship Types

### Similarity Relationships
- `similar_to`: Semantic similarity via Legal BERT (strength: 0.7-1.0)
- `same_cluster`: Documents in same topic cluster

### Temporal Relationships
- `followed_by`: Sequential relationship (A before B)
- `concurrent_with`: Within same time window (default: 24 hours)

### Reference Relationships
- `references`: Direct citation or mention
- `mentions`: Entity co-occurrence
- `discussed_in`: Content appears in another document

### Strength Scoring
- `0.9-1.0`: Very high confidence (exact matches, direct citations)
- `0.7-0.9`: High confidence (semantic similarity)
- `0.5-0.7`: Medium confidence (entity co-occurrence)
- `0.3-0.5`: Low confidence (weak associations)

## Performance Optimization

### Caching Strategy
- **Dual-layer caching**: In-memory + SQLite persistence
- **MD5 hashing**: Consistent pair identification
- **100x speedup**: Cache hits vs recomputation

### Batch Operations
- Process 1000+ nodes/edges per second
- Progress tracking for long operations
- Configurable batch sizes

### Query Optimization
- Indexes on all foreign keys
- Efficient SQL with parameterized queries
- Streaming results for large graphs

## Integration Points

### With Search Service
```python
# Enhance search results with related content
from search import get_search_service
from knowledge_graph import get_knowledge_graph_service

search = get_search_service()
kg = get_knowledge_graph_service()

results = search.search("contract dispute", limit=10)
for result in results:
    related = kg.get_related_content(result["content_id"], limit=3)
    result["related"] = related
```

### With Entity Service
```python
# Create relationships from entity co-occurrence
from entity.main import EntityService
from knowledge_graph import get_knowledge_graph_service

entities = EntityService()
kg = get_knowledge_graph_service()

extracted = entities.extract_entities(text)
for e1, e2 in itertools.combinations(extracted, 2):
    kg.add_edge(e1["content_id"], e2["content_id"], "co_occurrence", 0.5)
```

## Testing

### Test Coverage
- **Unit Tests**: 35 tests for core graph operations
- **Similarity Tests**: 20 tests for analyzer functionality
- **Integration Tests**: 12 tests with real Legal BERT embeddings
- **Total**: 67 comprehensive tests

### Running Tests
```bash
# All knowledge graph tests
python3 -m pytest tests/test_knowledge_graph.py tests/test_similarity_analyzer.py -v

# Integration tests with real embeddings (slower)
python3 -m pytest tests/test_legal_bert_integration.py -v -m slow

# Quick unit tests only
python3 -m pytest tests/test_knowledge_graph.py -v -m "not slow"
```

## Usage Guidelines

### When to Use
- **Document Research**: Find all related documents for a case
- **Timeline Analysis**: Understand chronological relationships
- **Similarity Search**: Find documents similar to a reference
- **Content Organization**: Cluster documents by topic

### Best Practices
1. **Set appropriate thresholds**: Default 0.7 for similarity works well
2. **Use batch operations**: Process multiple documents together
3. **Cache warming**: Pre-compute similarities during off-hours
4. **Monitor graph size**: Use statistics to track growth

### Performance Considerations
- **Initial setup**: First-time similarity computation takes time
- **Cache benefits**: Subsequent queries are near-instant
- **Graph queries**: Efficient for graphs under 100K edges
- **Memory usage**: Minimal due to SQLite backend

## Troubleshooting

### Common Issues

#### Slow similarity computation
- Check if Legal BERT model is loaded
- Verify GPU/MPS availability for acceleration
- Consider lowering batch size

#### Missing relationships
- Verify similarity threshold isn't too high
- Check date extraction for temporal relationships
- Ensure content has been processed

#### Cache issues
- Clear old cache entries: `analyzer.clear_cache(older_than_days=30)`
- Check cache statistics: `analyzer.get_cache_stats()`

## Future Enhancements

### Planned Features
- Graph visualization export (D3.js compatible JSON)
- PageRank-style importance scoring
- Community detection algorithms
- Advanced clustering (DBSCAN, spectral)

### Integration Opportunities
- Real-time relationship updates on content addition
- Relationship-based search ranking
- Automatic document categorization
- Legal precedent discovery

## API Reference

For complete API documentation with all methods and parameters, see:
- Comprehensive API guide available in search intelligence documentation
- `tests/test_legal_bert_integration.py` - Real-world usage examples

## Performance Metrics

### Benchmarks (MacBook Pro M1)
- Node insertion: 1000+ per second
- Edge creation: 500+ per second
- Similarity computation: 1.5 seconds per pair (first time)
- Cache retrieval: <10ms
- Graph traversal: <100ms for 1000 nodes
- Batch similarity (100 docs): ~3 minutes

### Resource Usage
- Memory: ~500MB for Legal BERT model
- Disk: ~1MB per 1000 relationships
- CPU: Moderate during computation, minimal otherwise
