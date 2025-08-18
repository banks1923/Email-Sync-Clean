"""
Transcription Service - Simplified Audio/Video to Text Conversion

Direct interface for transcribing audio and video files using:
- Local Whisper models
- Simple error handling
- Database integration via ContentWriter
- CLI integration via scripts/vsearch

Simplified Components:
- TranscriptionService: Main service class (~240 lines)
- WhisperProvider: Direct Whisper interface (~100 lines)
- No factory patterns or complex architecture
"""

from .main import TranscriptionService

__all__ = ["TranscriptionService"]

__version__ = "1.0.0"
