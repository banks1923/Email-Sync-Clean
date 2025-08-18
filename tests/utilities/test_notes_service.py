"""Comprehensive tests for NotesService."""

import pytest
from unittest.mock import MagicMock, patch
from pathlib import Path
import tempfile

from utilities.notes.main import NotesService


@pytest.fixture
def temp_db():
    """Create a temporary database for testing."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
        db_path = tmp.name
    yield db_path
    Path(db_path).unlink(missing_ok=True)


@pytest.fixture
def notes_service(temp_db):
    """Create a NotesService instance with temporary database."""
    return NotesService(db_path=temp_db)


class TestNotesService:
    """Test NotesService functionality."""
    
    def test_initialization(self, temp_db):
        """Test service initialization and table creation."""
        service = NotesService(db_path=temp_db)
        assert service.db_path == temp_db
        assert service.db is not None
        
    def test_create_note_success(self, notes_service):
        """Test successful note creation."""
        result = notes_service.create_note(
            title="Test Note",
            content="Test content",
            note_type="general",
            tags=["test", "sample"],
            importance_level=3
        )
        
        assert result["success"] is True
        assert "note_id" in result
        assert result["note_id"] is not None
        
    def test_create_note_minimal(self, notes_service):
        """Test note creation with minimal parameters."""
        result = notes_service.create_note(
            title="Minimal Note",
            content="Minimal content"
        )
        
        assert result["success"] is True
        assert "note_id" in result
        
    def test_create_note_with_empty_tags(self, notes_service):
        """Test note creation with empty tags."""
        result = notes_service.create_note(
            title="Note without tags",
            content="Content",
            tags=[]
        )
        
        assert result["success"] is True
        assert "note_id" in result
        
    def test_create_note_database_error(self, notes_service):
        """Test note creation with database error."""
        with patch.object(notes_service.db, 'execute', 
                         side_effect=Exception("DB Error")):
            result = notes_service.create_note(
                title="Test",
                content="Content"
            )
            
            assert result["success"] is False
            assert "error" in result
            assert "DB Error" in result["error"]
            
    def test_create_note_exception(self, notes_service):
        """Test note creation with exception."""
        with patch.object(notes_service.db, 'execute', 
                         side_effect=Exception("Test exception")):
            result = notes_service.create_note(
                title="Test",
                content="Content"
            )
            
            assert result["success"] is False
            assert "error" in result
            assert "Test exception" in result["error"]
            
    def test_link_note_to_content_success(self, notes_service):
        """Test successful note linking."""
        # First create a note
        note_result = notes_service.create_note(
            title="Test Note",
            content="Test content"
        )
        note_id = note_result["note_id"]
        
        # Link it to content
        link_result = notes_service.link_note_to_content(
            note_id=note_id,
            linked_type="email",
            linked_id="email_123",
            description="Linked to test email"
        )
        
        assert link_result["success"] is True
        assert "link_id" in link_result
        assert link_result["link_id"] is not None
        
    def test_link_note_without_description(self, notes_service):
        """Test linking note without description."""
        note_result = notes_service.create_note(
            title="Test Note",
            content="Test content"
        )
        note_id = note_result["note_id"]
        
        link_result = notes_service.link_note_to_content(
            note_id=note_id,
            linked_type="document",
            linked_id="doc_456"
        )
        
        assert link_result["success"] is True
        assert "link_id" in link_result
        
    def test_link_note_database_error(self, notes_service):
        """Test note linking with database error."""
        with patch.object(notes_service.db, 'execute', 
                         side_effect=Exception("Link Error")):
            result = notes_service.link_note_to_content(
                note_id="test_id",
                linked_type="email",
                linked_id="email_123"
            )
            
            assert result["success"] is False
            assert "Link Error" in result["error"]
            
    def test_get_notes_for_content_success(self, notes_service):
        """Test retrieving notes for content."""
        # Create and link notes
        note1 = notes_service.create_note(
            title="Note 1",
            content="Content 1",
            tags=["tag1"],
            importance_level=5
        )
        note2 = notes_service.create_note(
            title="Note 2",
            content="Content 2",
            tags=["tag2"],
            importance_level=3
        )
        
        notes_service.link_note_to_content(
            note_id=note1["note_id"],
            linked_type="email",
            linked_id="email_test"
        )
        notes_service.link_note_to_content(
            note_id=note2["note_id"],
            linked_type="email",
            linked_id="email_test"
        )
        
        # Retrieve notes
        result = notes_service.get_notes_for_content("email", "email_test")
        
        assert result["success"] is True
        assert "notes" in result
        assert "count" in result
        assert result["count"] == 2
        assert len(result["notes"]) == 2
        
        # Check ordering by importance
        notes = result["notes"]
        assert notes[0]["importance_level"] >= notes[1]["importance_level"]
        
    def test_get_notes_for_content_empty(self, notes_service):
        """Test retrieving notes when none exist."""
        result = notes_service.get_notes_for_content("email", "nonexistent")
        
        assert result["success"] is True
        assert result["count"] == 0
        assert len(result["notes"]) == 0
        
    def test_get_notes_with_json_tags(self, notes_service):
        """Test notes with JSON tags are properly parsed."""
        # Mock database response with JSON tags
        mock_data = [{
            "note_id": "test",
            "title": "Test",
            "content": "Content",
            "tags": '["tag1", "tag2"]',
            "importance_level": 1
        }]
        
        with patch.object(notes_service.db, 'fetch', 
                         return_value=mock_data):
            result = notes_service.get_notes_for_content("email", "test")
            
            assert result["success"] is True
            assert result["notes"][0]["tags"] == ["tag1", "tag2"]
            
    def test_get_notes_with_invalid_json_tags(self, notes_service):
        """Test notes with invalid JSON tags."""
        mock_data = [{
            "note_id": "test",
            "title": "Test",
            "content": "Content",
            "tags": "invalid json",
            "importance_level": 1
        }]
        
        with patch.object(notes_service.db, 'fetch', 
                         return_value=mock_data):
            result = notes_service.get_notes_for_content("email", "test")
            
            assert result["success"] is True
            assert result["notes"][0]["tags"] == []
            
    def test_search_notes_basic(self, notes_service):
        """Test basic note searching."""
        # Create test notes
        notes_service.create_note(
            title="Python Programming",
            content="Learn Python basics",
            note_type="technical"
        )
        notes_service.create_note(
            title="Java Guide",
            content="Java programming guide",
            note_type="technical"
        )
        notes_service.create_note(
            title="Meeting Notes",
            content="Discuss Python project",
            note_type="meeting"
        )
        
        # Search for Python
        result = notes_service.search_notes("Python")
        
        assert result["success"] is True
        assert "notes" in result
        assert "count" in result
        # Should find at least the notes with "Python" in title or content
        assert result["count"] >= 2
        
    def test_search_notes_with_filters(self, notes_service):
        """Test note searching with filters."""
        # Create test notes
        notes_service.create_note(
            title="Tech Note",
            content="Technical content",
            note_type="technical",
            tags=["python", "coding"]
        )
        notes_service.create_note(
            title="Another Tech",
            content="More technical",
            note_type="technical",
            tags=["java"]
        )
        
        # Search with type filter
        result = notes_service.search_notes(
            "technical",
            note_type="technical"
        )
        
        assert result["success"] is True
        assert result["count"] >= 2
        
    def test_search_notes_with_tags(self, notes_service):
        """Test note searching with tag filters."""
        # Create notes with tags
        notes_service.create_note(
            title="Python Guide",
            content="Python programming",
            tags=["python", "programming"]
        )
        notes_service.create_note(
            title="Java Guide",
            content="Java programming",
            tags=["java", "programming"]
        )
        
        # Search with tag filter
        result = notes_service.search_notes(
            "Guide",
            tags=["python"]
        )
        
        assert result["success"] is True
        # Should find notes with "python" tag
        for note in result["notes"]:
            if note.get("tags"):
                assert any("python" in str(tag) for tag in note["tags"])
                
    def test_search_notes_with_limit(self, notes_service):
        """Test note searching with result limit."""
        # Create multiple notes
        for i in range(10):
            notes_service.create_note(
                title=f"Test Note {i}",
                content="Test content"
            )
            
        # Search with limit
        result = notes_service.search_notes("Test", limit=5)
        
        assert result["success"] is True
        assert len(result["notes"]) <= 5
        
    def test_search_notes_empty_query(self, notes_service):
        """Test searching with empty query."""
        result = notes_service.search_notes("")
        
        # Should still work but might return empty or all notes
        assert result["success"] is True
        assert "notes" in result
        assert "count" in result
        
    def test_search_notes_database_error(self, notes_service):
        """Test search with database error."""
        with patch.object(notes_service.db, 'fetch', 
                         side_effect=Exception("Search Error")):
            result = notes_service.search_notes("test")
            
            assert result["success"] is False
            assert "Search Error" in result["error"]
            
    def test_search_notes_exception(self, notes_service):
        """Test search with exception."""
        with patch.object(notes_service.db, 'fetch', 
                         side_effect=Exception("Search exception")):
            result = notes_service.search_notes("test")
            
            assert result["success"] is False
            assert "Search exception" in result["error"]
            
    @patch('utilities.notes.main.SimpleDB')
    def test_ensure_notes_tables_error(self, mock_simple_db):
        """Test table creation error handling."""
        mock_db = MagicMock()
        mock_db.execute.side_effect = Exception("Table creation failed")
        mock_simple_db.return_value = mock_db
        
        # Should log error but not raise
        service = NotesService()
        assert service is not None  # Service still created despite error


@pytest.mark.integration
class TestNotesServiceIntegration:
    """Integration tests for NotesService."""
    
    def test_full_workflow(self, notes_service):
        """Test complete note workflow."""
        # Create note
        note_result = notes_service.create_note(
            title="Project Documentation",
            content="Important project details",
            note_type="documentation",
            tags=["project", "important"],
            importance_level=5
        )
        assert note_result["success"] is True
        note_id = note_result["note_id"]
        
        # Link to email
        link_result = notes_service.link_note_to_content(
            note_id=note_id,
            linked_type="email",
            linked_id="email_proj_123",
            description="Related to project email"
        )
        assert link_result["success"] is True
        
        # Link to document
        link_result2 = notes_service.link_note_to_content(
            note_id=note_id,
            linked_type="document",
            linked_id="doc_proj_456"
        )
        assert link_result2["success"] is True
        
        # Retrieve notes for email
        email_notes = notes_service.get_notes_for_content("email", "email_proj_123")
        assert email_notes["success"] is True
        assert email_notes["count"] == 1
        assert email_notes["notes"][0]["title"] == "Project Documentation"
        
        # Search for notes
        search_result = notes_service.search_notes("project")
        assert search_result["success"] is True
        assert search_result["count"] >= 1
        
        # Search with filters
        filtered_result = notes_service.search_notes(
            "Important",
            note_type="documentation",
            tags=["project"]
        )
        assert filtered_result["success"] is True
        assert filtered_result["count"] >= 1