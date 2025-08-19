"""Simplified transcription providers.

Contains only the essential WhisperProvider without factory patterns.
"""

from .whisper_provider import WhisperProvider

__all__ = ["WhisperProvider"]
