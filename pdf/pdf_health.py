"""
PDF service health monitoring functionality
"""

from datetime import datetime
from typing import Any


class PDFHealthManager:
    """Manages health checking for PDF service"""

    def __init__(self, processor, storage, validator, health_monitor, logger) -> None:
        self.processor = processor
        self.storage = storage
        self.validator = validator
        self.health_monitor = health_monitor
        self.logger = logger

    def perform_health_check(self) -> dict[str, Any]:
        """Perform comprehensive health check for PDF service"""
        try:
            health_metrics = self._gather_health_metrics()
            if not health_metrics["success"]:
                return health_metrics

            service_healthy = self._evaluate_service_health(health_metrics)
            return self._build_health_response(health_metrics, service_healthy)

        except Exception as e:
            return self._build_error_response(e, "Health check failed")

    def _gather_health_metrics(self) -> dict[str, Any]:
        """Gather all health-related metrics"""
        # Check dependencies
        deps_check = self.processor.validate_dependencies()
        if not deps_check["success"]:
            return deps_check

        return {
            "success": True,
            "database": self.health_monitor.health_check(),
            "pdf_stats": self.storage.get_pdf_stats(),
            "performance": self.health_monitor.get_performance_report(),
            "system": self.validator.check_system_health(),
            "constants": self.validator.get_resource_constants(),
        }

    def _evaluate_service_health(self, metrics: dict[str, Any]) -> bool:
        """Evaluate overall service health from metrics"""
        db_health = metrics["database"]
        pdf_stats = metrics["pdf_stats"]
        system_health = metrics["system"]
        resources = system_health.get("resources", {})
        constants = metrics["constants"]

        return (
            db_health.get("success", False)
            and pdf_stats.get("success", False)
            and system_health.get("success", False)
            and resources.get("memory_available_mb", 0) > constants["memory_threshold_mb"]
            and db_health.get("disk", {}).get("available_space_mb", 0) > 100
        )

    def _build_health_response(self, metrics: dict[str, Any], healthy: bool) -> dict[str, Any]:
        """Build health check response"""
        return {
            "success": True,
            "service": "pdf_service",
            "healthy": healthy,
            "timestamp": datetime.now().isoformat(),
            "database_health": metrics["database"],
            "pdf_collection": metrics["pdf_stats"].get("stats", {}),
            "performance": metrics["performance"],
            "resources": {
                **metrics["system"].get("resources", {}),
                **metrics["constants"],
                "max_concurrent_uploads": 10,  # From main constants
            },
        }

    def _build_error_response(self, error: Exception, message: str) -> dict[str, Any]:
        """Build error response for health check"""
        self.logger.error(f"{message}: {str(error)}")
        return {
            "success": False,
            "error": f"{message}: {str(error)}",
            "service": "pdf_service",
            "healthy": False,
            "timestamp": datetime.now().isoformat(),
        }
