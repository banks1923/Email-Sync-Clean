"""
MCP Configuration with Pydantic Validation

Secure, centralized configuration for all MCP servers with environment-based
API key loading. Follows CLAUDE.md principles: Simple > Complex, Working > Perfect.
"""

import os
from pathlib import Path
from typing import Dict, List, Optional, Any

try:
    from pydantic_settings import BaseSettings
    from pydantic import Field, SecretStr
    PYDANTIC_AVAILABLE = True
except ImportError:
    # Graceful fallback - use dataclasses
    from dataclasses import dataclass, field
    PYDANTIC_AVAILABLE = False
    print("Warning: pydantic-settings not available, using simple dataclass fallback")


if PYDANTIC_AVAILABLE:
    class MCPConfig(BaseSettings):
        """MCP Configuration with Pydantic validation"""
        
        # Project paths
        project_root: Path = Field(default=Path("/Users/jim/Projects/Email-Sync-Clean-Backup"))
        
        # Optional API keys (loaded from environment)
        anthropic_api_key: Optional[SecretStr] = Field(None, alias='ANTHROPIC_API_KEY')
        openai_api_key: Optional[SecretStr] = Field(None, alias='OPENAI_API_KEY')
        perplexity_api_key: Optional[SecretStr] = Field(None, alias='PERPLEXITY_API_KEY')
        google_api_key: Optional[SecretStr] = Field(None, alias='GOOGLE_API_KEY')
        mistral_api_key: Optional[SecretStr] = Field(None, alias='MISTRAL_API_KEY')
        
        class Config:
            env_file = "/Users/jim/Secrets/.env"
            env_file_encoding = 'utf-8'
            extra = 'ignore'  # Ignore extra environment variables
            
        def get_mcp_servers(self) -> Dict[str, Dict[str, Any]]:
            """Generate MCP server configurations"""
            servers = {
                "legal-intelligence": {
                    "type": "stdio",
                    "command": "python3",
                    "args": ["infrastructure/mcp_servers/legal_intelligence_mcp.py"],
                    "env": {"PYTHONPATH": str(self.project_root)}
                },
                "search-intelligence": {
                    "type": "stdio", 
                    "command": "python3",
                    "args": ["infrastructure/mcp_servers/search_intelligence_mcp.py"],
                    "env": {"PYTHONPATH": str(self.project_root)}
                },
                "filesystem": {
                    "type": "stdio",
                    "command": "npx",
                    "args": ["-y", "@modelcontextprotocol/server-filesystem", str(self.project_root)]
                },
                "sequential-thinking": {
                    "type": "stdio",
                    "command": "python3",
                    "args": ["/Users/jim/Projects/mcp-sequential-thinking/run_server.py"],
                    "env": {
                        "PYTHONPATH": "/Users/jim/Projects/mcp-sequential-thinking",
                        "MCP_STORAGE_DIR": str(self.project_root / "data/sequential_thinking")
                    }
                }
            }
            
            # Add task-master-ai if API keys available
            if self.anthropic_api_key or self.openai_api_key or self.google_api_key:
                servers["task-master-ai"] = {
                    "type": "stdio",
                    "command": "npx",
                    "args": ["-y", "--package=task-master-ai", "task-master-ai"]
                    # API keys loaded from environment automatically
                }
                
            return servers
        
        def get_claude_desktop_servers(self) -> Dict[str, Dict[str, Any]]:
            """Generate Claude Desktop server configurations (different format)"""
            servers = {
                "email-sync": {
                    "command": "python3",
                    "args": ["infrastructure/mcp_servers/legal_intelligence_mcp.py"],
                    "env": {"PYTHONPATH": str(self.project_root)}
                },
                "search-intelligence": {
                    "command": "python3",
                    "args": ["infrastructure/mcp_servers/search_intelligence_mcp.py"],
                    "env": {"PYTHONPATH": str(self.project_root)}
                },
                "filesystem": {
                    "command": "npx",
                    "args": ["-y", "@modelcontextprotocol/server-filesystem", str(self.project_root)]
                },
                "sequential-thinking": {
                    "command": "python3",
                    "args": ["/Users/jim/Projects/mcp-sequential-thinking/run_server.py"],
                    "env": {
                        "PYTHONPATH": "/Users/jim/Projects/mcp-sequential-thinking",
                        "MCP_STORAGE_DIR": str(self.project_root / "data/sequential_thinking")
                    }
                }
            }
            
            # Add memory MCP server
            servers["memory"] = {
                "command": "npx",
                "args": ["-y", "@modelcontextprotocol/server-memory"]
            }
            
            # Add puppeteer for browser automation
            servers["puppeteer"] = {
                "command": "npx",
                "args": ["-y", "@modelcontextprotocol/server-puppeteer"]
            }
                
            return servers
        
        def validate_config(self) -> Dict[str, str]:
            """Validate configuration and return status"""
            status = {}
            status["project_root"] = "✅ Valid" if self.project_root.exists() else "❌ Missing"
            status["legal_mcp"] = "✅ Found" if (self.project_root / "infrastructure/mcp_servers/legal_intelligence_mcp.py").exists() else "❌ Missing"
            status["search_mcp"] = "✅ Found" if (self.project_root / "infrastructure/mcp_servers/search_intelligence_mcp.py").exists() else "❌ Missing"
            
            # Check for sequential thinking server
            seq_thinking_path = Path("/Users/jim/Projects/mcp-sequential-thinking/run_server.py")
            status["sequential_thinking"] = "✅ Found" if seq_thinking_path.exists() else "⚠️ Missing"
            
            api_count = sum(1 for key in [
                self.anthropic_api_key, self.openai_api_key, self.perplexity_api_key, 
                self.google_api_key, self.mistral_api_key
            ] if key)
            status["api_keys"] = f"✅ {api_count} configured" if api_count > 0 else "⚠️ None configured"
            
            return status
        
        def check_security(self) -> List[str]:
            """Check for security issues"""
            warnings = []
            
            # Check if .mcp.json exists and is readable by others
            mcp_json = self.project_root / ".mcp.json"
            if mcp_json.exists():
                stat = mcp_json.stat()
                if stat.st_mode & 0o044:  # Check if readable by group/others
                    warnings.append("⚠️ .mcp.json is readable by group/others")
            
            # Check if config file exists and has secure permissions
            claude_config = Path.home() / ".config/claude/claude_desktop_config.json"
            if claude_config.exists():
                stat = claude_config.stat()
                if stat.st_mode & 0o044:
                    warnings.append("⚠️ Claude Desktop config is readable by group/others")
            
            return warnings

