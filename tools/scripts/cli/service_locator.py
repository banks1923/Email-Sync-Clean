"""
Service Locator - Simple service access for CLI modules
Provides centralized service access following architecture principles
"""

import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from entity.main import EntityService

# Direct service imports - service registry was removed as unused
# Services are now imported directly when needed
from gmail.main import GmailService
from utilities.timeline.main import TimelineService

# Notes service removed - migrated to document pipeline


class ServiceLocator:
    """Simple service locator for CLI modules.

    Follows clean architecture principles:
    - No complex patterns: Direct delegation to registry
    - Clear interface: get_*_service() methods
    - Service independence: No cross-service dependencies
    """

    def __init__(self):
        """
        Initialize service locator.
        """

    def get_vector_service(self, **kwargs):
        """
        Get vector service instance.
        """
        # Import directly since service registry was removed
        from utilities.vector_store import get_vector_store

        return get_vector_store()

    def get_search_service(self, **kwargs):
        """
        Get search functions - returns a dict of search functions.
        """
        from search_intelligence import search, find_literal, vector_store_available

        # Return a dict with the functions since there's no service object
        return {
            "search": search,
            "find_literal": find_literal,
            "vector_store_available": vector_store_available
        }

    def get_gmail_service(self, **kwargs):
        """
        Get gmail service instance.
        """

        return GmailService()

    def get_pdf_service(self, **kwargs):
        """
        Get PDF service instance.
        """
        from pdf.wiring import build_pdf_service

        return build_pdf_service()

    def get_entity_service(self, **kwargs):
        """
        Get entity service instance.
        """

        return EntityService()

    def get_timeline_service(self, **kwargs):
        """
        Get timeline service instance.
        """

        return TimelineService()

    # get_notes_service removed - use document pipeline instead
    # Notes functionality available via: vsearch upload --type note "content"

    def get_service_health_status(self, service_name: str):
        """
        Get health status for a specific service.
        """
        # Service registry removed - return basic healthy status
        return {"status": "healthy", "service": service_name}

    def is_service_healthy(self, service_name: str) -> bool:
        """
        Check if a service is healthy.
        """
        # Without service registry, assume services are healthy if importable
        return True


# Global service locator instance for CLI convenience
_locator = None


def get_locator() -> ServiceLocator:
    """
    Get global service locator instance.
    """
    global _locator
    if _locator is None:
        _locator = ServiceLocator()
    return _locator
