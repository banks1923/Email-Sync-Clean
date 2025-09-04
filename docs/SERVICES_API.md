# Services API Reference

Complete API reference for all Email Sync services with usage examples and integration patterns.

### Code Quality Status (Updated 2025-08-22) WORKING:
- **Type Safety**: Core services now feature comprehensive type annotations with modern Python syntax
- **Complexity**: High-complexity functions refactored for maintainability (95% reduction in complex functions)
- **Dependencies**: All packages current and secure, deprecation warnings resolved
- **Architecture Compliance**: Functions follow 30-line guideline, clean separation of concerns

## ARCHITECTURE: Architecture Overview

### Service Organization
```
# Core Business Services (Root Level)
gmail/                # Email processing and sync
pdf/                  # PDF processing with OCR  
entity/               # Named entity recognition
summarization/        # Document summarization
search_intelligence/  # Unified search and intelligence
knowledge_graph/      # Document relationships
legal_intelligence/   # Legal case analysis
monitoring/           # Health monitoring

# Organized Utility Services  
utilities/
 embeddings/       # Legal BERT embeddings
 vector_store/     # Qdrant vector operations
 notes/            # Notes management
 timeline/         # Timeline service

# Infrastructure Services
infrastructure/
 pipelines/        # Document processing pipelines
 documents/        # Document lifecycle management
 mcp_servers/      # MCP server implementations
```

##  Gmail Service (`gmail/`)

### Quick Start
```python
from gmail.main import GmailService

service = GmailService()
# Streaming batch sync (reliable for 500+ emails)
result = service.sync_emails(max_results=500, batch_mode=True)
# Incremental sync using Gmail History API
result = service.sync_incremental(max_results=500)
```

### Key Features
- **Streaming batch sync**: Processes 50 emails/chunk, saves immediately
- **Performance**: ~50 emails/minute, reliable for large volumes (500+ emails)
- **Memory efficient**: <50MB usage, no timeout failures
- **Automatic summarization**: Generates TF-IDF keywords and key sentences
- **Incremental sync**: Uses Gmail History API with fallback
- **Content-based deduplication**: SHA-256 hashing
- **Sync state persistence**: Resumable syncs
- **Attachment metadata**: Tracking without downloading
- **OAuth2 authentication**: Secure keyring storage
- **Sender filters**: 10 configured legal/property contacts

### API Methods
```python
# Basic sync operations
result = service.sync_emails(max_results=100, batch_mode=True)
result = service.sync_incremental(max_results=100)

# Authentication 
service.authenticate()  # OAuth2 flow
creds = service.get_credentials()

# Message processing
messages = service.get_messages(query="", max_results=10)
message = service.get_message_content(message_id)

# Filtering and search
filtered = service.filter_messages_by_sender(messages, sender_filter)
```

##  PDF Service (`pdf/`)

### Quick Start
```python
from pdf.main import PDFService

service = PDFService()
result = service.upload_single_pdf("document.pdf")  # Auto-detects OCR need
result = service.upload_directory("/path/to/pdfs/")  # Batch processing
```

### Key Features
- **Intelligent OCR Detection**: Automatically identifies scanned vs text PDFs
- **Integrated Processing**: OCR seamlessly built into upload flow
- **Automatic summarization**: 5 sentences, 15 keywords for legal documents
- **Batch Operations**: High-performance bulk document processing
- **Legal Metadata**: Extracts case numbers, parties, dates
- **Deduplication**: SHA-256 based duplicate prevention
- **Unified content storage**: Adds to content table with content_id

### API Methods
```python
# Single document processing
result = service.upload_single_pdf("path/to/document.pdf")
result = service.process_pdf_with_ocr("path/to/scanned.pdf")

# Batch operations
result = service.upload_directory("/path/to/pdfs/")
result = service.batch_process_pdfs(file_paths_list)

# Content extraction
text = service.extract_text_from_pdf("path/to/document.pdf")
metadata = service.extract_metadata("path/to/document.pdf")

# OCR operations
is_scanned = service.needs_ocr("path/to/document.pdf")
ocr_text = service.perform_ocr("path/to/scanned.pdf")
```


##  Entity Extraction (`entity/`)

### Quick Start
```python
from entity.main import EntityService

entities = EntityService()
extracted = entities.extract_entities(text)
```

