# MCP Server Configuration

## Filesystem Access Configuration

This file documents the MCP server configuration for proper filesystem access.

### Included Directories
- Source code directories (gmail_service/, search_service/, vector_service/, etc.)
- Configuration files
- Tests directory
- Documentation

### Excluded Patterns (via .mcpignore)
- Virtual environments (venv/, env/, .venv/)
- Cache directories (__pycache__/, .pytest_cache/, .cache/)
- Build artifacts (dist/, build/, *.egg-info/)
- IDE files (.vscode/, .idea/)
- OS files (.DS_Store, Thumbs.db)
- Log files (*.log, logs/)
- Database files (*.db, except for schema documentation)
- Vector database data (qdrant_data/)
- Credentials and secrets (credentials.json, token.json, .env)
- Large model files (*.bin, *.pt, *.safetensors)
- Temporary files (tmp/, temp/, *.tmp)

The MCP server uses the correct project path and excludes unwanted files via .mcpignore patterns.
