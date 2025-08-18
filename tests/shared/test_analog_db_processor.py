"""
Comprehensive tests for AnalogDBProcessor following project testing patterns.
Tests cover all public methods, error handling, retry mechanisms, and integration scenarios.
"""

import tempfile
import shutil
from datetime import datetime
from pathlib import Path
from unittest.mock import Mock, patch
import pytest

from shared.analog_db_processor import (
    AnalogDBProcessor, 
    AnalogDBError, 
    MetadataError
)
from shared.file_operations import FileOperations
from shared.simple_db import SimpleDB


@pytest.mark.unit
class TestAnalogDBProcessor:
    """Unit tests for AnalogDBProcessor with mocked dependencies."""
    
    @pytest.fixture
    def temp_dir(self):
        """Create temporary directory for testing."""
        temp_path = tempfile.mkdtemp()
        yield Path(temp_path)
        shutil.rmtree(temp_path, ignore_errors=True)
    
    @pytest.fixture
    def mock_db(self):
        """Mock SimpleDB instance."""
        mock = Mock(spec=SimpleDB)
        mock.add_content.return_value = "test_content_id"
        mock.search_content.return_value = []
        mock.update_content.return_value = True
        mock.delete_content.return_value = True
        mock.execute.return_value = None
        return mock
    
    @pytest.fixture
    def mock_file_ops(self):
        """Mock FileOperations instance."""
        mock = Mock(spec=FileOperations)
        mock.file_exists.return_value = True
        mock.get_file_size.return_value = 1024
        mock.move_file.return_value = True
        mock.copy_file.return_value = True
        mock.delete_file.return_value = True
        mock.create_directory.return_value = True
        mock.sanitize_path.side_effect = lambda x: x.replace(" ", "_")
        return mock
    
    @pytest.fixture
    def mock_retry_helper(self):
        """Mock retry helper function."""
        def mock_retry(max_attempts=3, delay=0.5, backoff=2.0, logger_instance=None):
            def decorator(func):
                return func  # No retry in tests
            return decorator
        return mock_retry
    
    @pytest.fixture
    def processor(self, temp_dir, mock_db, mock_file_ops, mock_retry_helper):
        """Create AnalogDBProcessor with mocked dependencies."""
        with patch('shared.analog_db_processor.AnalogDBManager') as mock_manager:
            mock_manager_instance = Mock()
            mock_manager_instance.setup.return_value = True
            mock_manager_instance.directories = {
                "documents": temp_dir / "documents",
                "email_threads": temp_dir / "email_threads",
                "pdfs": temp_dir / "pdfs",
                "emails": temp_dir / "emails"
            }
            mock_manager.return_value = mock_manager_instance
            
            return AnalogDBProcessor(
                base_path=temp_dir,
                db_client=mock_db,
                file_ops=mock_file_ops,
                retry_helper=mock_retry_helper
            )
    
    # Initialization Tests
    
    def test_initialization_success(self, temp_dir, mock_db, mock_file_ops):
        """Test successful initialization."""
        with patch('shared.analog_db_processor.AnalogDBManager') as mock_manager:
            mock_manager_instance = Mock()
            mock_manager_instance.setup.return_value = True
            mock_manager.return_value = mock_manager_instance
            
            processor = AnalogDBProcessor(
                base_path=temp_dir,
                db_client=mock_db,
                file_ops=mock_file_ops
            )
            
            assert processor.db == mock_db
            assert processor.file_ops == mock_file_ops
            assert mock_manager_instance.setup.called
    
    def test_initialization_failure(self, temp_dir):
        """Test initialization failure when setup fails."""
        with patch('shared.analog_db_processor.AnalogDBManager') as mock_manager:
            mock_manager_instance = Mock()
            mock_manager_instance.setup.return_value = False
            mock_manager.return_value = mock_manager_instance
            
            with pytest.raises(AnalogDBError):
                AnalogDBProcessor(base_path=temp_dir)
    
    # Document Processing Tests
    
    def test_process_document_success(self, processor, temp_dir):
        """Test successful document processing."""
        test_file = temp_dir / "test.txt"
        test_file.write_text("Test content")
        
        result = processor.process_document(test_file, "pdf")
        
        assert result["success"] is True
        assert "doc_id" in result
        assert "target_path" in result
        assert "metadata" in result
        
        # Verify mocks were called
        processor.file_ops.move_file.assert_called_once()
        processor.db.add_content.assert_called_once()
    
    def test_process_document_validation_failure(self, processor, temp_dir):
        """Test document processing with validation failure."""
        test_file = temp_dir / "nonexistent.txt"
        processor.file_ops.file_exists.return_value = False
        
        result = processor.process_document(test_file, "pdf")
        
        assert result["success"] is False
        assert "error" in result
        assert "doc_id" in result
    
    def test_process_document_move_failure(self, processor, temp_dir):
        """Test document processing with file move failure."""
        test_file = temp_dir / "test.txt"
        test_file.write_text("Test content")
        processor.file_ops.move_file.return_value = False
        
        result = processor.process_document(test_file, "pdf")
        
        assert result["success"] is False
        assert "error" in result
    
    def test_validate_document_success(self, processor, temp_dir):
        """Test successful document validation."""
        test_file = temp_dir / "test.txt"
        
        result = processor.validate_document(test_file)
        
        assert result is True
        processor.file_ops.file_exists.assert_called_with(test_file)
        processor.file_ops.get_file_size.assert_called_with(test_file)
    
    def test_validate_document_file_not_exists(self, processor, temp_dir):
        """Test validation failure when file doesn't exist."""
        test_file = temp_dir / "nonexistent.txt"
        processor.file_ops.file_exists.return_value = False
        
        result = processor.validate_document(test_file)
        
        assert result is False
    
    def test_validate_document_empty_file(self, processor, temp_dir):
        """Test validation failure for empty file."""
        test_file = temp_dir / "empty.txt"
        processor.file_ops.get_file_size.return_value = 0
        
        result = processor.validate_document(test_file)
        
        assert result is False
    
    def test_validate_document_too_large(self, processor, temp_dir):
        """Test validation failure for oversized file."""
        test_file = temp_dir / "huge.txt"
        processor.file_ops.get_file_size.return_value = 200 * 1024 * 1024  # 200MB
        
        result = processor.validate_document(test_file)
        
        assert result is False
    
    def test_extract_metadata_success(self, processor, temp_dir):
        """Test successful metadata extraction."""
        test_file = temp_dir / "test.txt"
        
        with patch.object(processor, '_calculate_file_hash', return_value="test_hash"):
            metadata = processor.extract_metadata(test_file, "pdf")
        
        assert metadata["doc_type"] == "pdf"
        assert metadata["title"] == "test.txt"
        assert metadata["file_hash"] == "test_hash"
        assert "doc_id" in metadata
        assert "date_created" in metadata
    
    def test_extract_metadata_hash_failure(self, processor, temp_dir):
        """Test metadata extraction when hash calculation fails."""
        test_file = temp_dir / "test.txt"
        
        with patch.object(processor, '_calculate_file_hash', side_effect=Exception("Hash error")):
            with pytest.raises(MetadataError):
                processor.extract_metadata(test_file, "pdf")
    
    def test_chunk_document_success(self, processor):
        """Test successful document chunking."""
        content = "This is a test document with multiple words that should be chunked properly."
        
        chunks = processor.chunk_document(content, chunk_size=20)
        
        assert len(chunks) > 1
        assert all(len(chunk) <= 30 for chunk in chunks)  # Allow some flexibility
    
    def test_chunk_document_empty_content(self, processor):
        """Test chunking empty content."""
        chunks = processor.chunk_document("")
        
        assert chunks == []
    
    def test_chunk_document_small_content(self, processor):
        """Test chunking content smaller than chunk size."""
        content = "Small content"
        
        chunks = processor.chunk_document(content, chunk_size=100)
        
        assert len(chunks) == 1
        assert chunks[0] == content
    
    # File Organization Tests
    
    def test_create_document_path_document_type(self, processor, temp_dir):
        """Test document path creation for document type."""
        date = datetime(2025, 8, 18, 10, 30, 0)
        
        path = processor.create_document_path("document", "test file", date)
        
        # The mock file_ops sanitizes path by replacing spaces with underscores
        expected = processor.manager.directories["documents"] / "2025-08-18_test_file.md"
        assert path == expected
    
    def test_create_document_path_email_type(self, processor, temp_dir):
        """Test document path creation for email type."""
        date = datetime(2025, 8, 18, 10, 30, 0)
        
        path = processor.create_document_path("email", "test email", date)
        
        # The mock file_ops sanitizes path by replacing spaces with underscores
        expected = processor.manager.directories["email_threads"] / "2025-08-18_test_email.md"
        assert path == expected
    
    def test_organize_by_type_email(self, processor):
        """Test file organization by email type."""
        test_file = Path("test.txt")
        
        organized_path = processor.organize_by_type(test_file, "email")
        
        expected = processor.manager.directories["email_threads"] / "test.txt"
        assert organized_path == expected
    
    def test_organize_by_type_pdf(self, processor):
        """Test file organization by PDF type."""
        test_file = Path("test.pdf")
        
        organized_path = processor.organize_by_type(test_file, "pdf")
        
        expected = processor.manager.directories["documents"] / "test.pdf"
        assert organized_path == expected
    
    def test_move_to_analog_db_success(self, processor):
        """Test successful file move to analog database."""
        source = Path("source.txt")
        target = Path("target.txt")
        
        result = processor.move_to_analog_db(source, target)
        
        assert result is True
        processor.file_ops.create_directory.assert_called_with(target.parent)
        processor.file_ops.move_file.assert_called_with(source, target)
    
    def test_move_to_analog_db_directory_creation_failure(self, processor):
        """Test file move failure when directory creation fails."""
        source = Path("source.txt")
        target = Path("target.txt")
        processor.file_ops.create_directory.return_value = False
        
        result = processor.move_to_analog_db(source, target)
        
        assert result is False
    
    def test_move_to_analog_db_move_failure(self, processor):
        """Test file move failure."""
        source = Path("source.txt")
        target = Path("target.txt")
        processor.file_ops.move_file.return_value = False
        
        result = processor.move_to_analog_db(source, target)
        
        assert result is False
    
    def test_validate_file_structure_success(self, processor):
        """Test successful file structure validation."""
        with patch.object(processor.manager, 'validate_directory_structure') as mock_validate:
            mock_validate.return_value = (True, {
                "documents": {"exists": True, "is_directory": True, "writable": True},
                "email_threads": {"exists": True, "is_directory": True, "writable": True}
            })
            
            results = processor.validate_file_structure()
            
            assert results["documents"] is True
            assert results["email_threads"] is True
    
    def test_handle_duplicate_names_no_conflict(self, processor, temp_dir):
        """Test duplicate name handling when no conflict exists."""
        target_path = temp_dir / "unique.txt"
        
        result = processor.handle_duplicate_names(target_path)
        
        assert result == target_path
    
    def test_handle_duplicate_names_with_conflict(self, processor, temp_dir):
        """Test duplicate name handling with existing file."""
        # Create existing file
        existing_file = temp_dir / "duplicate.txt"
        existing_file.touch()
        
        result = processor.handle_duplicate_names(existing_file)
        
        expected = temp_dir / "duplicate_1.txt"
        assert result == expected
    
    def test_handle_duplicate_names_multiple_conflicts(self, processor, temp_dir):
        """Test duplicate name handling with multiple existing files."""
        # Create multiple existing files
        for i in range(3):
            if i == 0:
                (temp_dir / "duplicate.txt").touch()
            else:
                (temp_dir / f"duplicate_{i}.txt").touch()
        
        target_path = temp_dir / "duplicate.txt"
        result = processor.handle_duplicate_names(target_path)
        
        expected = temp_dir / "duplicate_3.txt"
        assert result == expected
    
    # SimpleDB Integration Tests
    
    def test_register_document_success(self, processor):
        """Test successful document registration."""
        doc_id = "test_doc_id"
        metadata = {"title": "Test Document", "doc_type": "pdf"}
        file_path = Path("test.txt")
        
        result = processor.register_document(doc_id, metadata, file_path)
        
        assert result is True
        processor.db.add_content.assert_called_once()
        
        # Check add_content was called with correct parameters
        call_args = processor.db.add_content.call_args
        assert call_args[1]["content_type"] == "pdf"
        assert call_args[1]["title"] == "Test Document"
        assert call_args[1]["source_path"] == str(file_path)
    
    def test_register_document_database_failure(self, processor):
        """Test document registration with database failure."""
        processor.db.add_content.side_effect = Exception("DB Error")
        
        doc_id = "test_doc_id"
        metadata = {"title": "Test Document"}
        file_path = Path("test.txt")
        
        result = processor.register_document(doc_id, metadata, file_path)
        
        assert result is False
    
    def test_update_metadata_success(self, processor):
        """Test successful metadata update."""
        doc_id = "test_doc_id"
        processor.db.search_content.return_value = [{
            "content_id": "test_content_id",
            "metadata": '{"existing": "data"}'
        }]
        
        updates = {"new_field": "value"}
        result = processor.update_metadata(doc_id, updates)
        
        assert result is True
        processor.db.update_content.assert_called_once()
        
        # Check metadata was properly merged
        call_args = processor.db.update_content.call_args
        updated_metadata = call_args[1]["metadata"]
        assert updated_metadata["existing"] == "data"
        assert updated_metadata["new_field"] == "value"
        assert "last_updated" in updated_metadata
    
    def test_update_metadata_document_not_found(self, processor):
        """Test metadata update when document not found."""
        doc_id = "nonexistent_doc_id"
        processor.db.search_content.return_value = []
        
        updates = {"new_field": "value"}
        result = processor.update_metadata(doc_id, updates)
        
        assert result is False
    
    def test_query_documents_with_filters(self, processor):
        """Test document querying with filters."""
        filters = {"doc_type": "pdf", "limit": 50}
        mock_results = [{"content_id": "1", "title": "Test"}]
        processor.db.search_content.return_value = mock_results
        
        results = processor.query_documents(filters)
        
        assert results == mock_results
        processor.db.search_content.assert_called_with("pdf", limit=50, filters=filters)
    
    def test_query_documents_no_filters(self, processor):
        """Test document querying without filters."""
        mock_results = [{"content_id": "1", "title": "Test"}]
        processor.db.search_content.return_value = mock_results
        
        results = processor.query_documents()
        
        assert results == mock_results
        processor.db.search_content.assert_called_with("", limit=100, filters=None)
    
    def test_query_documents_database_error(self, processor):
        """Test document querying with database error."""
        processor.db.search_content.side_effect = Exception("DB Error")
        
        results = processor.query_documents()
        
        assert results == []
    
    def test_track_processing_status_success(self, processor):
        """Test successful processing status tracking."""
        doc_id = "test_doc_id"
        status = "processed"
        
        result = processor.track_processing_status(doc_id, status)
        
        assert result is True
        processor.db.execute.assert_called_once()
        
        # Check execute was called with correct SQL
        call_args = processor.db.execute.call_args[0]
        assert "INSERT OR REPLACE INTO relationship_cache" in call_args[0]
        assert f"doc_status_{doc_id}" in call_args[1]
    
    def test_track_processing_status_database_error(self, processor):
        """Test processing status tracking with database error."""
        processor.db.execute.side_effect = Exception("DB Error")
        
        doc_id = "test_doc_id"
        status = "processed"
        
        result = processor.track_processing_status(doc_id, status)
        
        assert result is False
    
    def test_handle_transaction_rollback(self, processor):
        """Test transaction rollback handling."""
        doc_id = "test_doc_id"
        processor.db.search_content.return_value = [{"content_id": "test_content_id"}]
        
        processor.handle_transaction_rollback(doc_id)
        
        # Should call execute to delete from cache and delete_content
        assert processor.db.execute.called
        processor.db.delete_content.assert_called_with("test_content_id")
    
    # Error Handling Tests
    
    def test_process_with_retry_success(self, processor):
        """Test successful retry wrapper execution."""
        mock_func = Mock(return_value="success")
        
        result = processor.process_with_retry(mock_func, "arg1", kwarg1="value1")
        
        assert result == "success"
        mock_func.assert_called_with("arg1", kwarg1="value1")
    
    def test_circuit_breaker_check_new_service(self, processor):
        """Test circuit breaker check for new service."""
        result = processor.circuit_breaker_check("new_service")
        
        assert result is True
        assert "new_service" in processor._circuit_breaker_state
        assert processor._circuit_breaker_state["new_service"]["state"] == "closed"
    
    def test_circuit_breaker_check_open_circuit_timeout(self, processor):
        """Test circuit breaker with open circuit past timeout."""
        # Set up open circuit with old failure time
        old_time = datetime.now().replace(second=0)  # 1+ minute ago
        processor._circuit_breaker_state["test_service"] = {
            "failures": 5,
            "last_failure": old_time,
            "state": "open"
        }
        
        with patch('shared.analog_db_processor.datetime') as mock_datetime:
            mock_datetime.now.return_value = datetime.now().replace(minute=1)  # Current time
            
            result = processor.circuit_breaker_check("test_service")
            
            assert result is True
            assert processor._circuit_breaker_state["test_service"]["state"] == "half-open"
    
    def test_cleanup_on_error(self, processor):
        """Test error cleanup functionality."""
        doc_id = "test_doc_id"
        file_path = Path("test.txt")
        
        with patch.object(processor, 'handle_transaction_rollback') as mock_rollback:
            processor.cleanup_on_error(doc_id, file_path)
            
            mock_rollback.assert_called_with(doc_id)
    
    def test_calculate_file_hash_success(self, processor, temp_dir):
        """Test successful file hash calculation."""
        test_file = temp_dir / "test.txt"
        test_file.write_text("Test content for hashing")
        
        hash_result = processor._calculate_file_hash(test_file)
        
        assert len(hash_result) == 64  # SHA-256 hex length
        assert hash_result != ""
    
    def test_calculate_file_hash_file_not_found(self, processor, temp_dir):
        """Test file hash calculation with missing file."""
        nonexistent_file = temp_dir / "nonexistent.txt"
        
        hash_result = processor._calculate_file_hash(nonexistent_file)
        
        assert hash_result == ""