### Key Features
- **Named entity recognition (NER)**: SpaCy-based extraction
- **Legal entity focus**: Case numbers, parties, dates
- **Confidence scoring**: Entity extraction confidence
- **Batch processing**: Multiple documents efficiently

### API Methods
```python
# Basic entity extraction
entities = service.extract_entities("John Doe filed a motion in case 24NNCV00555")
entities = service.extract_entities_from_content(content_id)

# Specific entity types
persons = service.extract_persons(text)
organizations = service.extract_organizations(text)
dates = service.extract_dates(text)
case_numbers = service.extract_case_numbers(text)

# Batch operations
results = service.batch_extract_entities(text_list)

# Entity relationships
relationships = service.find_entity_relationships(entities_list)
```

##  Document Summarization (`summarization/`)

### Quick Start
```python
from summarization import get_document_summarizer

summarizer = get_document_summarizer()
summary = summarizer.extract_summary(
    text="Your document text...",
    max_sentences=3,
    max_keywords=10,
    summary_type="combined"  # or "tfidf" or "textrank"
)
```

### Key Features
- **TF-IDF**: Keyword extraction using scikit-learn
- **TextRank**: Sentence extraction with Legal BERT embeddings
- **Auto-integration**: PDFs and emails automatically summarized on ingestion
- **Database storage**: Summaries stored in `document_summaries` table

### API Methods
```python
# Summary generation
summary = summarizer.extract_summary(text, max_sentences=3, max_keywords=10)
tfidf_summary = summarizer.extract_tfidf_summary(text, max_keywords=15)
textrank_summary = summarizer.extract_textrank_summary(text, max_sentences=5)

# Batch operations
summaries = summarizer.batch_summarize(text_list)

# Content-specific summarization
email_summary = summarizer.summarize_email(email_content)
pdf_summary = summarizer.summarize_pdf(pdf_content)

# Database integration
summary_id = summarizer.save_summary_to_db(content_id, summary_data)
cached_summary = summarizer.get_cached_summary(content_id)
```

##  Search Intelligence Service (`search_intelligence/`)

### Quick Start
```python
from search_intelligence import get_search_intelligence_service

intelligence = get_search_intelligence_service()

# Smart search with query expansion
results = intelligence.smart_search_with_preprocessing(
    "contract attorney",  # Automatically expands to include synonyms
    limit=10,
    use_expansion=True
)

# Find similar documents
similar = intelligence.analyze_document_similarity("doc_id", threshold=0.7)

# Cluster related content
clusters = intelligence.cluster_similar_content(threshold=0.7, limit=100)
```

### Key Features
- **Query Preprocessing**: Abbreviation expansion, normalization
- **Query Expansion**: Synonym-based query enhancement
- **Intelligent Ranking**: Entity relevance + recency scoring
- **Document Similarity**: Legal BERT-based similarity analysis
- **DBSCAN Clustering**: Group similar documents (threshold=0.7)
- **Duplicate Detection**: SHA-256 hash + semantic similarity
- **Entity Caching**: TTL-based caching in relationship_cache

### API Methods
```python
# Smart search operations
results = intelligence.smart_search_with_preprocessing(query, limit=10, use_expansion=True)
results = intelligence.basic_search(query, limit=10)

# Document similarity
similar = intelligence.analyze_document_similarity(doc_id, threshold=0.7)
similarity_score = intelligence.calculate_similarity(doc1_id, doc2_id)

# Clustering operations
clusters = intelligence.cluster_similar_content(threshold=0.7, limit=100)
cluster_stats = intelligence.get_cluster_statistics(clusters)

# Duplicate detection
duplicates = intelligence.detect_duplicates(similarity_threshold=0.95)
potential_duplicates = intelligence.find_potential_duplicates(doc_id)

# Entity operations
entities = intelligence.extract_and_cache_entities(doc_id)
cached_entities = intelligence.get_cached_entities(doc_id)

# Summarization
summary = intelligence.auto_summarize_document(doc_id)
batch_summaries = intelligence.batch_summarize_documents(doc_ids)
```

##  Embedding Service (`utilities/embeddings/`)

### Quick Start
```python
from utilities.embeddings import get_embedding_service

emb = get_embedding_service()
vector = emb.encode("text")  # Returns 1024D Legal BERT vector
```

