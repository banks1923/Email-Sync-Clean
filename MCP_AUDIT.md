# MCP Configuration Audit Report

## Configuration Locations Found

### 1. **Claude Desktop App** (Primary)
- **Location**: `~/Library/Application Support/Claude/claude_desktop_config.json`
- **Servers Configured**:
  - `task-master` → node /Users/jim/Projects/OCR/task-master-mcp-server.js (FILE MISSING)
  - `sequential-thinking` → npx -y sequential-thinking-mcp
  - `filesystem` → npx -y @modelcontextprotocol/server-filesystem

### 2. **Project Root** (Claude Code)
- **Location**: `/Users/jim/Projects/Litigator_solo/.mcp.json`
- **Servers Configured**:
  - `sequential-thinking` → python3 /Users/jim/Projects/mcp-sequential-thinking/run_server.py (FILE EXISTS)

### 3. **Project .config Directory**
- **Location**: `/Users/jim/Projects/Litigator_solo/.config/.mcp.json`
- **Servers Configured**:
  - `legal-intelligence` → python3 infrastructure/mcp_servers/legal_intelligence_mcp.py (WRONG PATH: Email-Sync-Clean-Backup)
  - `search-intelligence` → python3 infrastructure/mcp_servers/search_intelligence_mcp.py (WRONG PATH: Email-Sync-Clean-Backup)
  - `filesystem` → npx -y @modelcontextprotocol/server-filesystem
  - `sequential-thinking` → python3 /Users/jim/Projects/mcp-sequential-thinking/run_server.py
  - `task-master-ai` → npx -y --package=task-master-ai task-master-ai

### 4. **Project .claude Directory**
- **Location**: `/Users/jim/Projects/Litigator_solo/.claude/mcp.json`
- **Servers Configured**:
  - `filesystem` → npx -y @modelcontextprotocol/server-filesystem
  - `git` → npx -y @modelcontextprotocol/server-git
  - `task-master-ai` → npx -y --package=task-master-ai task-master-ai (WITH API KEYS)

### 5. **Alternative Desktop Config**
- **Location**: `~/.config/claude-desktop/claude_desktop_config.json`
- **Servers Configured**:
  - `filesystem` → npx -y @modelcontextprotocol/server-filesystem (OLD PATHS: Email Sync)

## Server Availability Status

### ✅ Working Servers
1. **sequential-thinking** (Python)
   - File: `/Users/jim/Projects/mcp-sequential-thinking/run_server.py`
   - Status: FILE EXISTS
   
2. **legal-intelligence** (Python)
   - File: `/Users/jim/Projects/Litigator_solo/infrastructure/mcp_servers/legal_intelligence_mcp.py`
   - Status: FILE EXISTS
   
3. **search-intelligence** (Python)
   - File: `/Users/jim/Projects/Litigator_solo/infrastructure/mcp_servers/search_intelligence_mcp.py`
   - Status: FILE EXISTS

4. **task-master-ai** (NPM)
   - Package: Globally installed (v0.25.1)
   - CLI: `/opt/homebrew/bin/task-master`
   - Status: AVAILABLE via npx

5. **filesystem** (NPM)
   - Package: @modelcontextprotocol/server-filesystem
   - Status: AVAILABLE via npx

### ❌ Broken/Missing
1. **task-master** (Node)
   - File: `/Users/jim/Projects/OCR/task-master-mcp-server.js`
   - Status: FILE MISSING

2. **sequential-thinking-mcp** (NPM)
   - Status: May not exist as npm package (should use Python version)

## Issues Found

1. **Multiple conflicting configs** - 5 different MCP config files
2. **Path mismatches** - .config/.mcp.json points to wrong project (Email-Sync-Clean-Backup)
3. **Missing files** - task-master Node server doesn't exist
4. **API keys exposed** - .claude/mcp.json contains API keys
5. **Duplicate server definitions** - Same servers defined differently across configs

## Recommendations

### Primary Configuration Strategy
According to Anthropic's documentation:
- **Claude Desktop**: Uses `~/Library/Application Support/Claude/claude_desktop_config.json`
- **Claude Code (Terminal)**: Uses project `.mcp.json` in root directory

### Proposed Cleanup
1. **Keep**: 
   - `~/Library/Application Support/Claude/claude_desktop_config.json` (for Desktop)
   - `/Users/jim/Projects/Litigator_solo/.mcp.json` (for Claude Code)

2. **Remove/Archive**:
   - `/Users/jim/Projects/Litigator_solo/.config/.mcp.json` (outdated paths)
   - `/Users/jim/Projects/Litigator_solo/.claude/mcp.json` (contains exposed API keys)
   - `~/.config/claude-desktop/claude_desktop_config.json` (old project paths)

### Standardized Server Configuration
All servers should use consistent launch methods:
- Python servers: Direct python3 execution
- NPM servers: npx with package name
- Filesystem: Standard MCP filesystem server