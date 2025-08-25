"""Test fixtures for Timeline service tests.

Following TESTING_PROTOCOLS.md: Isolated databases, real data, minimal
mocking.
"""

import json
import os
import sqlite3
import tempfile
import uuid
from collections.abc import Generator
from datetime import datetime, timedelta

import pytest


@pytest.fixture(scope="function")
def isolated_timeline_db_path() -> Generator[str, None, None]:
    """Completely isolated test database per test function.

    Following TESTING_PROTOCOLS.md standards.
    """
    # Create unique database file for each test
    test_db_name = f"test_timeline_{uuid.uuid4().hex[:8]}.db"
    test_db_path = os.path.join(tempfile.gettempdir(), test_db_name)

    yield test_db_path

    # Cleanup after test
    if os.path.exists(test_db_path):
        os.remove(test_db_path)

    # Clean up any WAL files
    for suffix in ["-wal", "-shm"]:
        wal_file = test_db_path + suffix
        if os.path.exists(wal_file):
            os.remove(wal_file)


@pytest.fixture(scope="function")
def timeline_database_with_tables(isolated_timeline_db_path) -> str:
    """Create isolated database with timeline tables schema.

    Following timeline service database schema.
    """
    conn = sqlite3.connect(isolated_timeline_db_path)
    cursor = conn.cursor()

    # Create timeline_events table
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS timeline_events (
            event_id TEXT PRIMARY KEY,
            event_type TEXT NOT NULL,
            content_id TEXT,
            title TEXT NOT NULL,
            description TEXT,
            event_date TEXT NOT NULL,
            created_date TEXT DEFAULT CURRENT_TIMESTAMP,
            metadata TEXT,
            source_type TEXT,
            importance_score INTEGER DEFAULT 0
        )
    """
    )

    # Create timeline_relationships table
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS timeline_relationships (
            relationship_id TEXT PRIMARY KEY,
            parent_event_id TEXT NOT NULL,
            child_event_id TEXT NOT NULL,
            relationship_type TEXT DEFAULT 'related',
            created_date TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (parent_event_id) REFERENCES timeline_events(event_id),
            FOREIGN KEY (child_event_id) REFERENCES timeline_events(event_id)
        )
    """
    )

    # Create indexes
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_timeline_date ON timeline_events(event_date)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_timeline_type ON timeline_events(event_type)")
    cursor.execute(
        "CREATE INDEX IF NOT EXISTS idx_timeline_importance ON timeline_events(importance_score)"
    )
    cursor.execute(
        "CREATE INDEX IF NOT EXISTS idx_relationships_parent ON timeline_relationships(parent_event_id)"
    )

    conn.commit()
    conn.close()

    return isolated_timeline_db_path


@pytest.fixture(scope="function")
def database_with_emails_and_documents(timeline_database_with_tables) -> str:
    """Create test database with emails and documents tables for sync testing.

    Real document content patterns following TESTING_PROTOCOLS.md.
    """
    conn = sqlite3.connect(timeline_database_with_tables)
    cursor = conn.cursor()

    # Create emails table
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS emails (
            message_id TEXT PRIMARY KEY,
            subject TEXT,
            sender TEXT,
            recipient TEXT,
            datetime_utc TEXT,
            body_text TEXT,
            labels TEXT,
            thread_id TEXT,
            has_attachments BOOLEAN DEFAULT 0
        )
    """
    )

    # Create documents table
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS documents (
            chunk_id TEXT PRIMARY KEY,
            file_path TEXT NOT NULL,
            file_name TEXT NOT NULL,
            chunk_index INTEGER NOT NULL,
            text_content TEXT NOT NULL,
            char_count INTEGER NOT NULL,
            file_size INTEGER,
            file_hash TEXT,
            source_type TEXT DEFAULT 'upload',
            modified_time REAL,
            processed_time TEXT DEFAULT CURRENT_TIMESTAMP,
            content_type TEXT DEFAULT 'document',
            vector_processed BOOLEAN DEFAULT 0
        )
    """
    )

    conn.commit()
    conn.close()

    return timeline_database_with_tables


