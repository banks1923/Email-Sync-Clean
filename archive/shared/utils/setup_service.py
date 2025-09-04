import json
import os
import subprocess
import sys
import time
from pathlib import Path

import requests  # For Qdrant check
from loguru import logger

from gmail.main import GmailService
from gmail.oauth import GmailAuth
from lib.db import SimpleDB


class SetupService:
    """
    Core setup logic for the Email Sync System, decoupled from UI.
    """

    def __init__(self, project_root: Path):
        self.project_root = project_root

    def check_python_version(self) -> bool:
        """
        Check if Python version is compatible.
        """
        version = sys.version_info
        return version.major == 3 and version.minor >= 9

    def install_dependencies(self) -> bool:
        """
        Install Python dependencies.
        """
        requirements_path = self.project_root / "requirements.txt"
        if not requirements_path.exists():
            logger.error(f"requirements.txt not found at {requirements_path}")
            return False

        result = subprocess.run(
            [sys.executable, "-m", "pip", "install", "-r", str(requirements_path)],
            capture_output=True,
            text=True
        )

        if result.returncode == 0:
            logger.info("Dependencies installed successfully")
            return True
        else:
            logger.error(f"Installation failed: {result.stderr}")
            return False

    def setup_gmail_auth(self, credentials_json_content: str | None = None) -> dict:
        """Set up Gmail authentication.

        If credentials_json_content is provided, it saves it first.
        """
        creds_path = self.project_root / "gmail" / "credentials.json"
        self.project_root / "gmail" / "token.json"

        if credentials_json_content:
            try:
                json.loads(credentials_json_content) # Validate JSON
                creds_path.parent.mkdir(exist_ok=True)
                creds_path.write_text(credentials_json_content)
                logger.info("Credentials saved")
            except json.JSONDecodeError:
                return {"success": False, "error": "Invalid JSON credentials"}

        # Run authentication flow
        auth = GmailAuth()
        result = auth.get_credentials()

        if result["success"]:
            logger.info("Gmail authenticated successfully")
        else:
            logger.error(f"Gmail authentication failed: {result.get('error')}")
        return result

    def configure_gmail_senders(self, filter_type: str, senders: list[str] | None = None) -> bool:
        """
        Configure email sender filters.
        """
        config_path = self.project_root / "gmail" / "config.py"

        if filter_type == "Specific senders only":
            if senders:
                config_content = f'''"""Gmail configuration for Email Sync System"""\n\nclass GmailConfig:\n    """Gmail service configuration"""\n    \n    def __init__(self):\n        self.max_results = 500\n        self.use_filters = True\n        self.preferred_senders = {senders!r}\n        \n    def build_query(self) -> str:\n        """Build Gmail search query from configured senders"""\n        if not self.use_filters or not self.preferred_senders:\n            return ""\n            \n        sender_queries = [f"from:{{sender}}" for sender in self.preferred_senders]\n        return f"({' OR '.join(sender_queries)})"\n'''
                config_path.write_text(config_content)
                logger.info(f"Configured {len(senders)} senders")
                return True
            else:
                logger.error("No senders provided for 'Specific senders only' filter type.")
                return False
        else: # All emails (no filter)
            config_content = '''"""Gmail configuration for Email Sync System"""\n\nclass GmailConfig:\n    """Gmail service configuration"""\n    \n    def __init__(self):\n        self.max_results = 500\n        self.use_filters = False\n        self.preferred_senders = []\n        \n    def build_query(self) -> str:\n        """Build Gmail search query from configured senders"""\n        return ""\n'''
            config_path.write_text(config_content)
            logger.info("Configured to sync all emails")
            return True
            
    def install_qdrant(self, system: str) -> bool:
        """
        Install Qdrant vector database.
        """
        install_commands = {
            "macOS (Apple Silicon)": [
                "curl -L -o /tmp/qdrant.tar.gz https://github.com/qdrant/qdrant/releases/download/v1.12.5/qdrant-aarch64-apple-darwin.tar.gz",
                "tar -xzf /tmp/qdrant.tar.gz -C /tmp",
                "mkdir -p ~/bin && cp /tmp/qdrant ~/bin/qdrant",
                "chmod +x ~/bin/qdrant"
            ],
            "macOS (Intel)": [
                "curl -L -o /tmp/qdrant.tar.gz https://github.com/qdrant/qdrant/releases/download/v1.12.5/qdrant-x86_64-apple-darwin.tar.gz",
                "tar -xzf /tmp/qdrant.tar.gz -C /tmp",
                "mkdir -p ~/bin && cp /tmp/qdrant ~/bin/qdrant",
                "chmod +x ~/bin/qdrant"
            ],
            "Linux": [
                "curl -L -o /tmp/qdrant.tar.gz https://github.com/qdrant/qdrant/releases/download/v1.12.5/qdrant-x86_64-unknown-linux-gnu.tar.gz",
                "tar -xzf /tmp/qdrant.tar.gz -C /tmp",
                "mkdir -p ~/bin && cp /tmp/qdrant ~/bin/qdrant",
                "chmod +x ~/bin/qdrant"
            ]
        }
        
        if system not in install_commands:
            logger.warning(f"Manual installation required for {system}. Visit: https://qdrant.tech/documentation/quick-start/")
            return False

        logger.info(f"Installing Qdrant for {system}...")
        
        for cmd in install_commands[system]:
            logger.info(f"Running: {cmd}")
            result = subprocess.run(cmd, shell=True, capture_output=True)
            if result.returncode != 0:
                logger.error(f"Command failed: {result.stderr}")
                return False
                
        logger.info("Qdrant installed to ~/bin/qdrant")
        
        # Test Qdrant
        logger.info("Testing Qdrant...")
        test_process = subprocess.Popen(
            [str(Path.home() / "bin" / "qdrant")],
            env={**os.environ, "QDRANT__STORAGE__PATH": str(self.project_root / "qdrant_data")},
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )
        
        time.sleep(3) # Give Qdrant time to start
        
        try:
            response = requests.get("http://localhost:6333/readiness", timeout=2)
            if response.status_code == 200:
                logger.info("Qdrant is working!")
                return True
        except requests.exceptions.ConnectionError:
            logger.warning("Qdrant installed but not responding (ConnectionError)")
        except Exception as e:
            logger.warning(f"Qdrant installed but not responding ({e})")
        finally:
            test_process.terminate() # Ensure process is terminated
            
        return False
            
    def initialize_database(self) -> dict:
        """
        Initialize the database.
        """
        try:
            db = SimpleDB()
            stats = db.get_content_stats()
            logger.info(f"Database initialized. Total content: {stats['total_content']}")
            return stats
        except Exception as e:
            logger.error(f"Database error: {e}")
            raise # Re-raise to be handled by wrapper

    def setup_mcp_servers(self) -> bool:
        """
        Configure MCP servers.
        """
        mcp_config = {
            "mcpServers": {
                "email-sync": {
                    "command": "python",
                    "args": ["-m", "infrastructure.mcp_servers.legal_intelligence_server"],
                    "cwd": str(self.project_root)
                },
                "search-intelligence": {
                    "command": "python",
                    "args": ["-m", "infrastructure.mcp_servers.search_intelligence_server"],
                    "cwd": str(self.project_root)
                }
            }
        }
        
        config_path = self.project_root / ".claude" / "mcp.json" # Assuming .claude is the config dir
        config_path.parent.mkdir(parents=True, exist_ok=True)
        config_path.write_text(json.dumps(mcp_config, indent=2))
        
        logger.info("MCP servers configured")
        return True
        
    def run_first_sync(self) -> dict:
        """
        Run the first email sync.
        """
        service = GmailService()
        result = service.sync_incremental(max_results=50) # Use incremental sync

        if result["success"]:
            logger.info(f"Synced {result['processed']} new emails ({result.get('duplicates', 0)} duplicates)")
        else:
            logger.error(f"Email sync failed: {result.get('error')}")
        return result
                
    def create_shortcuts(self, project_root: Path) -> Path:
        """
        Create convenient command shortcuts.
        """
        aliases = f"""# Email Sync System Shortcuts
# Add to your ~/.bashrc or ~/.zshrc

alias vsearch='{project_root}/tools/cli/vsearch'
alias vsync='python3 {project_root}/tools/scripts/run_full_system'
alias vsetup='python3 {project_root}/tools/scripts/setup_wizard'

# Quick commands
alias vsearch-maintenance='vsearch search maintenance'
alias vsearch-legal='vsearch legal process'
alias vsearch-info='vsearch info'
"""
        
        alias_path = project_root / "setup_aliases.sh"
        alias_path.write_text(aliases)
        
        logger.info(f"Created setup_aliases.sh at {alias_path}")
        return alias_path
        
    def save_configuration(self, config: dict, project_root: Path) -> Path:
        """
        Save setup configuration for future reference.
        """
        config_path = project_root / ".setup_complete"
        config_path.write_text(json.dumps({
            "setup_date": datetime.now().isoformat(), # Use current datetime
            "python_version": f"{sys.version_info.major}.{sys.version_info.minor}",
            "features": config
        }, indent=2))
        logger.info(f"Configuration saved to {config_path}")
        return config_path
