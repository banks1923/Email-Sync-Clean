# MCP Server Integration Guide

Complete guide to all Model Context Protocol (MCP) servers available in the Email Sync system.

## 🎯 Overview

The Email Sync system provides 40+ specialized tools through MCP servers for Claude Desktop integration.

### Quick Integration Summary
- **Total Tools**: 40+ available in Claude Desktop
- **Agents**: 11 specialized development agents  
- **Intelligence Servers**: 12 advanced intelligence tools (6 legal + 6 search)
- **Content Management**: 10 content handling tools
- **Infrastructure**: Service integration and filesystem tools

## 🏛️ Legal Intelligence MCP Server

**Purpose**: Unified legal document analysis, timeline generation, and case intelligence using Legal BERT embeddings.

### Configuration
- **Server**: `legal-intelligence` in `.mcp.json`
- **File**: `infrastructure/mcp_servers/legal_intelligence_mcp.py`
- **Status**: ✅ Fully Implemented
- **Dependencies**: Legal Intelligence Service, Entity Service, Timeline Service

### Available Tools

#### 1. legal_extract_entities
Extract legal entities from text using Legal BERT and NER capabilities.
```python
legal_extract_entities(
    content="John Doe, attorney for plaintiff, filed motion in case 24NNCV00555",
    case_id="optional_case_id"
)
```
**Features**: Legal entity highlighting, relationship analysis, confidence scoring

#### 2. legal_timeline_events
Generate comprehensive timeline of legal case events with gap analysis.
```python
legal_timeline_events(
    case_number="24NNCV00555",
    start_date="2024-01-01",  # Optional
    end_date="2024-12-31"     # Optional
)
```
**Features**: Chronological organization, milestone identification, gap detection

#### 3. legal_knowledge_graph
Build and analyze knowledge graph relationships for legal cases.
```python
legal_knowledge_graph(
    case_number="24NNCV00555",
    include_relationships=True  # Optional
)
```
**Features**: Document relationship mapping, graph statistics, network insights

#### 4. legal_document_analysis
Perform comprehensive document analysis using Legal BERT embeddings.
```python
legal_document_analysis(
    case_number="24NNCV00555",
    analysis_type="comprehensive"  # or "patterns"
)
```
**Features**: Pattern analysis, missing document prediction, entity integration

#### 5. legal_case_tracking
Track legal case status, deadlines, and procedural requirements.
```python
legal_case_tracking(
    case_number="24NNCV00555",
    track_type="status"  # "status", "deadlines", or "missing"
)
```
**Features**: Case stage determination, deadline extraction, missing document analysis

#### 6. legal_relationship_discovery
Discover relationships between entities, documents, and cases.
```python
legal_relationship_discovery(
    case_number="24NNCV00555",
    entity_focus="John Doe"  # Optional entity focus
)
```
**Features**: Entity relationships, cross-case analysis, connection strength

### Usage Examples
```python
# Comprehensive case analysis
mcp__legal-intelligence__legal_document_analysis(
    case_number="24NNCV00555",
    analysis_type="comprehensive"
)

# Timeline with date filtering
mcp__legal-intelligence__legal_timeline_events(
    case_number="24NNCV00555",
    start_date="2024-01-01",
    end_date="2024-06-30"
)

# Entity extraction from legal text
mcp__legal-intelligence__legal_extract_entities(
    content="Motion for summary judgment filed by plaintiff's counsel..."
)
```

## 🔍 Search Intelligence MCP Server

**Purpose**: Comprehensive search and document intelligence including smart search, similarity analysis, and clustering.

### Configuration
- **Server**: `search-intelligence` in `.mcp.json`
- **File**: `infrastructure/mcp_servers/search_intelligence_mcp.py`
- **Status**: ✅ Fully Implemented
- **Dependencies**: Search Intelligence Service, Entity Service, Document Summarizer

### Available Tools

#### 1. search_smart
Smart search with query preprocessing and expansion for enhanced results.
```python
search_smart(
    query="contract attorney",
    limit=10,
    use_expansion=True,
    content_type="pdf"  # Optional filter
)
```
**Features**: Query expansion, abbreviation expansion, entity-aware ranking

#### 2. search_similar
Find documents similar to a given document using Legal BERT embeddings.
```python
search_similar(
    document_id="content_123",
    threshold=0.7,
    limit=10
)
```
**Features**: Cosine similarity, common entity detection, similarity scoring

