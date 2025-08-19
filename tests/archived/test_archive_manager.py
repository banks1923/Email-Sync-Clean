"""
Tests for ArchiveManager - Simple, direct tests following CLAUDE.md principles.
"""

import json
import tempfile
import zipfile
from datetime import datetime, timedelta
from pathlib import Path

import pytest

from zarchive.archive_manager import ArchiveManager, get_archive_manager


class TestArchiveManager:
    """Test suite for ArchiveManager."""

    @pytest.fixture
    def temp_archive_dir(self):
        """Create temporary archive directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)

    @pytest.fixture
    def archive_manager(self, temp_archive_dir):
        """Create ArchiveManager with temp directory."""
        return ArchiveManager(str(temp_archive_dir))

    @pytest.fixture
    def sample_file(self):
        """Create a sample file for testing."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            f.write("This is test content for archiving.")
            temp_path = Path(f.name)
        yield temp_path
        # Cleanup
        if temp_path.exists():
            temp_path.unlink()

    def test_initialization(self, temp_archive_dir):
        """Test ArchiveManager initialization creates directories."""
        manager = ArchiveManager(str(temp_archive_dir))
        
        assert manager.archive_path.exists()
        assert manager.monthly_archives.exists()
        assert manager.yearly_archives.exists()

    def test_archive_single_file(self, archive_manager, sample_file):
        """Test archiving a single file."""
        # Archive the file
        archive_path = archive_manager.archive_file(
            sample_file,
            metadata={"test": "data"},
            case_name="TEST_CASE",
            processing_status="processed"
        )
        
        assert archive_path.exists()
        assert archive_path.suffix == ".zip"
        
        # Verify archive contents
        with zipfile.ZipFile(archive_path, 'r') as zf:
            assert sample_file.name in zf.namelist()
            assert "metadata.json" in zf.namelist()
            
            # Check metadata
            meta = json.loads(zf.read("metadata.json"))
            assert meta["case_name"] == "TEST_CASE"
            assert meta["processing_status"] == "processed"
            assert meta["custom_metadata"]["test"] == "data"

    def test_archive_batch(self, archive_manager):
        """Test batch archiving multiple files."""
        # Create multiple temp files
        temp_files = []
        for i in range(3):
            with tempfile.NamedTemporaryFile(mode='w', suffix=f'_{i}.txt', delete=False) as f:
                f.write(f"Content {i}")
                temp_files.append(Path(f.name))
        
        try:
            # Archive batch
            archive_path = archive_manager.archive_batch(
                temp_files,
                batch_name="test_batch",
                metadata={"batch_type": "test"}
            )
            
            assert archive_path.exists()
            
            # Verify contents
            with zipfile.ZipFile(archive_path, 'r') as zf:
                for temp_file in temp_files:
                    assert temp_file.name in zf.namelist()
                assert "batch_metadata.json" in zf.namelist()
                
                # Check batch metadata
                meta = json.loads(zf.read("batch_metadata.json"))
                assert meta["batch_name"] == "test_batch"
                assert meta["file_count"] == 3
        
        finally:
            # Cleanup temp files
            for f in temp_files:
                if f.exists():
                    f.unlink()

    def test_retrieve_archived(self, archive_manager, sample_file):
        """Test retrieving an archived file."""
        # First archive a file
        archive_path = archive_manager.archive_file(sample_file)
        archive_name = archive_path.name
        
        # Retrieve it
        extract_path = archive_manager.retrieve_archived(archive_name)
        
        assert extract_path.exists()
        extracted_file = extract_path / sample_file.name
        assert extracted_file.exists()
        
        # Verify content
        assert extracted_file.read_text() == sample_file.read_text()

    def test_list_archives(self, archive_manager, sample_file):
        """Test listing archives with filters."""
        # Create archives with different case names
        archive_manager.archive_file(sample_file, case_name="CASE_A")
        archive_manager.archive_file(sample_file, case_name="CASE_B")
        
        # List all archives
        all_archives = archive_manager.list_archives()
        assert len(all_archives) == 2
        
        # Filter by case name
        case_a_archives = archive_manager.list_archives(case_name="CASE_A")
        assert len(case_a_archives) == 1
        assert case_a_archives[0]["case_name"] == "CASE_A"

    def test_list_archives_date_filter(self, archive_manager, sample_file):
        """Test listing archives with date filters."""
        # Archive a file
        archive_manager.archive_file(sample_file)
        
        # List with date filters
        now = datetime.now()
        yesterday = now - timedelta(days=1)
        tomorrow = now + timedelta(days=1)
        
        # Should find archive from today
        archives = archive_manager.list_archives(since=yesterday, until=tomorrow)
        assert len(archives) == 1
        
        # Should find nothing from tomorrow
        future_archives = archive_manager.list_archives(since=tomorrow)
        assert len(future_archives) == 0

    def test_promote_to_yearly(self, archive_manager, sample_file):
        """Test promoting old monthly archives to yearly."""
        # Create an archive
        archive_path = archive_manager.archive_file(sample_file)
        
        # Initially in monthly
        assert archive_path.parent == archive_manager.monthly_archives
        
        # Promote archives older than 0 days (all archives)
        promoted = archive_manager.promote_to_yearly(older_than_days=0)
        assert promoted == 1
        
        # Check it's now in yearly
        yearly_archives = list(archive_manager.yearly_archives.glob("*.zip"))
        assert len(yearly_archives) == 1
        assert yearly_archives[0].name == archive_path.name

    def test_cleanup_old_archives(self, archive_manager, sample_file):
        """Test cleanup of old archives."""
        # Create an archive
        archive_manager.archive_file(sample_file)
        
        # Should not delete recent archives
        deleted = archive_manager.cleanup_old_archives(days_to_keep=1)
        assert deleted == 0
        
        # Should delete when days_to_keep is 0
        deleted = archive_manager.cleanup_old_archives(days_to_keep=0)
        assert deleted == 1
        
        # Verify archive is gone
        all_archives = archive_manager.list_archives()
        assert len(all_archives) == 0

    def test_get_archive_stats(self, archive_manager, sample_file):
        """Test getting archive statistics."""
        # Create archives
        archive_manager.archive_file(sample_file, case_name="TEST1")
        archive_manager.archive_file(sample_file, case_name="TEST2")
        
        # Get initial stats - both should be in monthly
        stats = archive_manager.get_archive_stats()
        assert stats["monthly"]["count"] == 2
        assert stats["yearly"]["count"] == 0
        assert stats["total"]["count"] == 2
        # Size might be very small for test files, just check it exists
        assert "size_mb" in stats["total"]
        
        # Promote all to yearly (older_than_days=0 means all)
        archive_manager.promote_to_yearly(older_than_days=0)
        
        # Get stats after promotion
        stats = archive_manager.get_archive_stats()
        assert stats["monthly"]["count"] == 0
        assert stats["yearly"]["count"] == 2
        assert stats["total"]["count"] == 2
        # Size might be very small for test files, just check it exists
        assert "size_mb" in stats["total"]

    def test_archive_nonexistent_file(self, archive_manager):
        """Test archiving a non-existent file raises error."""
        fake_path = Path("/nonexistent/file.txt")
        
        with pytest.raises(FileNotFoundError):
            archive_manager.archive_file(fake_path)

    def test_retrieve_nonexistent_archive(self, archive_manager):
        """Test retrieving non-existent archive raises error."""
        with pytest.raises(FileNotFoundError):
            archive_manager.retrieve_archived("nonexistent.zip")

    def test_empty_batch_archive(self, archive_manager):
        """Test batch archiving with empty list raises error."""
        with pytest.raises(ValueError):
            archive_manager.archive_batch([])

    def test_factory_function(self, temp_archive_dir):
        """Test the get_archive_manager factory function."""
        manager = get_archive_manager(str(temp_archive_dir))
        assert isinstance(manager, ArchiveManager)
        assert manager.archive_path == temp_archive_dir