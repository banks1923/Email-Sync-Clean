"""
Temporary adapters for service mismatches.

These adapters isolate API mismatches between services until they can be properly aligned.
Each adapter has a target removal date after which the underlying services should be fixed.

REMOVAL TARGET: 2025-09-01
"""

from .email_thread_adapter import EmailThreadAdapter
from .schema_adapter import SchemaAdapter

# VectorMaintenanceAdapter removed 2025-08-20 - functionality moved to vector_maintenance.py

__all__ = [
    "EmailThreadAdapter",
    "SchemaAdapter"
]