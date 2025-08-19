"""
System health monitoring and diagnostic tools
"""

import os
import subprocess
from datetime import datetime, timedelta
from pathlib import Path

import psutil
from rich.console import Console
from rich.progress import track
from rich.table import Table

console = Console()

class HealthMonitor:
    """Comprehensive system health monitoring"""
    
    def __init__(self):
        self.project_root = Path(__file__).parent.parent.parent
        self.issues = []
        self.warnings = []
        
    def check_system_resources(self) -> dict:
        """Check system resource usage"""
        try:
            # Memory usage
            memory = psutil.virtual_memory()
            memory_percent = memory.percent
            memory_available = memory.available // (1024**3)  # GB
            
            # Disk usage
            disk = psutil.disk_usage(self.project_root)
            disk_percent = (disk.used / disk.total) * 100
            disk_free = disk.free // (1024**3)  # GB
            
            # CPU usage
            cpu_percent = psutil.cpu_percent(interval=1)
            
            resources = {
                "memory_percent": memory_percent,
                "memory_available_gb": memory_available,
                "disk_percent": disk_percent,
                "disk_free_gb": disk_free,
                "cpu_percent": cpu_percent,
                "healthy": True
            }
            
            # Check for resource issues
            if memory_percent > 90:
                self.issues.append(f"High memory usage: {memory_percent:.1f}%")
                resources["healthy"] = False
            elif memory_percent > 80:
                self.warnings.append(f"Memory usage high: {memory_percent:.1f}%")
                
            if disk_percent > 95:
                self.issues.append(f"Disk almost full: {disk_percent:.1f}%")
                resources["healthy"] = False
            elif disk_percent > 85:
                self.warnings.append(f"Disk usage high: {disk_percent:.1f}%")
                
            if cpu_percent > 90:
                self.warnings.append(f"High CPU usage: {cpu_percent:.1f}%")
                
            return resources
            
        except Exception as e:
            self.issues.append(f"Resource check failed: {e}")
            return {"healthy": False, "error": str(e)}
            
    def check_database_health(self) -> dict:
        """Check database integrity and performance"""
        try:
            from shared.simple_db import SimpleDB
            
            db = SimpleDB()
            db_path = Path("emails.db")
            
            health = {
                "exists": db_path.exists(),
                "size_mb": 0,
                "tables_ok": False,
                "content_count": 0,
                "integrity_ok": False,
                "healthy": True
            }
            
            if not db_path.exists():
                self.issues.append("Database file not found")
                health["healthy"] = False
                return health
                
            # File size
            health["size_mb"] = db_path.stat().st_size / (1024**2)
            
            # Check basic operations
            try:
                stats = db.get_content_stats()
                health["content_count"] = stats.get("total_content", 0)
                health["tables_ok"] = True
            except Exception as e:
                self.issues.append(f"Database query failed: {e}")
                health["healthy"] = False
                
            # Check integrity (quick check)
            try:
                result = subprocess.run(
                    ["sqlite3", str(db_path), "PRAGMA quick_check;"],
                    capture_output=True,
                    text=True,
                    timeout=10
                )
                if result.returncode == 0 and "ok" in result.stdout.lower():
                    health["integrity_ok"] = True
                else:
                    self.warnings.append("Database integrity check failed")
            except Exception:
                self.warnings.append("Could not run integrity check")
                
            # Size warnings
            if health["size_mb"] > 1000:  # 1GB
                self.warnings.append(f"Large database: {health['size_mb']:.1f}MB")
                
            return health
            
        except Exception as e:
            self.issues.append(f"Database health check failed: {e}")
            return {"healthy": False, "error": str(e)}
            
    def check_dependencies(self) -> dict:
        """Check Python dependencies"""
        try:
            required_packages = [
                "loguru",
                "numpy", 
                "torch",
                "transformers",
                "qdrant-client",
                "rich",
                "questionary"
            ]
            
            missing = []
            versions = {}
            
            for package in track(required_packages, description="Checking dependencies..."):
                try:
                    if package == "qdrant-client":
                        import qdrant_client
                        versions[package] = qdrant_client.__version__
                    elif package == "torch":
                        import torch
                        versions[package] = torch.__version__
                    elif package == "transformers":
                        import transformers
                        versions[package] = transformers.__version__
                    elif package == "numpy":
                        import numpy
                        versions[package] = numpy.__version__
                    elif package == "loguru":
                        import loguru
                        versions[package] = loguru.__version__
                    elif package == "rich":
                        import rich
                        versions[package] = rich.__version__
                    elif package == "questionary":
                        import questionary
                        versions[package] = questionary.__version__
                        
                except ImportError:
                    missing.append(package)
                    
            deps = {
                "missing": missing,
                "versions": versions,
                "healthy": len(missing) == 0
            }
            
            if missing:
                self.issues.append(f"Missing packages: {', '.join(missing)}")
                
            return deps
            
        except Exception as e:
            self.issues.append(f"Dependency check failed: {e}")
            return {"healthy": False, "error": str(e)}
            
    def check_gmail_connection(self) -> dict:
        """Test Gmail API connection"""
        try:
            from gmail.gmail_api import GmailAPI
            from gmail.oauth import GmailAuth

            # Check credentials
            creds_path = Path("gmail/credentials.json")
            token_path = Path("gmail/token.json")
            
            gmail_health = {
                "credentials_exist": creds_path.exists(),
                "token_exists": token_path.exists(),
                "connection_ok": False,
                "profile_ok": False,
                "healthy": True
            }
            
            if not creds_path.exists():
                self.issues.append("Gmail credentials.json missing")
                gmail_health["healthy"] = False
                return gmail_health
                
            if not token_path.exists():
                self.warnings.append("Gmail token.json missing (need to authenticate)")
                gmail_health["healthy"] = False
                return gmail_health
                
            # Test authentication
            auth = GmailAuth()
            result = auth.get_credentials()
            
            if not result["success"]:
                self.issues.append(f"Gmail auth failed: {result.get('error')}")
                gmail_health["healthy"] = False
                return gmail_health
                
            gmail_health["connection_ok"] = True
            
            # Test API call
            try:
                api = GmailAPI()
                profile_result = api.get_profile()
                if profile_result["success"]:
                    gmail_health["profile_ok"] = True
                    gmail_health["email"] = profile_result.get("email")
                else:
                    self.warnings.append("Gmail profile fetch failed")
            except Exception as e:
                self.warnings.append(f"Gmail API test failed: {e}")
                
            return gmail_health
            
        except Exception as e:
            self.issues.append(f"Gmail check failed: {e}")
            return {"healthy": False, "error": str(e)}
            
    def check_qdrant_status(self) -> dict:
        """Check Qdrant vector database status"""
        try:
            import requests
            
            qdrant_health = {
                "running": False,
                "reachable": False,
                "collections": 0,
                "points": 0,
                "healthy": True  # Qdrant is optional
            }
            
            # Test connection
            try:
                response = requests.get("http://localhost:6333/readiness", timeout=5)
                if response.status_code == 200:
                    qdrant_health["running"] = True
                    qdrant_health["reachable"] = True
                    
                    # Get collection info
                    collections_response = requests.get("http://localhost:6333/collections", timeout=5)
                    if collections_response.status_code == 200:
                        data = collections_response.json()
                        collections = data.get("result", {}).get("collections", [])
                        qdrant_health["collections"] = len(collections)
                        
                        # Get point count for 'emails' collection
                        for collection in collections:
                            if collection.get("name") == "emails":
                                points_response = requests.get(
                                    "http://localhost:6333/collections/emails",
                                    timeout=5
                                )
                                if points_response.status_code == 200:
                                    collection_data = points_response.json()
                                    qdrant_health["points"] = collection_data.get("result", {}).get("points_count", 0)
                                break
                                
            except requests.exceptions.ConnectionError:
                # Qdrant not running - this is OK, it's optional
                pass
            except Exception as e:
                self.warnings.append(f"Qdrant check error: {e}")
                
            return qdrant_health
            
        except Exception as e:
            self.warnings.append(f"Qdrant status check failed: {e}")
            return {"healthy": True, "error": str(e)}  # Still healthy since optional
            
    def check_log_files(self) -> dict:
        """Check log file status and recent errors"""
        try:
            logs_dir = Path("logs")
            
            log_health = {
                "directory_exists": logs_dir.exists(),
                "file_count": 0,
                "total_size_mb": 0,
                "recent_errors": 0,
                "healthy": True
            }
            
            if not logs_dir.exists():
                self.warnings.append("Logs directory not found")
                return log_health
                
            # Count files and size
            log_files = list(logs_dir.glob("*.log"))
            log_health["file_count"] = len(log_files)
            
            total_size = sum(f.stat().st_size for f in log_files)
            log_health["total_size_mb"] = total_size / (1024**2)
            
            # Check for recent errors
            cutoff = datetime.now() - timedelta(hours=24)
            error_count = 0
            
            for log_file in log_files:
                try:
                    # Only check recent log files
                    if datetime.fromtimestamp(log_file.stat().st_mtime) > cutoff:
                        with open(log_file) as f:
                            for line in f:
                                if "ERROR" in line or "CRITICAL" in line:
                                    error_count += 1
                except Exception:
                    continue
                    
            log_health["recent_errors"] = error_count
            
            # Warnings
            if log_health["total_size_mb"] > 100:
                self.warnings.append(f"Large log files: {log_health['total_size_mb']:.1f}MB")
                
            if error_count > 10:
                self.warnings.append(f"Many recent errors: {error_count}")
                
            return log_health
            
        except Exception as e:
            self.warnings.append(f"Log check failed: {e}")
            return {"healthy": True, "error": str(e)}
            
    def check_file_permissions(self) -> dict:
        """Check critical file permissions"""
        try:
            critical_paths = [
                "emails.db",
                "gmail/",
                "logs/",
                "data/",
                "tools/scripts/"
            ]
            
            perms = {
                "readable": [],
                "writable": [],
                "issues": [],
                "healthy": True
            }
            
            for path_str in critical_paths:
                path = Path(path_str)
                if path.exists():
                    if os.access(path, os.R_OK):
                        perms["readable"].append(path_str)
                    else:
                        perms["issues"].append(f"Cannot read {path_str}")
                        perms["healthy"] = False
                        
                    if os.access(path, os.W_OK):
                        perms["writable"].append(path_str)
                    else:
                        perms["issues"].append(f"Cannot write {path_str}")
                        perms["healthy"] = False
                        
            if perms["issues"]:
                for issue in perms["issues"]:
                    self.issues.append(issue)
                    
            return perms
            
        except Exception as e:
            self.issues.append(f"Permission check failed: {e}")
            return {"healthy": False, "error": str(e)}
            
    def run_comprehensive_check(self, verbose: bool = False) -> dict:
        """Run all health checks"""
        console.print("[bold cyan]🏥 Running System Health Check[/bold cyan]")
        
        results = {}
        
        # Run all checks
        checks = [
            ("System Resources", self.check_system_resources),
            ("Database Health", self.check_database_health),
            ("Dependencies", self.check_dependencies),
            ("Gmail Connection", self.check_gmail_connection),
            ("Qdrant Status", self.check_qdrant_status),
            ("Log Files", self.check_log_files),
            ("File Permissions", self.check_file_permissions)
        ]
        
        for check_name, check_func in track(checks, description="Running checks..."):
            try:
                results[check_name.lower().replace(" ", "_")] = check_func()
            except Exception as e:
                results[check_name.lower().replace(" ", "_")] = {
                    "healthy": False,
                    "error": str(e)
                }
                self.issues.append(f"{check_name} check failed: {e}")
                
        # Overall health
        overall_healthy = all(
            result.get("healthy", False) 
            for result in results.values()
        )
        
        results["overall"] = {
            "healthy": overall_healthy,
            "issues": len(self.issues),
            "warnings": len(self.warnings)
        }
        
        # Display results
        self._display_health_results(results, verbose)
        
        return results
        
    def _display_health_results(self, results: dict, verbose: bool):
        """Display health check results"""
        
        # Overall status
        overall = results.get("overall", {})
        if overall.get("healthy", False):
            status_color = "green"
            status_icon = "✅"
            status_text = "HEALTHY"
        else:
            status_color = "red"
            status_icon = "❌"
            status_text = "NEEDS ATTENTION"
            
        console.print(f"\n[bold {status_color}]{status_icon} Overall Status: {status_text}[/bold {status_color}]")
        
        if self.issues:
            console.print(f"\n[bold red]🚨 Issues ({len(self.issues)}):[/bold red]")
            for issue in self.issues:
                console.print(f"  [red]• {issue}[/red]")
                
        if self.warnings:
            console.print(f"\n[bold yellow]⚠️  Warnings ({len(self.warnings)}):[/bold yellow]")
            for warning in self.warnings:
                console.print(f"  [yellow]• {warning}[/yellow]")
                
        if verbose or self.issues or self.warnings:
            console.print("\n[bold]Detailed Results:[/bold]")
            
            # Create summary table
            table = Table(title="Health Check Details")
            table.add_column("Component", style="cyan")
            table.add_column("Status", style="white")
            table.add_column("Details", style="dim")
            
            for check_name, result in results.items():
                if check_name == "overall":
                    continue
                    
                display_name = check_name.replace("_", " ").title()
                
                if result.get("healthy", False):
                    status = "[green]✅ OK[/green]"
                    details = self._get_check_details(check_name, result)
                else:
                    status = "[red]❌ ISSUE[/red]"
                    details = result.get("error", "Failed")
                    
                table.add_row(display_name, status, details)
                
            console.print(table)
            
    def _get_check_details(self, check_name: str, result: dict) -> str:
        """Get human-readable details for a check"""
        if check_name == "system_resources":
            return f"Memory: {result.get('memory_percent', 0):.1f}%, Disk: {result.get('disk_percent', 0):.1f}%"
        elif check_name == "database_health":
            return f"{result.get('content_count', 0)} items, {result.get('size_mb', 0):.1f}MB"
        elif check_name == "dependencies":
            return f"{len(result.get('versions', {}))} packages installed"
        elif check_name == "gmail_connection":
            return f"Connected as {result.get('email', 'unknown')}"
        elif check_name == "qdrant_status":
            if result.get("running"):
                return f"{result.get('collections', 0)} collections, {result.get('points', 0)} points"
            else:
                return "Not running (optional)"
        elif check_name == "log_files":
            return f"{result.get('file_count', 0)} files, {result.get('recent_errors', 0)} recent errors"
        elif check_name == "file_permissions":
            return f"{len(result.get('readable', []))} readable, {len(result.get('writable', []))} writable"
        else:
            return "OK"


def health_check_command(verbose: bool = False):
    """CLI command for health check"""
    monitor = HealthMonitor()
    results = monitor.run_comprehensive_check(verbose)
    
    # Return appropriate exit code
    return 0 if results.get("overall", {}).get("healthy", False) else 1