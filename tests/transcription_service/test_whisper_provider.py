"""
Tests for WhisperProvider including audio validation and transcription.
"""

import os
import sys
import tempfile
from unittest.mock import MagicMock, patch

import pytest

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from transcription.providers.whisper_provider import WhisperProvider


class TestWhisperProvider:
    """Test WhisperProvider functionality."""

    def test_provider_initialization(self):
        """Test provider initializes with correct model name."""
        with patch("transcription.providers.whisper_provider.WHISPER_AVAILABLE", True):
            with patch("transcription.providers.whisper_provider.LIBROSA_AVAILABLE", True):
                with patch.object(WhisperProvider, "_load_model"):
                    provider = WhisperProvider(model_name="base")
                    assert provider.model_name == "base"
                    assert provider.model is None  # Not loaded due to mock

    def test_is_available_checks_dependencies(self):
        """Test availability check for whisper and librosa."""
        provider = WhisperProvider()

        # Test with both available
        with patch("transcription.providers.whisper_provider.WHISPER_AVAILABLE", True):
            with patch("transcription.providers.whisper_provider.LIBROSA_AVAILABLE", True):
                assert provider.is_available() is True

        # Test with whisper missing
        with patch("transcription.providers.whisper_provider.WHISPER_AVAILABLE", False):
            with patch("transcription.providers.whisper_provider.LIBROSA_AVAILABLE", True):
                assert provider.is_available() is False

        # Test with librosa missing
        with patch("transcription.providers.whisper_provider.WHISPER_AVAILABLE", True):
            with patch("transcription.providers.whisper_provider.LIBROSA_AVAILABLE", False):
                assert provider.is_available() is False

    def test_transcribe_file_validates_file_existence(self):
        """Test transcription validates file exists."""
        provider = WhisperProvider()

        result = provider.transcribe_file("/nonexistent/file.mp4")
        assert result["success"] is False
        assert "not found" in result["error"].lower()

    def test_transcribe_file_with_mock_whisper(self):
        """Test transcription with mocked Whisper model."""
        with patch("transcription.providers.whisper_provider.WHISPER_AVAILABLE", True):
            with patch("transcription.providers.whisper_provider.LIBROSA_AVAILABLE", True):

                # Create provider with mocked model
                provider = WhisperProvider()
                mock_model = MagicMock()
                provider.model = mock_model

                # Mock transcribe result
                mock_model.transcribe.return_value = {
                    "text": "This is a test transcription",
                    "segments": [
                        {"start": 0.0, "end": 2.5, "text": "This is a test", "avg_logprob": -0.5},
                        {"start": 2.5, "end": 4.0, "text": "transcription", "avg_logprob": -0.3},
                    ],
                    "language": "en",
                }

                # Create a temporary test file
                import tempfile

                with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as tmp:
                    tmp_path = tmp.name

                try:
                    result = provider.transcribe_file(tmp_path)

                    assert result["success"] is True
                    assert result["data"]["text"] == "This is a test transcription"
                    assert len(result["data"]["segments"]) == 2
                    assert result["data"]["language"] == "en"
                    assert result["data"]["avg_confidence"] == pytest.approx(-0.4, rel=0.01)
                    assert result["data"]["duration"] == 4.0
                    assert result["data"]["engine"] == "whisper_base"

                finally:
                    os.unlink(tmp_path)

    def test_confidence_calculation(self):
        """Test confidence score calculation from segments."""
        provider = WhisperProvider()
        provider.model = MagicMock()

        # Test with varying confidence segments
        provider.model.transcribe.return_value = {
            "text": "Test",
            "segments": [
                {"start": 0, "end": 1, "text": "Test1", "avg_logprob": -0.2},
                {"start": 1, "end": 2, "text": "Test2", "avg_logprob": -0.8},
                {"start": 2, "end": 3, "text": "Test3", "avg_logprob": -0.5},
            ],
            "language": "en",
        }

        with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as tmp:
            tmp_path = tmp.name

        try:
            result = provider.transcribe_file(tmp_path)

            # Average of -0.2, -0.8, -0.5 = -1.5/3 = -0.5
            assert result["data"]["avg_confidence"] == pytest.approx(-0.5, rel=0.01)
            assert result["data"]["duration"] == 3.0

        finally:
            os.unlink(tmp_path)

    def test_validate_audio_with_mock_librosa(self):
        """Test audio validation with mocked librosa."""
        provider = WhisperProvider()

        with patch("transcription.providers.whisper_provider.LIBROSA_AVAILABLE", True):
            with patch("transcription.providers.whisper_provider.librosa") as mock_librosa:
                # Mock librosa.load
                mock_librosa.load.return_value = (
                    [0.1, 0.2, 0.3] * 1000,  # Mock audio data
                    22050,  # Sample rate
                )

                # Mock RMS calculation
                mock_rms = MagicMock()
                mock_rms.mean.return_value = 0.05
                mock_librosa.feature.rms.return_value = mock_rms

                result = provider.validate_audio("test.mp4")

                assert result["success"] is True
                assert result["valid"] is True
                assert result["duration"] > 0
                assert result["rms_energy"] == 0.05
                assert result["sample_rate"] == 22050

    def test_validate_audio_invalid_file(self):
        """Test audio validation with invalid audio (too short or silent)."""
        provider = WhisperProvider()

        with patch("transcription.providers.whisper_provider.LIBROSA_AVAILABLE", True):
            with patch("transcription.providers.whisper_provider.librosa") as mock_librosa:
                # Mock very short audio
                mock_librosa.load.return_value = ([0.0] * 10, 22050)  # Very short, silent audio

                mock_rms = MagicMock()
                mock_rms.mean.return_value = 0.0001  # Below threshold
                mock_librosa.feature.rms.return_value = mock_rms

                result = provider.validate_audio("test.mp4")

                assert result["success"] is True
                assert result["valid"] is False  # Invalid due to low energy

    def test_error_handling_in_transcription(self):
        """Test error handling when transcription fails."""
        provider = WhisperProvider()
        provider.model = MagicMock()
        provider.model.transcribe.side_effect = Exception("Transcription error")

        with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as tmp:
            tmp_path = tmp.name

        try:
            result = provider.transcribe_file(tmp_path)

            assert result["success"] is False
            assert "Transcription failed" in result["error"]

        finally:
            os.unlink(tmp_path)

    def test_model_loading(self):
        """Test model loading with mock."""
        with patch("transcription.providers.whisper_provider.WHISPER_AVAILABLE", True):
            with patch("transcription.providers.whisper_provider.LIBROSA_AVAILABLE", True):
                with patch("transcription.providers.whisper_provider.whisper") as mock_whisper:
                    mock_model = MagicMock()
                    mock_whisper.load_model.return_value = mock_model

                    provider = WhisperProvider(model_name="small")

                    assert provider.model == mock_model
                    mock_whisper.load_model.assert_called_once_with("small")

    def test_segment_timestamp_extraction(self):
        """Test that segment timestamps are properly extracted."""
        provider = WhisperProvider()
        provider.model = MagicMock()

        provider.model.transcribe.return_value = {
            "text": "Full text",
            "segments": [
                {"start": 0.0, "end": 1.5, "text": "First", "avg_logprob": -0.4},
                {"start": 1.5, "end": 3.2, "text": "Second", "avg_logprob": -0.6},
            ],
            "language": "en",
        }

        with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as tmp:
            tmp_path = tmp.name

        try:
            result = provider.transcribe_file(tmp_path)

            segments = result["data"]["segments"]
            assert segments[0]["start"] == 0.0
            assert segments[0]["end"] == 1.5
            assert segments[0]["text"] == "First"
            assert segments[1]["start"] == 1.5
            assert segments[1]["end"] == 3.2

        finally:
            os.unlink(tmp_path)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
