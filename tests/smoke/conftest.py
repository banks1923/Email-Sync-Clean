"""
Minimal fixtures for smoke tests - fast and reliable only.
"""

import tempfile
from pathlib import Path

import pytest


@pytest.fixture
def temp_db():
    """
    In-memory SQLite database for testing.
    """
    import sqlite3

    conn = sqlite3.connect(":memory:")
    yield conn
    conn.close()


@pytest.fixture
def temp_dir():
    """
    Temporary directory for file operations.
    """
    with tempfile.TemporaryDirectory() as tmp_dir:
        yield Path(tmp_dir)


@pytest.fixture
def mock_env(monkeypatch):
    """
    Mock environment variables for testing.
    """
    test_env = {"EMAIL_SYNC_DB": ":memory:", "SKIP_MODEL_LOAD": "1", "TEST_MODE": "1"}
    for key, value in test_env.items():
        monkeypatch.setenv(key, value)
    yield test_env


@pytest.fixture
def sample_email_data():
    """
    Sample email data for testing.
    """
    return {
        "id": "test_123",
        "subject": "Test Email",
        "sender": "test@example.com",
        "date": "2024-01-01 12:00:00",
        "body": "This is a test email for smoke testing.",
    }


@pytest.fixture
def sample_pdf_path(temp_dir):
    """
    Create a minimal test PDF.
    """
    pdf_path = temp_dir / "test.pdf"
    # Create a minimal PDF-like file for testing
    pdf_path.write_bytes(b"%PDF-1.4\nTest PDF content\n%%EOF")
    return pdf_path
