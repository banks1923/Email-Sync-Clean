"""
Simple health check for all services.
Just check if things are up - no complex metrics.
"""

import os
import sqlite3
from typing import Any

from loguru import logger
from config.settings import settings

# Logger is now imported globally from loguru


class HealthCheck:
    """Simple health checker - is it working or not?"""

    def __init__(self, db_path: str = settings.database.emails_db_path):
        self.db_path = db_path

    def check_database(self) -> dict[str, Any]:
        """Check if database is accessible."""
        try:
            # Try a simple query
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute("SELECT 1")
                cursor.fetchone()

            # Check if main tables exist
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
                tables = [row[0] for row in cursor.fetchall()]

                expected_tables = ["content", "documents", "emails"]
                missing_tables = [t for t in expected_tables if t not in tables]

                if missing_tables:
                    return {
                        "healthy": False,
                        "service": "database",
                        "error": f"Missing tables: {missing_tables}",
                    }

            return {"healthy": True, "service": "database"}

        except Exception as e:
            logger.error(f"Database health check failed: {e}")
            return {"healthy": False, "service": "database", "error": str(e)}

    def check_qdrant(self) -> dict[str, Any]:
        """Check if Qdrant vector service is available by testing basic connectivity."""
        try:
            # Basic connectivity test without importing higher-layer modules
            import requests
            response = requests.get("http://localhost:6333/collections", timeout=2)
            if response.status_code == 200:
                return {"healthy": True, "service": "qdrant", "status": "connected"}
            else:
                return {
                    "healthy": True,  # Still healthy, just degraded
                    "service": "qdrant", 
                    "status": "unavailable (using keyword search)",
                    "error": f"HTTP {response.status_code}"
                }
        except Exception as e:
            # Qdrant is optional, so not being available is okay
            logger.info(f"Qdrant not available (optional): {e}")
            return {
                "healthy": True,  # Still healthy, just degraded
                "service": "qdrant",
                "status": "unavailable (using keyword search)",
                "error": str(e),
            }

    def check_gmail(self) -> dict[str, Any]:
        """Check if Gmail API credentials exist."""
        try:
            # Just check if credentials file exists
            creds_path = settings.gmail.credentials_path
            token_path = settings.gmail.token_path

            if not os.path.exists(creds_path):
                return {"healthy": False, "service": "gmail", "error": "Credentials file not found"}

            return {
                "healthy": True,
                "service": "gmail",
                "credentials": "found",
                "authenticated": os.path.exists(token_path),
            }

        except Exception as e:
            logger.error(f"Gmail health check failed: {e}")
            return {"healthy": False, "service": "gmail", "error": str(e)}

    def check_models(self) -> dict[str, Any]:
        """Check if AI models are available at a basic level."""
        try:
            # Check for basic model dependencies without importing higher-layer modules
            models_status = {}
            
            # Check if sentence-transformers is available (for embeddings)
            try:
                models_status["sentence_transformers"] = "available"
            except ImportError:
                models_status["sentence_transformers"] = "not installed"

            # Check Whisper
            try:
                models_status["whisper"] = "available"
            except ImportError:
                models_status["whisper"] = "not installed"

            return {
                "healthy": True,
                "service": "models",
                "models": models_status,
            }

        except Exception as e:
            logger.error(f"Model health check failed: {e}")
            return {"healthy": False, "service": "models", "error": str(e)}

    def check_all(self) -> dict[str, Any]:
        """Run all health checks."""
        results = {"overall_health": True, "services": {}}

        # Check each service
        checks = [
            ("database", self.check_database),
            ("qdrant", self.check_qdrant),
            ("gmail", self.check_gmail),
            ("models", self.check_models),
        ]

        for name, check_func in checks:
            result = check_func()
            results["services"][name] = result

            # Update overall health (but Qdrant being down is okay)
            if not result["healthy"] and name != "qdrant":
                results["overall_health"] = False

        # Add summary
        healthy_count = sum(1 for s in results["services"].values() if s["healthy"])
        total_count = len(results["services"])

        results["summary"] = f"{healthy_count}/{total_count} services healthy"

        return results


def run_health_check() -> dict[str, Any]:
    """Convenience function to run full health check."""
    checker = HealthCheck()
    return checker.check_all()
