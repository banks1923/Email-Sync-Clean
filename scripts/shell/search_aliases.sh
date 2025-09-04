#!/bin/bash
# Add these to your ~/.zshrc or ~/.bashrc for quick access

# Unified search CLI
alias search='python3 ~/Projects/Litigator_solo/tools/scripts/vsearch search'

# Export search to HTML and open in browser
alias searchhtml='python3 ~/Projects/Litigator_solo/tools/scripts/export_search.py'

# Quick database query
function searchdb() {
    sqlite3 ~/Projects/Litigator_solo/data/system_data/emails.db \
        "SELECT title, substr(body, 1, 500) FROM content_unified WHERE body LIKE '%$1%' LIMIT 10"
}

# Search and save to file
function searchsave() {
    tools/scripts/vsearch search "$1" > "search_results_$(date +%Y%m%d_%H%M%S).txt"
    echo "Saved to: search_results_$(date +%Y%m%d_%H%M%S).txt"
}

echo "Add these aliases to your shell config:"
echo "source ~/Projects/Litigator_solo/search_aliases.sh"
