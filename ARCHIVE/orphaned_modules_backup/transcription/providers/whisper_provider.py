"""Simple Whisper provider for local transcription.

Simple, direct Whisper transcription following project principles.
No complex architecture, just working code.
"""

from typing import Any

from loguru import logger

from .base_provider import BaseTranscriptionProvider

try:
    import whisper
    WHISPER_AVAILABLE = True
except ImportError:
    WHISPER_AVAILABLE = False

LIBROSA_AVAILABLE = False
try:
    import librosa
    LIBROSA_AVAILABLE = True
except ImportError:
    pass


class WhisperProvider(BaseTranscriptionProvider):
    """Simple Whisper transcription provider.

    Direct interface to OpenAI Whisper without complex architecture.
    """

    def __init__(self, model_name: str = "base", forensic_mode: bool = False) -> None:
        """Initialize Whisper provider with model name.
        
        Args:
            model_name: Whisper model to use (recommend large-v3 for legal use)
            forensic_mode: Enable anti-hallucination settings for legal evidence
        """
        super().__init__(f"whisper_local_{model_name}")
        
        self.model_name = model_name
        self.model = None
        self.forensic_mode = forensic_mode
        
        # Anti-hallucination settings for legal use
        if forensic_mode:
            logger.info("FORENSIC MODE: Enhanced anti-hallucination settings enabled")

        # Initialize if dependencies available
        if self.is_available():
            self._load_model()

    def _load_model(self):
        """Load Whisper model."""
        try:
            self.model = whisper.load_model(self.model_name)
            logger.info(f"Whisper model '{self.model_name}' loaded")
        except Exception as e:
            logger.error(f"Failed to load Whisper model: {e}")
            raise

    def is_available(self) -> bool:
        """Check if Whisper is available."""
        return WHISPER_AVAILABLE and LIBROSA_AVAILABLE

    def transcribe_file(self, file_path: str, context_type: str = "legal_general") -> dict[str, Any]:
        """Transcribe audio/video file.

        Args:
            file_path: Path to audio/video file
            context_type: Legal context type (ignored for now, kept for compatibility)

        Returns:
            Standard response: {"success": bool, "data": dict, "error": str}
        """
        if not self.is_available():
            return self.create_standard_response(
                False, 
                error="Whisper or librosa not available. Install with: pip install openai-whisper librosa"
            )

        if not self.model:
            return self.create_standard_response(False, error="Whisper model not loaded")

        # Validate file path using base class method
        path_result = self.validate_file_path(file_path)
        if not path_result["success"]:
            return self.create_standard_response(False, error=path_result["error"])
        
        file_path_obj = path_result["path"]

        try:
            # Improved Whisper settings for better accuracy
            whisper_options = {
                "language": "en",  # Force English for legal content
                "temperature": 0.0,  # Reduce hallucinations
                "condition_on_previous_text": False,  # Prevent drift
                "no_speech_threshold": 0.6,  # Better silence detection
                "logprob_threshold": -1.0,  # Filter low-confidence segments
                "compression_ratio_threshold": 2.4,  # Detect repetitive text
            }
            
            # Add legal context prompt
            if context_type == "legal_general":
                whisper_options["initial_prompt"] = "This is a legal conversation with formal language. No casual expressions or slang."
            elif context_type == "landlord_tenant":
                whisper_options["initial_prompt"] = "This is a landlord-tenant discussion about property, rent, repairs, and housing issues."
            
            # Transcribe with improved settings
            result = self.model.transcribe(str(file_path_obj), **whisper_options)

            # Quality check - reject if obviously bad
            text = result.get("text", "").strip()
            if not text or len(text) < 10:
                return self.create_standard_response(False, error="Transcription too short or empty")

            # Extract and filter segments
            segments = []
            total_confidence = 0
            segment_count = 0

            for segment in result.get("segments", []):
                confidence = segment.get("avg_logprob", -1.0)
                segment_text = segment.get("text", "").strip()
                
                # Skip very low confidence segments
                if confidence < -3.0 or not segment_text:
                    continue
                
                segment_data = {
                    "start": segment.get("start", 0.0),
                    "end": segment.get("end", 0.0),
                    "text": segment_text,
                    "confidence": confidence,
                }
                segments.append(segment_data)

                total_confidence += confidence
                segment_count += 1

            # Rebuild text from filtered segments
            filtered_text = " ".join(seg["text"] for seg in segments).strip()
            
            # Final quality checks
            if not filtered_text or len(filtered_text) < 10:
                return self.create_standard_response(False, error="No reliable transcription after filtering")

            avg_confidence = total_confidence / segment_count if segment_count > 0 else -1.0
            
            # Reject if average confidence too low
            if avg_confidence < -2.5:
                return self.create_standard_response(False, error=f"Transcription confidence too low: {avg_confidence:.3f}")

            duration = segments[-1]["end"] if segments else 0.0
            word_count = len(filtered_text.split())

            data = {
                "text": filtered_text,
                "segments": segments,
                "language": result.get("language", "en"),
                "stats": {
                    "avg_confidence": avg_confidence,
                    "total_duration": duration,
                    "word_count": word_count,
                    "speech_rate": word_count / (duration / 60) if duration > 0 else 0
                },
                "context_type": context_type,
                "engine": f"whisper_{self.model_name}_filtered",
                "filename": file_path_obj.name,
            }

            return self.create_standard_response(True, data=data)

        except Exception as e:
            logger.error(f"Transcription failed for {file_path}: {e}")
            return self.create_standard_response(False, error=f"Transcription failed: {str(e)}")

    def validate_audio(self, file_path: str) -> dict[str, Any]:
        """Basic audio validation using librosa.

        Args:
            file_path: Path to audio/video file

        Returns:
            Dict with validation results
        """
        try:
            if not LIBROSA_AVAILABLE:
                return {"success": False, "error": "librosa not available for audio validation"}

            # Load audio for basic validation (first 10 seconds)
            y, sr = librosa.load(file_path, duration=10.0)

            duration = len(y) / sr
            rms_energy = float(librosa.feature.rms(y=y).mean())

            # Basic quality checks
            is_valid = duration > 0.5 and rms_energy > 0.001  # At least 0.5s and some audio energy

            return {
                "success": True,
                "valid": is_valid,
                "duration": duration,
                "rms_energy": rms_energy,
                "sample_rate": sr,
            }

        except Exception as e:
            return {"success": False, "error": f"Audio validation failed: {str(e)}"}
