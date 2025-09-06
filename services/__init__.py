"""Services package providing PDF, Entity, and Summarization functionality.

Modules:
- pdf: PDF processing and extraction
- entity: Entity extraction and management
- summarization: Document summarization
- cli: Command-line interface
"""

from .entity.config import EntityConfig
from .entity.database import EntityDatabase

# Entity Service  
from .entity.main import EntityService

# PDF Service
from .pdf.main import PDFService
from .pdf.pdf_health import PDFHealthManager
from .pdf.pdf_idempotent_writer import IdempotentPDFWriter
from .pdf.pdf_processor_enhanced import EnhancedPDFProcessor
from .pdf.wiring import build_pdf_service, get_pdf_service

# Summarization Service
from .summarization.engine import DocumentSummarizer, TextRankSummarizer, TFIDFSummarizer

# Define public API
__all__ = [
    # PDF
    "PDFService",
    "EnhancedPDFProcessor",
    "IdempotentPDFWriter",
    "PDFHealthManager",
    "build_pdf_service",
    "get_pdf_service",
    # Entity
    "EntityService",
    "EntityDatabase",
    "EntityConfig",
    # Summarization
    "DocumentSummarizer",
    "TFIDFSummarizer",
    "TextRankSummarizer",
]
