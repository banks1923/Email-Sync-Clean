"""
Content search functionality using ripgrep for analog database.

Handles full-text search operations with ripgrep integration.
"""

import json
import subprocess
from pathlib import Path
from typing import Any, Dict, List, Optional

from loguru import logger


class ContentSearcher:
    """Handles content searching with ripgrep."""
    
    def __init__(self, base_path: Path):
        """Initialize content searcher."""
        self.base_path = base_path
        self.analog_db_path = base_path / "analog_db"
    
    def search_content(
        self,
        query: str,
        path: Optional[Path] = None,
        limit: int = 20,
        regex: bool = False,
        case_sensitive: bool = False
    ) -> List[Dict[str, Any]]:
        """Full-text search using ripgrep."""
        try:
            rg_args = self._build_ripgrep_args(
                query, path, limit, regex, case_sensitive
            )
            output = self._execute_ripgrep(rg_args)
            return self._parse_ripgrep_output(output, query)
        except Exception as e:
            logger.error(f"Content search failed: {e}")
            return []
    
    def _build_ripgrep_args(
        self,
        query: str,
        path: Optional[Path],
        limit: int,
        regex: bool,
        case_sensitive: bool
    ) -> List[str]:
        """Build ripgrep command arguments."""
        rg_args = [
            "rg",
            "--json",
            "--max-count", str(limit),
            "--type", "markdown",
            "--no-heading"
        ]
        
        if not case_sensitive:
            rg_args.append("--ignore-case")
        
        if not regex:
            rg_args.append("--fixed-strings")
        
        rg_args.append(query)
        search_path = path if path else self.analog_db_path
        rg_args.append(str(search_path))
        
        return rg_args
    
    def _execute_ripgrep(self, rg_args: List[str]) -> str:
        """Execute ripgrep command safely."""
        try:
            result = subprocess.run(
                rg_args,
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode not in (0, 1):
                logger.warning(f"ripgrep returned code {result.returncode}: {result.stderr}")
            
            return result.stdout
            
        except subprocess.TimeoutExpired:
            logger.error("ripgrep search timed out after 30 seconds")
            return ""
        except FileNotFoundError:
            logger.error("ripgrep not found - install ripgrep for fast search")
            return ""
        except Exception as e:
            logger.error(f"ripgrep execution failed: {e}")
            return ""
    
    def _parse_ripgrep_output(self, output: str, query: str) -> List[Dict[str, Any]]:
        """Parse ripgrep JSON output into structured results."""
        results = []
        
        for line in output.strip().split('\n'):
            if not line:
                continue
                
            try:
                data = json.loads(line)
                
                if data.get("type") == "match":
                    match_data = data.get("data", {})
                    path = match_data.get("path", {}).get("text", "")
                    line_num = match_data.get("line_number")
                    content = match_data.get("lines", {}).get("text", "")
                    
                    result = {
                        "file_path": path,
                        "line_number": line_num,
                        "matched_content": content.strip(),
                        "query": query,
                        "match_type": "content"
                    }
                    results.append(result)
                    
            except (json.JSONDecodeError, Exception) as e:
                logger.debug(f"Error parsing ripgrep output line: {e}")
                continue
        
        return results