#### 3. search_entities
Extract entities from documents or text using NER.
```python
search_entities(
    document_id="content_123",  # Or use text parameter
    text="John Smith signed the contract",
    cache_results=True
)
```
**Features**: SpaCy NER, entity type grouping, confidence scoring, result caching

#### 4. search_summarize
Generate document summaries using TF-IDF and TextRank.
```python
search_summarize(
    document_id="content_123",  # Or use text parameter
    text="Document content here",
    max_sentences=3,
    max_keywords=10
)
```
**Features**: Combined TF-IDF/TextRank, keyword extraction, key sentence extraction

#### 5. search_cluster
Cluster similar documents using DBSCAN algorithm.
```python
search_cluster(
    threshold=0.7,
    limit=100,
    min_cluster_size=2
)
```
**Features**: DBSCAN clustering, theme detection, cluster statistics

#### 6. search_process_all
Batch process documents with various operations.
```python
search_process_all(
    operation="extract_entities",  # or "generate_summaries", "find_duplicates"
    content_type="email",  # Optional filter
    limit=100
)
```
**Features**: Batch entity extraction, batch summarization, duplicate detection

### Usage Examples
```python
# Smart search with query expansion
mcp__search-intelligence__search_smart(
    query="LLC contract",
    use_expansion=True
)

# Find similar documents
mcp__search-intelligence__search_similar(
    document_id="content_456",
    threshold=0.8
)

# Extract entities from text
mcp__search-intelligence__search_entities(
    text="ABC Corporation filed the lawsuit on January 15, 2024"
)

# Batch process for duplicate detection
mcp__search-intelligence__search_process_all(
    operation="find_duplicates",
    limit=500
)
```

## 🧠 Sequential Thinking MCP Server

**Purpose**: Structured thinking framework for complex problem-solving with progress tracking.

### Configuration
- **Server**: `sequential-thinking` in `.mcp.json`
- **Storage**: `/Users/jim/Projects/Email Sync/data/sequential_thinking`
- **Status**: ✅ Fully Operational

### Key Features
- **Structured Thinking**: Numbered thoughts with stages (Problem Definition → Research → Analysis → Synthesis → Conclusion)
- **Progress Tracking**: Real-time completion percentages (33% → 67% → 100%)
- **Context Preservation**: Maintains relationships between related thoughts
- **Tag Organization**: Categorize thoughts with tags for better organization
- **Persistent Storage**: All thinking sessions saved locally for review

### Usage Examples
```python
# Process a sequential thought
mcp__sequential-thinking__process_thought(
    thought="Analyzing the architecture for performance issues...",
    thought_number=1,
    total_thoughts=3,
    next_thought_needed=True,
    stage="Analysis",
    tags=["architecture", "performance", "review"]
)

# Generate summary of thinking session
mcp__sequential-thinking__generate_summary()

# Clear history for new thinking session
mcp__sequential-thinking__clear_history()
```

### When to Use Sequential Thinking
- **Complex architectural decisions**: Break down into structured analysis
- **Multi-step problem solving**: Track progress through investigation
- **Code review**: Provide structured feedback with clear progression
- **Planning implementation**: Think through approaches systematically
- **Debugging complex issues**: Maintain context while investigating

## 💾 Memory MCP Server

**Purpose**: Persistent memory using knowledge graph structure that maintains context across sessions.

### Configuration
- **Server**: `memory` in `.mcp.json`
- **Package**: `@modelcontextprotocol/server-memory` (v2025.8.4)
- **Status**: ✅ Configured and Operational

### Key Features
- **Knowledge Graph**: Store entities, relationships, and observations
- **Persistent Context**: Remember information across Claude sessions
- **User Preferences**: Store and recall user-specific information
- **Project Memory**: Track project details and relationships
- **Conversation History**: Maintain context from previous interactions

### Knowledge Graph Structure
```python
# Entities - Primary nodes in the graph
entity = {
    "name": "Email Sync Project",
    "type": "project",
    "attributes": ["Python", "MCP", "Legal BERT"]
}

# Relations - Directed connections between entities
relation = {
    "from": "User",
    "to": "Email Sync Project",
    "type": "owns"
}

# Observations - Discrete information about entities
observation = {
    "entity": "User",
    "fact": "Prefers flat architecture over nested structures"
}
```

