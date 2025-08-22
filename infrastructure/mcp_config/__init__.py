"""
MCP Configuration Infrastructure

Provides centralized, secure MCP server configuration using Pydantic.
Follows CLAUDE.md principles: Simple > Complex, Working > Perfect.
"""

from .config import MCPConfig, get_mcp_config
from .generate import generate_claude_desktop_config, generate_mcp_json

__all__ = [
    "MCPConfig",
    "get_mcp_config", 
    "generate_mcp_json",
    "generate_claude_desktop_config"
]