@pytest.fixture(scope="function")
def sample_email_data() -> list[dict]:
    """Sample email data for testing timeline sync.

    Real email content patterns following TESTING_PROTOCOLS.md.
    """
    base_time = datetime.now()
    return [
        {
            "message_id": "msg_001@example.com",
            "subject": "Water damage in apartment",
            "sender": "tenant@example.com",
            "recipient": "landlord@example.com",
            "datetime_utc": (base_time - timedelta(days=5)).isoformat(),
            "body_text": "There is significant water damage in the bathroom ceiling.",
            "labels": "INBOX",
            "thread_id": "thread_001",
            "has_attachments": 0,
        },
        {
            "message_id": "msg_002@example.com",
            "subject": "Re: Water damage in apartment",
            "sender": "landlord@example.com",
            "recipient": "tenant@example.com",
            "datetime_utc": (base_time - timedelta(days=4)).isoformat(),
            "body_text": "I will send a plumber tomorrow morning.",
            "labels": "SENT",
            "thread_id": "thread_001",
            "has_attachments": 0,
        },
        {
            "message_id": "msg_003@example.com",
            "subject": "Legal notice - Rent increase",
            "sender": "property_manager@example.com",
            "recipient": "tenant@example.com",
            "datetime_utc": (base_time - timedelta(days=2)).isoformat(),
            "body_text": "Notice of rent increase effective next month.",
            "labels": "INBOX,IMPORTANT",
            "thread_id": "thread_002",
            "has_attachments": 1,
        },
        {
            "message_id": "msg_004@example.com",
            "subject": "Maintenance request - Broken heater",
            "sender": "tenant@example.com",
            "recipient": "maintenance@example.com",
            "datetime_utc": (base_time - timedelta(days=1)).isoformat(),
            "body_text": "The heater in the living room is not working.",
            "labels": "SENT",
            "thread_id": "thread_003",
            "has_attachments": 0,
        },
        {
            "message_id": "msg_005@example.com",
            "subject": "",  # Test empty subject
            "sender": "automated@example.com",
            "recipient": "tenant@example.com",
            "datetime_utc": base_time.isoformat(),
            "body_text": "Automated system notification.",
            "labels": "INBOX",
            "thread_id": "thread_004",
            "has_attachments": 0,
        },
    ]


@pytest.fixture(scope="function")
def sample_document_data() -> list[dict]:
    """Sample document data for testing timeline sync.

    Real document content patterns following TESTING_PROTOCOLS.md.
    """
    base_time = datetime.now()
    return [
        {
            "chunk_id": "doc_001_chunk_0",
            "file_path": "/tmp/lease_agreement.pdf",
            "file_name": "lease_agreement.pdf",
            "chunk_index": 0,
            "text_content": "RESIDENTIAL LEASE AGREEMENT\n\nTenant: John Smith\nLandlord: Property Management LLC\nProperty: 123 Main Street, Apt 2B\nRent: $1,200/month\nLease Term: 12 months starting January 1, 2024",
            "char_count": 158,
            "file_size": 245760,
            "file_hash": "abc123def456",
            "source_type": "upload",
            "processed_time": (base_time - timedelta(days=3)).isoformat(),
            "content_type": "document",
            "vector_processed": 0,
        },
        {
            "chunk_id": "doc_002_chunk_0",
            "file_path": "/tmp/inspection_report.pdf",
            "file_name": "inspection_report.pdf",
            "chunk_index": 0,
            "text_content": "PROPERTY INSPECTION REPORT\n\nInspection Date: March 15, 2024\nProperty: 123 Main Street, Apt 2B\nInspector: Mike Johnson\n\nFindings:\n- Water stains on bathroom ceiling\n- Loose tile in kitchen\n- Working smoke detectors",
            "char_count": 198,
            "file_size": 89456,
            "file_hash": "def456ghi789",
            "source_type": "upload",
            "processed_time": (base_time - timedelta(days=1)).isoformat(),
            "content_type": "document",
            "vector_processed": 1,
        },
        {
            "chunk_id": "doc_003_chunk_0",
            "file_path": "/tmp/legal_notice.pdf",
            "file_name": "legal_notice.pdf",
            "chunk_index": 0,
            "text_content": "NOTICE TO QUIT\n\nTo: John Smith\nProperty: 123 Main Street, Apt 2B\n\nYou are hereby notified that your tenancy is terminated. You must quit and surrender the premises within 30 days.",
            "char_count": 162,
            "file_size": 34567,
            "file_hash": "ghi789jkl012",
            "source_type": "upload",
            "processed_time": base_time.isoformat(),
            "content_type": "document",
            "vector_processed": 0,
        },
    ]


@pytest.fixture(scope="function")
def populated_timeline_database(
    database_with_emails_and_documents, sample_email_data, sample_document_data
) -> str:
    """Test database pre-populated with emails and documents for timeline
    testing.

    Provides realistic test data for validating timeline operations
    without mocks.
    """
    conn = sqlite3.connect(database_with_emails_and_documents)
    cursor = conn.cursor()

    # Insert sample emails
    for email in sample_email_data:
        cursor.execute(
            """
            INSERT INTO emails (message_id, subject, sender, recipient, datetime_utc,
                              body_text, labels, thread_id, has_attachments)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
            (
                email["message_id"],
                email["subject"],
                email["sender"],
                email["recipient"],
                email["datetime_utc"],
                email["body_text"],
                email["labels"],
                email["thread_id"],
                email["has_attachments"],
            ),
        )

    # Insert sample documents
    for doc in sample_document_data:
        cursor.execute(
            """
            INSERT INTO documents (chunk_id, file_path, file_name, chunk_index,
                                 text_content, char_count, file_size, file_hash,
                                 source_type, processed_time, content_type, vector_processed)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
            (
                doc["chunk_id"],
                doc["file_path"],
                doc["file_name"],
                doc["chunk_index"],
                doc["text_content"],
                doc["char_count"],
                doc["file_size"],
                doc["file_hash"],
                doc["source_type"],
                doc["processed_time"],
                doc["content_type"],
                doc["vector_processed"],
            ),
        )

    conn.commit()
    conn.close()

    return database_with_emails_and_documents