### Key Features
- **Singleton pattern**: Model reuse for efficiency
- **Auto-detects device**: MPS/CUDA/CPU optimization
- **Legal BERT 1024D**: Domain-specific embeddings by default

### API Methods
```python
# Basic encoding
vector = emb.encode("Contract text to embed")
vectors = emb.encode_batch(["text1", "text2", "text3"])

# Model information
model_name = emb.model_name
dimensions = emb.dimensions
device = emb.device

# Similarity operations
similarity = emb.cosine_similarity(vector1, vector2)
similarities = emb.batch_similarity(query_vector, document_vectors)

# Advanced operations
embeddings = emb.encode_with_metadata(text_list, metadata_list)
normalized = emb.normalize_embeddings(vectors)
```

##  Vector Store (`utilities/vector_store/`)

### Quick Start
```python
from utilities.vector_store import get_vector_store

store = get_vector_store()
store.upsert(vector, {"metadata": "here"}, id="unique_id")
results = store.search(query_vector, limit=10)
```

### Key Features
- **Simple Qdrant wrapper**: No complex abstractions
- **Falls back gracefully**: If Qdrant unavailable
- **Collection management**: Automatic handling

### API Methods
```python
# Basic operations
store.upsert(vector, metadata, id="doc_123")
results = store.search(query_vector, limit=10)
store.delete(id="doc_123")

# Batch operations
store.batch_upsert(vectors, metadata_list, ids)
batch_results = store.batch_search(query_vectors, limit=10)

# Collection management
store.create_collection(name="documents", dimension=1024)
collections = store.list_collections()
store.delete_collection("old_collection")

# Advanced search
results = store.search_with_filter(
    query_vector=vector,
    filter_conditions={"content_type": "pdf"},
    limit=10
)

# Statistics
stats = store.get_collection_stats()
count = store.count_documents()
```

## STATUS: SimpleDB (`shared/simple_db.py`)

### Quick Start
```python
from shared.simple_db import SimpleDB

db = SimpleDB()
content_id = db.add_content("email", "Subject", "Body", metadata)

# Basic search
results = db.search_content("keyword", limit=10)

# Advanced search with filters
filters = {
    "since": "last month",              # Flexible date parsing
    "until": "today",
    "content_types": ["email", "pdf"],   # Multiple content types
    "tags": ["urgent", "legal"],         # Tag filtering
    "tag_logic": "OR"                    # AND/OR logic
}
results = db.search_content("keyword", limit=10, filters=filters)
```

### Key Features
- **Direct SQLite operations**: No ORM, no pooling, just SQL
- **Batch operations**: High-performance bulk inserts with INSERT OR IGNORE
- **Auto-generation**: UUIDs, word counts, char counts handled automatically
- **Progress tracking**: Optional callbacks for long-running operations
- **Performance metrics**: ~2000+ records/second on typical hardware

### API Methods
```python
# Content operations
content_id = db.add_content("email", "Subject", "Body", metadata)
content = db.get_content(content_id)
db.update_content(content_id, title="New Title")
db.delete_content(content_id)

# Search operations
results = db.search_content("query", limit=10)
results = db.search_content_with_filters("query", filters, limit=10)
advanced_results = db.advanced_search(query, filters, sort_by="date")

# Batch operations
stats = db.batch_insert(
    table_name="emails",
    columns=["id", "subject", "body", "date"],
    data_list=[tuple1, tuple2, ...],
    batch_size=1000,
    progress_callback=lambda curr, total: print(f"{curr}/{total}")
)

result = db.batch_add_content(content_list, batch_size=1000)
result = db.batch_add_document_chunk(chunk_list, batch_size=1000)

# Document intelligence
summary_id = db.add_document_summary(
    document_id="content_123",
    summary_type="combined",
    summary_text="Summary text",
    tf_idf_keywords={"legal": 0.8, "contract": 0.6},
    textrank_sentences=["Key sentence 1", "Key sentence 2"]
)

intel_id = db.add_document_intelligence(
    document_id="content_123",
    intelligence_type="entity_extraction",
    intelligence_data={"entities": ["John Doe", "ABC Corp"]},
    confidence_score=0.85
)

# Statistics and analytics
stats = db.get_content_stats()
type_stats = db.get_content_type_statistics()
tag_stats = db.get_tag_statistics()
timeline = db.get_content_timeline(start_date, end_date)

# Relationship management
rel_id = db.add_relationship(from_id, to_id, "similar_to", 0.85)
relationships = db.get_relationships(content_id)
db.update_relationship_score(rel_id, new_score)
```

