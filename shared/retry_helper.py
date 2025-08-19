"""
Simple retry decorator for transient failures.
No complex configuration - just sensible defaults that work.
"""

import time
from collections.abc import Callable
from functools import wraps
from typing import Any


def retry_on_failure(
    max_attempts: int = 3,
    exceptions: tuple[type[Exception], ...] = (Exception,),
    delay: float = 0.1,
    backoff: float = 2.0,
    logger_instance: Any = None,
) -> Callable:
    """
    Simple retry decorator with exponential backoff.

    Args:
        max_attempts: Maximum retry attempts (default 3)
        exceptions: Exceptions to catch and retry (default all)
        delay: Initial delay in seconds (default 0.1s)
        backoff: Backoff multiplier (default 2.0)
        logger_instance: Optional logger for retry messages

    Returns:
        Decorated function that retries on failure
    """

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            current_delay = delay
            last_exception = None

            for attempt in range(max_attempts):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e

                    if attempt < max_attempts - 1:
                        if logger_instance:
                            logger_instance.warning(
                                f"Attempt {attempt + 1}/{max_attempts} failed for {func.__name__}: {e}. "
                                f"Retrying in {current_delay:.1f}s..."
                            )
                        time.sleep(current_delay)
                        current_delay *= backoff
                    else:
                        if logger_instance:
                            logger_instance.error(
                                f"All {max_attempts} attempts failed for {func.__name__}: {e}"
                            )

            # Re-raise the last exception after all retries failed
            raise last_exception

        return wrapper

    return decorator


# Convenience decorators for common use cases
def retry_database(func: Callable) -> Callable:
    """Retry decorator specifically for database operations."""
    import sqlite3

    return retry_on_failure(
        exceptions=(sqlite3.OperationalError, sqlite3.DatabaseError), delay=0.1, backoff=2.0
    )(func)


def retry_network(func: Callable) -> Callable:
    """Retry decorator specifically for network operations."""
    import socket
    import urllib.error

    return retry_on_failure(
        exceptions=(socket.timeout, ConnectionError, urllib.error.URLError), delay=0.5, backoff=2.0
    )(func)
