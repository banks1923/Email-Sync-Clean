# Analog Database Search Interface

Fast, markdown-aware search system for document and email thread files stored in the analog database.

## Overview

The SearchInterface provides comprehensive search capabilities for markdown files with YAML frontmatter metadata:

- **Full-text search** using ripgrep for blazing-fast content search
- **Metadata search** using python-frontmatter for structured query filtering  
- **Hybrid search** combining content, metadata, and semantic vector search
- **Performance optimization** with LRU caching and search statistics tracking
- **Integration** with existing search_intelligence services

## Quick Start

```python
from analog_db import SearchInterface

# Initialize search interface
search = SearchInterface()

# Content search
results = search.search_content("contract payment terms")

# Metadata search
results = search.search_metadata({
    "title": "Contract Review",
    "doc_type": "email",
    "tags": ["legal", "contract"]
})

# Hybrid search (combines everything)
results = search.hybrid_search(
    query="payment terms",
    metadata_filters={"doc_type": "email"},
    use_vector=True
)
```

## CLI Usage

The analog database search is integrated into the `vsearch` CLI:

### Basic Search Commands

```bash
# Content and metadata search
tools/scripts/vsearch analog search "contract terms" --limit 10

# Metadata-only search
tools/scripts/vsearch analog meta --title "Contract" --doc-type email --limit 5

# Hybrid search with metadata filters
tools/scripts/vsearch analog hybrid "payment terms" --doc-type email --limit 15

# Database statistics
tools/scripts/vsearch analog stats
```

### Advanced Search Options

```bash
# Content-only search
tools/scripts/vsearch analog search "contract" --content-only

# Regex search
tools/scripts/vsearch analog search "payment.*terms" --regex

# Case-sensitive search
tools/scripts/vsearch analog search "ABC Corp" --case-sensitive

# Disable semantic search
tools/scripts/vsearch analog search "contract" --no-vector

# JSON output
tools/scripts/vsearch analog search "contract" --json
```

### Metadata Filter Options

```bash
# Filter by document properties
tools/scripts/vsearch analog meta --title "Contract" --doc-type email

# Filter by sender (for emails)
tools/scripts/vsearch analog meta --sender "legal@example.com"

# Filter by tags
tools/scripts/vsearch analog meta --tag legal --tag contract --tag-logic AND

# Filter by date range
tools/scripts/vsearch analog meta --since "2025-01-01" --until "2025-12-31"
```

## API Reference

### SearchInterface Class

#### Initialization

```python
SearchInterface(base_path: Optional[Path] = None)
```

**Parameters:**
- `base_path`: Base directory for analog database (defaults to current directory)

#### Methods

##### Content Search

```python
search_content(
    query: str,
    path: Optional[Path] = None,
    limit: int = 20,
    regex: bool = False,
    case_sensitive: bool = False
) -> List[Dict[str, Any]]
```

Fast full-text search using ripgrep.

**Parameters:**
- `query`: Search query string
- `path`: Specific path to search (defaults to all analog_db)  
- `limit`: Maximum number of results (default: 20)
- `regex`: Treat query as regex pattern (default: False)
- `case_sensitive`: Enable case-sensitive search (default: False)

**Returns:** List of results with file paths, line numbers, and matched content.

##### Metadata Search

```python
search_metadata(
    filters: Dict[str, Any],
    limit: int = 20
) -> List[Dict[str, Any]]
```

Search by YAML frontmatter metadata fields.

**Filter Options:**
- `title`: Title contains string
- `doc_type`: Document type (email, document, etc.)
- `tags`: List of tags to match
- `tag_logic`: 'AND' or 'OR' for tag matching (default: 'OR')
- `since`: Date filter (ISO format or relative like '2 days ago')
- `until`: Date filter (ISO format or relative)
- `sender`: Email sender filter

**Returns:** List of matching files with metadata and content previews.

##### Hybrid Search

```python
hybrid_search(
    query: str,
    metadata_filters: Optional[Dict[str, Any]] = None,
    limit: int = 20,
    use_vector: bool = True
) -> List[Dict[str, Any]]
```

Combined search with content, metadata, and optional semantic vector search.

**Parameters:**
- `query`: Search query
- `metadata_filters`: Optional metadata filters (same format as search_metadata)
- `limit`: Maximum results (default: 20)
- `use_vector`: Include semantic search results (default: True)

**Returns:** Ranked list of combined search results with relevance scores.

#### Performance Methods

```python
get_search_stats() -> Dict[str, Any]
```

Get search performance statistics including total searches, average time, and cache hits.

```python
clear_cache() -> None  
```

