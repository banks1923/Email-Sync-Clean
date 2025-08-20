"""Legal Evidence Tracking System for Email Documentation.

This module provides tools for creating legally traceable references to emails,
organizing them by threads, and generating evidence reports for legal proceedings.
"""

from .evidence_tracker import EvidenceTracker, get_evidence_tracker
from .report_generator import LegalReportGenerator, get_report_generator
from .thread_analyzer import ThreadAnalyzer, get_thread_analyzer

__all__ = [
    'EvidenceTracker',
    'get_evidence_tracker',
    'LegalReportGenerator',
    'get_report_generator',
    'ThreadAnalyzer',
    'get_thread_analyzer'
]