# Search Context for Claude

When the user mentions "search" or wants to find something in their email/document system:

1. **Use this command**: `scripts/vsearch search "query"`
2. **It automatically searches**: Emails + PDFs + Transcripts
3. **Uses**: Legal BERT 1024D embeddings + keyword fallback
4. **No setup needed**: Just run the command

## Quick Reference
```bash
# These all do AI-powered unified search:
scripts/vsearch search "contract terms"
scripts/vsearch search "meeting yesterday"
scripts/vsearch search "invoice 2024"
```

## MCP Tools
If in Claude Desktop with MCP:
- `hybrid_search` - Best overall
- `search_all_content` - With filters
- `vector_search` - Semantic only
