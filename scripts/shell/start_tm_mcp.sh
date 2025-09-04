#!/bin/bash
# Task Master MCP server startup script
# Sources environment from ~/Secrets/.env and starts the MCP server

# Source the environment
source ~/Secrets/.env

# Start Task Master MCP server
exec npx -y --package=task-master-ai task-master-ai "$@"