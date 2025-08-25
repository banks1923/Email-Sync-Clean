"""Centralized loguru configuration for Email Sync system.

Production-safe with environment detection and sensitive data filtering.
"""

import os
import re
import sys
from pathlib import Path

from loguru import logger

# Patterns for sensitive data
SENSITIVE_PATTERNS = [
    r'password["\']?\s*[:=]\s*["\']?[\w\S]+',
    r'token["\']?\s*[:=]\s*["\']?[\w\S]+',
    r'api_key["\']?\s*[:=]\s*["\']?[\w\S]+',
    r'secret["\']?\s*[:=]\s*["\']?[\w\S]+',
    r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b",  # Email
]


def filter_sensitive(record):
    """
    Filter sensitive data from log messages.
    """
    message = record["message"]
    for pattern in SENSITIVE_PATTERNS:
        message = re.sub(pattern, "***REDACTED***", message, flags=re.IGNORECASE)
    record["message"] = message
    return record


def setup_logging(
    service_name: str = "email_sync",
    log_level: str | None = None,
    log_dir: str = "logs",
    enable_rotation: bool = True,
    enable_json: bool = False,
    use_loguru: bool = None,  # Toggle for gradual migration
):
    """Configure loguru for the application with production safety.

    Environment Variables:
    - LOG_LEVEL: Set logging level (DEBUG, INFO, WARNING, ERROR)
    - ENVIRONMENT: Set to 'production' for production safety
    - USE_LOGURU: Set to 'false' to use standard logging (migration toggle)
    """
    # Check if we should use loguru (for gradual migration)
    if use_loguru is None:
        use_loguru = os.getenv("USE_LOGURU", "true").lower() != "false"

    if not use_loguru:
        # Fall back to standard logging for safety
        import logging

        logging.basicConfig(
            level=log_level or os.getenv("LOG_LEVEL", "INFO"),
            format="%(asctime)s | %(levelname)-8s | %(name)s:%(funcName)s:%(lineno)d - %(message)s",
        )
        return logging.getLogger(service_name)

    # Remove default handler
    logger.remove()

    # Detect environment
    is_production = os.getenv("ENVIRONMENT", "").lower() == "production"

    # Get log level from environment or parameter
    level = log_level or os.getenv("LOG_LEVEL", "INFO" if is_production else "DEBUG")

    # Create logs directory
    Path(log_dir).mkdir(exist_ok=True)

    # Console handler with color (disabled in production)
    console_format = (
        "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
        "<level>{level: <8}</level> | "
        "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - "
        "<level>{message}</level>"
    )

    logger.add(
        sys.stderr,
        format=console_format,
        level=level,
        colorize=not is_production,  # No colors in production
        filter=filter_sensitive if is_production else None,
    )

    # File handler with rotation
    if enable_rotation:
        file_format = (
            "{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | " "{name}:{function}:{line} - {message}"
        )

        logger.add(
            f"{log_dir}/{service_name}_{'{'}time:YYYY-MM-DD{'}'}.log",
            rotation="500 MB",
            retention="10 days" if is_production else "30 days",
            compression="zip",
            format=file_format,
            level=level,
            backtrace=True,
            diagnose=not is_production,  # CRITICAL: Disable in production
            filter=filter_sensitive if is_production else None,
        )

    # JSON handler for structured logging (useful for log aggregation)
    if enable_json:
        logger.add(
            f"{log_dir}/{service_name}_json.log",
            format="{message}",
            serialize=True,
            rotation="1 GB",
            retention="30 days" if is_production else "7 days",
            level=level,
            filter=filter_sensitive if is_production else None,
        )

    # Error-only file for critical issues
    if is_production:
        logger.add(
            f"{log_dir}/{service_name}_errors.log",
            level="ERROR",
            rotation="100 MB",
            retention="90 days",
            backtrace=True,
            diagnose=False,
            filter=filter_sensitive,
        )

    # Add context binding for service
    return logger.bind(service=service_name)


# Backward compatibility
def get_logger(name: str = __name__):
    """
    Get a logger instance (backward compatibility).
    """
    return logger.bind(module=name)


def setup_service_logging(service_name: str, log_level: str = "INFO"):
    """
    Backward compatibility wrapper for existing code.
    """
    return setup_logging(service_name, log_level)
