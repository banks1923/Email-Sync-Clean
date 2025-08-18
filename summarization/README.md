# Document Summarization Engine

Automatic document summarization using TF-IDF and TextRank algorithms for all ingested documents.

## Features

### TF-IDF Keyword Extraction
- Extracts top keywords using scikit-learn's TfidfVectorizer
- Configurable n-gram range (1-3 grams by default)
- Automatic stop word removal
- Batch processing support for multiple documents

### TextRank Sentence Extraction
- Graph-based sentence ranking using networkx
- Integration with Legal BERT embeddings for semantic similarity
- Falls back to TF-IDF similarity if embeddings unavailable
- Maintains original sentence order in output

### Unified Document Summarizer
- Orchestrates both TF-IDF and TextRank methods
- Three summary types: 'tfidf', 'textrank', or 'combined'
- Configurable parameters for sentences and keywords
- Singleton pattern for efficient resource usage

## Integration

### PDF Service
- Automatically generates summaries during PDF upload
- Stores in document_summaries table with content_id reference
- 5 sentences and 15 keywords for legal documents
- Non-blocking: PDF upload succeeds even if summarization fails

### Gmail Service
- Processes email summaries during sync
- Adds emails to content table for unified access
- 3 sentences and 10 keywords for emails
- Batch processing for efficiency

## Database Schema

The summarization data is stored in the `document_summaries` table:
- `summary_id`: Unique identifier
- `document_id`: References content(content_id)
- `summary_type`: 'tfidf', 'textrank', or 'combined'
- `summary_text`: Combined summary text
- `tf_idf_keywords`: JSON dictionary of keyword->score pairs
- `textrank_sentences`: JSON array of key sentences

## Usage

```python
from summarization import get_document_summarizer

# Get singleton instance
summarizer = get_document_summarizer()

# Generate summary
summary = summarizer.extract_summary(
    text="Your document text here...",
    max_sentences=3,
    max_keywords=10,
    summary_type="combined"
)

# Access results
print(summary["summary_text"])
print(summary["tf_idf_keywords"])  # Dict of keyword->score
print(summary["textrank_sentences"])  # List of sentences
```

## Testing

```bash
# Unit tests
pytest tests/test_summarization.py -v

# Integration tests
pytest tests/test_summarization_integration.py -v
```

## Performance

- TF-IDF: ~100ms for 10KB document
- TextRank: ~500ms with embeddings, ~200ms without
- Batch processing: ~2 seconds for 10 documents
- Memory usage: <100MB for typical workloads
