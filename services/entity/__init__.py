"""
Entity Service - Named Entity Recognition for Email Content

Provides entity extraction capabilities using spaCy NLP models.
Follows service independence patterns with database-only communication.

Public API:
- EntityService: Main service class for entity extraction
- EntityDatabase: Database operations for entity storage
"""

from .database import EntityDatabase
from .main import EntityService

__version__ = "0.1.0"
__all__ = ["EntityService", "EntityDatabase"]