Clear metadata and result caches.

## File Structure

```
analog_db/
├── __init__.py              # Package initialization
├── search_interface.py      # Main SearchInterface class
└── README.md               # This documentation

analog_db/documents/         # Document markdown files
├── 2025-08-17_contract.md
├── 2025-08-16_meeting.md
└── ...

analog_db/email_threads/     # Email thread markdown files
├── thread_001.md
├── thread_002.md  
└── ...
```

## Markdown File Format

Files should have YAML frontmatter with metadata:

```markdown
---
title: "Contract Review - ABC Corp Agreement"
doc_type: email
date_created: 2025-08-17 20:31:02
sender: legal@example.com
recipient: review@example.com
tags: ["contract", "legal", "abc_corp"]
---

# Contract Review

Document content goes here...
```

## Performance Characteristics

- **Search Speed**: Typically <1 second for most queries
- **Caching**: LRU cache for metadata parsing and search results
- **Scalability**: Optimized for thousands of markdown files
- **Memory Usage**: Efficient with lazy loading and streaming

### Performance Tips

1. **Use metadata filters** to narrow down search scope
2. **Enable caching** by reusing SearchInterface instances  
3. **Limit results** with the `limit` parameter for faster responses
4. **Use content-only search** when metadata filtering isn't needed
5. **Install ripgrep** for fastest full-text search performance

## Integration with Existing Services

The SearchInterface integrates seamlessly with existing Email Sync services:

- **search_intelligence**: Query expansion and smart preprocessing
- **utilities/embeddings**: Legal BERT embeddings for semantic search
- **utilities/vector_store**: Qdrant vector database when available
- **shared/simple_db**: Fallback database search capabilities

## Error Handling

The SearchInterface handles various error conditions gracefully:

- **Missing ripgrep**: Falls back to Python-based search
- **Invalid metadata**: Skips files with malformed frontmatter  
- **Network issues**: Vector search degrades gracefully
- **File system errors**: Individual file failures don't break batch operations

## Testing

Run tests with pytest:

```bash
# Run all analog database tests
pytest tests/analog_db/

# Run with coverage
pytest tests/analog_db/ --cov=analog_db --cov-report=html

# Run performance tests  
pytest tests/analog_db/ -m performance
```

## Examples

### Basic Content Search

```python
from analog_db import SearchInterface

search = SearchInterface()

# Find all files mentioning "contract terms"
results = search.search_content("contract terms", limit=10)

for result in results:
    print(f"Found in: {result['file_path']}")
    print(f"Content: {result['matched_content']}")
    print(f"Line: {result['line_number']}")
    print("---")
```

### Advanced Metadata Filtering

```python
# Find legal emails from specific sender about contracts
results = search.search_metadata({
    "doc_type": "email",
    "sender": "legal@example.com", 
    "tags": ["contract", "legal"],
    "tag_logic": "AND"
})

for result in results:
    metadata = result['metadata']
    print(f"Title: {metadata['title']}")
    print(f"Date: {metadata.get('date_created', 'Unknown')}")
    print(f"Tags: {metadata.get('tags', [])}")
    print("---")
```

### Hybrid Search with Ranking

```python
# Smart search combining multiple approaches
results = search.hybrid_search(
    query="payment schedule contract",
    metadata_filters={
        "doc_type": "email",
        "tags": ["contract"]
    },
    limit=20,
    use_vector=True
)

# Results are ranked by relevance score
for i, result in enumerate(results, 1):
    print(f"{i}. {result['metadata']['title']} (Score: {result['score']:.2f})")
    print(f"   Source: {result.get('source', 'unknown')}")
    print(f"   File: {Path(result['file_path']).name}")
    print()
```

## Troubleshooting

### Common Issues

**No search results found:**
- Check that markdown files exist in analog_db/documents/ or analog_db/email_threads/
- Verify files have proper YAML frontmatter
- Try broader search terms

**Slow search performance:**
- Install ripgrep for faster full-text search: `brew install ripgrep`
- Use metadata filters to narrow search scope
- Enable result limiting with `limit` parameter

**Import errors:**
- Ensure python-frontmatter is installed: `pip install python-frontmatter`
- Check that analog_db module is in Python path

**Cache issues:**
- Clear cache manually: `search.clear_cache()`
- Restart SearchInterface instance to reset caches

### Debug Mode

Enable debug logging to troubleshoot issues:

```python
import logging
logging.getLogger('analog_db').setLevel(logging.DEBUG)

# Or with loguru
from loguru import logger  
logger.add(sys.stdout, level="DEBUG")
```