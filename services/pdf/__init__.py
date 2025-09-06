"""PDF Service Module.

Simple PDF upload and processing service that preserves service independence
while leveraging existing infrastructure for PDF ingestion and vector search.

Follows Email Sync System architecture principles:
- Service independence through shared database communication
- Standard error response format: {"success": bool, "error": str}
- Legal BERT Large (1024D) preservation for vector compatibility
- Minimal orchestration using proven components
"""

from .main import PDFService
from .wiring import build_pdf_service


def get_pdf_service():
    """
    Factory function for PDFService with proper dependency wiring.
    """
    return build_pdf_service()


__all__ = ["PDFService", "get_pdf_service"]