@pytest.fixture(scope="function")
def sample_timeline_events() -> list[dict]:
    """Sample timeline events for testing timeline database operations.

    Real timeline data patterns following TESTING_PROTOCOLS.md.
    """
    base_time = datetime.now()
    return [
        {
            "event_id": "timeline_001",
            "event_type": "email",
            "content_id": "msg_001@example.com",
            "title": "Water damage reported",
            "description": "Tenant reported water damage in apartment",
            "event_date": (base_time - timedelta(days=5)).isoformat(),
            "metadata": json.dumps({"sender": "tenant@example.com", "thread_id": "thread_001"}),
            "source_type": "gmail",
            "importance_score": 3,
        },
        {
            "event_id": "timeline_002",
            "event_type": "document",
            "content_id": "doc_001_chunk_0",
            "title": "Lease agreement uploaded",
            "description": "Original lease agreement document processed",
            "event_date": (base_time - timedelta(days=3)).isoformat(),
            "metadata": json.dumps({"file_name": "lease_agreement.pdf", "char_count": 158}),
            "source_type": "upload",
            "importance_score": 5,
        },
        {
            "event_id": "timeline_003",
            "event_type": "email",
            "content_id": "msg_003@example.com",
            "title": "Legal notice received",
            "description": "Rent increase notice from property manager",
            "event_date": (base_time - timedelta(days=2)).isoformat(),
            "metadata": json.dumps(
                {"sender": "property_manager@example.com", "has_attachments": True}
            ),
            "source_type": "gmail",
            "importance_score": 4,
        },
        {
            "event_id": "timeline_004",
            "event_type": "document",
            "content_id": "doc_002_chunk_0",
            "title": "Inspection report uploaded",
            "description": "Property inspection findings documented",
            "event_date": (base_time - timedelta(days=1)).isoformat(),
            "metadata": json.dumps(
                {"file_name": "inspection_report.pdf", "vector_processed": True}
            ),
            "source_type": "upload",
            "importance_score": 4,
        },
        {
            "event_id": "timeline_005",
            "event_type": "note",
            "content_id": "note_001",
            "title": "Meeting with landlord scheduled",
            "description": "Discuss repairs and maintenance issues",
            "event_date": base_time.isoformat(),
            "metadata": json.dumps({"location": "property office", "duration": "30 minutes"}),
            "source_type": "manual",
            "importance_score": 2,
        },
    ]


@pytest.fixture(scope="function")
def timeline_error_scenarios(isolated_timeline_db_path):
    """Timeline error scenario testing fixtures.

    Tests real database constraint violations and error conditions.
    """
    import sqlite3

    def create_invalid_timeline_data():
        """
        Create scenario to test timeline error handling.
        """
        conn = sqlite3.connect(isolated_timeline_db_path)
        cursor = conn.cursor()

        # Create timeline tables first
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS timeline_events (
                event_id TEXT PRIMARY KEY,
                event_type TEXT NOT NULL,
                content_id TEXT,
                title TEXT NOT NULL,
                description TEXT,
                event_date TEXT NOT NULL,
                created_date TEXT DEFAULT CURRENT_TIMESTAMP,
                metadata TEXT,
                source_type TEXT,
                importance_score INTEGER DEFAULT 0
            )
        """
        )

        # Insert event with potential duplicate ID for constraint testing
        cursor.execute(
            """
            INSERT INTO timeline_events (event_id, event_type, title, event_date)
            VALUES (?, ?, ?, ?)
        """,
            ("test_event_1", "email", "Test Event", datetime.now().isoformat()),
        )

        conn.commit()
        conn.close()

    return {
        "db_path": isolated_timeline_db_path,
        "create_invalid_data": create_invalid_timeline_data,
    }


@pytest.fixture(scope="function")
def date_filtering_test_data() -> dict:
    """Test data for date filtering scenarios.

    Provides events across different time periods for filtering tests.
    """
    base_time = datetime.now()

    return {
        "start_date": (base_time - timedelta(days=7)).isoformat(),
        "end_date": base_time.isoformat(),
        "events_in_range": [
            {
                "event_date": (base_time - timedelta(days=5)).isoformat(),
                "title": "Event within range 1",
            },
            {
                "event_date": (base_time - timedelta(days=3)).isoformat(),
                "title": "Event within range 2",
            },
        ],
        "events_outside_range": [
            {
                "event_date": (base_time - timedelta(days=10)).isoformat(),
                "title": "Event before range",
            },
            {
                "event_date": (base_time + timedelta(days=1)).isoformat(),
                "title": "Event after range",
            },
        ],
    }
