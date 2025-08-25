"""
PDF Service Wiring - Builds the service with all providers

This module is the single construction point for PDFService, using the
Facade + Providers pattern to reduce coupling from 11 to 3 dependencies.

Architecture:
- Core dependencies: SimpleDB, EnhancedPDFProcessor, EnhancedPDFStorage
- Optional providers: OCR, validation, health, recovery, summarization, etc.
- Lazy loading: Providers created only when first accessed
"""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pdf.main import PDFService


def build_pdf_service(db_path: str = "data/emails.db") -> "PDFService":
    """
    Build PDF service with lazy-loaded providers.
    """
    from pdf.pdf_processor_enhanced import EnhancedPDFProcessor
    from pdf.pdf_storage_enhanced import EnhancedPDFStorage
    from shared.simple_db import SimpleDB

    # Construct core instances once; providers capture these by closure
    db = SimpleDB(db_path)
    processor = EnhancedPDFProcessor(900, 100)  # TODO: import defaults from config/constants
    storage = EnhancedPDFStorage(db_path)

    # Lazy provider factories (imports only on first call)
    def make_ocr():
        from pdf.ocr.ocr_coordinator import OCRCoordinator
        return OCRCoordinator()

    def make_validator():
        from pdf.pdf_validator import PDFValidator
        return PDFValidator()

    def make_health_monitor():
        from pdf.database_health_monitor import DatabaseHealthMonitor
        return DatabaseHealthMonitor(db_path)

    def make_error_recovery():
        from pdf.database_error_recovery import DatabaseErrorRecovery
        return DatabaseErrorRecovery(db_path)

    def make_summarizer():
        from summarization import get_document_summarizer
        return get_document_summarizer()

    # Pipeline and exporter removed - using direct processing now

    def make_health_manager():
        """Special case: needs other components assembled. Reuse core instances."""
        from pdf.pdf_health import PDFHealthManager
        try:
            from loguru import logger  # optional dependency
        except Exception:  # fallback to stdlib logger if loguru not present
            import logging
            logger = logging.getLogger("pdf.health")

        validator = make_validator()
        monitor = make_health_monitor()
        return PDFHealthManager(processor, storage, validator, monitor, logger)

    from collections.abc import Callable
    providers: dict[str, Callable[[], object]] = {
        "ocr": make_ocr,
        "validator": make_validator,
        "health_monitor": make_health_monitor,
        "error_recovery": make_error_recovery,
        "summarizer": make_summarizer,
        "health_manager": make_health_manager,
    }

    # Create facade with only 3 core dependencies + providers
    from pdf.main import PDFService
    return PDFService(
        db=db,
        processor=processor,
        storage=storage,
        providers=providers,
    )


# Module-level singleton for backward compatibility
_service_instance = None


def get_pdf_service(db_path: str = "data/emails.db") -> "PDFService":
    """Get or create PDF service instance.

    Args:
        db_path: Database path (default: "data/emails.db")

    Returns:
        Configured PDFService instance
    """
    global _service_instance
    if _service_instance is None:
        _service_instance = build_pdf_service(db_path)
    return _service_instance


def reset_pdf_service() -> None:
    """
    Reset service instance (for testing)
    """
    global _service_instance
    _service_instance = None