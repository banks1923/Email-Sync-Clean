"""Base provider abstract class for transcription services.

Defines the standard interface that all transcription providers must implement,
following the project's clean architecture principles and established patterns.
"""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any

from loguru import logger


class BaseTranscriptionProvider(ABC):
    """Abstract base class for all transcription providers.
    
    Defines the standard interface and common functionality that all providers
    must implement. Follows project patterns from WhisperProvider and other services.
    """

    def __init__(self, provider_name: str) -> None:
        """Initialize base provider with common configuration.
        
        Args:
            provider_name: Unique name identifier for this provider
        """
        self.provider_name = provider_name
        self.legal_context_types = ["landlord_tenant", "legal_general", "property_inspection"]
        
        # Standard legal domain prompts
        self.legal_prompts = {
            "landlord_tenant": "The following is a conversation about landlord-tenant matters, property management, lease agreements, and rental disputes.",
            "legal_general": "The following is a legal conversation involving contracts, agreements, documentation, and legal procedures.",
            "property_inspection": "The following is a conversation about property inspection, maintenance, repairs, and building conditions."
        }
        
        logger.info(f"Initialized {provider_name} transcription provider")

    @abstractmethod
    def is_available(self) -> bool:
        """Check if the provider is available and properly configured.
        
        Returns:
            bool: True if provider can be used, False otherwise
        """

    @abstractmethod
    def transcribe_file(self, file_path: str, context_type: str = "legal_general") -> dict[str, Any]:
        """Transcribe audio/video file with legal domain context.
        
        Args:
            file_path: Path to audio/video file to transcribe
            context_type: Legal context type (landlord_tenant, legal_general, property_inspection)
            
        Returns:
            Standard response format: {
                "success": bool,
                "data": {
                    "text": str,               # Full transcription text
                    "segments": List[dict],    # Timestamped segments
                    "language": str,           # Detected language
                    "stats": dict,             # Statistics (duration, confidence, etc.)
                    "context_type": str,       # Applied context type
                    "engine": str,             # Provider engine identifier
                    "filename": str,           # Original filename
                },
                "error": str               # Error message if success=False
            }
        """

    @abstractmethod
    def validate_audio(self, file_path: str) -> dict[str, Any]:
        """Validate audio file for transcription requirements.
        
        Args:
            file_path: Path to audio/video file
            
        Returns:
            Dict with validation results: {
                "success": bool,
                "valid": bool,          # True if file meets requirements
                "duration": float,      # Audio duration in seconds
                "error": str            # Error message if validation fails
            }
        """

    def get_legal_prompt(self, context_type: str) -> str:
        """Get legal domain prompt for the specified context type.
        
        Args:
            context_type: Legal context type
            
        Returns:
            str: Domain-specific prompt or default legal_general prompt
        """
        if context_type not in self.legal_context_types:
            logger.warning(f"Unknown context type '{context_type}', using 'legal_general'")
            context_type = "legal_general"
            
        return self.legal_prompts.get(context_type, self.legal_prompts["legal_general"])

    def validate_file_path(self, file_path: str) -> dict[str, Any]:
        """Common file path validation for all providers.
        
        Args:
            file_path: Path to validate
            
        Returns:
            Dict with validation results
        """
        file_path_obj = Path(file_path)
        
        if not file_path_obj.exists():
            return {"success": False, "error": f"File not found: {file_path}"}
            
        if not file_path_obj.is_file():
            return {"success": False, "error": f"Path is not a file: {file_path}"}
            
        # Check for common audio/video extensions
        valid_extensions = {".mp3", ".wav", ".m4a", ".mp4", ".avi", ".mov", ".mkv", ".wmv", ".flv", ".aac", ".ogg"}
        if file_path_obj.suffix.lower() not in valid_extensions:
            logger.warning(f"File extension '{file_path_obj.suffix}' may not be supported: {file_path}")
            
        return {"success": True, "path": file_path_obj}

    def create_standard_response(
        self, 
        success: bool,
        data: dict[str, Any] = None,
        error: str = ""
    ) -> dict[str, Any]:
        """Create standardized response format for all providers.
        
        Args:
            success: Whether the operation succeeded
            data: Result data (only included if success=True)
            error: Error message (only included if success=False)
            
        Returns:
            Dict: Standardized response format
        """
        response = {"success": success}
        
        if success and data:
            response["data"] = data
        elif not success and error:
            response["error"] = error
            
        return response

    def calculate_basic_stats(self, segments: list, full_text: str) -> dict[str, Any]:
        """Calculate basic transcription statistics common to all providers.
        
        Args:
            segments: List of transcription segments with start/end times
            full_text: Complete transcription text
            
        Returns:
            Dict: Basic statistics
        """
        if not segments:
            return {
                "total_segments": 0,
                "total_duration": 0.0,
                "word_count": 0,
                "speech_rate": 0.0
            }
            
        total_duration = segments[-1].get("end", 0.0) - segments[0].get("start", 0.0)
        word_count = len(full_text.split()) if full_text else 0
        speech_rate = word_count / (total_duration / 60) if total_duration > 0 else 0
        
        return {
            "total_segments": len(segments),
            "total_duration": total_duration,
            "word_count": word_count,
            "speech_rate": speech_rate
        }

    def export_to_csv(self, transcription_data: dict[str, Any], output_path: Path) -> dict[str, Any]:
        """Export transcription data to CSV format.
        
        Common CSV export functionality that all providers can use.
        
        Args:
            transcription_data: Transcription result data
            output_path: Path for CSV output file
            
        Returns:
            Dict: Export operation result
        """
        try:
            import csv
            
            segments = transcription_data.get("segments", [])
            if not segments:
                return {"success": False, "error": "No segments to export"}
            
            with open(output_path, 'w', newline='', encoding='utf-8') as csvfile:
                fieldnames = ["filename", "start", "end", "text", "confidence", "speaker"]
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                writer.writeheader()
                
                filename = transcription_data.get("filename", "unknown")
                for segment in segments:
                    writer.writerow({
                        "filename": filename,
                        "start": f"{segment.get('start', 0):.3f}",
                        "end": f"{segment.get('end', 0):.3f}",
                        "text": segment.get("text", ""),
                        "confidence": f"{segment.get('confidence', -1.0):.4f}",
                        "speaker": segment.get("speaker", "unknown")
                    })
            
            logger.info(f"Transcription exported to CSV: {output_path}")
            return {"success": True, "output_path": str(output_path)}
            
        except Exception as e:
            logger.error(f"CSV export failed: {e}")
            return {"success": False, "error": f"CSV export failed: {str(e)}"}

    def __str__(self) -> str:
        """String representation of the provider."""
        return f"{self.provider_name} (available: {self.is_available()})"

    def __repr__(self) -> str:
        """Technical representation of the provider."""
        return f"<{self.__class__.__name__}(name='{self.provider_name}', available={self.is_available()})>"