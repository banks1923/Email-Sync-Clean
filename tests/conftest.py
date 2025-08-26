"""Centralized test configuration and fixtures for Email Sync testing strategy.

This follows the 6-phase testing plan with:
1. Baseline coverage targets
2. CoverUp integration
3. Property-based testing (Hypothesis)
4. External I/O isolation (VCR.py)
5. Mutation testing support
6. Speed and stability optimizations
"""

import os
import sqlite3
import tempfile
from collections.abc import Generator
from pathlib import Path
from typing import Any
from unittest.mock import Mock

import pytest

# Core testing dependencies
from hypothesis import Verbosity, settings

# Project imports
from shared.simple_db import SimpleDB

# =============================================================================
# Test Environment Configuration
# =============================================================================


def pytest_configure(config):
    """
    Configure pytest for comprehensive testing strategy.
    """
    # Set test environment variables
    os.environ["TESTING"] = "true"
    os.environ["LOG_LEVEL"] = "WARNING"  # Reduce log noise in tests
    os.environ["DEBUG"] = "false"

    # Hypothesis settings for property-based testing
    settings.register_profile("default", max_examples=100, verbosity=Verbosity.normal)
    settings.register_profile("ci", max_examples=1000, verbosity=Verbosity.verbose)
    settings.register_profile("dev", max_examples=10, verbosity=Verbosity.normal)

    # Use appropriate profile based on environment
    if os.getenv("CI"):
        settings.load_profile("ci")
    elif os.getenv("PYTEST_QUICK"):
        settings.load_profile("dev")
    else:
        settings.load_profile("default")


def pytest_collection_modifyitems(config, items):
    """
    Auto-mark tests based on naming patterns and imports.
    """
    for item in items:
        # Mark CoverUp generated tests
        if "coverup" in item.nodeid:
            item.add_marker(pytest.mark.coverup_generated)

        # Mark slow tests automatically
        if "test_large" in item.name or "test_performance" in item.name:
            item.add_marker(pytest.mark.slow)

        # Mark property-based tests
        if hasattr(item, "function") and hasattr(item.function, "__code__"):
            source = item.function.__code__.co_filename
            with open(source, encoding="utf-8") as f:
                content = f.read()
                if "from hypothesis" in content or "@given" in content:
                    item.add_marker(pytest.mark.property)


# =============================================================================
# Database Fixtures (Phase 1: Baseline & Targets)
# =============================================================================


@pytest.fixture
def temp_db() -> Generator[str, None, None]:
    """
    Create isolated temporary database for testing.
    """
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp_file:
        db_path = tmp_file.name

    try:
        yield db_path
    finally:
        if os.path.exists(db_path):
            os.unlink(db_path)


@pytest.fixture
def simple_db(temp_db: str) -> SimpleDB:
    """
    Create SimpleDB instance with temporary database and proper schema.
    """
    db = SimpleDB(db_path=temp_db)

    # Create the content table that SimpleDB expects but doesn't create
    db.execute(
        """
        CREATE TABLE IF NOT EXISTS content (
            id TEXT PRIMARY KEY,
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
    """
    )

    # Create intelligence tables
    db.create_intelligence_tables()

    return db


@pytest.fixture
def populated_db(simple_db: SimpleDB) -> SimpleDB:
    """
    SimpleDB with sample test data for integration tests.
    """
    # Add sample content
    simple_db.add_content(
        content_type="email",
        title="Test Email 1",
        content="This is a test email about legal contracts.",
        metadata={"sender": "test@example.com", "tags": ["legal", "contract"]},
    )

    simple_db.add_content(
        content_type="pdf",
        title="Test Document",
        content="This is a test PDF document containing important information.",
        metadata={"file_path": "/tmp/test.pdf", "tags": ["document"]},
    )

    return simple_db


# =============================================================================
# HTTP/API Fixtures (Phase 4: External I/O Isolation)
# =============================================================================


@pytest.fixture(scope="session")
def vcr_config() -> dict[str, Any]:
    """
    VCR configuration for HTTP recording/replay.
    """
    return {
        "cassette_library_dir": "tests/cassettes",
        "record_mode": "once",  # Record once, then replay
        "match_on": ["method", "scheme", "host", "port", "path", "query"],
        "filter_headers": ["authorization", "x-api-key", "cookie", "set-cookie"],
        "filter_query_parameters": ["key", "token", "access_token"],
        "decode_compressed_response": True,
    }


@pytest.fixture
def gmail_api_mock():
    """
    Mock Gmail API for testing without external dependencies.
    """
    mock_service = Mock()
    mock_service.users.return_value.messages.return_value.list.return_value.execute.return_value = {
        "messages": [
            {"id": "test_message_1", "threadId": "test_thread_1"},
            {"id": "test_message_2", "threadId": "test_thread_2"},
        ],
        "nextPageToken": None,
    }

    mock_service.users.return_value.messages.return_value.get.return_value.execute.return_value = {
        "id": "test_message_1",
        "payload": {
            "headers": [
                {"name": "Subject", "value": "Test Subject"},
                {"name": "From", "value": "test@example.com"},
                {"name": "Date", "value": "Mon, 1 Jan 2024 12:00:00 +0000"},
            ],
            "body": {"data": "VGVzdCBlbWFpbCBjb250ZW50"},  # Base64: "Test email content"
        },
    }

    return mock_service


# =============================================================================
# File System Fixtures (Phase 4: I/O Isolation)
# =============================================================================


@pytest.fixture
def temp_dir() -> Generator[Path, None, None]:
    """
    Create temporary directory for file-based tests.
    """
    with tempfile.TemporaryDirectory() as tmp_dir:
        yield Path(tmp_dir)