##  Knowledge Graph Service (`knowledge_graph/`)

### Quick Start
```python
from knowledge_graph import (
    get_knowledge_graph_service,
    get_similarity_analyzer,
    get_timeline_relationships
)

# Initialize services
kg = get_knowledge_graph_service()
analyzer = get_similarity_analyzer(similarity_threshold=0.7)
timeline = get_timeline_relationships()

# Find similar documents
similar = analyzer.find_similar_content("email_123", limit=10)

# Create relationships
edge_id = kg.add_edge("email_123", "pdf_456", "references", 0.85)

# Build timeline
result = timeline.create_temporal_relationships()
```

### Key Features
- **Document Similarity**: Legal BERT embeddings with cosine similarity
- **Relationship Types**: similar_to, references, follows, mentions
- **Timeline Analysis**: Temporal relationships with date extraction
- **Topic Clustering**: Group related documents automatically
- **Dual-layer Caching**: In-memory + SQLite for 100x speedup
- **Batch Operations**: Process 1000+ nodes/edges per second

### API Methods
```python
# Graph operations
node_id = kg.add_node(content_id, content_type, metadata)
edge_id = kg.add_edge(from_id, to_id, relationship_type, weight)
kg.update_edge_weight(edge_id, new_weight)
kg.delete_edge(edge_id)

# Relationship discovery
similar = analyzer.find_similar_content(content_id, limit=10)
similarity_score = analyzer.calculate_similarity(content1_id, content2_id)
batch_similarities = analyzer.batch_similarity_analysis(content_ids)

# Graph traversal
related = kg.get_related_content(content_id, ["similar_to"], limit=5)
path = kg.find_shortest_path("doc_a", "doc_z", max_depth=5)
subgraph = kg.get_subgraph(center_id, max_distance=2)

# Timeline relationships
result = timeline.create_temporal_relationships()
cluster = timeline.find_temporal_cluster(content_id, window_days=7)
temporal_neighbors = timeline.get_temporal_neighbors(content_id, window_hours=24)

# Batch processing
result = analyzer.discover_and_store_similarities(content_type="pdf")
stats = kg.bulk_relationship_discovery(content_ids)

# Graph analytics
centrality = kg.calculate_centrality_scores()
communities = kg.detect_communities()
graph_stats = kg.get_graph_statistics()
```

##  Legal Intelligence Service (`legal_intelligence/`)

### Quick Start
```python
from legal_intelligence import get_legal_intelligence_service

legal = get_legal_intelligence_service()

# Process legal case
result = legal.process_legal_case("24NNCV00555")

# Generate timeline
timeline = legal.generate_case_timeline("24NNCV00555")

# Build knowledge graph
graph = legal.build_case_knowledge_graph("24NNCV00555")
```

### Key Features
- **Case Processing**: Comprehensive legal case analysis with entity extraction
- **Timeline Generation**: Chronological event timeline with document sources
- **Relationship Mapping**: Graph-based document relationship analysis
- **Legal Search**: Entity-aware search with case filtering
- **Missing Document Prediction**: Pattern analysis to identify gaps
- **Document Summarization**: TF-IDF and TextRank summaries with legal entity focus

### Test Hooks (Patchable Factories)
- `legal_intelligence.main.get_knowledge_graph_service(db_path)`: returns the knowledge graph service. Tests can `patch` this to inject a mock. The default is a minimal in-memory graph with `add_node`/`add_edge` methods for lightweight integration.
- `legal_intelligence.main.get_similarity_analyzer()`: returns a simple similarity helper. Tests can patch this to control similarity behavior deterministically.

These tiny factories exist to keep production wiring lightweight while making tests stable and easy to patch, without reaching into private internals. In production, you can ignore them and use `get_legal_intelligence_service()` as usual.

