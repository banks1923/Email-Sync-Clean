#!/bin/bash
# User Prompt Submit Hook - Automatically inject principles before each prompt

# Check if principles file exists
if [ -f "$HOME/.config/claude-principles.md" ]; then
    # Output principles with clear separator
    cat "$HOME/.config/claude-principles.md"
    echo -e "\n---\n"
fi

# Pass through the original prompt
cat
