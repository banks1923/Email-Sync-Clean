#!/bin/bash
# MCP Configuration Cleanup Script

echo "Creating backup directory..."
mkdir -p ~/mcp_config_backup/$(date +%Y%m%d)

echo "Backing up existing configs..."
cp ~/Library/Application\ Support/Claude/claude_desktop_config.json ~/mcp_config_backup/$(date +%Y%m%d)/ 2>/dev/null
cp .mcp.json ~/mcp_config_backup/$(date +%Y%m%d)/ 2>/dev/null
cp -r .claude ~/mcp_config_backup/$(date +%Y%m%d)/ 2>/dev/null
cp -r .config ~/mcp_config_backup/$(date +%Y%m%d)/ 2>/dev/null

echo "Removing redundant configs..."
rm -f ~/.config/claude-desktop/claude_desktop_config.json
rm -f .claude/mcp.json
rm -f .config/.mcp.json  
rm -f .config/claude_desktop_config.json

echo "Configs to keep:"
echo "  - ~/Library/Application Support/Claude/claude_desktop_config.json (Claude Desktop)"
echo "  - ./.mcp.json (Claude Code)"

echo "Choose configuration:"
echo "  1) Minimal (sequential-thinking only) - 50MB"
echo "  2) Full Python servers (no task-master) - 200MB"
echo "  3) Keep current (all 4 servers) - 350MB+"
read -p "Enter choice (1-3): " choice

case $choice in
  1) cp .mcp.json.optimized .mcp.json && echo "Applied minimal config";;
  2) cp .mcp.json.full .mcp.json && echo "Applied full Python config";;
  3) echo "Keeping current config";;
  *) echo "Invalid choice";;
esac

echo "Done! Restart Claude Code to apply changes."
