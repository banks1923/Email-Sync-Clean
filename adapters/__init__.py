"""
Temporary adapters for service mismatches.

These adapters isolate API mismatches between services until they can be properly aligned.
Each adapter has a target removal date after which the underlying services should be fixed.

REMOVAL TARGET: 2025-09-01
"""

from .email_thread_adapter import EmailThreadAdapter
from .vector_maintenance_adapter import VectorMaintenanceAdapter
from .schema_adapter import SchemaAdapter

__all__ = [
    "EmailThreadAdapter",
    "VectorMaintenanceAdapter", 
    "SchemaAdapter"
]