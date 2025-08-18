"""
Unit tests for the Analog Database Manager.
"""

import tempfile
import shutil
from pathlib import Path
import pytest
from unittest.mock import patch

from shared.analog_db import AnalogDBManager, initialize_analog_db


class TestAnalogDBManager:
    """Test suite for AnalogDBManager."""
    
    @pytest.fixture
    def temp_dir(self):
        """Create a temporary directory for testing."""
        temp_path = tempfile.mkdtemp()
        yield Path(temp_path)
        # Cleanup after test
        shutil.rmtree(temp_path, ignore_errors=True)
    
    @pytest.fixture
    def manager(self, temp_dir):
        """Create an AnalogDBManager instance with temp directory."""
        return AnalogDBManager(base_path=temp_dir)
    
    def test_initialization(self, temp_dir):
        """Test proper initialization of AnalogDBManager."""
        manager = AnalogDBManager(base_path=temp_dir)
        
        assert manager.base_path == temp_dir
        assert manager.analog_db_path == temp_dir / "analog_db"
        assert manager.data_path == temp_dir / "data"
        assert manager.originals_path == temp_dir / "data" / "originals"
        assert len(manager.directories) == 4
        assert "documents" in manager.directories
        assert "email_threads" in manager.directories
        assert "pdfs" in manager.directories
        assert "emails" in manager.directories
    
    def test_create_directory_structure_success(self, manager):
        """Test successful creation of directory structure."""
        results = manager.create_directory_structure()
        
        # All directories should be created successfully
        assert all(results.values())
        assert len(results) == 4
        
        # Verify directories actually exist
        for name, path in manager.directories.items():
            assert path.exists()
            assert path.is_dir()
    
    def test_create_directory_structure_existing(self, manager):
        """Test creation when directories already exist."""
        # Create directories first
        results1 = manager.create_directory_structure()
        assert all(results1.values())
        
        # Create again - should not fail
        results2 = manager.create_directory_structure()
        assert all(results2.values())
    
    @patch('shared.analog_db.Path.mkdir')
    def test_create_directory_structure_permission_error(self, mock_mkdir, manager):
        """Test handling of permission errors during creation."""
        mock_mkdir.side_effect = PermissionError("No permission")
        
        results = manager.create_directory_structure()
        
        # All should fail due to permission error
        assert not any(results.values())
        assert len(results) == 4
    
    def test_validate_directory_structure_valid(self, manager):
        """Test validation of valid directory structure."""
        # Create directories first
        manager.create_directory_structure()
        
        is_valid, status = manager.validate_directory_structure()
        
        assert is_valid
        for name, dir_status in status.items():
            assert dir_status["exists"]
            assert dir_status["is_directory"]
            assert dir_status["readable"]
            assert dir_status["writable"]
    
    def test_validate_directory_structure_missing(self, manager):
        """Test validation when directories are missing."""
        is_valid, status = manager.validate_directory_structure()
        
        assert not is_valid
        for name, dir_status in status.items():
            assert not dir_status["exists"]
            assert not dir_status["is_directory"]
            assert not dir_status["writable"]
    
    def test_validate_directory_structure_file_not_dir(self, manager):
        """Test validation when path exists but is a file, not directory."""
        # Create a file where directory should be
        file_path = manager.directories["documents"]
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.touch()
        
        is_valid, status = manager.validate_directory_structure()
        
        assert not is_valid
        assert status["documents"]["exists"]
        assert not status["documents"]["is_directory"]
    
    def test_get_directory_info_empty(self, manager):
        """Test getting info for empty directories."""
        manager.create_directory_structure()
        
        info = manager.get_directory_info()
        
        assert len(info) == 4
        for name, details in info.items():
            assert details["exists"]
            assert details["file_count"] == 0
            assert details["total_size"] == 0
            assert details["size_readable"] == "0.00 B"
            assert details["subdirs"] == []
    
    def test_get_directory_info_with_files(self, manager):
        """Test getting info for directories with files."""
        manager.create_directory_structure()
        
        # Add test files
        test_file1 = manager.directories["documents"] / "test1.md"
        test_file1.write_text("Test content 1")
        test_file2 = manager.directories["documents"] / "test2.md"
        test_file2.write_text("Test content 2 with more data")
        
        # Add subdirectory
        subdir = manager.directories["documents"] / "subdir"
        subdir.mkdir()
        
        info = manager.get_directory_info()
        
        doc_info = info["documents"]
        assert doc_info["file_count"] == 2
        assert doc_info["total_size"] > 0
        assert "subdir" in doc_info["subdirs"]
    
    def test_format_bytes(self, manager):
        """Test byte formatting function."""
        assert manager._format_bytes(0) == "0.00 B"
        assert manager._format_bytes(512) == "512.00 B"
        assert manager._format_bytes(1024) == "1.00 KB"
        assert manager._format_bytes(1024 * 1024) == "1.00 MB"
        assert manager._format_bytes(1024 * 1024 * 1024) == "1.00 GB"
    
    def test_setup_success(self, manager):
        """Test complete setup process."""
        result = manager.setup()
        
        assert result is True
        
        # Verify all directories exist
        for name, path in manager.directories.items():
            assert path.exists()
            assert path.is_dir()
    
    @patch('shared.analog_db.Path.mkdir')
    def test_setup_failure(self, mock_mkdir, manager):
        """Test setup process when directory creation fails."""
        mock_mkdir.side_effect = PermissionError("No permission")
        
        result = manager.setup()
        
        assert result is False
    
    def test_initialize_analog_db(self, temp_dir):
        """Test the initialize_analog_db helper function."""
        manager = initialize_analog_db(base_path=temp_dir)
        
        assert isinstance(manager, AnalogDBManager)
        assert manager.base_path == temp_dir
        
        # Verify directories were created
        for name, path in manager.directories.items():
            assert path.exists()
            assert path.is_dir()
    
    def test_idempotency(self, manager):
        """Test that operations are idempotent."""
        # Run setup multiple times
        result1 = manager.setup()
        result2 = manager.setup()
        result3 = manager.setup()
        
        assert result1 is True
        assert result2 is True
        assert result3 is True
        
        # Directory structure should remain the same
        info = manager.get_directory_info()
        assert len(info) == 4