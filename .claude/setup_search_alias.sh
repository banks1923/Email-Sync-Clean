#!/bin/bash
# Add this to your ~/.bashrc or ~/.zshrc

# Email Sync AI Search
alias aisearch='cd /Users/jim/Projects/Email\ Sync && scripts/vsearch search'
alias asearch='cd /Users/jim/Projects/Email\ Sync && scripts/search'

# Quick MCP search (if using Claude Desktop)
alias mcpsearch='echo "Use: hybrid_search query=\"your query\""'

echo "Search aliases added!"
echo "Usage:"
echo "  aisearch \"your query\"  - AI-powered search"
echo "  asearch \"your query\"   - Direct search"
echo "  mcpsearch             - Show MCP usage"
