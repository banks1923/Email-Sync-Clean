"""Legal Intelligence Module.

Consolidates legal analysis, timeline generation, knowledge graph
building, and case processing into a unified service.
"""

from .main import LegalIntelligenceService


def get_legal_intelligence_service(db_path: str = "emails.db"):
    """
    Get singleton instance of LegalIntelligenceService.
    """
    return LegalIntelligenceService(db_path)


__all__ = ["LegalIntelligenceService", "get_legal_intelligence_service"]
