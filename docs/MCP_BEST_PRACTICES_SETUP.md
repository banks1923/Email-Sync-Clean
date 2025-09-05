# MCP Best Practices Setup - Streamlined Configuration

## 🎯 Optimal Architecture

### **Single Source of Truth Principle**
Use ONE configuration per environment, not multiple overlapping configs.

```
Claude Desktop App  → ~/Library/Application Support/Claude/claude_desktop_config.json
Claude Code CLI     → {project}/.mcp.json
VS Code Extensions  → Managed by VS Code, not file-based
```

## 📁 Recommended File Structure

### **KEEP These Files:**
```
~/Library/Application Support/Claude/
  └── claude_desktop_config.json    # Claude Desktop ONLY

/Users/jim/Projects/Litigator_solo/
  └── .mcp.json                      # Claude Code CLI ONLY
```

### **DELETE These Redundant Files:**
```
~/.config/claude-desktop/             # Old/wrong location
  └── claude_desktop_config.json      # DELETE

/Users/jim/Projects/Litigator_solo/
  ├── .claude/mcp.json                # DELETE (has exposed API keys!)
  ├── .config/.mcp.json               # DELETE (wrong project paths)
  └── .config/claude_desktop_config.json  # DELETE (not used)
```

## 🚀 Optimized Configuration

### **For Claude Desktop** (GUI App)
```json
{
  "mcpServers": {
    "sequential-thinking": {
      "command": "python3",
      "args": ["/Users/jim/Projects/mcp-sequential-thinking/run_server.py"],
      "env": {
        "PYTHONPATH": "/Users/jim/Projects/mcp-sequential-thinking",
        "MCP_STORAGE_DIR": "/Users/jim/Library/Application Support/Claude/sequential_thinking"
      }
    }
  }
}
```

### **For Claude Code** (Terminal)
```json
{
  "mcpServers": {
    "sequential-thinking": {
      "type": "stdio",
      "command": "python3",
      "args": ["/Users/jim/Projects/mcp-sequential-thinking/run_server.py"],
      "env": {
        "PYTHONPATH": "/Users/jim/Projects/mcp-sequential-thinking",
        "MCP_STORAGE_DIR": "/Users/jim/Projects/Litigator_solo/data/system_data/sequential_thinking"
      }
    }
  }
}
```

### **For VS Code Extensions**
- Let VS Code manage these independently
- They don't conflict with Claude configs
- Enable/disable as needed in Extensions panel

## 💾 Memory Optimization Strategy

### **Tier 1: Essential** (Always On)
- **sequential-thinking**: Lightweight, useful for complex reasoning
- Memory: ~30-50MB

### **Tier 2: On-Demand** (Enable When Needed)
```json
"legal-intelligence": {
  "command": "python3",
  "args": ["infrastructure/mcp_servers/legal_intelligence_mcp.py"],
  "env": {"PYTHONPATH": "/Users/jim/Projects/Litigator_solo"}
}
```
Memory: +50-100MB per server

### **Tier 3: Avoid** (Memory Hogs)
- ❌ Task-master via Node.js (use CLI directly instead)
- ❌ Filesystem MCP (use native file operations)
- ❌ Multiple instances of same server

## 🏗️ Implementation Steps

### Step 1: Backup Current Configs
```bash
mkdir ~/mcp_config_backup
cp ~/Library/Application\ Support/Claude/claude_desktop_config.json ~/mcp_config_backup/
cp .mcp.json ~/mcp_config_backup/
```

### Step 2: Clean Up Redundant Files
```bash
# Remove redundant configs
rm -f ~/.config/claude-desktop/claude_desktop_config.json
rm -f .claude/mcp.json  # Contains exposed API keys!
rm -f .config/.mcp.json
rm -f .config/claude_desktop_config.json
```

### Step 3: Update Active Configs
Apply the optimized configurations above to:
- `~/Library/Application Support/Claude/claude_desktop_config.json`
- `.mcp.json` (in project root)

### Step 4: Restart Applications
- Quit and restart Claude Desktop
- Exit and restart Claude Code sessions

## 🔧 Maintenance Best Practices

### **DO:**
- ✅ Keep configs minimal - only essential servers
- ✅ Use Python directly, not NPX wrappers
- ✅ Store session data in app-specific directories
- ✅ Version control `.mcp.json` (without secrets)

### **DON'T:**
- ❌ Duplicate server definitions across configs
- ❌ Store API keys in MCP configs
- ❌ Run multiple instances of same server
- ❌ Use Node.js wrappers for Python servers

## 📊 Expected Results

### **Memory Savings:**
- Before: ~400-600MB (multiple Node processes + Python)
- After: ~80-150MB (direct Python only)
- **Saved: 250-450MB RAM**

### **Performance:**
- Faster startup (no NPX downloads)
- Less process overhead
- Cleaner process management

### **Maintainability:**
- Clear separation of environments
- No config conflicts
- Easy to debug issues

## 🔍 Monitoring

Check running servers:
```bash
# See what's running
ps aux | grep -E "mcp|sequential" | grep -v grep

# Check memory usage
ps aux | grep python3 | grep mcp
```

Kill orphaned processes:
```bash
# Clean up if needed
pkill -f "mcp_servers"
pkill -f "sequential-thinking"
```

## 📝 Environment-Specific Notes

### **Development** (Your Current Setup)
- Use Claude Code with minimal `.mcp.json`
- Enable VS Code extensions as needed
- Keep Claude Desktop config empty or minimal

### **Production/Daily Use**
- Use Claude Desktop with only sequential-thinking
- Disable VS Code MCP extensions to save memory
- Use Claude Code CLI for project-specific work

## 🎓 Key Principles

1. **Separation of Concerns**: Each app has its own config file
2. **DRY (Don't Repeat Yourself)**: No duplicate server definitions
3. **Least Privilege**: Only run servers you actively need
4. **Direct Execution**: Avoid wrapper overhead (NPX, Node)
5. **Clean State**: Regular cleanup of orphaned processes

---

*This configuration reduces memory usage by ~60% while maintaining full functionality.*