# System Architecture Documentation

This directory contains system architecture diagrams and configuration documentation for the Email Sync system.

## Architecture Diagrams

### Data Flow Diagram
- **File**: `data_flow.mmd` / `data_flow.svg`
- **Description**: Shows the complete data flow from input sources (Gmail, PDFs, uploads) through processing layers to vector storage
- **Key Components**: 
  - Input Sources: Gmail API, PDF Files, Direct Uploads
  - Unified Storage: content_unified table (run `make db-stats` for current counts)
  - AI Processing: Entity extraction, summarization, embedding generation
  - Vector Storage: Qdrant for semantic search

### Dependency Graph
- **File**: `dependency_graph.mmd` / `dependency_graph.svg`
- **Description**: Illustrates module dependencies and service relationships
- **Key Statistics**:
  - 35 files depend on SimpleDB
  - 16 files directly reference content_unified table
  - Clear separation between service layers

### Migration Status Diagram
- **File**: `migration_complete.mmd` / `migration_complete.svg`
- **Description**: Documents the migration from content → content_unified table
- **Status**: ⚠️ Check current status with `sqlite3 data/emails.db "SELECT 'old:' || COUNT(*) FROM content UNION ALL SELECT 'new:' || COUNT(*) FROM content_unified"`

## Viewing Diagrams

### SVG Files
The `.svg` files can be viewed directly in any web browser or image viewer.

### Mermaid Source Files
The `.mmd` files are Mermaid diagram source files. To edit or regenerate:

```bash
# Install Mermaid CLI (if not already installed)
npm install -g @mermaid-js/mermaid-cli

# Generate SVG from Mermaid source
mmdc -i data_flow.mmd -o data_flow.svg
mmdc -i dependency_graph.mmd -o dependency_graph.svg
mmdc -i migration_complete.mmd -o migration_complete.svg
```

## System Configuration

The Email Sync system uses a centralized configuration approach:

- **Database**: SQLite with content_unified table as central storage
- **Vector Database**: Qdrant for semantic search capabilities
- **Embedding Model**: Legal BERT 1024D vectors
- **Processing Pipeline**: Raw → Staged → Processed → Embeddings

## Architecture Principles

1. **SimpleDB as Central Abstraction**: All database operations go through SimpleDB
2. **Flat Service Structure**: Services at root level for easy access
3. **Clean Separation**: Business logic, utilities, and infrastructure clearly separated
4. **No Cross-Service Imports**: Services remain independent