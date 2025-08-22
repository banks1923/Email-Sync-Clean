# MCP Configuration Infrastructure

Centralized, secure configuration management for all Model Context Protocol (MCP) servers.

## Overview

This module provides:
- **Secure API key management** via environment variables (~/Secrets/.env)
- **Unified configuration** for Claude Code (.mcp.json) and Claude Desktop
- **Validation and health checks** for all MCP servers
- **Graceful fallback** when dependencies are unavailable

## Quick Start

### Generate MCP Configurations

```bash
# Show current status
python3 infrastructure/mcp_config/generate.py status

# Generate .mcp.json for Claude Code
python3 infrastructure/mcp_config/generate.py generate

# Generate Claude Desktop config
python3 infrastructure/mcp_config/generate.py generate --claude-desktop

# Preview configuration without writing files
python3 infrastructure/mcp_config/generate.py generate --dry-run
```

### Using Makefile Targets

```bash
make mcp-status        # Show MCP configuration status
make mcp-generate      # Generate .mcp.json from Pydantic config
make mcp-validate      # Validate MCP servers can start
make mcp-clean         # Remove generated MCP configs
```

## Configuration Structure

### Core Files
- `config.py` - Main Pydantic configuration with validation
- `generate.py` - CLI tool for generating configurations
- `__init__.py` - Module exports for programmatic use

### Environment Variables

API keys are loaded from `~/Secrets/.env`:
```bash
ANTHROPIC_API_KEY=your_key_here
OPENAI_API_KEY=your_key_here
PERPLEXITY_API_KEY=your_key_here
GOOGLE_API_KEY=your_key_here
MISTRAL_API_KEY=your_key_here
```

### MCP Servers Configured

#### Always Available
- **Legal Intelligence**: Legal document analysis with Legal BERT
- **Search Intelligence**: Smart search and document clustering
- **Filesystem**: File system operations for Claude Code
- **Sequential Thinking**: Structured problem-solving framework

#### Conditional (based on API keys)
- **Task Master AI**: Advanced task management (requires AI API keys)

#### Claude Desktop Only
- **Memory**: Persistent knowledge graph across sessions
- **Puppeteer**: Browser automation capabilities

## Security Features

### API Key Protection
- ✅ No hardcoded secrets in configuration files
- ✅ Environment-based loading from ~/Secrets/.env
- ✅ SecretStr type for secure handling
- ✅ Automatic masking in logs

### File Permissions
- ⚠️ Automatic check for world-readable config files
- ⚠️ Warnings for insecure permissions

### Validation
- ✅ Server file existence checks
- ✅ Path validation for all components
- ✅ Graceful degradation when dependencies missing

## Programmatic Usage

### Basic Configuration
```python
from infrastructure.mcp_config import get_mcp_config

config = get_mcp_config()
servers = config.get_mcp_servers()
status = config.validate_config()
```

### Generate Configurations
```python
from infrastructure.mcp_config import generate_mcp_json, generate_claude_desktop_config

# Generate .mcp.json
generate_mcp_json()

# Generate Claude Desktop config
generate_claude_desktop_config()
```

## Architecture Principles

Following CLAUDE.md principles:

### ✅ Good Patterns
- **Simple > Complex**: Direct configuration, no factories
- **Working > Perfect**: Pragmatic validation with fallbacks
- **Direct > Indirect**: Import and use directly
- **Single Responsibility**: Each file has one clear purpose

### ❌ Anti-Patterns Avoided
- No dependency injection or factory patterns
- No over-engineering with abstract classes
- No complex routing or enterprise patterns
- No God modules - focused on configuration only

## Troubleshooting

### Common Issues

#### "pydantic-settings not available"
Install with: `pip install pydantic-settings`
The system gracefully falls back to dataclasses if unavailable.

#### "API keys not configured"
Check that ~/Secrets/.env exists and contains API keys.
Use `make mcp-status` to see current configuration.

#### "Server validation failed"
Check that all MCP server files exist:
```bash
python3 infrastructure/mcp_config/generate.py validate
```

#### Permission warnings
Fix with:
```bash
chmod 600 .mcp.json
chmod 600 ~/.config/claude/claude_desktop_config.json
```

### Debugging

Enable debug output:
```bash
LOG_LEVEL=DEBUG python3 infrastructure/mcp_config/generate.py status
```

## Integration with CLAUDE.md

This configuration system aligns with project principles:
- **NO Band-Aids**: Proper security and validation from start
- **Build it right, build it once**: Centralized configuration
- **Atomic Tasks**: Each command does one thing well
- **Best Practices**: Standard Python module structure