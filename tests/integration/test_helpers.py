"""Shared utilities for integration tests.

Provides database setup, file management, and verification helpers.
"""

import os
import shutil
import sys
import tempfile
import time
from pathlib import Path
from typing import Any

sys.path.append(str(Path(__file__).parent.parent.parent))

from lib.db import SimpleDB


def create_test_database(db_path: str | None = None) -> tuple[SimpleDB, str]:
    """Create a temporary database with all required tables.

    Returns:
        tuple: (SimpleDB instance, database path)
    """
    if not db_path:
        temp_db = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        db_path = temp_db.name
        temp_db.close()

    db = SimpleDB(db_path)

    # Create content table
    db.execute(
        """
        CREATE TABLE IF NOT EXISTS content (
            id TEXT PRIMARY KEY,
            content_type TEXT,
            title TEXT,
            content TEXT,
            source_path TEXT,
            metadata TEXT,
            word_count INTEGER,
            char_count INTEGER,
            created_time TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """
    )

    # Create emails table
    db.execute(
        """
        CREATE TABLE IF NOT EXISTS emails (
            id TEXT PRIMARY KEY,
            subject TEXT,
            sender TEXT,
            recipients TEXT,
            date TEXT,
            body TEXT,
            html_body TEXT,
            labels TEXT,
            thread_id TEXT,
            message_id TEXT,
            attachments TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """
    )

    # Create documents table for PDFs with correct schema
    db.execute(
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
            vector_processed BOOLEAN DEFAULT 0,
            extraction_method TEXT DEFAULT 'pdfplumber',
            legal_metadata TEXT,
            ocr_confidence REAL
        )
    """
    )

    # Create intelligence tables
    db.create_intelligence_tables()

    # Run migration
    db.migrate_schema()

    return db, db_path


def cleanup_test_files(paths: list[str]) -> None:
    """Remove test artifacts from filesystem.

    Args:
        paths: List of file/directory paths to remove
    """
    for path in paths:
        try:
            if os.path.isfile(path):
                os.unlink(path)
            elif os.path.isdir(path):
                shutil.rmtree(path)
        except Exception:
            pass  # Ignore errors during cleanup


def setup_data_directories(base_path: str) -> dict[str, str]:
    """Create data pipeline directory structure for testing.

    Args:
        base_path: Base directory for data pipeline

    Returns:
        dict: Paths to each pipeline directory
    """
    dirs = {
        "raw": os.path.join(base_path, "raw"),
        "staged": os.path.join(base_path, "staged"),
        "processed": os.path.join(base_path, "processed"),
        "quarantine": os.path.join(base_path, "quarantine"),
        "export": os.path.join(base_path, "export"),
    }

    for dir_path in dirs.values():
        os.makedirs(dir_path, exist_ok=True)

    return dirs


def wait_for_processing(check_func, timeout: int = 30, interval: float = 0.5) -> bool:
    """Wait for async processing to complete.

    Args:
        check_func: Function that returns True when processing is complete
        timeout: Maximum seconds to wait
        interval: Seconds between checks

    Returns:
        bool: True if processing completed, False if timeout
    """
    start_time = time.time()

    while time.time() - start_time < timeout:
        if check_func():
            return True
        time.sleep(interval)

    return False


def verify_summary_quality(
    summary: dict[str, Any], min_keywords: int = 3, min_sentences: int = 1
) -> bool:
    """Check if summary meets minimum quality requirements.

    Args:
        summary: Summary dictionary from database
        min_keywords: Minimum number of keywords required
        min_sentences: Minimum number of sentences required

    Returns:
        bool: True if summary meets requirements
    """
    if not summary:
        return False

    # Check TF-IDF keywords
    keywords = summary.get("tf_idf_keywords", {})
    if len(keywords) < min_keywords:
        return False

    # Check TextRank sentences
    sentences = summary.get("textrank_sentences", [])
    if len(sentences) < min_sentences:
        return False

    # Check summary text exists
    if not summary.get("summary_text"):
        return False

    return True


def create_test_email_data() -> dict[str, Any]:
    """Create realistic test email data with legal content.

    Returns:
        dict: Email data suitable for testing
    """
    return {
        "id": "test_email_001",
        "subject": "Contract Review - ABC Corp Agreement",
        "sender": "legal@example.com",
        "recipients": "review@example.com",
        "date": "2024-01-15T10:30:00Z",
        "body": """
        Dear Team,

        Please review the attached contract for ABC Corporation. The agreement covers:

        1. Service delivery terms effective January 2024
        2. Payment schedule of $50,000 monthly
        3. Termination clause requiring 60 days notice
        4. Intellectual property assignments
        5. Confidentiality provisions lasting 5 years

        The contract includes standard indemnification clauses and limitation of liability.
        ABC Corp has requested execution by end of month.

        Key parties:
        - ABC Corporation (Service Provider)
        - XYZ Industries (Client)
        - John Smith, CEO of ABC
        - Jane Doe, General Counsel of XYZ

        Please provide feedback by Wednesday.

        Best regards,
        Legal Team
        """,
        "html_body": None,
        "labels": '["contracts", "review", "urgent"]',
        "thread_id": "thread_001",
        "message_id": "msg_001",
        "attachments": "[]",
    }


def verify_file_in_directory(directory: str, filename_pattern: str) -> bool:
    """Check if a file matching the pattern exists in directory.

    Args:
        directory: Directory path to check
        filename_pattern: Pattern to match (can be partial filename)

    Returns:
        bool: True if matching file found
    """
    if not os.path.exists(directory):
        return False

    for file in os.listdir(directory):
        if filename_pattern in file:
            return True

    return False


def get_test_pdf_path() -> str:
    """Get path to a test PDF file.

    Returns:
        str: Full path to test PDF
    """
    base_dir = Path(__file__).parent.parent.parent
    test_pdf = base_dir / "tests" / "test_data" / "pdf_samples" / "text_based_contract.pdf"

    if not test_pdf.exists():
        raise FileNotFoundError(f"Test PDF not found: {test_pdf}")

    return str(test_pdf)


def verify_database_record(db: SimpleDB, table: str, where_clause: str, params: tuple = ()) -> bool:
    """Check if a record exists in database.

    Args:
        db: SimpleDB instance
        table: Table name
        where_clause: SQL WHERE clause
        params: Parameters for WHERE clause

    Returns:
        bool: True if record exists
    """
    query = f"SELECT COUNT(*) as count FROM {table} WHERE {where_clause}"
    result = db.fetch_one(query, params)
    return result and result["count"] > 0


def get_summary_for_document(db: SimpleDB, document_id: str) -> dict | None:
    """Get summary data for a document.

    Args:
        db: SimpleDB instance
        document_id: Document ID to look up

    Returns:
        dict: Summary data or None
    """
    summaries = db.get_document_summaries(document_id)
    return summaries[0] if summaries else None
