"""Tests for EmailThreadProcessor (simplified after analog removal).

Tests Gmail thread processing, chronological sorting, and markdown
formatting.
"""

from unittest.mock import Mock, patch

import pytest

try:
    from infrastructure.documents.processors.email_thread_processor import EmailThreadProcessor

    PROCESSOR_AVAILABLE = True
except ImportError:
    PROCESSOR_AVAILABLE = False

# Skip all tests if EmailThreadProcessor not available
pytestmark = pytest.mark.skipif(
    not PROCESSOR_AVAILABLE, reason="EmailThreadProcessor not available - Gmail service required"
)


class TestEmailThreadProcessor:
    """
    Test suite for EmailThreadProcessor (simplified).
    """

    @pytest.fixture
    def sample_messages(self):
        """
        Create sample email messages for testing.
        """
        return [
            {
                "message_id": "msg_001",
                "thread_id": "thread_123",
                "subject": "Test Email Thread",
                "sender": "Alice <alice@example.com>",
                "recipient_to": "Bob <bob@example.com>",
                "content": "<p>Hello Bob, this is the first message.</p>",
                "datetime_utc": "2025-01-15T10:00:00",
                "internal_date": "1642248000000",
            },
            {
                "message_id": "msg_002",
                "thread_id": "thread_123",
                "subject": "Re: Test Email Thread",
                "sender": "Bob <bob@example.com>",
                "recipient_to": "Alice <alice@example.com>",
                "content": "<p>Hi Alice, this is my reply.</p>",
                "datetime_utc": "2025-01-15T11:00:00",
                "internal_date": "1642251600000",
            },
        ]

    @pytest.fixture
    def mock_processor(self):
        """
        Create EmailThreadProcessor with mocked Gmail service.
        """
        processor = EmailThreadProcessor()

        # Mock Gmail service
        mock_service = Mock()
        mock_service.gmail_api = Mock()
        mock_service.gmail_api.service = Mock()
        mock_service.gmail_api.connect.return_value = {"success": True}
        mock_service.gmail_api._execute_with_timeout = Mock()
        mock_service.gmail_api.parse_message = lambda msg: msg

        processor.gmail_service = mock_service
        return processor

    def test_initialization(self):
        """
        Test EmailThreadProcessor initialization.
        """
        if PROCESSOR_AVAILABLE:
            processor = EmailThreadProcessor()
            assert processor.gmail_service is None  # Set externally
            assert processor.max_emails_per_file == 100

    def test_sort_chronologically(self, mock_processor, sample_messages):
        """
        Test chronological sorting of messages.
        """
        # Reverse the messages
        reversed_messages = list(reversed(sample_messages))

        sorted_messages = mock_processor._sort_chronologically(reversed_messages)

        assert sorted_messages[0]["message_id"] == "msg_001"
        assert sorted_messages[1]["message_id"] == "msg_002"

    def test_generate_thread_metadata(self, mock_processor, sample_messages):
        """
        Test metadata generation for thread.
        """
        metadata = mock_processor._generate_thread_metadata(sample_messages, "thread_123")

        assert metadata["thread_id"] == "thread_123"
        assert metadata["subject"] == "Test Email Thread"
        assert metadata["message_count"] == 2
        assert metadata["participant_count"] == 2
        assert "alice@example.com" in metadata["participants"]
        assert "bob@example.com" in metadata["participants"]

    def test_process_single_thread(self, mock_processor, sample_messages):
        """
        Test processing a single thread (returns markdown).
        """
        metadata = {"thread_id": "thread_123", "subject": "Test Thread", "message_count": 2}

        with patch.object(mock_processor, "_format_thread_to_markdown") as mock_format:
            mock_format.return_value = "# Test Thread\n\nContent"

            result = mock_processor._process_single_thread(
                sample_messages, metadata, include_metadata=True
            )

        assert result["success"] is True
        assert result["thread_id"] == "thread_123"
        assert result["message_count"] == 2
        assert result["markdown_content"] == "# Test Thread\n\nContent"
        assert result["suggested_filename"]

    def test_process_large_thread(self, mock_processor):
        """
        Test processing a large thread (returns multiple markdown parts).
        """
        # Create 150 messages
        large_messages = []
        for i in range(150):
            large_messages.append(
                {
                    "message_id": f"msg_{i:03d}",
                    "thread_id": "thread_large",
                    "subject": "Large Thread",
                    "sender": f"user{i}@example.com",
                    "content": f"Message {i}",
                    "datetime_utc": f"2025-01-15T{10 + i//60:02d}:{i%60:02d}:00",
                    "internal_date": str(1642248000000 + i * 60000),
                }
            )

        metadata = {"thread_id": "thread_large", "subject": "Large Thread", "message_count": 150}

        with patch.object(mock_processor, "_format_thread_to_markdown") as mock_format:
            mock_format.side_effect = ["# Part 1\n\nContent", "# Part 2\n\nContent"]

            result = mock_processor._process_large_thread(
                large_messages, metadata, include_metadata=True
            )

        assert result["success"] is True
        assert result["thread_id"] == "thread_large"
        assert result["message_count"] == 150
        assert result["parts_created"] == 2
        assert len(result["markdown_parts"]) == 2
        assert len(result["suggested_filenames"]) == 2
        assert result["split_into_parts"] is True

    def test_format_message_as_markdown(self, mock_processor, sample_messages):
        """
        Test formatting single message as markdown.
        """
        with patch(
            "infrastructure.documents.processors.email_thread_processor.clean_html_content"
        ) as mock_clean:
            mock_clean.return_value = "Hello Bob, this is the first message."

            markdown = mock_processor._format_message_as_markdown(sample_messages[0], 1)

        assert "## Message 1" in markdown
        assert "**From:** Alice <alice@example.com>" in markdown
        assert "**To:** Bob <bob@example.com>" in markdown
        assert "Hello Bob, this is the first message." in markdown

    def test_generate_filename(self, mock_processor):
        """
        Test filename generation.
        """
        metadata = {
            "thread_id": "thread_123",
            "subject": "Test Email Thread!",
            "date_range": {"start": "2025-01-15T10:00:00Z"},
        }

        filename = mock_processor._generate_filename(metadata)
        assert "2025-01-15" in filename
        assert "test_email_thread" in filename
        assert "thread_123" in filename
        assert filename.endswith(".md")

        # Test with part number
        filename_part = mock_processor._generate_filename(metadata, part_num=2)
        assert "part2" in filename_part

    def test_process_thread_end_to_end(self, mock_processor, sample_messages):
        """
        Test complete thread processing.
        """
        thread_id = "thread_123"

        # Mock the fetch method
        with patch.object(mock_processor, "_fetch_thread_messages") as mock_fetch:
            mock_fetch.return_value = {"success": True, "messages": sample_messages}

            result = mock_processor.process_thread(thread_id, include_metadata=True)

        assert result["success"] is True
        assert result["thread_id"] == thread_id
        assert result["message_count"] == 2
        assert result["markdown_content"]

    def test_validate_setup(self, mock_processor):
        """
        Test setup validation.
        """
        result = mock_processor.validate_setup()

        assert "gmail_available" in result
        assert "dependencies" in result
        assert "directories" in result
        assert (
            result["directories"]["note"]
            == "Analog database removed - no directory validation needed"
        )
