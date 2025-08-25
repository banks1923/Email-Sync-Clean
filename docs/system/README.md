# System Architecture Documentation

This directory contains current system architecture diagrams and configuration documentation for the Email Sync system.

## Current Architecture Diagrams (2025)

### Updated Data Flow (2025)
- **File**: `updated_data_flow_2025.mmd` / `updated_data_flow_2025.svg`
- **Description**: Complete current data flow including Email v2.0 deduplication system
- **Key Features**: 
  - Email message-level deduplication with `individual_messages` table
  - Legal BERT 1024D embedding pipeline
  - MCP server integration with Claude Desktop (12+ tools)
  - Real metrics: 645 records in content_unified table
  - Qdrant vector database integration

### Service Dependencies (2025)
- **File**: `current_dependency_graph_2025.mmd` / `current_dependency_graph_2025.svg`
- **Description**: Current service dependencies and data flow relationships
- **Key Statistics**:
  - SimpleDB as central hub (47 methods, WAL mode, 64MB cache)
  - Email parsing v2.0 with 97% test coverage
  - Infrastructure layer organization (MCP, documents, pipelines)
  - Live monitoring tools integration

### Service Architecture (2025)
- **File**: `service_architecture_2025.mmd` / `service_architecture_2025.svg`
- **Description**: Clean flat architecture with service organization
- **Key Components**:
  - Root-level business services (6,123+ lines of core logic)
  - Organized utilities layer (embeddings, vector store, timeline)
  - Infrastructure services (MCP servers, document pipeline)
  - Email processing v2.0 with advanced deduplication

## Viewing Diagrams

### SVG Files
The `.svg` files can be viewed directly in any web browser or image viewer. They are scalable and print-friendly.

### Mermaid Source Files
The `.mmd` files are Mermaid diagram source files. To edit or regenerate:

```bash
# Install Mermaid CLI (if not already installed)
npm install -g @mermaid-js/mermaid-cli

# Generate SVG from current Mermaid sources
mmdc -i updated_data_flow_2025.mmd -o updated_data_flow_2025.svg
mmdc -i current_dependency_graph_2025.mmd -o current_dependency_graph_2025.svg
mmdc -i service_architecture_2025.mmd -o service_architecture_2025.svg
```

## System Configuration (Current)

The Email Sync system uses a centralized configuration approach:

- **Database**: SQLite with content_unified table as central storage (7.7MB, 645 records)
- **Email Processing**: v2.0 message-level deduplication (70-80% content reduction)
- **Vector Database**: Qdrant for semantic search (localhost:6333, 1024D vectors)
- **Embedding Model**: Legal BERT (pile-of-law/legalbert-large-1.7M-2)
- **Processing Pipeline**: Unified ingestion → content_unified → embeddings → vector search

## Architecture Principles

1. **SimpleDB as Central Abstraction**: All database operations go through SimpleDB (47 methods)
2. **Flat Service Structure**: Services at root level for easy access (no deep nesting)
3. **Clean Separation**: Business logic, utilities, and infrastructure clearly separated
4. **No Cross-Service Imports**: Services remain independent and modular
5. **Email v2.0**: Message-level deduplication with TEXT source_ids for flexibility

## System Health Monitoring

For live system monitoring, use:

```bash
# Static health snapshot
python3 scripts/system_health_graph.py

# Live monitoring dashboard
python3 scripts/live_health_dashboard.py

# System diagnostics
make diag-wiring
```

## Archived Files

Previous versions and outdated diagrams have been moved to the `archived/` directory to maintain historical reference while keeping the current documentation clean.