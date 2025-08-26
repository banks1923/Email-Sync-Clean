"""Search Intelligence Module.

Unified search intelligence layer that consolidates search, entity
extraction, and document intelligence capabilities.
"""

# Singleton instance
_search_intelligence_service = None


def get_search_intelligence_service():
    """
    Get singleton instance of SearchIntelligenceService.
    """
    global _search_intelligence_service
    if _search_intelligence_service is None:
        from .main import SearchIntelligenceService

        _search_intelligence_service = SearchIntelligenceService()
    return _search_intelligence_service


__all__ = ["get_search_intelligence_service", "search"]

# Basic search functionality
from .basic_search import search
