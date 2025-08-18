"""
Shared utilities for Email Sync services

Only truly shared components remain here.
Service-specific utilities have been moved to their respective services.
"""

from .service_interfaces import IService
from .simple_db import SimpleDB

__all__ = ["SimpleDB", "IService"]
