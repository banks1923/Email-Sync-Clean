"""Multi-Format Document Processing System.

Supports DOCX, TXT, MD, and PDF formats with full lifecycle management.
Follows CLAUDE.md principles with simple, direct implementation.
"""

from .format_detector import FormatDetector
from .lifecycle_manager import DocumentLifecycleManager
from .naming_convention import NamingConvention
from .processors import DocxProcessor, MarkdownProcessor, TextProcessor

__all__ = [
    "DocumentLifecycleManager",
    "TextProcessor",
    "MarkdownProcessor",
    "DocxProcessor",
    "FormatDetector",
    "NamingConvention",
]
