"""
Core Gmail service tests - Essential functionality only.

Focuses on:
- Service initialization
- Batch sync (primary use case)
- Incremental sync
- Error handling
- End-to-end functionality

Removed: Mock-heavy tests, edge cases, property tests
"""

from unittest.mock import Mock, patch

from gmail.main import GmailService


class TestGmailServiceCore:
    """Essential Gmail service tests."""
    
    def test_service_initialization(self, simple_db):
        """Test Gmail service initializes with all required components."""
        service = GmailService(db_path=simple_db.db_path)
        
        assert service.gmail_api is not None
        assert service.storage is not None
        assert service.config is not None
        assert service.db is not None
        assert service.summarizer is not None

    @patch('gmail.main.GmailService._sync_emails_batch')
    def test_sync_emails_batch_mode(self, mock_batch, gmail_service_with_mocks):
        """Test batch sync for production use (50+ emails)."""
        service, mocks = gmail_service_with_mocks
        
        mock_messages = [{"id": f"msg_{i}"} for i in range(50)]
        mocks['gmail_api'].get_messages.return_value = {
            "success": True,
            "data": mock_messages
        }
        mock_batch.return_value = {"success": True, "processed": 50}
        
        result = service.sync_emails(max_results=500, batch_mode=True)
        
        mock_batch.assert_called_once_with(mock_messages)
        assert result["success"] is True

    def test_sync_emails_with_config(self, gmail_service_with_mocks):
        """Test sync using config-based sender filters."""
        service, mocks = gmail_service_with_mocks
        
        mocks['config'].get_query.return_value = "from:important@example.com"
        mocks['config'].get_max_results.return_value = 100
        mocks['gmail_api'].get_messages.return_value = {
            "success": True,
            "data": []
        }
        
        result = service.sync_emails(use_config=True)
        
        mocks['gmail_api'].get_messages.assert_called_with(
            query="from:important@example.com",
            max_results=100
        )
        assert result["success"] is True

    def test_sync_emails_api_failure(self, gmail_service_with_mocks):
        """Test graceful handling of API failures."""
        service, mocks = gmail_service_with_mocks
        
        mocks['gmail_api'].get_messages.return_value = {
            "success": False,
            "error": "API quota exceeded"
        }
        
        result = service.sync_emails(max_results=10)
        
        assert result["success"] is False
        assert "API quota exceeded" in result["error"]

    def test_sync_incremental_with_history(self, gmail_service_with_mocks):
        """Test incremental sync using Gmail History API."""
        service, mocks = gmail_service_with_mocks
        
        mocks['storage'].get_last_history_id.return_value = "12345"
        mocks['gmail_api'].get_history.return_value = {
            "success": True,
            "history": [{"messages": [{"id": "msg1"}, {"id": "msg2"}]}],
            "history_id": "12346"
        }
        mocks['gmail_api'].extract_message_ids_from_history.return_value = ["msg1", "msg2"]
        
        result = service.sync_incremental(max_results=100)
        
        assert result["success"] is True
        assert result["processed"] == 2

    def test_sync_incremental_fallback_to_full(self, gmail_service_with_mocks):
        """Test fallback to full sync when no history available."""
        service, mocks = gmail_service_with_mocks
        
        mocks['storage'].get_last_history_id.return_value = None
        mocks['gmail_api'].get_messages.return_value = {
            "success": True,
            "data": [{"id": "msg1"}]
        }
        
        result = service.sync_incremental(max_results=10)
        
        # Should fall back to full sync
        mocks['gmail_api'].get_messages.assert_called_once()
        assert result["success"] is True

    def test_sync_emails_batch_chunking(self, gmail_service_with_mocks):
        """Test batch sync processes in 50-email chunks."""
        service, mocks = gmail_service_with_mocks
        
        # Create 120 messages
        messages = [{"id": f"msg_{i}"} for i in range(120)]
        
        # Mock fetch to return data for each message
        def mock_fetch(msg_ids):
            return {
                "success": True,
                "messages": [{"id": mid, "content": f"content_{mid}"} for mid in msg_ids]
            }
        
        mocks['gmail_api'].fetch_messages_batch.side_effect = mock_fetch
        mocks['storage'].save_emails_batch.return_value = {"success": True, "saved": 50}
        
        result = service._sync_emails_batch(messages)
        
        # Should be called 3 times (50, 50, 20)
        assert mocks['gmail_api'].fetch_messages_batch.call_count == 3
        assert result["processed"] == 120

    def test_fetch_and_save_messages(self, gmail_service_with_mocks):
        """Test fetching and saving messages with deduplication."""
        service, mocks = gmail_service_with_mocks
        
        messages = [{"id": "msg1"}, {"id": "msg2"}]
        mocks['gmail_api'].fetch_messages_batch.return_value = {
            "success": True,
            "messages": [
                {"id": "msg1", "content": "test1"},
                {"id": "msg2", "content": "test2"}
            ]
        }
        mocks['storage'].save_emails_batch.return_value = {
            "success": True,
            "saved": 1,
            "duplicates": 1
        }
        
        result = service._fetch_and_save_messages(messages)
        
        assert result["fetched"] == 2
        assert result["saved"] == 1
        assert result["duplicates"] == 1

    def test_process_email_summaries(self, gmail_service_with_mocks):
        """Test email summarization for long content."""
        service, mocks = gmail_service_with_mocks
        
        # Mock emails with long content
        emails = [
            {"id": 1, "content": "x" * 100},  # Long enough to summarize
            {"id": 2, "content": "short"}      # Too short
        ]
        
        # Only first email should be summarized
        service._process_email_summaries(emails)
        
        assert mocks['summarizer'].extract_summary.call_count == 1
        assert mocks['db'].add_content.call_count == 1

    def test_get_emails_basic(self, gmail_service_with_mocks):
        """Test retrieving emails from storage."""
        service, mocks = gmail_service_with_mocks
        
        mocks['storage'].get_all_emails.return_value = {
            "success": True,
            "emails": [{"id": 1}, {"id": 2}],
            "count": 2
        }
        
        result = service.get_emails()
        
        assert result["success"] is True
        assert result["count"] == 2

    def test_get_emails_storage_failure(self, gmail_service_with_mocks):
        """Test handling storage failures gracefully."""
        service, mocks = gmail_service_with_mocks
        
        mocks['storage'].get_all_emails.return_value = {
            "success": False,
            "error": "Database locked"
        }
        
        result = service.get_emails()
        
        assert result["success"] is False
        assert "Database locked" in result["error"]

    def test_sync_emails_empty_messages(self, gmail_service_with_mocks):
        """Test handling empty message list."""
        service, mocks = gmail_service_with_mocks
        
        mocks['gmail_api'].get_messages.return_value = {
            "success": True,
            "data": []
        }
        
        result = service.sync_emails(max_results=10)
        
        assert result["success"] is True
        assert result["processed"] == 0
        assert result["message"] == "No messages to sync"

    def test_gmail_service_with_real_db(self, simple_db):
        """Test Gmail service with real database operations."""
        GmailService(db_path=simple_db.db_path)
        
        # Verify database tables exist
        tables = simple_db.fetch("SELECT name FROM sqlite_master WHERE type='table'")
        table_names = [t['name'] for t in tables]
        
        assert 'content' in table_names
        assert 'summaries' in table_names

    def test_config_integration(self, simple_db):
        """Test config loading and usage."""
        with patch('gmail.config.GmailConfig') as mock_config_class:
            mock_config = Mock()
            mock_config.preferred_senders = ["test@example.com"]
            mock_config.get_query.return_value = "from:test@example.com"
            mock_config.get_max_results.return_value = 50
            mock_config_class.return_value = mock_config
            
            service = GmailService(db_path=simple_db.db_path)
            
            assert service.config.preferred_senders == ["test@example.com"]

    def test_end_to_end_sync_flow(self, gmail_service_with_mocks):
        """Test complete sync flow from API to storage."""
        service, mocks = gmail_service_with_mocks
        
        # Setup complete flow
        mocks['gmail_api'].get_messages.return_value = {
            "success": True,
            "data": [{"id": "msg1"}]
        }
        mocks['gmail_api'].fetch_messages_batch.return_value = {
            "success": True,
            "messages": [{"id": "msg1", "content": "Test email content"}]
        }
        mocks['storage'].save_emails_batch.return_value = {
            "success": True,
            "saved": 1
        }
        
        result = service.sync_emails(max_results=10, batch_mode=True)
        
        assert result["success"] is True
        assert result["processed"] == 1
        assert result["saved"] == 1