@pytest.fixture
def sample_pdf_files(temp_dir: Path) -> dict[str, Path]:
    """
    Create sample PDF files for testing.
    """
    files = {}

    # Simple text PDF (mock content)
    simple_pdf = temp_dir / "simple.pdf"
    simple_pdf.write_bytes(b"%PDF-1.4\n1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n")
    files["simple"] = simple_pdf

    # Empty file
    empty_pdf = temp_dir / "empty.pdf"
    empty_pdf.write_bytes(b"")
    files["empty"] = empty_pdf

    # Corrupted PDF
    corrupted_pdf = temp_dir / "corrupted.pdf"
    corrupted_pdf.write_bytes(b"This is not a PDF file at all!")
    files["corrupted"] = corrupted_pdf

    return files


@pytest.fixture
def sample_text_files(temp_dir: Path) -> dict[str, Path]:
    """
    Create sample text files for document processing tests.
    """
    files = {}

    # UTF-8 text file
    utf8_file = temp_dir / "utf8.txt"
    utf8_file.write_text("This is a UTF-8 text file with émojis 🚀", encoding="utf-8")
    files["utf8"] = utf8_file

    # ASCII text file
    ascii_file = temp_dir / "ascii.txt"
    ascii_file.write_text("This is plain ASCII text", encoding="ascii")
    files["ascii"] = ascii_file

    # Large text file
    large_file = temp_dir / "large.txt"
    large_file.write_text(f"Line {i}\n" for i in range(10000))
    files["large"] = large_file

    return files


# =============================================================================
# AI/ML Model Fixtures (Phase 3: Property-based Testing)
# =============================================================================


@pytest.fixture
def mock_embeddings():
    """
    Mock embedding service for testing without model loading.
    """
    mock_service = Mock()
    mock_service.encode.return_value = [0.1] * 1024  # Mock 1024D vector
    mock_service.model_name = "mock-legal-bert"
    mock_service.dimension = 1024
    return mock_service


@pytest.fixture
def mock_vector_store():
    """
    Mock vector store for testing without Qdrant.
    """
    mock_store = Mock()
    mock_store.upsert.return_value = True
    mock_store.search.return_value = [
        {"id": "test_1", "score": 0.95, "metadata": {"content": "test"}},
        {"id": "test_2", "score": 0.85, "metadata": {"content": "example"}},
    ]
    mock_store.count.return_value = 100
    return mock_store


# =============================================================================
# Performance and Monitoring Fixtures (Phase 6: Speed & Stability)
# =============================================================================


@pytest.fixture
def performance_monitor():
    """
    Monitor test performance and resource usage.
    """
    import time

    import psutil

    start_time = time.time()
    start_memory = psutil.Process().memory_info().rss / 1024 / 1024  # MB

    yield {"start_time": start_time, "start_memory": start_memory}

    end_time = time.time()
    end_memory = psutil.Process().memory_info().rss / 1024 / 1024  # MB

    duration = end_time - start_time
    memory_delta = end_memory - start_memory

    # Log performance metrics (could be sent to monitoring system)
    if duration > 1.0:  # Log slow tests
        print(f"SLOW TEST: {duration:.2f}s, Memory: +{memory_delta:.1f}MB")


# =============================================================================
# Mutation Testing Support (Phase 5: Test Quality Validation)
# =============================================================================


@pytest.fixture
def mutation_context():
    """
    Context for mutation testing scenarios.
    """
    return {
        "mutant_id": os.getenv("MUTANT_ID"),
        "original_function": os.getenv("MUTANT_ORIGINAL"),
        "mutated_function": os.getenv("MUTANT_MUTATED"),
        "is_mutation_test": bool(os.getenv("MUTANT_ID")),
    }


# =============================================================================
# Test Data Factories (Property-based Testing Support)
# =============================================================================


def create_sample_email_data() -> dict[str, Any]:
    """
    Factory for creating sample email data.
    """
    return {
        "id": "test_email_001",
        "subject": "Test Email Subject",
        "sender": "sender@example.com",
        "recipient": "recipient@example.com",
        "body": "This is a test email body with some content.",
        "date": "2024-01-01T12:00:00Z",
        "labels": ["inbox", "important"],
        "thread_id": "thread_001",
    }


def create_sample_document_data() -> dict[str, Any]:
    """
    Factory for creating sample document data.
    """
    return {
        "id": "test_doc_001",
        "title": "Test Document",
        "content": "This is test document content with legal terms.",
        "content_type": "pdf",
        "file_path": "/tmp/test.pdf",
        "metadata": {
            "page_count": 5,
            "file_size": 1024,
            "created_date": "2024-01-01",
            "tags": ["legal", "contract"],
        },
    }


# =============================================================================
# Cleanup and Validation
# =============================================================================


@pytest.fixture(autouse=True)
def cleanup_test_artifacts():
    """
    Automatically clean up test artifacts after each test.
    """
    yield

    # Clean up any temporary files that might have been created
    temp_patterns = ["test_*.tmp", "*.test", "coverup_*.py"]
    current_dir = Path.cwd()

    for pattern in temp_patterns:
        for temp_file in current_dir.glob(pattern):
            try:
                temp_file.unlink()
            except (OSError, PermissionError):
                pass  # Best effort cleanup


def pytest_runtest_teardown(item, nextitem):
    """
    Validate test isolation after each test.
    """
    # Ensure no test data leaked into the main database
    if os.path.exists("emails.db"):
        conn = sqlite3.connect("emails.db")
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM content WHERE title LIKE 'Test %'")
        test_count = cursor.fetchone()[0]
        conn.close()

        if test_count > 0:
            print(f"WARNING: Found {test_count} test records in main database!")
