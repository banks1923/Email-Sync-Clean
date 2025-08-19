"""
Database Health Monitoring for Email Sync System
Phase 4 Implementation: Production Hardening
"""

import os
import sqlite3
import threading
import time
from collections import defaultdict, deque
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta
from typing import Any

import psutil
from loguru import logger


@dataclass
class DatabaseMetrics:
    """Database health metrics data structure"""

    connection_time_ms: float
    query_time_ms: float
    success_rate: float
    error_count: int
    total_operations: int
    db_size_mb: float
    available_disk_mb: float
    disk_usage_percent: float
    active_connections: int


@dataclass
class OperationMetric:
    """Individual operation metric"""

    timestamp: datetime
    operation_type: str
    duration_ms: float
    success: bool
    error_message: str | None = None


class DatabaseHealthMonitor:
    """
    Production-ready database health monitoring system

    Features:
    - Connection health checks with timing
    - Operation performance tracking
    - Error rate monitoring with rolling windows
    - Disk space monitoring for database growth
    - Alerting for critical conditions
    """

    def __init__(self, db_path: str, monitoring_window_minutes: int = 60) -> None:
        """
        Initialize database health monitor

        Args:
            db_path: Path to SQLite database file
            monitoring_window_minutes: Time window for metrics aggregation
        """
        self.db_path = db_path
        self.monitoring_window = timedelta(minutes=monitoring_window_minutes)
        self.metrics_history = deque(maxlen=1000)  # Store last 1000 operations
        self.error_counts = defaultdict(int)
        self.operation_counts = defaultdict(int)
        # Logger is now imported globally from loguru
        self._lock = threading.Lock()

        # Performance thresholds (configurable)
        self.connection_timeout_ms = 1000  # 1 second max for connections
        self.query_timeout_ms = 5000  # 5 seconds max for queries
        self.error_rate_threshold = 0.05  # 5% error rate threshold
        self.disk_usage_threshold = 0.85  # 85% disk usage threshold

    def health_check(self) -> dict[str, Any]:
        """
        Comprehensive database health check

        Returns:
            Dict with health status and detailed metrics
        """
        start_time = time.time()

        try:
            # Test basic connectivity
            connection_result = self._test_database_connection()

            # Get current metrics
            current_metrics = self._get_current_metrics()

            # Check disk space
            disk_result = self._check_disk_space()

            # Analyze recent performance
            performance_analysis = self._analyze_recent_performance()

            # Determine overall health status
            health_status = self._determine_health_status(
                connection_result, current_metrics, disk_result, performance_analysis
            )

            total_time_ms = (time.time() - start_time) * 1000

            return {
                "success": True,
                "health_status": health_status["status"],
                "health_score": health_status["score"],
                "timestamp": datetime.now().isoformat(),
                "check_duration_ms": round(total_time_ms, 2),
                "connection": connection_result,
                "metrics": asdict(current_metrics),
                "disk": disk_result,
                "performance": performance_analysis,
                "alerts": health_status["alerts"],
            }

        except Exception as e:
            logger.error(f"Health check failed: {str(e)}")
            return {
                "success": False,
                "error": f"Health check failed: {str(e)}",
                "health_status": "CRITICAL",
                "health_score": 0,
                "timestamp": datetime.now().isoformat(),
            }

    def track_operation(
        self,
        operation_type: str,
        start_time: float,
        success: bool,
        error_message: str | None = None,
    ) -> None:
        """
        Track database operation performance

        Args:
            operation_type: Type of operation (SELECT, INSERT, UPDATE, etc.)
            start_time: Operation start time (time.time())
            success: Whether operation succeeded
            error_message: Error message if operation failed
        """
        duration_ms = (time.time() - start_time) * 1000

        metric = OperationMetric(
            timestamp=datetime.now(),
            operation_type=operation_type,
            duration_ms=duration_ms,
            success=success,
            error_message=error_message,
        )

        with self._lock:
            self.metrics_history.append(metric)
            self.operation_counts[operation_type] += 1
            if not success:
                self.error_counts[operation_type] += 1

        # Log performance warnings
        if duration_ms > self.query_timeout_ms:
            logger.warning(
                f"Slow database operation: {operation_type} took {duration_ms:.1f}ms (threshold: {self.query_timeout_ms}ms)"
            )

        if not success:
            logger.error(f"Database operation failed: {operation_type} - {error_message}")

    def get_performance_report(self) -> dict[str, Any]:
        """
        Generate comprehensive performance report

        Returns:
            Dict with performance metrics and analysis
        """
        with self._lock:
            recent_metrics = self._get_recent_metrics()

        if not recent_metrics:
            return {
                "success": True,
                "message": "No recent operations to analyze",
                "total_operations": 0,
            }

        # Analyze operations by type
        operation_analysis = self._analyze_operations_by_type(recent_metrics)

        # Calculate overall statistics
        total_ops = len(recent_metrics)
        successful_ops = sum(1 for m in recent_metrics if m.success)
        error_rate = (total_ops - successful_ops) / total_ops if total_ops > 0 else 0

        avg_duration = sum(m.duration_ms for m in recent_metrics) / total_ops
        max_duration = max(m.duration_ms for m in recent_metrics)

        return {
            "success": True,
            "report_period_minutes": self.monitoring_window.total_seconds() / 60,
            "total_operations": total_ops,
            "successful_operations": successful_ops,
            "error_rate": round(error_rate, 4),
            "average_duration_ms": round(avg_duration, 2),
            "max_duration_ms": round(max_duration, 2),
            "operations_by_type": operation_analysis,
            "timestamp": datetime.now().isoformat(),
        }

    def _test_database_connection(self) -> dict[str, Any]:
        """Test database connectivity and measure connection time"""
        start_time = time.time()

        try:
            with sqlite3.connect(self.db_path, timeout=5.0) as conn:
                # Test basic query
                cursor = conn.cursor()
                cursor.execute("SELECT 1")
                result = cursor.fetchone()

                connection_time_ms = (time.time() - start_time) * 1000

                return {
                    "success": True,
                    "connection_time_ms": round(connection_time_ms, 2),
                    "basic_query_works": result[0] == 1,
                    "database_exists": True,
                }

        except sqlite3.OperationalError as e:
            connection_time_ms = (time.time() - start_time) * 1000
            return {
                "success": False,
                "error": str(e),
                "connection_time_ms": round(connection_time_ms, 2),
                "database_exists": os.path.exists(self.db_path),
            }
        except Exception as e:
            connection_time_ms = (time.time() - start_time) * 1000
            return {
                "success": False,
                "error": f"Unexpected error: {str(e)}",
                "connection_time_ms": round(connection_time_ms, 2),
                "database_exists": os.path.exists(self.db_path),
            }

    def _get_current_metrics(self) -> DatabaseMetrics:
        """Get current database metrics"""
        with self._lock:
            recent_metrics = self._get_recent_metrics()

        if not recent_metrics:
            # Return default metrics if no recent operations
            db_size_mb, available_disk_mb, disk_usage_percent = self._get_disk_metrics()
            return DatabaseMetrics(
                connection_time_ms=0.0,
                query_time_ms=0.0,
                success_rate=1.0,
                error_count=0,
                total_operations=0,
                db_size_mb=db_size_mb,
                available_disk_mb=available_disk_mb,
                disk_usage_percent=disk_usage_percent,
                active_connections=0,
            )

        # Calculate metrics from recent operations
        total_ops = len(recent_metrics)
        successful_ops = sum(1 for m in recent_metrics if m.success)
        success_rate = successful_ops / total_ops if total_ops > 0 else 1.0
        error_count = total_ops - successful_ops

        avg_query_time = sum(m.duration_ms for m in recent_metrics) / total_ops

        # Test connection time separately
        connection_test = self._test_database_connection()
        connection_time_ms = connection_test.get("connection_time_ms", 0.0)

        db_size_mb, available_disk_mb, disk_usage_percent = self._get_disk_metrics()

        return DatabaseMetrics(
            connection_time_ms=connection_time_ms,
            query_time_ms=round(avg_query_time, 2),
            success_rate=round(success_rate, 4),
            error_count=error_count,
            total_operations=total_ops,
            db_size_mb=db_size_mb,
            available_disk_mb=available_disk_mb,
            disk_usage_percent=disk_usage_percent,
            active_connections=1,  # SQLite doesn't have connection pools like PostgreSQL
        )

    def _check_disk_space(self) -> dict[str, Any]:
        """Check disk space for database file"""
        try:
            db_size_mb, available_disk_mb, disk_usage_percent = self._get_disk_metrics()

            # Check if disk usage is critical
            is_critical = disk_usage_percent > self.disk_usage_threshold

            return {
                "success": True,
                "database_size_mb": db_size_mb,
                "available_space_mb": available_disk_mb,
                "disk_usage_percent": disk_usage_percent,
                "is_critical": is_critical,
                "threshold_percent": self.disk_usage_threshold * 100,
            }

        except Exception as e:
            return {"success": False, "error": f"Failed to check disk space: {str(e)}"}

    def _get_disk_metrics(self) -> tuple[float, float, float]:
        """Get database size and disk space metrics"""
        # Database file size
        db_size_mb = 0.0
        if os.path.exists(self.db_path):
            db_size_bytes = os.path.getsize(self.db_path)
            db_size_mb = db_size_bytes / 1024 / 1024

        # Disk space for database directory
        db_dir = os.path.dirname(os.path.abspath(self.db_path))
        disk_usage = psutil.disk_usage(db_dir)

        available_disk_mb = disk_usage.free / 1024 / 1024
        disk_usage_percent = disk_usage.used / disk_usage.total

        return db_size_mb, available_disk_mb, disk_usage_percent

    def _analyze_recent_performance(self) -> dict[str, Any]:
        """Analyze recent performance trends"""
        with self._lock:
            recent_metrics = self._get_recent_metrics()

        if len(recent_metrics) < 10:
            return {
                "trend": "insufficient_data",
                "message": "Need at least 10 operations for trend analysis",
            }

        # Split into two halves for trend analysis
        mid_point = len(recent_metrics) // 2
        first_half = recent_metrics[:mid_point]
        second_half = recent_metrics[mid_point:]

        # Calculate average durations
        first_avg = sum(m.duration_ms for m in first_half) / len(first_half)
        second_avg = sum(m.duration_ms for m in second_half) / len(second_half)

        # Determine trend
        if second_avg > first_avg * 1.2:  # 20% slower
            trend = "degrading"
        elif second_avg < first_avg * 0.8:  # 20% faster
            trend = "improving"
        else:
            trend = "stable"

        # Calculate error rates
        first_errors = sum(1 for m in first_half if not m.success)
        second_errors = sum(1 for m in second_half if not m.success)

        first_error_rate = first_errors / len(first_half)
        second_error_rate = second_errors / len(second_half)

        return {
            "trend": trend,
            "first_half_avg_ms": round(first_avg, 2),
            "second_half_avg_ms": round(second_avg, 2),
            "performance_change_percent": round(((second_avg - first_avg) / first_avg) * 100, 1),
            "first_half_error_rate": round(first_error_rate, 4),
            "second_half_error_rate": round(second_error_rate, 4),
            "total_operations_analyzed": len(recent_metrics),
        }

    def _determine_health_status(
        self,
        connection_result: dict,
        metrics: DatabaseMetrics,
        disk_result: dict,
        performance: dict,
    ) -> dict[str, Any]:
        """Determine overall health status and generate alerts"""
        alerts = []
        score = 100  # Start with perfect score

        # Check connection health
        if not connection_result["success"]:
            alerts.append(
                {
                    "severity": "CRITICAL",
                    "message": f"Database connection failed: {connection_result['error']}",
                }
            )
            score -= 50
        elif connection_result["connection_time_ms"] > self.connection_timeout_ms:
            alerts.append(
                {
                    "severity": "WARNING",
                    "message": f"Slow database connection: {connection_result['connection_time_ms']:.1f}ms",
                }
            )
            score -= 10

        # Check error rate
        if metrics.success_rate < (1 - self.error_rate_threshold):
            alerts.append(
                {
                    "severity": "CRITICAL",
                    "message": f"High error rate: {(1-metrics.success_rate)*100:.1f}% (threshold: {self.error_rate_threshold*100:.1f}%)",
                }
            )
            score -= 30

        # Check query performance
        if metrics.query_time_ms > self.query_timeout_ms:
            alerts.append(
                {
                    "severity": "WARNING",
                    "message": f"Slow query performance: {metrics.query_time_ms:.1f}ms average",
                }
            )
            score -= 15

        # Check disk space
        if disk_result["success"] and disk_result["is_critical"]:
            alerts.append(
                {
                    "severity": "CRITICAL",
                    "message": f"Low disk space: {disk_result['disk_usage_percent']*100:.1f}% used",
                }
            )
            score -= 25
        elif disk_result["success"] and disk_result["disk_usage_percent"] > 0.75:
            alerts.append(
                {
                    "severity": "WARNING",
                    "message": f"Disk usage getting high: {disk_result['disk_usage_percent']*100:.1f}% used",
                }
            )
            score -= 10

        # Check performance trends
        if performance.get("trend") == "degrading":
            alerts.append(
                {
                    "severity": "WARNING",
                    "message": f"Performance degrading: {performance.get('performance_change_percent', 0):.1f}% slower",
                }
            )
            score -= 15

        # Determine status based on score
        if score >= 90:
            status = "HEALTHY"
        elif score >= 70:
            status = "WARNING"
        elif score >= 40:
            status = "DEGRADED"
        else:
            status = "CRITICAL"

        return {"status": status, "score": max(0, score), "alerts": alerts}

    def _get_recent_metrics(self) -> list[OperationMetric]:
        """Get metrics within the monitoring window"""
        cutoff_time = datetime.now() - self.monitoring_window
        return [m for m in self.metrics_history if m.timestamp >= cutoff_time]

    def _analyze_operations_by_type(self, metrics: list[OperationMetric]) -> dict[str, Any]:
        """Analyze operations grouped by type"""
        operations = defaultdict(list)

        for metric in metrics:
            operations[metric.operation_type].append(metric)

        analysis = {}
        for op_type, op_metrics in operations.items():
            total = len(op_metrics)
            successful = sum(1 for m in op_metrics if m.success)
            avg_duration = sum(m.duration_ms for m in op_metrics) / total
            max_duration = max(m.duration_ms for m in op_metrics)

            analysis[op_type] = {
                "total_operations": total,
                "success_rate": round(successful / total, 4),
                "average_duration_ms": round(avg_duration, 2),
                "max_duration_ms": round(max_duration, 2),
            }

        return analysis