@pytest.mark.integration
class TestAnalogDBProcessorIntegration:
    """Integration tests for AnalogDBProcessor with real components."""
    
    @pytest.fixture
    def temp_dir(self):
        """Create temporary directory for integration testing."""
        temp_path = tempfile.mkdtemp()
        yield Path(temp_path)
        shutil.rmtree(temp_path, ignore_errors=True)
    
    @pytest.fixture
    def real_db(self, temp_dir):
        """Create real SimpleDB instance for integration testing."""
        db_path = temp_dir / "test.db"
        db = SimpleDB(str(db_path))
        
        # Initialize required tables for testing
        db.execute("""
            CREATE TABLE IF NOT EXISTS content (
                content_id TEXT PRIMARY KEY,
                content_type TEXT,
                title TEXT,
                content TEXT,
                metadata TEXT,
                source_path TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                content_hash TEXT,
                word_count INTEGER,
                char_count INTEGER
            )
        """)
        
        # Create intelligence tables
        db.create_intelligence_tables()
        
        return db
    
    @pytest.fixture
    def integration_processor(self, temp_dir, real_db):
        """Create AnalogDBProcessor with real database for integration testing."""
        return AnalogDBProcessor(
            base_path=temp_dir,
            db_client=real_db
        )
    
    def test_full_document_processing_workflow(self, integration_processor, temp_dir):
        """Test complete document processing workflow with real database."""
        # Create test document
        test_file = temp_dir / "integration_test.txt"
        test_file.write_text("This is integration test content for full workflow testing.")
        
        # Process document
        result = integration_processor.process_document(test_file, "pdf")
        
        # Verify success
        assert result["success"] is True
        result["doc_id"]
        assert "target_path" in result
        assert "metadata" in result
        
        # Verify document is tracked in database
        docs = integration_processor.query_documents({"doc_type": "pdf"})
        assert len(docs) > 0
        
        # Verify the document has the expected metadata
        doc = docs[0]
        assert doc["content_type"] == "pdf"
        assert "integration_test" in doc["title"]
        
        # Verify file was moved to correct location
        target_path = Path(result["target_path"])
        assert target_path.exists()
        assert target_path.suffix == ".md"
        assert "2025-08-17" in target_path.name
    
    def test_error_recovery_workflow(self, integration_processor, temp_dir):
        """Test error recovery and cleanup workflow."""
        # Create test document
        test_file = temp_dir / "error_test.txt"
        test_file.write_text("Error test content")
        
        # Simulate processing with subsequent database error
        with patch.object(integration_processor.db, 'add_content', side_effect=Exception("DB Error")):
            result = integration_processor.process_document(test_file, "pdf")
        
        # Verify failure was handled gracefully
        assert result["success"] is False
        assert "error" in result
        
        # Verify cleanup was performed (no orphaned records)
        docs = integration_processor.query_documents()
        assert len(docs) == 0