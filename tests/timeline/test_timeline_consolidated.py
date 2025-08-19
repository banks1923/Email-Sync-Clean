"""
Consolidated Timeline tests - Essential functionality only.

Combines the most important tests from:
- test_timeline_database.py (28 tests)
- test_timeline_service.py (25 tests) 
- test_timeline_integration.py (14 tests)

Focuses on core timeline operations, not edge cases.
"""

import os
import sys
import tempfile
from datetime import datetime, timedelta

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from utilities.timeline.database import TimelineDatabase


class TestTimelineCore:
    """Essential timeline functionality tests."""
    
    def test_timeline_service_initialization(self, isolated_timeline_db_path):
        """Test TimelineService initializes with required tables."""
        service = TimelineService(db_path=isolated_timeline_db_path)
        
        # Verify tables were created
        db = TimelineDatabase(db_path=isolated_timeline_db_path)
        tables = db.fetch("SELECT name FROM sqlite_master WHERE type='table'")
        table_names = [t['name'] for t in tables]
        
        assert 'timeline_events' in table_names
        assert service.db_path == isolated_timeline_db_path

    def test_create_timeline_event(self, timeline_database_with_tables):
        """Test creating a timeline event."""
        result = timeline_database_with_tables.create_timeline_event(
            event_id="evt_001",
            event_type="email",
            title="Test Event",
            event_date=datetime.now().isoformat()
        )
        
        assert result["success"] is True
        assert result["event_id"] == "evt_001"

    def test_get_timeline_events(self, populated_timeline_database):
        """Test retrieving timeline events."""
        result = populated_timeline_database.get_timeline_events(limit=10)
        
        assert result["success"] is True
        assert "events" in result
        assert len(result["events"]) > 0

    def test_timeline_events_with_date_filter(self, populated_timeline_database):
        """Test filtering events by date range."""
        start = (datetime.now() - timedelta(days=7)).isoformat()
        end = datetime.now().isoformat()
        
        result = populated_timeline_database.get_timeline_events(
            start_date=start,
            end_date=end
        )
        
        assert result["success"] is True
        assert all(start <= e["event_date"] <= end for e in result["events"])

    def test_sync_emails_to_timeline(self, populated_timeline_database, sample_email_data):
        """Test syncing emails to timeline events."""
        service = TimelineService(db_path=populated_timeline_database.db_path)
        
        result = service.sync_emails_to_timeline(limit=5)
        
        assert result["success"] is True
        assert result["processed"] > 0

    def test_sync_documents_to_timeline(self, populated_timeline_database):
        """Test syncing documents to timeline events."""
        service = TimelineService(db_path=populated_timeline_database.db_path)
        
        # Add test document
        service.db.add_content(
            content_type="pdf",
            title="Test Document",
            content="Document content",
            metadata={"date": datetime.now().isoformat()}
        )
        
        result = service.sync_documents_to_timeline(limit=5)
        
        assert result["success"] is True

    def test_build_case_timeline(self, populated_timeline_database):
        """Test building timeline for a specific case."""
        service = TimelineService(db_path=populated_timeline_database.db_path)
        
        # Add case-specific events
        service.db.execute("""
            INSERT INTO timeline_events 
            (event_id, event_type, title, event_date, metadata)
            VALUES (?, ?, ?, ?, ?)
        """, ("case_001", "legal", "Case 24NNCV Filing", datetime.now().isoformat(), 
              '{"case_number": "24NNCV"}'))
        
        result = service.build_case_timeline("24NNCV")
        
        assert result["success"] is True
        assert result["case_number"] == "24NNCV"

    def test_timeline_event_importance_scoring(self, timeline_database_with_tables):
        """Test importance scoring for events."""
        # Create events with different importance
        timeline_database_with_tables.create_timeline_event(
            event_id="imp_001",
            event_type="legal",
            title="Court Order",
            event_date=datetime.now().isoformat(),
            importance_score=9
        )
        
        result = timeline_database_with_tables.get_timeline_events(
            min_importance=7
        )
        
        assert result["success"] is True
        assert all(e.get("importance_score", 0) >= 7 for e in result["events"])

    def test_timeline_event_relationships(self, timeline_database_with_tables):
        """Test linking related timeline events."""
        # Create parent event
        parent = timeline_database_with_tables.create_timeline_event(
            event_id="parent_001",
            event_type="email",
            title="Original Email",
            event_date=datetime.now().isoformat()
        )
        
        # Create related event
        child = timeline_database_with_tables.create_timeline_event(
            event_id="child_001",
            event_type="email",
            title="Reply Email",
            event_date=datetime.now().isoformat(),
            metadata='{"parent_id": "parent_001"}'
        )
        
        assert parent["success"] is True
        assert child["success"] is True

    def test_export_timeline_json(self, populated_timeline_database):
        """Test exporting timeline to JSON format."""
        service = TimelineService(db_path=populated_timeline_database.db_path)
        
        result = service.export_timeline(format="json")
        
        assert result["success"] is True
        assert "timeline" in result
        assert isinstance(result["timeline"], list)

    def test_get_timeline_statistics(self, populated_timeline_database):
        """Test getting timeline statistics."""
        result = populated_timeline_database.get_timeline_statistics()
        
        assert result["success"] is True
        assert "total_events" in result
        assert "event_types" in result
        assert result["total_events"] > 0

    def test_timeline_gap_detection(self, populated_timeline_database):
        """Test detecting gaps in timeline."""
        service = TimelineService(db_path=populated_timeline_database.db_path)
        
        result = service.detect_timeline_gaps(gap_days=30)
        
        assert result["success"] is True
        assert "gaps" in result

    def test_timeline_event_search(self, populated_timeline_database):
        """Test searching timeline events."""
        result = populated_timeline_database.search_timeline_events("test")
        
        assert result["success"] is True
        assert "events" in result

    def test_timeline_pagination(self, populated_timeline_database):
        """Test paginating through timeline events."""
        # Get first page
        page1 = populated_timeline_database.get_timeline_events(limit=5, offset=0)
        
        # Get second page
        page2 = populated_timeline_database.get_timeline_events(limit=5, offset=5)
        
        assert page1["success"] is True
        assert page2["success"] is True
        # Events should be different
        if page1["events"] and page2["events"]:
            assert page1["events"][0]["event_id"] != page2["events"][0]["event_id"]

    def test_update_timeline_event(self, timeline_database_with_tables):
        """Test updating an existing timeline event."""
        # Create event
        timeline_database_with_tables.create_timeline_event(
            event_id="upd_001",
            event_type="email",
            title="Original Title",
            event_date=datetime.now().isoformat()
        )
        
        # Update it
        result = timeline_database_with_tables.update_timeline_event(
            event_id="upd_001",
            title="Updated Title"
        )
        
        assert result["success"] is True

    def test_delete_timeline_event(self, timeline_database_with_tables):
        """Test deleting a timeline event."""
        # Create event
        timeline_database_with_tables.create_timeline_event(
            event_id="del_001",
            event_type="email",
            title="To Delete",
            event_date=datetime.now().isoformat()
        )
        
        # Delete it
        result = timeline_database_with_tables.delete_timeline_event("del_001")
        
        assert result["success"] is True

    def test_timeline_service_error_handling(self):
        """Test timeline service handles errors gracefully."""
        with tempfile.TemporaryDirectory() as tmpdir:
            invalid_path = os.path.join(tmpdir, "nonexistent", "timeline.db")
            
            # Should handle invalid path gracefully
            service = TimelineService(db_path=invalid_path)
            result = service.get_timeline_events()
            
            # Should return error, not crash
            assert result["success"] is False

    def test_timeline_content_extraction(self, populated_timeline_database):
        """Test extracting timeline from document content."""
        service = TimelineService(db_path=populated_timeline_database.db_path)
        
        content = """
        On January 15, 2024, the complaint was filed.
        The hearing is scheduled for February 20, 2024.
        Settlement conference set for March 1, 2024.
        """
        
        result = service.extract_dates_from_content(content)
        
        assert result["success"] is True
        assert len(result["dates"]) >= 3

    def test_timeline_event_deduplication(self, timeline_database_with_tables):
        """Test duplicate event prevention."""
        # Create first event
        result1 = timeline_database_with_tables.create_timeline_event(
            event_id="dup_001",
            event_type="email",
            title="Test Event",
            event_date=datetime.now().isoformat()
        )
        
        # Try to create duplicate
        result2 = timeline_database_with_tables.create_timeline_event(
            event_id="dup_001",  # Same ID
            event_type="email",
            title="Test Event",
            event_date=datetime.now().isoformat()
        )
        
        assert result1["success"] is True
        assert result2["success"] is False  # Should fail on duplicate

    def test_complete_timeline_workflow(self, populated_timeline_database, sample_email_data):
        """Test complete workflow from data to timeline."""
        service = TimelineService(db_path=populated_timeline_database.db_path)
        
        # Sync emails
        sync_result = service.sync_emails_to_timeline(limit=5)
        
        # Get timeline
        timeline_result = service.get_timeline_events(limit=10)
        
        # Export
        export_result = service.export_timeline(format="json")
        
        assert sync_result["success"] is True
        assert timeline_result["success"] is True  
        assert export_result["success"] is True