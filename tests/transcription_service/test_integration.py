"""
Integration tests for the complete transcription pipeline.
Tests the full workflow from audio input to database storage.
"""

import os
import sqlite3
import sys
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from shared.simple_db import SimpleDB
from transcription.main import TranscriptionService
from transcription.providers.whisper_provider import WhisperProvider


class TestTranscriptionIntegration:
    """Test complete transcription pipeline integration."""

    def test_end_to_end_transcription_flow(self):
        """Test complete flow from audio file to database storage."""
        # Use temporary database
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp_db:
            db_path = tmp_db.name

        try:
            service = TranscriptionService(db_path=db_path)

            # Create temporary audio file
            with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as tmp_audio:
                audio_path = tmp_audio.name

            # Mock the provider's transcription
            mock_transcription = {
                "success": True,
                "data": {
                    "text": "This is an integration test transcription",
                    "filename": Path(audio_path).name,
                    "avg_confidence": -0.45,
                    "duration": 5.5,
                    "engine": "whisper_base",
                    "segments": [
                        {
                            "start": 0,
                            "end": 2.5,
                            "text": "This is an integration",
                            "confidence": -0.4,
                        },
                        {
                            "start": 2.5,
                            "end": 5.5,
                            "text": "test transcription",
                            "confidence": -0.5,
                        },
                    ],
                    "language": "en",
                },
            }

            with patch.object(service.provider, "is_available", return_value=True):
                with patch.object(
                    service.provider, "transcribe_file", return_value=mock_transcription
                ):

                    # Perform transcription
                    result = service.transcribe_file(audio_path)

                    assert result["success"] is True
                    assert result["processed"] == 1

                    # Verify database storage
                    db = SimpleDB(db_path)
                    results = db.search_content("integration test transcription")

                    assert len(results) == 1
                    stored = results[0]
                    assert stored["content_type"] == "transcript"
                    assert "Audio:" in stored["title"]
                    assert "integration test transcription" in stored["content"].lower()

                    # Verify metadata
                    import json

                    metadata = json.loads(stored["metadata"])
                    assert metadata["confidence"] == -0.45
                    assert metadata["duration"] == 5.5
                    assert metadata["engine"] == "whisper_base"
                    assert metadata["segments"] == 2
                    assert metadata["language"] == "en"

            os.unlink(audio_path)

        finally:
            os.unlink(db_path)

    def test_audio_validation_integration(self):
        """Test integration of audio validation with transcription."""
        provider = WhisperProvider()

        # Create a mock audio file path
        with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as tmp:
            audio_path = tmp.name

        try:
            # Mock librosa for validation
            with patch("transcription.providers.whisper_provider.LIBROSA_AVAILABLE", True):
                with patch("transcription.providers.whisper_provider.librosa") as mock_librosa:
                    # Mock valid audio
                    mock_librosa.load.return_value = ([0.1] * 44100, 44100)  # 1 second of audio
                    mock_rms = MagicMock()
                    mock_rms.mean.return_value = 0.05
                    mock_librosa.feature.rms.return_value = mock_rms

                    # Validate audio
                    validation = provider.validate_audio(audio_path)

                    assert validation["success"] is True
                    assert validation["valid"] is True
                    assert validation["duration"] > 0.5
                    assert validation["rms_energy"] > 0.001

                    # Now mock transcription
                    provider.model = MagicMock()
                    provider.model.transcribe.return_value = {
                        "text": "Valid audio transcribed",
                        "segments": [
                            {"start": 0, "end": 1, "text": "Valid audio", "avg_logprob": -0.3}
                        ],
                        "language": "en",
                    }

                    # Transcribe the validated audio
                    result = provider.transcribe_file(audio_path)

                    assert result["success"] is True
                    assert result["data"]["text"] == "Valid audio transcribed"

        finally:
            os.unlink(audio_path)

    def test_batch_processing_integration(self):
        """Test batch processing with database storage."""
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp_db:
            db_path = tmp_db.name

        try:
            service = TranscriptionService(db_path=db_path)

            # Create test files
            test_files = []
            for i in range(3):
                tmp = tempfile.NamedTemporaryFile(suffix=f"_{i}.mp4", delete=False)
                test_files.append(tmp.name)
                tmp.close()

            # Mock transcriptions for each file
            def mock_transcribe(file_path):
                filename = Path(file_path).name
                idx = filename.split("_")[1].split(".")[0]
                return {
                    "success": True,
                    "data": {
                        "text": f"Transcription {idx}",
                        "filename": filename,
                        "avg_confidence": -0.5,
                        "duration": float(idx) + 1,
                        "engine": "whisper_base",
                        "segments": [],
                        "language": "en",
                    },
                }

            with patch.object(service.provider, "is_available", return_value=True):
                with patch.object(service.provider, "transcribe_file", side_effect=mock_transcribe):

                    # Process batch
                    result = service.transcribe_batch(test_files)

                    assert result["success"] is True
                    assert result["data"]["successful"] == 3
                    assert result["data"]["failed"] == 0

                    # Verify all transcriptions in database
                    conn = sqlite3.connect(db_path)
                    cursor = conn.cursor()
                    cursor.execute("SELECT COUNT(*) FROM content WHERE content_type = 'transcript'")
                    count = cursor.fetchone()[0]
                    conn.close()

                    assert count == 3

            # Cleanup test files
            for f in test_files:
                os.unlink(f)

        finally:
            os.unlink(db_path)

    def test_confidence_filtering(self):
        """Test filtering based on confidence scores."""
        service = TranscriptionService()

        # Test with varying confidence levels
        test_cases = [
            ("high_confidence.mp4", -0.2, True),  # High confidence
            ("medium_confidence.mp4", -0.6, True),  # Medium confidence
            ("low_confidence.mp4", -1.5, False),  # Low confidence (could be filtered)
        ]

        for filename, confidence, should_store in test_cases:
            mock_result = {
                "success": True,
                "data": {
                    "text": f"Text for {filename}",
                    "filename": filename,
                    "avg_confidence": confidence,
                    "duration": 10.0,
                    "engine": "whisper_base",
                    "segments": [],
                    "language": "en",
                },
            }

            with patch.object(service.provider, "is_available", return_value=True):
                with patch.object(service.provider, "transcribe_file", return_value=mock_result):
                    with patch.object(service.db, "add_content", return_value="content_id"):

                        result = service.transcribe_file(filename)

                        # All should succeed in current implementation
                        # Future: Add confidence threshold filtering
                        assert result["success"] is True

                        # Verify confidence is stored for potential filtering
                        assert result["data"]["avg_confidence"] == confidence

    def test_model_variants(self):
        """Test using different Whisper model variants."""
        models = ["tiny", "base", "small"]

        for model_name in models:
            with patch("transcription.providers.whisper_provider.WHISPER_AVAILABLE", True):
                with patch("transcription.providers.whisper_provider.LIBROSA_AVAILABLE", True):
                    with patch(
                        "transcription.providers.whisper_provider.whisper.load_model"
                    ) as mock_load:
                        mock_model = MagicMock()
                        mock_load.return_value = mock_model

                        provider = WhisperProvider(model_name=model_name)

                        assert provider.model_name == model_name
                        mock_load.assert_called_once_with(model_name)

    def test_error_recovery(self):
        """Test service recovery from various error conditions."""
        service = TranscriptionService()

        # Test recovery from provider error
        with patch.object(service.provider, "is_available", return_value=True):
            with patch.object(
                service.provider, "transcribe_file", side_effect=Exception("Provider error")
            ):

                result = service.transcribe_file("test.mp4")
                assert result["success"] is False
                assert service.stats["failed"] == 1

                # Service should still be operational for next request
                with patch.object(
                    service.provider, "transcribe_file", return_value={"success": True, "data": {}}
                ):
                    with patch.object(service.db, "add_content", return_value="id"):
                        # Reset stats for clarity
                        service.stats["failed"] = 0

                        # Mock successful transcription data
                        mock_data = {
                            "success": True,
                            "data": {
                                "text": "Recovery test",
                                "filename": "test2.mp4",
                                "avg_confidence": -0.5,
                                "duration": 5.0,
                                "engine": "whisper_base",
                                "segments": [],
                                "language": "en",
                            },
                        }

                        with patch.object(
                            service.provider, "transcribe_file", return_value=mock_data
                        ):
                            result2 = service.transcribe_file("test2.mp4")
                            assert result2["success"] is True

    def test_segment_timeline_integration(self):
        """Test that segment timestamps enable timeline features."""
        service = TranscriptionService()

        mock_segments = [
            {"start": 0.0, "end": 5.2, "text": "First segment", "confidence": -0.3},
            {"start": 5.2, "end": 10.5, "text": "Second segment", "confidence": -0.4},
            {"start": 10.5, "end": 15.0, "text": "Third segment", "confidence": -0.35},
        ]

        mock_result = {
            "success": True,
            "data": {
                "text": "First segment Second segment Third segment",
                "filename": "timeline_test.mp4",
                "avg_confidence": -0.35,
                "duration": 15.0,
                "engine": "whisper_base",
                "segments": mock_segments,
                "language": "en",
            },
        }

        with patch.object(service.provider, "is_available", return_value=True):
            with patch.object(service.provider, "transcribe_file", return_value=mock_result):
                with patch.object(service.db, "add_content") as mock_add:

                    result = service.transcribe_file("timeline_test.mp4")

                    assert result["success"] is True

                    # Verify segments are stored for timeline
                    call_args = mock_add.call_args[1]
                    metadata = call_args["metadata"]
                    assert metadata["segments"] == 3  # Count of segments
                    assert metadata["duration"] == 15.0  # Total duration from segments


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
