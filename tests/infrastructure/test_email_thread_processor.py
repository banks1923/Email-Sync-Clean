"""
Tests for EmailThreadProcessor - Simple, direct tests following CLAUDE.md principles.

Tests Gmail thread processing, chronological sorting, markdown formatting, and file saving.
"""

import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

try:
    from infrastructure.documents.processors.email_thread_processor import (
        EmailThreadProcessor,
        get_email_thread_processor,
    )
    PROCESSOR_AVAILABLE = True
except ImportError:
    PROCESSOR_AVAILABLE = False

# Skip all tests if EmailThreadProcessor not available
pytestmark = pytest.mark.skipif(
    not PROCESSOR_AVAILABLE, 
    reason="EmailThreadProcessor not available - Gmail service required"
)


class TestEmailThreadProcessor:
    """Test suite for EmailThreadProcessor."""

    @pytest.fixture
    def temp_dir(self):
        """Create temporary directory for test files."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)

    @pytest.fixture
    def sample_messages(self):
        """Create sample email messages for testing."""
        return [
            {
                "message_id": "msg_001",
                "thread_id": "thread_123",
                "subject": "Test Email Thread",
                "sender": "Alice <alice@example.com>",
                "recipient_to": "Bob <bob@example.com>",
                "content": "<p>Hello Bob, this is the first message.</p>",
                "datetime_utc": "2025-01-15T10:00:00",
                "internal_date": "1642248000000"
            },
            {
                "message_id": "msg_002", 
                "thread_id": "thread_123",
                "subject": "Re: Test Email Thread",
                "sender": "Bob <bob@example.com>",
                "recipient_to": "Alice <alice@example.com>",
                "content": "<p>Hi Alice, thanks for your message!</p>",
                "datetime_utc": "2025-01-15T11:00:00",
                "internal_date": "1642251600000"
            },
            {
                "message_id": "msg_003",
                "thread_id": "thread_123", 
                "subject": "Re: Test Email Thread",
                "sender": "Alice <alice@example.com>",
                "recipient_to": "Bob <bob@example.com>",
                "content": "<div>You're welcome! Let's meet tomorrow.</div>",
                "datetime_utc": "2025-01-15T12:00:00",
                "internal_date": "1642255200000"
            }
        ]

    @pytest.fixture
    def mock_processor(self, temp_dir):
        """Create EmailThreadProcessor with mocked dependencies."""
        with patch('infrastructure.documents.processors.email_thread_processor.GmailService') as mock_service_class, \
             patch('infrastructure.documents.processors.email_thread_processor.AnalogDBManager') as mock_db_class:
            
            # Configure mocks
            mock_service = Mock()
            mock_service.gmail_api.service = Mock()
            mock_service.gmail_api.connect.return_value = {"success": True}
            mock_service.gmail_api._execute_with_timeout = Mock()
            mock_service.gmail_api.parse_message = Mock()
            mock_service_class.return_value = mock_service
            
            mock_db = Mock()
            mock_db.directories = {"email_threads": temp_dir / "email_threads"}
            mock_db.create_directory_structure.return_value = {"email_threads": True}
            mock_db_class.return_value = mock_db
            
            processor = EmailThreadProcessor(base_path=temp_dir)
            processor.gmail_service = mock_service
            processor.analog_db = mock_db
            
            return processor

    def test_initialization(self):
        """Test EmailThreadProcessor initialization."""
        if PROCESSOR_AVAILABLE:
            with patch('infrastructure.documents.processors.email_thread_processor.GmailService'), \
                 patch('infrastructure.documents.processors.email_thread_processor.AnalogDBManager'):
                processor = EmailThreadProcessor()
                assert processor.gmail_service is not None
                assert processor.analog_db is not None
                assert processor.max_emails_per_file == 100

    def test_get_processor_factory(self):
        """Test the factory function."""
        with patch('infrastructure.documents.processors.email_thread_processor.GmailService'), \
             patch('infrastructure.documents.processors.email_thread_processor.AnalogDBManager'):
            processor = get_email_thread_processor()
            if PROCESSOR_AVAILABLE:
                assert isinstance(processor, EmailThreadProcessor)
            else:
                assert processor is None

    def test_sort_chronologically(self, mock_processor, sample_messages):
        """Test chronological sorting of messages."""
        # Shuffle messages to test sorting
        unsorted_messages = [sample_messages[2], sample_messages[0], sample_messages[1]]
        
        sorted_messages = mock_processor._sort_chronologically(unsorted_messages)
        
        # Check that messages are sorted by internal_date
        assert len(sorted_messages) == 3
        assert sorted_messages[0]["message_id"] == "msg_001"
        assert sorted_messages[1]["message_id"] == "msg_002"
        assert sorted_messages[2]["message_id"] == "msg_003"

    def test_generate_thread_metadata(self, mock_processor, sample_messages):
        """Test thread metadata generation."""
        metadata = mock_processor._generate_thread_metadata(sample_messages, "thread_123")
        
        # Check required metadata fields
        assert metadata["thread_id"] == "thread_123"
        assert metadata["subject"] == "Test Email Thread"
        assert metadata["message_count"] == 3
        assert metadata["participant_count"] == 2
        assert "alice@example.com" in metadata["participants"]
        assert "bob@example.com" in metadata["participants"]
        assert metadata["document_type"] == "email_thread"
        assert "processed_at" in metadata
        assert "date_range" in metadata

    def test_extract_email_address(self, mock_processor):
        """Test email address extraction from sender fields."""
        # Test with angle brackets
        assert mock_processor._extract_email_address("Alice <alice@example.com>") == "alice@example.com"
        
        # Test without brackets
        assert mock_processor._extract_email_address("bob@example.com") == "bob@example.com"
        
        # Test empty input
        assert mock_processor._extract_email_address("") == ""
        assert mock_processor._extract_email_address(None) == ""

    def test_create_slug(self, mock_processor):
        """Test slug creation from text."""
        # Test normal text
        assert mock_processor._create_slug("Test Email Thread") == "test_email_thread"
        
        # Test with special characters
        assert mock_processor._create_slug("Re: Important Contract!") == "re_important_contract"
        
        # Test empty input
        assert mock_processor._create_slug("") == "untitled"
        
        # Test long text
        long_text = "This is a very long email subject that should be truncated"
        slug = mock_processor._create_slug(long_text)
        assert len(slug) <= 50

    def test_format_message_as_markdown(self, mock_processor):
        """Test single message markdown formatting."""
        message = {
            "sender": "Alice <alice@example.com>",
            "recipient_to": "Bob <bob@example.com>",
            "datetime_utc": "2025-01-15T10:00:00",
            "content": "<p>Hello world!</p>"
        }
        
        markdown = mock_processor._format_message_as_markdown(message, 1)
        
        # Check markdown structure
        assert "## Message 1" in markdown
        assert "**From:** Alice <alice@example.com>" in markdown
        assert "**To:** Bob <bob@example.com>" in markdown
        assert "**Date:**" in markdown
        assert "Hello world!" in markdown

    def test_generate_filename(self, mock_processor):
        """Test filename generation."""
        metadata = {
            "thread_id": "thread_123",
            "subject": "Test Email Thread",
            "date_range": {"start": "2025-01-15T10:00:00"}
        }
        
        # Test single file
        filename = mock_processor._generate_filename(metadata)
        assert "2025-01-15" in filename
        assert "test_email_thread" in filename
        assert "thread_123" in filename
        assert filename.endswith(".md")
        
        # Test multi-part file
        part_filename = mock_processor._generate_filename(metadata, 2)
        assert "part2" in part_filename

    def test_split_messages(self, mock_processor):
        """Test message splitting for large threads."""
        # Create 250 test messages
        messages = []
        for i in range(250):
            messages.append({
                "message_id": f"msg_{i:03d}",
                "internal_date": str(1642248000000 + i * 3600000)  # 1 hour apart
            })
        
        chunks = mock_processor._split_messages(messages)
        
        # Should split into 3 chunks (100, 100, 50)
        assert len(chunks) == 3
        assert len(chunks[0]) == 100
        assert len(chunks[1]) == 100
        assert len(chunks[2]) == 50

    @patch('infrastructure.documents.processors.email_thread_processor.clean_html_content')
    def test_format_thread_to_markdown_single(self, mock_clean_html, mock_processor, sample_messages):
        """Test formatting thread as markdown (single file)."""
        mock_clean_html.side_effect = lambda x: x.replace('<p>', '').replace('</p>', '').replace('<div>', '').replace('</div>', '')
        
        metadata = {
            "thread_id": "thread_123",
            "subject": "Test Email Thread",
            "message_count": 3
        }
        
        markdown = mock_processor._format_thread_to_markdown(sample_messages, metadata)
        
        # Check structure
        assert "---" in markdown  # YAML frontmatter
        assert "thread_id: thread_123" in markdown
        assert "# Test Email Thread" in markdown
        assert "## Message 1" in markdown
        assert "## Message 2" in markdown
        assert "## Message 3" in markdown

    @patch('infrastructure.documents.processors.email_thread_processor.clean_html_content')
    def test_format_thread_to_markdown_multipart(self, mock_clean_html, mock_processor, sample_messages):
        """Test formatting multi-part thread as markdown."""
        mock_clean_html.side_effect = lambda x: x.replace('<p>', '').replace('</p>', '')
        
        metadata = {
            "thread_id": "thread_123",
            "subject": "Test Email Thread"
        }
        
        markdown = mock_processor._format_thread_to_markdown(
            sample_messages, metadata, part_num=2, total_parts=3
        )
        
        # Check multi-part structure
        assert "# Email Thread (Part 2 of 3)" in markdown
        assert "← [Previous Part]" in markdown
        assert "[Next Part]" in markdown

    def test_fetch_thread_messages_success(self, mock_processor):
        """Test successful thread message fetching."""
        # Mock thread data
        mock_thread_data = {
            "messages": [
                {
                    "id": "msg_001",
                    "internalDate": "1642248000000",
                    "payload": {"headers": []}
                },
                {
                    "id": "msg_002", 
                    "internalDate": "1642251600000",
                    "payload": {"headers": []}
                }
            ]
        }
        
        # Configure mocks
        mock_processor.gmail_service.gmail_api._execute_with_timeout.return_value = mock_thread_data
        mock_processor.gmail_service.gmail_api.parse_message.side_effect = [
            {
                "message_id": "msg_001",
                "subject": "Test",
                "sender": "alice@example.com",
                "content": "Hello"
            },
            {
                "message_id": "msg_002",
                "subject": "Re: Test",
                "sender": "bob@example.com", 
                "content": "Hi back"
            }
        ]
        
        result = mock_processor._fetch_thread_messages("thread_123")
        
        assert result["success"] is True
        assert len(result["messages"]) == 2
        assert result["messages"][0]["thread_id"] == "thread_123"

    def test_fetch_thread_messages_failure(self, mock_processor):
        """Test thread message fetching failure."""
        # Mock connection failure
        mock_processor.gmail_service.gmail_api.service = None
        mock_processor.gmail_service.gmail_api.connect.return_value = {
            "success": False,
            "error": "Connection failed"
        }
        
        result = mock_processor._fetch_thread_messages("thread_123")
        
        assert result["success"] is False
        assert "Connection failed" in result["error"]

    def test_process_single_thread(self, mock_processor, sample_messages, temp_dir):
        """Test processing a single thread."""
        metadata = {
            "thread_id": "thread_123",
            "subject": "Test Thread",
            "message_count": 3
        }
        
        # Create email_threads directory
        email_threads_dir = temp_dir / "email_threads"
        email_threads_dir.mkdir(exist_ok=True)
        mock_processor.analog_db.directories["email_threads"] = email_threads_dir
        
        with patch.object(mock_processor, '_format_thread_to_markdown') as mock_format:
            mock_format.return_value = "# Test Thread\n\nContent here"
            
            result = mock_processor._process_single_thread(
                sample_messages, metadata, include_metadata=True, save_to_db=True
            )
        
        assert result["success"] is True
        assert result["message_count"] == 3
        assert result["files_created"] == 1
        assert len(result["file_paths"]) == 1

    def test_process_large_thread(self, mock_processor, temp_dir):
        """Test processing a large thread that needs splitting."""
        # Create 150 messages
        large_messages = []
        for i in range(150):
            large_messages.append({
                "message_id": f"msg_{i:03d}",
                "thread_id": "thread_large",
                "subject": "Large Thread",
                "sender": f"user{i % 2}@example.com",
                "content": f"Message {i}",
                "internal_date": str(1642248000000 + i * 3600000)
            })
        
        metadata = {
            "thread_id": "thread_large",
            "subject": "Large Thread",
            "message_count": 150
        }
        
        # Create email_threads directory
        email_threads_dir = temp_dir / "email_threads"
        email_threads_dir.mkdir(exist_ok=True)
        mock_processor.analog_db.directories["email_threads"] = email_threads_dir
        
        with patch.object(mock_processor, '_format_thread_to_markdown') as mock_format:
            mock_format.return_value = "# Large Thread Part\n\nContent here"
            
            result = mock_processor._process_large_thread(
                large_messages, metadata, include_metadata=True, save_to_db=True
            )
        
        assert result["success"] is True
        assert result["message_count"] == 150
        assert result["files_created"] == 2  # 150 messages / 100 per file = 2 files
        assert result["split_into_parts"] is True

    def test_save_to_analog_db(self, mock_processor, temp_dir):
        """Test saving markdown to analog database."""
        # Create email_threads directory
        email_threads_dir = temp_dir / "email_threads"
        email_threads_dir.mkdir(exist_ok=True)
        mock_processor.analog_db.directories["email_threads"] = email_threads_dir
        
        markdown_content = "# Test Thread\n\nThis is test content."
        filename = "test_thread.md"
        
        file_path = mock_processor._save_to_analog_db(markdown_content, filename)
        
        assert file_path is not None
        assert file_path.exists()
        assert file_path.read_text() == markdown_content

    def test_process_thread_success(self, mock_processor, sample_messages, temp_dir):
        """Test complete thread processing workflow."""
        # Setup mocks
        email_threads_dir = temp_dir / "email_threads"
        email_threads_dir.mkdir(exist_ok=True)
        mock_processor.analog_db.directories["email_threads"] = email_threads_dir
        
        with patch.object(mock_processor, '_fetch_thread_messages') as mock_fetch:
            mock_fetch.return_value = {"success": True, "messages": sample_messages}
            
            result = mock_processor.process_thread("thread_123")
        
        assert result["success"] is True
        assert result["thread_id"] == "thread_123"
        assert result["message_count"] == 3
        assert result["files_created"] == 1

    def test_process_thread_fetch_failure(self, mock_processor):
        """Test thread processing with fetch failure."""
        with patch.object(mock_processor, '_fetch_thread_messages') as mock_fetch:
            mock_fetch.return_value = {"success": False, "error": "Network error"}
            
            result = mock_processor.process_thread("thread_123")
        
        assert result["success"] is False
        assert "Network error" in result["error"]

    def test_process_threads_by_query(self, mock_processor, temp_dir):
        """Test batch processing of threads by query."""
        # Mock Gmail API response
        mock_messages = [
            {"threadId": "thread_001"},
            {"threadId": "thread_002"},
            {"threadId": "thread_001"},  # Duplicate should be handled
        ]
        
        mock_processor.gmail_service.gmail_api.get_messages.return_value = {
            "success": True,
            "data": mock_messages
        }
        
        # Mock individual thread processing
        with patch.object(mock_processor, 'process_thread') as mock_process:
            mock_process.return_value = {
                "success": True,
                "files_created": 1,
                "message_count": 5
            }
            
            result = mock_processor.process_threads_by_query("from:test@example.com", max_threads=5)
        
        assert result["success"] is True
        assert result["total_threads"] == 2  # Should deduplicate thread IDs
        assert result["success_count"] == 2
        assert result["error_count"] == 0

    def test_validate_setup(self, mock_processor, temp_dir):
        """Test setup validation."""
        # Create email_threads directory
        email_threads_dir = temp_dir / "email_threads"
        email_threads_dir.mkdir(exist_ok=True)
        mock_processor.analog_db.directories["email_threads"] = email_threads_dir
        
        result = mock_processor.validate_setup()
        
        assert "gmail_available" in result
        assert "dependencies" in result
        assert "directories" in result
        assert "ready" in result

    def test_metadata_generation_edge_cases(self, mock_processor):
        """Test metadata generation with edge cases."""
        # Empty messages
        metadata = mock_processor._generate_thread_metadata([], "thread_empty")
        assert metadata["thread_id"] == "thread_empty"
        assert "processed_at" in metadata
        # Empty messages case doesn't include message_count in minimal metadata
        
        # Messages without sender/recipient
        incomplete_messages = [
            {
                "message_id": "msg_001",
                "subject": "Test",
                "content": "Hello",
                "datetime_utc": "2025-01-15T10:00:00"
            }
        ]
        metadata = mock_processor._generate_thread_metadata(incomplete_messages, "thread_incomplete")
        assert metadata["thread_id"] == "thread_incomplete"
        assert metadata["message_count"] == 1

    def test_chronological_sorting_edge_cases(self, mock_processor):
        """Test chronological sorting with edge cases."""
        # Messages with missing internal_date
        messages_no_date = [
            {"message_id": "msg_001"},
            {"message_id": "msg_002", "internal_date": "1642248000000"},
            {"message_id": "msg_003"}
        ]
        
        sorted_messages = mock_processor._sort_chronologically(messages_no_date)
        assert len(sorted_messages) == 3
        # Should not crash, return in some order

    def test_html_cleaning_integration(self, mock_processor):
        """Test integration with HTML cleaner."""
        message = {
            "sender": "test@example.com",
            "content": "<p>Hello <strong>world</strong>!</p><script>alert('test')</script>"
        }
        
        with patch('infrastructure.documents.processors.email_thread_processor.clean_html_content') as mock_clean:
            mock_clean.return_value = "Hello world!"
            
            markdown = mock_processor._format_message_as_markdown(message, 1)
            
            mock_clean.assert_called_once()
            assert "Hello world!" in markdown
            assert "<script>" not in markdown

    def test_filename_generation_edge_cases(self, mock_processor):
        """Test filename generation edge cases."""
        # Metadata with no subject
        metadata_no_subject = {"thread_id": "thread_123"}
        filename = mock_processor._generate_filename(metadata_no_subject)
        assert "thread_123" in filename
        assert filename.endswith(".md")
        
        # Metadata with special characters in subject
        metadata_special = {
            "thread_id": "thread_456",
            "subject": "Re: Important Contract!!! @#$%"
        }
        filename = mock_processor._generate_filename(metadata_special)
        assert "re_important_contract" in filename