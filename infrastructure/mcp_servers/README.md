# MCP Servers Directory

Modular Model Context Protocol (MCP) servers for Claude Desktop integration.

## Architecture

Each MCP server is a standalone Python module (~150-500 lines) that:
- Provides 3-5 focused tools for a specific domain
- Directly imports and uses existing Email Sync services
- Follows the simple pattern established by entity_mcp_server.py
- Returns standardized error format: `{"success": False, "error": str}`

## Available Servers

### legal_intelligence_mcp.py (879 lines)
**Unified Legal Intelligence with Legal BERT + Entity Extraction**
- `legal_extract_entities` - Extract legal entities using Legal BERT and NER
- `legal_timeline_events` - Generate comprehensive legal case timeline
- `legal_knowledge_graph` - Build document relationships for legal cases
- `legal_document_analysis` - Comprehensive document analysis with Legal BERT
- `legal_case_tracking` - Track case status, deadlines, and requirements
- `legal_relationship_discovery` - Discover entity/document/case relationships

### search_intelligence_mcp.py (600+ lines)
**Unified Search Intelligence with Smart Query Processing**
- `search_smart` - Smart search with query preprocessing and expansion
- `search_similar` - Find documents similar to a given document
- `search_entities` - Extract entities from documents or text
- `search_summarize` - Summarize documents or text content
- `search_cluster` - Cluster similar documents for analysis
- `search_process_all` - Batch process documents with specified operations

## Deprecated Servers (Legacy)
- `entity_mcp_server.py` - Replaced by legal_intelligence_mcp.py
- `search_mcp_server.py` - Replaced by search_intelligence_mcp.py  
- `legal_mcp_server.py` - Replaced by legal_intelligence_mcp.py
- `timeline_mcp_server.py` - Integrated into legal_intelligence_mcp.py
- `docs_mcp_server.py` - Basic documentation viewer

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
    "legal-intelligence": {
      "command": "python3",
      "args": ["/path/to/Email-Sync-Clean-Backup/infrastructure/mcp_servers/legal_intelligence_mcp.py"],
      "env": {"PYTHONPATH": "/path/to/Email-Sync-Clean-Backup"}
    },
    "search-intelligence": {
      "command": "python3", 
      "args": ["/path/to/Email-Sync-Clean-Backup/infrastructure/mcp_servers/search_intelligence_mcp.py"],
      "env": {"PYTHONPATH": "/path/to/Email-Sync-Clean-Backup"}
    }
  }
}
```

**Note**: No PYTHONPATH needed if you have proper Pydantic configuration in `config/settings.py`

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

   # Add project root to path - flexible resolution
   try:
       from config.settings import settings
       project_root = Path(settings.paths.data_root).parent
   except ImportError:
       # Fallback for 3-level deep paths: infrastructure/mcp_servers/*.py
       project_root = Path(__file__).parent.parent.parent
   sys.path.insert(0, str(project_root))

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