### Usage Examples
```
# Store user preferences
"Remember that I prefer to use Legal BERT for all semantic searches"

# Store project relationships
"The Email Sync project uses Qdrant for vector storage"

# Recall stored information
"What do you know about my project preferences?"

# Create entity relationships
"John Smith is the lead attorney on the Johnson case"
```

## 🕸️ Web Scraping MCP Servers

### Firecrawl MCP Server
**Purpose**: Advanced web scraping and content extraction capabilities.

- **Server**: `firecrawl` in `.mcp.json`
- **Package**: `firecrawl-mcp` (v1.12.0)
- **Status**: 🔧 Available (requires API key)
- **API Key**: Get from <https://www.firecrawl.dev/app/api-keys>

**Key Features**:
- Web scraping with clean markdown output
- Site crawling with filtering options
- Structured data extraction using LLM
- Batch processing for multiple URLs
- Content search within scraped content

### Puppeteer MCP Server
**Purpose**: Browser automation for dynamic content interaction.

- **Server**: `puppeteer` in configuration
- **Use Cases**: Dynamic content interaction, form filling, screenshot capture
- **Integration**: Complements Firecrawl for interactive web tasks

## 🗃️ Vector Storage MCP Server

### Qdrant MCP Server
**Purpose**: Semantic memory layer and vector database integration.

- **Server**: `qdrant` in `.mcp.json`
- **Package**: `mcp-server-qdrant` (v0.8.0)
- **Status**: ✅ Available (Qdrant running on port 6333)
- **Qdrant**: Running locally with QDRANT__STORAGE__PATH=./qdrant_data

**Key Features**:
- Semantic memory storage using vector similarity
- Code snippet storage with descriptions
- Document embeddings processing
- Natural language search capabilities
- Collection management (automatic)
- FastEmbed models using sentence-transformers

**Usage Examples**:
```python
# Store a memory or code snippet
qdrant_store(
    content="Implementation of binary search in Python",
    metadata={"type": "algorithm", "language": "python"}
)

# Find relevant memories
qdrant_find(
    query="How to implement sorting algorithms",
    limit=5
)
```

### When to Use Different Servers
- **Qdrant MCP**: Vector-based semantic search with embeddings
- **Memory Server**: Graph-based relationship storage
- **Sequential Thinking**: Short-term structured reasoning within a session
- **Firecrawl**: Production web scraping with clean markdown output
- **Puppeteer**: Browser automation for dynamic content

### Integration with Email Sync
Since Email Sync already uses Qdrant for vector storage, the MCP server can:
- Share the same Qdrant instance (different collections)
- Provide direct semantic search without going through Email Sync
- Store code snippets and technical documentation
- Complement existing Legal BERT embeddings with general-purpose embeddings

## 🚫 Deprecated Servers

The following servers are deprecated and will be removed:
- ⚠️ `legal_mcp_server.py` → Use `legal_intelligence_mcp.py`
- ⚠️ `timeline_mcp_server.py` → Use `legal_timeline_events` tool
- ⚠️ `search_mcp_server.py` → Use `search_intelligence_mcp.py`
- ⚠️ `entity_mcp_server.py` → Use `search_entities` tool

## 📝 Best Practices

### Server Selection Guide
1. **Legal Analysis**: Use Legal Intelligence MCP Server
2. **Document Search**: Use Search Intelligence MCP Server  
3. **Complex Problem Solving**: Use Sequential Thinking MCP Server
4. **Long-term Memory**: Use Memory MCP Server
5. **Web Research**: Use Firecrawl MCP Server
6. **Code Storage**: Use Qdrant MCP Server
7. **Browser Automation**: Use Puppeteer MCP Server

### Performance Tips
- Use batch operations for multiple documents
- Leverage caching for frequently accessed entities
- Choose appropriate similarity thresholds (0.7-0.8 for most cases)
- Use content type filters to narrow search scope
- Take advantage of TTL-based caching in relationship storage

### Integration Patterns
- Combine Legal Intelligence with Sequential Thinking for complex legal analysis
- Use Memory Server to store findings from Search Intelligence
- Leverage Qdrant for code snippets while using Memory for project relationships
- Use Firecrawl for research, then store findings in Memory or Qdrant
