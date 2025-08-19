"""
Database Error Recovery System for Email Sync System
Phase 4 Implementation: Production Hardening - Error Recovery Mechanisms
"""

import os
import shutil
import sqlite3
import threading
import time
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum
from typing import Any

from loguru import logger


class AlertSeverity(Enum):
    """Alert severity levels"""

    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


@dataclass
class DatabaseAlert:
    """Database alert data structure"""

    timestamp: datetime
    severity: AlertSeverity
    error_type: str
    message: str
    recovery_attempted: bool = False
    recovery_successful: bool = False
    metadata: dict[str, Any] | None = None


class DatabaseErrorRecovery:
    """
    Production-ready database error recovery and alerting system

    Features:
    - Automatic connection retry with exponential backoff
    - Database backup and recovery procedures
    - Graceful degradation for database failures
    - Operational alerting for critical conditions
    - Circuit breaker pattern for connection failures
    """

    def __init__(self, db_path: str, backup_dir: str = "backups") -> None:
        """
        Initialize database error recovery system

        Args:
            db_path: Path to SQLite database file
            backup_dir: Directory for database backups
        """
        self.db_path = db_path
        self.backup_dir = os.path.abspath(backup_dir)
        # Logger is now imported globally from loguru
        self._lock = threading.Lock()

        # Circuit breaker state
        self.failure_count = 0
        self.last_failure_time = None
        self.circuit_open = False
        self.circuit_open_time = None

        # Configuration
        self.max_retries = 3
        self.base_retry_delay = 0.1  # 100ms
        self.max_retry_delay = 5.0  # 5 seconds
        self.circuit_failure_threshold = 5
        self.circuit_recovery_timeout = 30  # 30 seconds
        self.backup_retention_days = 7

        # Alert tracking
        self.alerts = []
        self.alert_callbacks: list[Callable[[DatabaseAlert], None]] = []

        # Ensure backup directory exists
        os.makedirs(self.backup_dir, exist_ok=True)

    def execute_with_retry(
        self, operation: Callable[[], Any], operation_name: str, critical: bool = False
    ) -> dict[str, Any]:
        """
        Execute database operation with automatic retry and error recovery

        Args:
            operation: Function to execute
            operation_name: Name of operation for logging
            critical: Whether this is a critical operation requiring alerts

        Returns:
            Dict with success status and result or error information
        """
        # Check circuit breaker
        if self._is_circuit_open():
            return {
                "success": False,
                "error": "Circuit breaker open - database connection unavailable",
                "circuit_open": True,
                "retry_after_seconds": self._get_circuit_recovery_time(),
            }

        last_exception = None

        for attempt in range(self.max_retries + 1):
            try:
                # Reset failure count on successful operation
                if attempt > 0:
                    logger.info(f"Retry attempt {attempt} for {operation_name}")

                result = operation()

                # Success - reset circuit breaker state
                self._reset_circuit_breaker()

                return {"success": True, "data": result, "attempts": attempt + 1}

            except sqlite3.OperationalError as e:
                last_exception = e
                error_msg = str(e)

                # Handle specific SQLite errors
                if "database is locked" in error_msg.lower():
                    self._handle_database_locked_error(operation_name, attempt)
                elif "no such table" in error_msg.lower():
                    self._handle_missing_table_error(operation_name, e)
                    break  # Don't retry for schema errors
                elif "disk i/o error" in error_msg.lower():
                    self._handle_disk_io_error(operation_name, e, critical)
                    break  # Don't retry for disk errors
                else:
                    logger.warning(f"{operation_name} failed: {error_msg}")

                # Increment failure count and check circuit breaker
                self._record_failure()

                # Don't retry if circuit is now open
                if self._is_circuit_open():
                    break

                # Calculate retry delay with exponential backoff
                if attempt < self.max_retries:
                    delay = min(self.base_retry_delay * (2**attempt), self.max_retry_delay)
                    logger.info(f"Retrying {operation_name} in {delay:.2f}s")
                    time.sleep(delay)

            except Exception as e:
                last_exception = e
                logger.error(f"Unexpected error in {operation_name}: {str(e)}")
                self._record_failure()
                break  # Don't retry for unexpected errors

        # All retries failed
        error_result = {
            "success": False,
            "error": str(last_exception),
            "attempts": self.max_retries + 1,
            "operation": operation_name,
        }

        # Send critical alert if needed
        if critical:
            self._send_alert(
                AlertSeverity.CRITICAL,
                "DATABASE_OPERATION_FAILED",
                f"Critical operation {operation_name} failed after {self.max_retries + 1} attempts: {str(last_exception)}",
            )

        return error_result

    def create_backup(self, backup_name: str | None = None) -> dict[str, Any]:
        """
        Create database backup with optional custom name

        Args:
            backup_name: Optional custom backup name

        Returns:
            Dict with backup operation result
        """
        try:
            if not os.path.exists(self.db_path):
                return {"success": False, "error": f"Database file does not exist: {self.db_path}"}

            # Generate backup filename
            if backup_name is None:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                backup_name = f"emails_backup_{timestamp}.db"

            backup_path = os.path.join(self.backup_dir, backup_name)

            # Create backup using SQLite backup API for consistency
            with sqlite3.connect(self.db_path) as source_conn:
                with sqlite3.connect(backup_path) as backup_conn:
                    source_conn.backup(backup_conn)

            # Verify backup integrity
            if not self._verify_backup_integrity(backup_path):
                os.remove(backup_path)
                return {"success": False, "error": "Backup integrity verification failed"}

            logger.info(f"Database backup created: {backup_path}")

            # Clean up old backups
            self._cleanup_old_backups()

            return {
                "success": True,
                "backup_path": backup_path,
                "backup_size_mb": round(os.path.getsize(backup_path) / (1024 * 1024), 2),
            }

        except Exception as e:
            error_msg = f"Backup creation failed: {str(e)}"
            logger.error(error_msg)

            self._send_alert(AlertSeverity.HIGH, "BACKUP_FAILED", error_msg)

            return {"success": False, "error": error_msg}

    def restore_from_backup(
        self, backup_path: str, create_current_backup: bool = True
    ) -> dict[str, Any]:
        """
        Restore database from backup

        Args:
            backup_path: Path to backup file
            create_current_backup: Whether to backup current database first

        Returns:
            Dict with restore operation result
        """
        try:
            if not os.path.exists(backup_path):
                return {"success": False, "error": f"Backup file does not exist: {backup_path}"}

            # Verify backup integrity before restore
            if not self._verify_backup_integrity(backup_path):
                return {
                    "success": False,
                    "error": "Backup file is corrupted and cannot be restored",
                }

            # Create backup of current database if requested
            current_backup_path = None
            if create_current_backup and os.path.exists(self.db_path):
                current_backup_result = self.create_backup("pre_restore_backup")
                if current_backup_result["success"]:
                    current_backup_path = current_backup_result["backup_path"]
                else:
                    logger.warning("Failed to create pre-restore backup")

            # Perform restore
            shutil.copy2(backup_path, self.db_path)

            # Verify restored database
            if not self._verify_database_integrity(self.db_path):
                # Restore failed - try to recover original if we have backup
                if current_backup_path and os.path.exists(current_backup_path):
                    shutil.copy2(current_backup_path, self.db_path)
                    return {
                        "success": False,
                        "error": "Restore failed, original database restored from backup",
                    }
                else:
                    return {
                        "success": False,
                        "error": "Restore failed and original database could not be recovered",
                    }

            logger.info(f"Database restored from backup: {backup_path}")

            return {
                "success": True,
                "restored_from": backup_path,
                "pre_restore_backup": current_backup_path,
            }

        except Exception as e:
            error_msg = f"Database restore failed: {str(e)}"
            logger.error(error_msg)

            self._send_alert(AlertSeverity.CRITICAL, "RESTORE_FAILED", error_msg)

            return {"success": False, "error": error_msg}

    def get_degraded_mode_response(self, operation_name: str) -> dict[str, Any]:
        """
        Provide graceful degradation response when database is unavailable

        Args:
            operation_name: Name of the operation that failed

        Returns:
            Dict with degraded mode response
        """
        return {
            "success": False,
            "degraded_mode": True,
            "error": f"Database temporarily unavailable - {operation_name} cannot be completed",
            "message": "Service is operating in degraded mode. Please try again later.",
            "retry_suggested": True,
            "estimated_recovery_time": (
                self._get_circuit_recovery_time() if self._is_circuit_open() else 60
            ),
        }

    def add_alert_callback(self, callback: Callable[[DatabaseAlert], None]) -> None:
        """Add callback function for alert notifications"""
        self.alert_callbacks.append(callback)

    def get_recovery_status(self) -> dict[str, Any]:
        """Get current recovery system status"""
        return {
            "circuit_breaker": {
                "open": self.circuit_open,
                "failure_count": self.failure_count,
                "last_failure": (
                    self.last_failure_time.isoformat() if self.last_failure_time else None
                ),
                "recovery_time_remaining": (
                    self._get_circuit_recovery_time() if self._is_circuit_open() else 0
                ),
            },
            "backups": {
                "backup_directory": self.backup_dir,
                "available_backups": self._list_available_backups(),
            },
            "recent_alerts": [
                {
                    "timestamp": alert.timestamp.isoformat(),
                    "severity": alert.severity.value,
                    "type": alert.error_type,
                    "message": alert.message,
                    "recovery_attempted": alert.recovery_attempted,
                }
                for alert in self.alerts[-10:]  # Last 10 alerts
            ],
        }

    def _is_circuit_open(self) -> bool:
        """Check if circuit breaker is open"""
        if not self.circuit_open:
            return False

        # Check if recovery timeout has passed
        if (
            datetime.now() - self.circuit_open_time
        ).total_seconds() > self.circuit_recovery_timeout:
            logger.info("Circuit breaker recovery timeout reached, attempting to close circuit")
            self.circuit_open = False
            self.circuit_open_time = None
            return False

        return True

    def _record_failure(self) -> None:
        """Record a database operation failure"""
        with self._lock:
            self.failure_count += 1
            self.last_failure_time = datetime.now()

            # Open circuit breaker if threshold reached
            if self.failure_count >= self.circuit_failure_threshold and not self.circuit_open:

                self.circuit_open = True
                self.circuit_open_time = datetime.now()

                logger.error(
                    f"Circuit breaker opened after {self.failure_count} failures. "
                    f"Recovery timeout: {self.circuit_recovery_timeout} seconds"
                )

                self._send_alert(
                    AlertSeverity.CRITICAL,
                    "CIRCUIT_BREAKER_OPEN",
                    f"Database circuit breaker opened after {self.failure_count} consecutive failures",
                )

    def _reset_circuit_breaker(self) -> None:
        """Reset circuit breaker state after successful operation"""
        if self.failure_count > 0 or self.circuit_open:
            with self._lock:
                was_open = self.circuit_open
                self.failure_count = 0
                self.circuit_open = False
                self.circuit_open_time = None

                if was_open:
                    logger.info("Circuit breaker closed - database connection recovered")
                    self._send_alert(
                        AlertSeverity.MEDIUM,
                        "CIRCUIT_BREAKER_CLOSED",
                        "Database connection recovered, circuit breaker closed",
                    )

    def _get_circuit_recovery_time(self) -> int:
        """Get remaining time until circuit breaker recovery attempt"""
        if not self.circuit_open:
            return 0

        elapsed = (datetime.now() - self.circuit_open_time).total_seconds()
        remaining = max(0, self.circuit_recovery_timeout - elapsed)
        return int(remaining)

    def _handle_database_locked_error(self, operation_name: str, attempt: int) -> None:
        """Handle database locked errors"""
        logger.warning(f"Database locked during {operation_name} (attempt {attempt + 1})")

        if attempt == 0:  # First attempt
            self._send_alert(
                AlertSeverity.MEDIUM,
                "DATABASE_LOCKED",
                f"Database lock detected during {operation_name}",
            )

    def _handle_missing_table_error(self, operation_name: str, error: Exception) -> None:
        """Handle missing table errors"""
        logger.error(f"Missing table error in {operation_name}: {str(error)}")

        self._send_alert(
            AlertSeverity.HIGH,
            "SCHEMA_ERROR",
            f"Database schema error in {operation_name}: {str(error)}",
        )

    def _handle_disk_io_error(self, operation_name: str, error: Exception, critical: bool) -> None:
        """Handle disk I/O errors"""
        logger.error(f"Disk I/O error in {operation_name}: {str(error)}")

        severity = AlertSeverity.CRITICAL if critical else AlertSeverity.HIGH
        self._send_alert(
            severity, "DISK_IO_ERROR", f"Disk I/O error in {operation_name}: {str(error)}"
        )

    def _send_alert(
        self,
        severity: AlertSeverity,
        error_type: str,
        message: str,
        metadata: dict | None = None,
    ) -> None:
        """Send alert through configured callbacks"""
        alert = DatabaseAlert(
            timestamp=datetime.now(),
            severity=severity,
            error_type=error_type,
            message=message,
            metadata=metadata,
        )

        # Store alert
        self.alerts.append(alert)

        # Keep only recent alerts to prevent memory growth
        if len(self.alerts) > 100:
            self.alerts = self.alerts[-50:]

        # Send to callbacks
        for callback in self.alert_callbacks:
            try:
                callback(alert)
            except Exception as e:
                logger.error(f"Alert callback failed: {str(e)}")

        # Log alert
        logger.log(
            "CRITICAL" if severity == AlertSeverity.CRITICAL else "WARNING",
            f"DATABASE ALERT [{severity.value}] {error_type}: {message}",
        )

    def _cleanup_old_backups(self) -> None:
        """Remove backups older than retention period"""
        try:
            cutoff_date = datetime.now() - timedelta(days=self.backup_retention_days)

            for filename in os.listdir(self.backup_dir):
                if filename.endswith(".db") and filename.startswith("emails_backup_"):
                    filepath = os.path.join(self.backup_dir, filename)
                    file_time = datetime.fromtimestamp(os.path.getmtime(filepath))

                    if file_time < cutoff_date:
                        os.remove(filepath)
                        logger.info(f"Removed old backup: {filename}")

        except Exception as e:
            logger.warning(f"Failed to cleanup old backups: {str(e)}")

    def _verify_backup_integrity(self, backup_path: str) -> bool:
        """Verify backup file integrity"""
        try:
            with sqlite3.connect(backup_path) as conn:
                conn.execute("PRAGMA integrity_check")
                return True
        except Exception:
            return False

    def _verify_database_integrity(self, db_path: str) -> bool:
        """Verify database integrity"""
        try:
            with sqlite3.connect(db_path) as conn:
                cursor = conn.execute("PRAGMA integrity_check")
                result = cursor.fetchone()
                return result and result[0] == "ok"
        except Exception:
            return False

    def _list_available_backups(self) -> list[dict[str, Any]]:
        """List available backup files"""
        backups = []

        try:
            for filename in os.listdir(self.backup_dir):
                # Accept any file that looks like a database backup
                if (
                    filename.endswith(".db")
                    or filename.startswith("emails_backup_")
                    or filename.startswith("test")
                    or "backup" in filename
                ):
                    filepath = os.path.join(self.backup_dir, filename)
                    stat = os.stat(filepath)

                    backups.append(
                        {
                            "filename": filename,
                            "path": filepath,
                            "size_mb": round(stat.st_size / (1024 * 1024), 2),
                            "created": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                        }
                    )

            # Sort by creation time, newest first
            backups.sort(key=lambda x: x["created"], reverse=True)

        except Exception as e:
            logger.warning(f"Failed to list backups: {str(e)}")

        return backups
