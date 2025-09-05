#!/bin/bash
# Wrapper to load secrets before starting Task Master MCP server

# Load secrets (prefer /secrets/.env)
if [ -f /secrets/.env ]; then
  source /secrets/.env
elif [ -f "$HOME/Secrets/.env" ]; then
  source "$HOME/Secrets/.env"
elif [ -f ./.env ]; then
  source ./.env
fi

# Now run the Task Master server with the loaded environment
exec npx -y --package=task-master-ai task-master-ai
