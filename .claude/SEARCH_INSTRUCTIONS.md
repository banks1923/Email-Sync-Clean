# AI-Powered Search Instructions for Claude

## Primary Search Command

When the user wants to search, use:
```bash
scripts/vsearch search "query"
```

This single command provides:
- Unified search across emails, PDFs, and transcripts
- Legal BERT 1024D semantic embeddings
- Automatic fallback to keyword search
- Access to all databases (SQLite emails.db + Qdrant vectors)

## MCP Tools for Search

If using MCP tools directly:
1. `hybrid_search` - Best for general queries (semantic + keyword)
2. `search_all_content` - Search with content type filters
3. `vector_search` - Pure semantic similarity

## Database Access

The system automatically accesses:
- **emails.db**: SQLite database with all email content
- **qdrant_data/**: Local Qdrant vector database
- **documents table**: PDFs and transcripts

## Quick Examples

```bash
# Search everything
scripts/vsearch search "contract termination clause"

# Search with more results
scripts/vsearch search "meeting notes from last week" -n 20

# Using MCP
mcp: hybrid_search query="patent infringement" limit=10
```

## No Setup Required

If vectors are already processed, just search. The system handles everything else automatically.