### API Methods
```python
# Case processing
result = legal.process_legal_case(case_number)
analysis = legal.analyze_case_documents(case_number, analysis_type="comprehensive")
patterns = legal.identify_case_patterns(case_number)

# Timeline operations
timeline = legal.generate_case_timeline(case_number, start_date=None, end_date=None)
events = legal.extract_timeline_events(case_number)
gaps = legal.identify_timeline_gaps(case_number)

# Knowledge graph
graph = legal.build_case_knowledge_graph(case_number, include_relationships=True)
relationships = legal.discover_document_relationships(case_number)
network = legal.analyze_entity_network(case_number)

# Document analysis
missing = legal.predict_missing_documents(case_number, confidence=0.6)
summaries = legal.summarize_case_documents(case_number, max_docs=10)
entities = legal.extract_case_entities(case_number)

# Search operations
results = legal.search_case_documents(query, case_number, limit=10)
similar = legal.find_similar_cases(case_number, threshold=0.7)

# Case tracking
status = legal.track_case_status(case_number)
deadlines = legal.extract_case_deadlines(case_number)
activities = legal.get_recent_case_activity(case_number)
```

##  Notes Service (`utilities/notes/`)

### Quick Start
```python
from utilities.notes.main import NotesService

notes = NotesService()
note_id = notes.create_note(title, content, tags)
```

### Key Features
- **Markdown note management**: Rich text formatting support
- **Tag-based organization**: Flexible categorization system
- **Full-text search integration**: Searchable with main search system

### API Methods
```python
# Note operations
note_id = notes.create_note("Title", "Content", ["tag1", "tag2"])
note = notes.get_note(note_id)
notes.update_note(note_id, title="New Title", content="New Content")
notes.delete_note(note_id)

# Search and filtering
results = notes.search_notes("query")
tagged_notes = notes.get_notes_by_tag("legal")
all_notes = notes.list_notes(limit=50)

# Tag management
tags = notes.get_all_tags()
notes.add_tag_to_note(note_id, "new_tag")
notes.remove_tag_from_note(note_id, "old_tag")

# Batch operations
notes.batch_create_notes(notes_data_list)
notes.bulk_tag_notes(note_ids, tags)
```

## ⏱ Timeline Service (`utilities/timeline/`)

### Quick Start
```python
from utilities.timeline.main import TimelineService

timeline = TimelineService()
events = timeline.get_timeline(start_date, end_date)
```

### Key Features
- **Chronological event tracking**: Time-based content organization
- **Legal timeline generation**: Case-specific timelines
- **Event relationship mapping**: Connected events analysis
- **SQLite-backed persistence**: Reliable data storage

### API Methods
```python
# Timeline operations
events = timeline.get_timeline(start_date, end_date)
timeline.add_event(date, event_type, description, metadata)
timeline.update_event(event_id, new_data)
timeline.delete_event(event_id)

# Event analysis
related_events = timeline.find_related_events(event_id)
event_sequence = timeline.get_event_sequence(start_date, end_date)
timeline_gaps = timeline.identify_gaps(start_date, end_date)

# Content integration
timeline.create_content_timeline(content_id)
events = timeline.extract_events_from_content(content_id)
timeline.link_content_to_events(content_id, event_ids)

# Legal timeline
legal_timeline = timeline.generate_legal_timeline(case_number)
case_events = timeline.get_case_events(case_number)
procedural_timeline = timeline.extract_procedural_events(case_number)
```

##  Integration Patterns

### Service Composition
```python
# Multi-service workflow example
from gmail.main import GmailService
from search_intelligence import get_search_intelligence_service
from utilities.embeddings import get_embedding_service
from shared.simple_db import SimpleDB

# Initialize services
gmail = GmailService()
search = get_search_intelligence_service()
embeddings = get_embedding_service()
db = SimpleDB()

# Workflow: Sync emails → Extract entities → Create embeddings → Build relationships
def process_new_emails():
    # 1. Sync new emails
    sync_result = gmail.sync_incremental(max_results=100)
    
    # 2. Extract entities from new content
    for content_id in sync_result.get('new_content_ids', []):
        entities = search.extract_and_cache_entities(content_id)
        
    # 3. Build document similarities
    similarities = search.cluster_similar_content(threshold=0.7)
    
    return {
        'emails_synced': len(sync_result.get('new_content_ids', [])),
        'entities_extracted': len(entities),
        'similarities_found': len(similarities)
    }
```

