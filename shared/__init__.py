"""Shared utilities for Email Sync services.

Only truly shared components remain here. Service-specific utilities
have been moved to their respective services.
"""

from lib.db import SimpleDB

__all__ = ["SimpleDB"]
