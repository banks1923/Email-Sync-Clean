#!/bin/bash
# Update .mcp.json with actual API keys from environment

# Load secrets
source ~/Secrets/.env

# Check if keys are loaded
if [ -z "$ANTHROPIC_API_KEY" ]; then
    echo "Error: API keys not found in ~/Secrets/.env"
    exit 1
fi

# Create updated .mcp.json with actual keys
cat > .mcp.json.tmp << EOF
{
	"mcpServers": {
		"task-master-ai": {
			"type": "stdio",
			"command": "npx",
			"args": [
				"-y",
				"--package=task-master-ai",
				"task-master-ai"
			],
			"env": {
				"ANTHROPIC_API_KEY": "${ANTHROPIC_API_KEY:-}",
				"PERPLEXITY_API_KEY": "${PERPLEXITY_API_KEY:-}",
				"OPENAI_API_KEY": "${OPENAI_API_KEY:-}",
				"GOOGLE_API_KEY": "${GOOGLE_API_KEY:-}",
				"XAI_API_KEY": "${XAI_API_KEY:-}",
				"OPENROUTER_API_KEY": "${OPENROUTER_API_KEY:-}",
				"MISTRAL_API_KEY": "${MISTRAL_API_KEY:-}",
				"AZURE_OPENAI_API_KEY": "${AZURE_OPENAI_API_KEY:-}",
				"OLLAMA_API_KEY": "${OLLAMA_API_KEY:-}"
			}
		},
		"legal-intelligence": {
			"command": "python3",
			"args": [
				"infrastructure/mcp_servers/legal_intelligence_mcp.py"
			],
			"env": {
				"PYTHONPATH": "/Users/jim/Projects/Email-Sync-Clean-Backup"
			}
		},
		"search-intelligence": {
			"command": "python3",
			"args": [
				"infrastructure/mcp_servers/search_intelligence_mcp.py"
			],
			"env": {
				"PYTHONPATH": "/Users/jim/Projects/Email-Sync-Clean-Backup"
			}
		},
		"sequential-thinking": {
			"command": "python3",
			"args": [
				"/Users/jim/Projects/mcp-sequential-thinking/run_server.py"
			],
			"env": {
				"PYTHONPATH": "/Users/jim/Projects/mcp-sequential-thinking",
				"MCP_STORAGE_DIR": "/Users/jim/Projects/Email-Sync-Clean-Backup/data/system_data/sequential_thinking"
			}
		}
	}
}
EOF

# Replace the original file
mv .mcp.json.tmp .mcp.json
echo "✅ Updated .mcp.json with API keys from ~/Secrets/.env"
echo "   ANTHROPIC_API_KEY: $([ -n "$ANTHROPIC_API_KEY" ] && echo "✓ Set" || echo "✗ Missing")"
echo "   PERPLEXITY_API_KEY: $([ -n "$PERPLEXITY_API_KEY" ] && echo "✓ Set" || echo "✗ Missing")"
echo "   OPENAI_API_KEY: $([ -n "$OPENAI_API_KEY" ] && echo "✓ Set" || echo "✗ Missing")"
