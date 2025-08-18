"""
Tests for TranscriptionService main orchestration.
"""

import os
import sys
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from transcription.main import TranscriptionService


class TestTranscriptionService:
    """Test TranscriptionService orchestration."""

    def test_service_initialization(self):
        """Test service initializes with correct database path."""
        service = TranscriptionService(db_path="test.db")
        assert service.db_path == "test.db"
        assert service.stats == {"processed": 0, "failed": 0, "skipped": 0}
        assert service.provider is not None

    def test_transcribe_file_orchestration(self):
        """Test complete transcription orchestration flow."""
        service = TranscriptionService()

        # Mock provider transcription
        mock_result = {
            "success": True,
            "data": {
                "text": "Test transcription",
                "filename": "test.mp4",
                "avg_confidence": -0.5,
                "duration": 10.0,
                "engine": "whisper_base",
                "segments": [{"text": "Test"}],
                "language": "en",
            },
        }

        with patch.object(service.provider, "is_available", return_value=True):
            with patch.object(service.provider, "transcribe_file", return_value=mock_result):
                with patch.object(service.db, "add_content", return_value="content_123"):

                    result = service.transcribe_file("test.mp4")

                    assert result["success"] is True
                    assert result["processed"] == 1
                    assert service.stats["processed"] == 1
                    assert service.stats["failed"] == 0

    def test_provider_not_available(self):
        """Test handling when provider is not available."""
        service = TranscriptionService()

        with patch.object(service.provider, "is_available", return_value=False):
            result = service.transcribe_file("test.mp4")

            assert result["success"] is False
            assert "not available" in result["error"]

    def test_transcription_failure_handling(self):
        """Test handling of transcription failures."""
        service = TranscriptionService()

        mock_result = {"success": False, "error": "Transcription failed"}

        with patch.object(service.provider, "is_available", return_value=True):
            with patch.object(service.provider, "transcribe_file", return_value=mock_result):

                result = service.transcribe_file("test.mp4")

                assert result["success"] is False
                assert service.stats["failed"] == 1

    def test_database_storage_failure(self):
        """Test handling of database storage failures."""
        service = TranscriptionService()

        mock_result = {
            "success": True,
            "data": {
                "text": "Test",
                "filename": "test.mp4",
                "avg_confidence": -0.5,
                "duration": 10.0,
                "engine": "whisper_base",
                "segments": [],
                "language": "en",
            },
        }

        with patch.object(service.provider, "is_available", return_value=True):
            with patch.object(service.provider, "transcribe_file", return_value=mock_result):
                with patch.object(service.db, "add_content", side_effect=Exception("DB error")):

                    result = service.transcribe_file("test.mp4")

                    assert result["success"] is False
                    assert "DB error" in result["error"]

    def test_batch_transcription(self):
        """Test batch transcription of multiple files."""
        service = TranscriptionService()

        files = ["file1.mp4", "file2.mp4", "file3.mp4"]

        # Mock different results for each file
        results_sequence = [
            {"success": True, "data": {"text": "Text 1"}},
            {"success": False, "error": "Failed"},
            {"success": True, "data": {"text": "Text 3"}},
        ]

        with patch.object(service, "transcribe_file", side_effect=results_sequence):
            result = service.transcribe_batch(files)

            assert result["success"] is True
            assert result["data"]["total_files"] == 3
            assert result["data"]["successful"] == 2
            assert result["data"]["failed"] == 1
            assert len(result["data"]["results"]) == 3

    def test_process_uploads_directory(self):
        """Test processing video files from uploads directory."""
        service = TranscriptionService()

        # Create temporary directories
        with tempfile.TemporaryDirectory() as tmpdir:
            input_dir = Path(tmpdir) / "input"
            output_dir = Path(tmpdir) / "output"
            input_dir.mkdir()

            # Create test video files
            video1 = input_dir / "video1.mp4"
            video2 = input_dir / "video2.avi"
            video1.touch()
            video2.touch()

            mock_result = {"success": True, "data": {"text": "Transcribed"}}

            with patch.object(service, "transcribe_file", return_value=mock_result):
                result = service.process_uploads_directory(str(input_dir), str(output_dir))

                assert result["success"] is True
                assert result["metadata"]["total_files"] == 2
                assert result["metadata"]["successful"] == 2
                assert result["metadata"]["failed"] == 0

                # Check files were moved
                assert (output_dir / "video1.mp4").exists()
                assert (output_dir / "video2.avi").exists()
                assert not (input_dir / "video1.mp4").exists()
                assert not (input_dir / "video2.avi").exists()

    def test_process_uploads_directory_with_failures(self):
        """Test processing with some failures."""
        service = TranscriptionService()

        with tempfile.TemporaryDirectory() as tmpdir:
            input_dir = Path(tmpdir) / "input"
            output_dir = Path(tmpdir) / "output"
            input_dir.mkdir()

            # Create test files
            video1 = input_dir / "video1.mp4"
            video2 = input_dir / "video2.mp4"
            video1.touch()
            video2.touch()

            # Mock success for first, failure for second
            results_sequence = [
                {"success": True, "data": {"text": "Success"}},
                {"success": False, "error": "Failed"},
            ]

            with patch.object(service, "transcribe_file", side_effect=results_sequence):
                result = service.process_uploads_directory(str(input_dir), str(output_dir))

                assert result["success"] is True
                assert result["metadata"]["successful"] == 1
                assert result["metadata"]["failed"] == 1

                # Only successful file should be moved
                assert (output_dir / "video1.mp4").exists()
                assert (input_dir / "video2.mp4").exists()  # Failed file stays

    def test_get_service_stats(self):
        """Test service statistics retrieval."""
        service = TranscriptionService()
        service.stats = {"processed": 5, "failed": 2, "skipped": 1}

        with patch.object(service.provider, "is_available", return_value=True):
            # Mock database query
            with patch("transcription.main.sqlite3.connect") as mock_connect:
                mock_cursor = MagicMock()
                mock_cursor.fetchone.return_value = [10]
                mock_conn = MagicMock()
                mock_conn.cursor.return_value = mock_cursor
                mock_connect.return_value = mock_conn

                result = service.get_service_stats()

                assert result["success"] is True
                assert result["data"]["status"] == "operational"
                assert result["data"]["transcripts_in_database"] == 10
                assert result["data"]["providers_available"] == ["whisper_local"]
                assert result["data"]["session_stats"]["processed"] == 5
                assert result["data"]["session_stats"]["failed"] == 2

    def test_metadata_storage(self):
        """Test that metadata is correctly stored in database."""
        service = TranscriptionService()

        mock_data = {
            "text": "Test transcript",
            "filename": "test.mp4",
            "avg_confidence": -0.75,
            "duration": 120.5,
            "engine": "whisper_base",
            "segments": [1, 2, 3],  # Mock segments
            "language": "en",
        }

        with patch.object(service.db, "add_content") as mock_add:
            service._store_transcript(mock_data)

            mock_add.assert_called_once()
            call_args = mock_add.call_args

            assert call_args[1]["content_type"] == "transcript"
            assert call_args[1]["title"] == "Audio: test.mp4"
            assert call_args[1]["content"] == "Test transcript"

            metadata = call_args[1]["metadata"]
            assert metadata["filename"] == "test.mp4"
            assert metadata["confidence"] == -0.75
            assert metadata["duration"] == 120.5
            assert metadata["engine"] == "whisper_base"
            assert metadata["segments"] == 3
            assert metadata["language"] == "en"

    def test_error_handling_with_exception(self):
        """Test exception handling in transcribe_file."""
        service = TranscriptionService()

        with patch.object(
            service.provider, "is_available", side_effect=Exception("Unexpected error")
        ):
            result = service.transcribe_file("test.mp4")

            assert result["success"] is False
            assert "Transcription failed" in result["error"]
            assert service.stats["failed"] == 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
