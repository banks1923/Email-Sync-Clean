#!/bin/bash
# Task Master MCP server startup script
# Sources environment from ~/Secrets/.env and starts the MCP server

# Source the environment (prefer /secrets/.env)
if [ -f /secrets/.env ]; then
  source /secrets/.env
elif [ -f "$HOME/Secrets/.env" ]; then
  source "$HOME/Secrets/.env"
elif [ -f ./.env ]; then
  source ./.env
fi

# Start Task Master MCP server
exec npx -y --package=task-master-ai task-master-ai "$@"