else:
    # Simple fallback without validation
    @dataclass
    class MCPConfig:
        project_root: Path = field(default_factory=lambda: Path("/Users/jim/Projects/Email-Sync-Clean-Backup"))
        
        def get_mcp_servers(self) -> Dict[str, Dict[str, Any]]:
            return {
                "legal-intelligence": {
                    "type": "stdio",
                    "command": "python3", 
                    "args": ["infrastructure/mcp_servers/legal_intelligence_mcp.py"],
                    "env": {"PYTHONPATH": str(self.project_root)}
                },
                "search-intelligence": {
                    "type": "stdio",
                    "command": "python3",
                    "args": ["infrastructure/mcp_servers/search_intelligence_mcp.py"], 
                    "env": {"PYTHONPATH": str(self.project_root)}
                }
            }
        
        def get_claude_desktop_servers(self) -> Dict[str, Dict[str, Any]]:
            return self.get_mcp_servers()
        
        def validate_config(self) -> Dict[str, str]:
            return {"status": "✅ Basic configuration (no validation)"}
        
        def check_security(self) -> List[str]:
            return ["⚠️ No security checks available without Pydantic"]


def get_mcp_config() -> MCPConfig:
    """Get MCP configuration with error handling"""
    try:
        return MCPConfig()
    except Exception as e:
        print(f"Warning: Configuration error: {e}")
        # Return minimal working config
        if PYDANTIC_AVAILABLE:
            return MCPConfig(project_root=Path.cwd())
        else:
            return MCPConfig()