### Error Handling Patterns
```python
# Graceful degradation example
def robust_search(query, limit=10):
    try:
        # Try semantic search first
        from utilities.vector_store import get_vector_store
        store = get_vector_store()
        vector = embeddings.encode(query)
        results = store.search(vector, limit=limit)
        return {'type': 'semantic', 'results': results}
    except Exception:
        # Fall back to keyword search
        db = SimpleDB()
        results = db.search_content(query, limit=limit)
        return {'type': 'keyword', 'results': results}
```

### Performance Optimization
```python
# Batch processing example
def process_large_document_set(content_ids, batch_size=100):
    results = []
    
    for i in range(0, len(content_ids), batch_size):
        batch = content_ids[i:i + batch_size]
        
        # Batch entity extraction
        batch_entities = search.batch_extract_entities(batch)
        
        # Batch embedding generation
        batch_texts = [db.get_content(cid)['content'] for cid in batch]
        batch_vectors = embeddings.encode_batch(batch_texts)
        
        # Batch vector storage
        store.batch_upsert(batch_vectors, batch_entities, batch)
        
        results.extend(batch)
    
    return results
```

## READY: Performance Guidelines

### Service Initialization
- **Singletons**: Embedding and vector services use singleton pattern
- **Lazy loading**: Services initialize only when first used
- **Connection pooling**: Database connections reused efficiently
- **Cache warming**: Frequently used data preloaded

### Batch Operations
- **Recommended batch sizes**: 100-1000 items depending on operation
- **Progress callbacks**: Monitor long-running operations
- **Memory management**: Process in chunks to avoid memory issues
- **Error isolation**: Failed items don't stop entire batch

### Caching Strategies
- **Entity cache**: TTL-based caching for entity extraction
- **Embedding cache**: Store computed embeddings to avoid recomputation
- **Relationship cache**: Cache document relationships with expiration
- **Query cache**: Cache frequently used search results

### Monitoring and Debugging
```python
# Service health check
def check_service_health():
    health = {}
    
    try:
        db = SimpleDB()
        stats = db.get_content_stats()
        health['database'] = 'healthy'
        health['content_count'] = stats.get('total_content', 0)
    except Exception as e:
        health['database'] = f'error: {str(e)}'
    
    try:
        embeddings = get_embedding_service()
        test_vector = embeddings.encode("test")
        health['embeddings'] = 'healthy'
        health['embedding_dimensions'] = len(test_vector)
    except Exception as e:
        health['embeddings'] = f'error: {str(e)}'
    
    try:
        store = get_vector_store()
        stats = store.get_collection_stats()
        health['vector_store'] = 'healthy'
        health['vector_count'] = stats.get('vectors_count', 0)
    except Exception as e:
        health['vector_store'] = f'error: {str(e)}'
    
    return health
```

## TOOLS: Maintenance Utilities

### Vector Maintenance (`utilities/maintenance/vector_maintenance.py`)
Consolidated tool for all vector store operations:

```bash
# Verify sync status across all collections
python utilities/maintenance/vector_maintenance.py verify

# Sync missing vectors for specific collection
python utilities/maintenance/vector_maintenance.py sync-missing --collection pdfs

# Reconcile vectors with database (dry run)
python utilities/maintenance/vector_maintenance.py reconcile

# Apply fixes for reconciliation
python utilities/maintenance/vector_maintenance.py reconcile --fix

# Sync emails to vector store
python utilities/maintenance/vector_maintenance.py sync-emails --limit 100

# Purge test vectors (dry run)
python utilities/maintenance/vector_maintenance.py purge-test

# Actually purge test vectors
python utilities/maintenance/vector_maintenance.py purge-test --execute
```

### Schema Maintenance (`utilities/maintenance/schema_maintenance.py`)
Consolidated tool for database schema operations:

```bash
# Validate schema integrity
python utilities/maintenance/schema_maintenance.py validate

# Fix schema issues (dry run)
python utilities/maintenance/schema_maintenance.py fix-schema

# Apply schema fixes
python utilities/maintenance/schema_maintenance.py fix-schema --execute

# Migrate legacy email tables
python utilities/maintenance/schema_maintenance.py migrate-emails --batch-size 100

# Update schema references after table changes
python utilities/maintenance/schema_maintenance.py update-refs
```

For more detailed implementation examples and advanced usage patterns, see individual service documentation in their respective directories.
