"""
Simple Transcription Service

Direct interface for audio/video transcription using Whisper.
Follows project patterns - simple, direct, and working.
"""

from pathlib import Path
from typing import Any

from loguru import logger

from shared.simple_db import SimpleDB

from .providers.whisper_provider import WhisperProvider


class TranscriptionService:
    """Simple transcription service using Whisper.

    Direct interface for converting audio/video to text with database storage.
    """

    def __init__(self, db_path: str = "emails.db", model_name: str = "large-v3") -> None:
        """Initialize transcription service.
        
        Args:
            db_path: Database path for storing transcripts
            model_name: Whisper model to use (recommend large-v3 for legal accuracy)
        """
        self.db_path = db_path
        self.db = SimpleDB(db_path)
        self.provider = WhisperProvider(model_name)
        self.stats = {"processed": 0, "failed": 0, "rejected": 0}
        
        logger.info(f"TranscriptionService initialized with model: {model_name} (anti-hallucination enabled)")

    def transcribe_file(self, file_path: str, context_type: str = "legal_general") -> dict[str, Any]:
        """Transcribe a single audio/video file."""
        if not self.provider.is_available():
            return {"success": False, "error": "Whisper not available"}

        try:
            # Transcribe file with improved settings
            result = self.provider.transcribe_file(file_path, context_type)
            if not result["success"]:
                # Track rejection reasons
                if "confidence too low" in result.get("error", ""):
                    self.stats["rejected"] += 1
                    logger.info(f"Rejected low-quality transcript: {file_path}")
                else:
                    self.stats["failed"] += 1
                return result

            # Store in database
            data = result["data"]
            content_id = self.db.add_content(
                content_type="transcript",
                title=f"Audio: {data['filename']}",
                content=data["text"],
                metadata={
                    "filename": data["filename"],
                    "confidence": data["stats"]["avg_confidence"],
                    "duration": data["stats"]["total_duration"],
                    "engine": data["engine"],
                    "language": data["language"],
                    "word_count": data["stats"]["word_count"],
                    "speech_rate": data["stats"]["speech_rate"],
                }
            )

            self.stats["processed"] += 1
            logger.info(f"Transcribed and stored: {data['filename']}")
            return {"success": True, "data": data, "content_id": content_id}

        except Exception as e:
            self.stats["failed"] += 1
            logger.error(f"Transcription failed for {file_path}: {e}")
            return {"success": False, "error": str(e)}

    def process_directory(self, input_dir: str = "data/raw") -> dict[str, Any]:
        """Process all audio/video files in directory."""
        input_path = Path(input_dir)
        if not input_path.exists():
            return {"success": False, "error": f"Directory not found: {input_dir}"}

        # Find audio/video files
        extensions = [".mp3", ".wav", ".m4a", ".mp4", ".avi", ".mov", ".mkv", ".wmv", ".flv"]
        files = []
        for ext in extensions:
            files.extend(input_path.rglob(f"*{ext}"))

        if not files:
            return {"success": True, "message": "No audio/video files found", "processed": 0}

        processed = 0
        failed = 0
        results = []

        for file_path in files:
            result = self.transcribe_file(str(file_path))
            results.append({
                "file": file_path.name,
                "success": result["success"],
                "error": result.get("error")
            })
            
            if result["success"]:
                processed += 1
            else:
                failed += 1

        return {
            "success": True,
            "processed": processed,
            "failed": failed,
            "total": len(files),
            "results": results
        }

    def get_stats(self) -> dict[str, Any]:
        """Get service statistics."""
        try:
            # Count transcripts in database
            import sqlite3
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM content WHERE content_type = 'transcript'")
            db_count = cursor.fetchone()[0]
            conn.close()

            return {
                "success": True,
                "data": {
                    "status": "operational" if self.provider.is_available() else "unavailable",
                    "transcripts_in_database": db_count,
                    "session_stats": self.stats,
                    "provider_available": self.provider.is_available()
                }
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    def validate_audio(self, file_path: str) -> dict[str, Any]:
        """Validate audio file."""
        return self.provider.validate_audio(file_path)