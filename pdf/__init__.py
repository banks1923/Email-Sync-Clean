"""
PDF Service Module

Simple PDF upload and processing service that preserves service independence
while leveraging existing infrastructure for PDF ingestion and vector search.

Follows Email Sync System architecture principles:
- Service independence through shared database communication
- Standard error response format: {"success": bool, "error": str}
- Legal BERT Large (1024D) preservation for vector compatibility
- Minimal orchestration using proven components
"""

from .main import PDFService

__all__ = ["PDFService"]
