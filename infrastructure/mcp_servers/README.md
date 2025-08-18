# MCP Servers Directory

Modular Model Context Protocol (MCP) servers for Claude Desktop integration.

## Architecture

Each MCP server is a standalone Python module (~150-500 lines) that:
- Provides 3-5 focused tools for a specific domain
- Directly imports and uses existing Email Sync services
- Follows the simple pattern established by entity_mcp_server.py
- Returns standardized error format: `{"success": False, "error": str}`

## Available Servers

### entity_mcp_server.py (306 lines)
**Entity extraction and relationship mapping using Legal BERT + spaCy**
- `extract_entities` - Extract named entities from text
- `search_entities` - Search consolidated entities
- `knowledge_graph` - Get entity relationship graph
- `entity_stats` - Entity extraction statistics

### docs_mcp_server.py (197 lines)
**Documentation viewer for project files**
- `docs` - Show CLAUDE.md, README.md, and other documentation
  - Options: type (claude/readme/changelog), service filter, summary view

### search_mcp_server.py (325 lines)
**Search functionality across all content**
- `search_content` - Basic keyword search with type filtering
- `hybrid_search` - Semantic + keyword using Legal BERT embeddings
- `search_by_type` - Filter by content type (email/pdf/transcript/note)
- `search_stats` - Vector and content statistics

### legal_mcp_server.py (510 lines)
**Legal document analysis and procedural intelligence**
- `tag_evidence` - Auto-tag documents with legal categories
- `find_case_documents` - Search documents by case number
- `detect_missing_documents` - Identify procedural gaps
- `analyze_case_relationships` - Document relationship analysis

### timeline_mcp_server.py (483 lines)
**Chronological event tracking and timeline management**
- `build_timeline` - Create chronological event timeline
- `timeline_gaps` - Identify missing time periods
- `add_timeline_event` - Add manual events to timeline
- `export_timeline` - Export timeline as JSON or Markdown

## Usage

### Running a Server Directly
```bash
python3 mcp_servers/entity_mcp_server.py
```

### Claude Desktop Configuration
Add to `~/.config/claude-desktop/claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "email-sync-entity": {
      "command": "python3",
      "args": ["/path/to/Email Sync/mcp_servers/entity_mcp_server.py"],
      "env": {"PYTHONPATH": "/path/to/Email Sync"}
    },
    "email-sync-search": {
      "command": "python3",
      "args": ["/path/to/Email Sync/mcp_servers/search_mcp_server.py"],
      "env": {"PYTHONPATH": "/path/to/Email Sync"}
    },
    "email-sync-legal": {
      "command": "python3",
      "args": ["/path/to/Email Sync/mcp_servers/legal_mcp_server.py"],
      "env": {"PYTHONPATH": "/path/to/Email Sync"}
    },
    "email-sync-timeline": {
      "command": "python3",
      "args": ["/path/to/Email Sync/mcp_servers/timeline_mcp_server.py"],
      "env": {"PYTHONPATH": "/path/to/Email Sync"}
    },
    "email-sync-docs": {
      "command": "python3",
      "args": ["/path/to/Email Sync/mcp_servers/docs_mcp_server.py"],
      "env": {"PYTHONPATH": "/path/to/Email Sync"}
    }
  }
}
```

## Development Guidelines

### Adding New MCP Servers

1. **Follow the Pattern**: Copy entity_mcp_server.py as template
2. **Keep It Simple**:
   - Target 150-200 lines, max 500 lines
   - No abstract classes or factories
   - Direct service imports and function calls
3. **Standard Structure**:
   ```python
   #!/usr/bin/env python3
   """Simple [Domain] MCP Server"""

   # Add project root to path
   sys.path.append(str(Path(__file__).parent.parent))

   # Import services directly
   from service.main import ServiceClass

   # Tool functions (simple, direct)
   def tool_function(args) -> str:
       service = ServiceClass()
       result = service.method(args)
       return format_result(result)

   # Server class with tool registration
   class DomainServer:
       def __init__(self):
           self.server = Server("domain-server")
           self.setup_tools()
   ```

### Testing

```bash
# Test imports
python3 -c "import sys; sys.path.append('mcp_servers'); import entity_mcp_server"

# Run server
python3 mcp_servers/entity_mcp_server.py

# Test with MCP client
# (Server will wait for stdio input from MCP client)
```

## Architecture Benefits

- **Modularity**: Each server is independent and focused
- **Simplicity**: Direct imports, no complex patterns
- **Maintainability**: Small file sizes, clear responsibilities
- **Compatibility**: Works with existing Email Sync services
- **Performance**: Minimal overhead, direct function calls

## Related Documentation

- Main MCP server: `/mcp_server/` (complex, being deprecated)
- Project docs: `/CLAUDE.md`
- Service docs: `/[service]/CLAUDE.md`
