"""
Legal Document Boilerplate Removal Module

Integrates with existing OCR and Legal Intelligence infrastructure
to automatically identify and remove repetitive boilerplate text
from legal documents.
"""

from .boilerplate_detector import LegalBoilerplateDetector
from .pattern_analyzer import LegalPatternAnalyzer
from .text_processor import LegalTextProcessor
from .integration import LegalDocumentProcessor

__all__ = [
    'LegalBoilerplateDetector',
    'LegalPatternAnalyzer', 
    'LegalTextProcessor',
    'LegalDocumentProcessor'
]
