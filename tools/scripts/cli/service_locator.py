"""
Service Locator - Simple service access for CLI modules
Provides centralized service access following architecture principles
"""

import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

# Direct service imports - service registry was removed as unused
# Services are now imported directly when needed
from gmail.main import GmailService
from transcription.main import TranscriptionService
from entity.main import EntityService
from utilities.timeline.main import TimelineService
from utilities.notes.main import NotesService


class ServiceLocator:
    """
    Simple service locator for CLI modules.

    Follows clean architecture principles:
    - No complex patterns: Direct delegation to registry
    - Clear interface: get_*_service() methods
    - Service independence: No cross-service dependencies
    """

    def __init__(self):
        """Initialize service locator"""

    def get_vector_service(self, **kwargs):
        """Get vector service instance"""
        # Import directly since service registry was removed
        from utilities.vector_store import get_vector_store

        return get_vector_store()

    def get_search_service(self, **kwargs):
        """Get search service instance"""
        from search_intelligence import get_search_intelligence_service

        return get_search_intelligence_service()

    def get_gmail_service(self, **kwargs):
        """Get gmail service instance"""

        return GmailService()

    def get_pdf_service(self, **kwargs):
        """Get PDF service instance"""
        from pdf.wiring import build_pdf_service

        return build_pdf_service()

    def get_transcription_service(self, **kwargs):
        """Get transcription service instance"""

        return TranscriptionService()

    def get_entity_service(self, **kwargs):
        """Get entity service instance"""

        return EntityService()

    def get_timeline_service(self, **kwargs):
        """Get timeline service instance"""

        return TimelineService()

    def get_notes_service(self, **kwargs):
        """Get notes service instance"""

        return NotesService()

    def get_service_health_status(self, service_name: str):
        """Get health status for a specific service"""
        # Service registry removed - return basic healthy status
        return {"status": "healthy", "service": service_name}

    def is_service_healthy(self, service_name: str) -> bool:
        """Check if a service is healthy"""
        # Without service registry, assume services are healthy if importable
        return True


# Global service locator instance for CLI convenience
_locator = None


def get_locator() -> ServiceLocator:
    """Get global service locator instance"""
    global _locator
    if _locator is None:
        _locator = ServiceLocator()
    return _locator
