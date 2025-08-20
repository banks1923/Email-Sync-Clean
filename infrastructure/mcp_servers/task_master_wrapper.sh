#!/bin/bash
# Wrapper to load secrets before starting Task Master MCP server

# Load secrets from your centralized location
source ~/Secrets/.env

# Now run the Task Master server with the loaded environment
exec npx -y --package=task-master-ai task-master-ai