"""Test fixtures for PDF service tests.

Following TESTING_PROTOCOLS.md: Isolated databases, real data, minimal
mocking.
"""

import hashlib
import os
import sqlite3
import tempfile
import uuid
from collections.abc import Generator

import pytest


@pytest.fixture(scope="function")
def isolated_test_db_path() -> Generator[str, None, None]:
    """Completely isolated test database per test function.

    Following TESTING_PROTOCOLS.md standards.
    """
    # Create unique database file for each test
    test_db_name = f"test_pdf_{uuid.uuid4().hex[:8]}.db"
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
def test_database_with_documents_table(isolated_test_db_path) -> str:
    """Create isolated database with documents table schema.

    Following pdf_service/CLAUDE.md database schema.
    """
    conn = sqlite3.connect(isolated_test_db_path)
    cursor = conn.cursor()

    # Create documents table with PDF service schema
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

    # Create performance indexes
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_documents_hash ON documents(file_hash)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_documents_vector ON documents(vector_processed)")

    conn.commit()
    conn.close()

    return isolated_test_db_path


@pytest.fixture(scope="function")
def sample_pdf_content() -> list[dict]:
    """Sample PDF content chunks for testing.

    Real document content patterns following TESTING_PROTOCOLS.md.
    """
    return [
        {
            "file_name": "business_proposal.pdf",
            "file_path": "/tmp/test_pdfs/business_proposal.pdf",
            "chunks": [
                {
                    "chunk_index": 0,
                    "text_content": """BUSINESS PROPOSAL

                    Company: Tech Solutions LLC
                    Date: January 15, 2024
                    Prepared for: Microsoft Corporation

                    Executive Summary:
                    This proposal outlines a $75,000 software development project
                    for creating a customer management system. The project will be
                    completed by our team of 5 engineers over 6 months.

                    Key deliverables include:
                    - Database design and implementation
                    - Web-based user interface
                    - API integration layer
                    - Documentation and training materials""",
                    "char_count": 489,
                },
                {
                    "chunk_index": 1,
                    "text_content": """PROJECT TIMELINE

                    Phase 1 (Months 1-2): Requirements and Design
                    - Stakeholder interviews
                    - System architecture design
                    - Database schema creation
                    - UI/UX mockups

                    Phase 2 (Months 3-4): Development
                    - Core application development
                    - Database implementation
                    - API endpoint creation
                    - Initial user interface

                    Phase 3 (Months 5-6): Testing and Deployment
                    - Quality assurance testing
                    - User acceptance testing
                    - Production deployment
                    - Training and documentation""",
                    "char_count": 567,
                },
            ],
        },
        {
            "file_name": "legal_contract.pdf",
            "file_path": "/tmp/test_pdfs/legal_contract.pdf",
            "chunks": [
                {
                    "chunk_index": 0,
                    "text_content": """SOFTWARE LICENSING AGREEMENT

                    This agreement is made between:

                    Licensor: ABC Software Corporation
                    Address: 123 Tech Street, San Francisco, CA

                    Licensee: XYZ Corporation
                    Address: 456 Business Ave, New York, NY

                    License Fee: $25,000 annually
                    Effective Date: March 1, 2024
                    Term: 3 years with automatic renewal

                    The licensor grants the licensee a non-exclusive license
                    to use the software for internal business operations only.""",
                    "char_count": 498,
                },
            ],
        },
        {
            "file_name": "financial_report.pdf",
            "file_path": "/tmp/test_pdfs/financial_report.pdf",
            "chunks": [
                {
                    "chunk_index": 0,
                    "text_content": """Q4 2023 FINANCIAL REPORT

                    Company: Global Tech Inc.
                    Report Period: October - December 2023
                    Prepared by: Sarah Johnson, CFO

                    REVENUE SUMMARY:
                    - Software sales: $1,200,000
                    - Consulting services: $800,000
                    - Support contracts: $400,000
                    - Total revenue: $2,400,000

                    EXPENSE BREAKDOWN:
                    - Salaries and benefits: $1,100,000
                    - Infrastructure costs: $300,000
                    - Marketing and sales: $200,000
                    - Other expenses: $150,000
                    - Total expenses: $1,750,000

                    NET PROFIT: $650,000 (27% margin)""",
                    "char_count": 612,
                },
            ],
        },
    ]


@pytest.fixture(scope="function")
def temp_pdf_files(tmp_path) -> dict[str, str]:
    """Create temporary PDF files for testing upload functionality.

    Real file system interaction following TESTING_PROTOCOLS.md.
    """
    # Create test PDF directory
    pdf_dir = tmp_path / "test_pdfs"
    pdf_dir.mkdir()

    # Create mock PDF files with realistic content
    pdf_files = {}

    # Business document
    business_pdf = pdf_dir / "business_proposal.pdf"
    business_content = b"%PDF-1.4\n1 0 obj\n<<\n/Type /Catalog\n/Pages 2 0 R\n>>\nendobj\n2 0 obj\n<<\n/Type /Pages\n/Kids [3 0 R]\n/Count 1\n>>\nendobj\n3 0 obj\n<<\n/Type /Page\n/Parent 2 0 R\n/MediaBox [0 0 612 792]\n>>\nendobj\nxref\n0 4\n0000000000 65535 f \n0000000010 00000 n \n0000000053 00000 n \n0000000125 00000 n \ntrailer\n<<\n/Size 4\n/Root 1 0 R\n>>\nstartxref\n179\n%%EOF"
    business_pdf.write_bytes(business_content)
    pdf_files["business"] = str(business_pdf)

    # Legal document
    legal_pdf = pdf_dir / "legal_contract.pdf"
    legal_content = b"%PDF-1.4\n1 0 obj\n<<\n/Type /Catalog\n/Pages 2 0 R\n>>\nendobj\n2 0 obj\n<<\n/Type /Pages\n/Kids [3 0 R]\n/Count 1\n>>\nendobj\n3 0 obj\n<<\n/Type /Page\n/Parent 2 0 R\n/MediaBox [0 0 612 792]\n>>\nendobj\nxref\n0 4\n0000000000 65535 f \n0000000010 00000 n \n0000000053 00000 n \n0000000125 00000 n \ntrailer\n<<\n/Size 4\n/Root 1 0 R\n>>\nstartxref\n179\n%%EOF"
    legal_pdf.write_bytes(legal_content)
    pdf_files["legal"] = str(legal_pdf)

    # Financial report
    financial_pdf = pdf_dir / "financial_report.pdf"
    financial_content = b"%PDF-1.4\n1 0 obj\n<<\n/Type /Catalog\n/Pages 2 0 R\n>>\nendobj\n2 0 obj\n<<\n/Type /Pages\n/Kids [3 0 R]\n/Count 1\n>>\nendobj\n3 0 obj\n<<\n/Type /Page\n/Parent 2 0 R\n/MediaBox [0 0 612 792]\n>>\nendobj\nxref\n0 4\n0000000000 65535 f \n0000000010 00000 n \n0000000053 00000 n \n0000000125 00000 n \ntrailer\n<<\n/Size 4\n/Root 1 0 R\n>>\nstartxref\n179\n%%EOF"
    financial_pdf.write_bytes(financial_content)
    pdf_files["financial"] = str(financial_pdf)

    # Directory path
    pdf_files["directory"] = str(pdf_dir)

    return pdf_files


@pytest.fixture
def malformed_pdf_test_cases(tmp_path) -> list[dict]:
    """Malformed PDF files for adversarial testing.

    Following TESTING_PROTOCOLS.md: Test edge cases that could break
    processing.
    """
    test_cases = []

    # Empty file
    empty_file = tmp_path / "empty.pdf"
    empty_file.write_bytes(b"")
    test_cases.append(
        {"description": "empty_file", "path": str(empty_file), "expected_error": "Invalid PDF file"}
    )

    # Non-PDF file with PDF extension
    fake_pdf = tmp_path / "fake.pdf"
    fake_pdf.write_text("This is not a PDF file")
    test_cases.append(
        {
            "description": "non_pdf_content",
            "path": str(fake_pdf),
            "expected_error": "Invalid PDF file",
        }
    )

    # Corrupted PDF header
    corrupted_pdf = tmp_path / "corrupted.pdf"
    corrupted_pdf.write_bytes(b"%PDF-CORRUPTED\nThis is corrupted")
    test_cases.append(
        {
            "description": "corrupted_header",
            "path": str(corrupted_pdf),
            "expected_error": "PDF parsing failed",
        }
    )

    # File with special characters in name
    special_char_pdf = tmp_path / "special_chars_测试_файл.pdf"
    special_char_pdf.write_bytes(b"%PDF-1.4\nMinimal PDF content")
    test_cases.append(
        {
            "description": "special_characters",
            "path": str(special_char_pdf),
            "expected_error": None,  # Should handle gracefully
        }
    )

    return test_cases


@pytest.fixture
def sample_document_hashes() -> dict[str, str]:
    """
    Pre-computed SHA-256 hashes for deduplication testing.
    """
    sample_content = {
        "business_proposal": b"Sample business proposal content",
        "legal_contract": b"Sample legal contract content",
        "financial_report": b"Sample financial report content",
    }

    hashes = {}
    for name, content in sample_content.items():
        hashes[name] = hashlib.sha256(content).hexdigest()

    return hashes


@pytest.fixture
def pdf_processing_mock_data():
    """Mock data for PDF processing pipeline testing.

    Simulates QuickPDFHandler output without requiring actual PDF
    parsing.
    """
    return {
        "successful_processing": {
            "chunks": [
                {
                    "text": "This is the first chunk of extracted text from the PDF document.",
                    "metadata": {"page": 1, "chunk_index": 0},
                },
                {
                    "text": "This is the second chunk containing more content from the document.",
                    "metadata": {"page": 1, "chunk_index": 1},
                },
            ],
            "total_pages": 1,
            "extraction_successful": True,
        },
        "processing_failure": {
            "error": "Failed to extract text from PDF",
            "extraction_successful": False,
        },
        "empty_document": {"chunks": [], "total_pages": 1, "extraction_successful": True},
    }


@pytest.fixture
def database_migration_scenarios():
    """Test scenarios for database schema migration testing.

    Tests backward compatibility with existing databases.
    """
    return [
        {
            "scenario": "missing_pdf_columns",
            "initial_schema": """
                CREATE TABLE documents (
                    chunk_id TEXT PRIMARY KEY,
                    file_path TEXT NOT NULL,
                    file_name TEXT NOT NULL,
                    chunk_index INTEGER NOT NULL,
                    text_content TEXT NOT NULL,
                    char_count INTEGER NOT NULL
                );
            """,
            "expected_columns": [
                "file_size",
                "file_hash",
                "source_type",
                "modified_time",
                "processed_time",
                "content_type",
                "vector_processed",
            ],
        },
        {
            "scenario": "partial_migration",
            "initial_schema": """
                CREATE TABLE documents (
                    chunk_id TEXT PRIMARY KEY,
                    file_path TEXT NOT NULL,
                    file_name TEXT NOT NULL,
                    chunk_index INTEGER NOT NULL,
                    text_content TEXT NOT NULL,
                    char_count INTEGER NOT NULL,
                    file_size INTEGER,
                    file_hash TEXT
                );
            """,
            "expected_columns": [
                "source_type",
                "modified_time",
                "processed_time",
                "content_type",
                "vector_processed",
            ],
        },
    ]


@pytest.fixture(scope="function")
def real_database_with_contentwriter(isolated_test_db_path):
    """Phase 2 Task 2.1: Real database fixture with ContentWriter for testing
    actual storage.

    Eliminates mock dependencies by providing real database operations.
    Following tri_plan.md Phase 2 requirements for mock elimination.
    """
    # Import ContentWriter for real database operations
    import os
    import sys

    project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    if project_root not in sys.path:
        sys.path.insert(0, project_root)

    from shared.simple_db import SimpleDB

    # Initialize real SimpleDB with isolated test database
    db = SimpleDB(isolated_test_db_path)

    return {"db_path": isolated_test_db_path, "db": db}


@pytest.fixture(scope="function")
def populated_test_database(real_database_with_contentwriter, sample_pdf_content):
    """Phase 2 Task 2.1: Test database pre-populated with real PDF document
    chunks.

    Provides realistic test data for validating database operations
    without mocks.
    """
    db = real_database_with_contentwriter["db"]
    db_path = real_database_with_contentwriter["db_path"]

    # Populate database with sample PDF chunks using real ContentWriter
    for pdf_doc in sample_pdf_content:
        file_hash = f"test_hash_{pdf_doc['file_name']}"

        for chunk in pdf_doc["chunks"]:
            chunk_data = {
                "chunk_id": f"{file_hash}_{chunk['chunk_index']}",
                "file_path": pdf_doc["file_path"],
                "file_name": pdf_doc["file_name"],
                "chunk_index": chunk["chunk_index"],
                "text_content": chunk["text_content"],
                "char_count": chunk["char_count"],
                "file_hash": file_hash,
                "source_type": "test_upload",
                "content_type": "document",
                "vector_processed": 0,
            }

            # Use real database operation - no mocks
            try:
                db.add_document_chunk(chunk_data)
            except Exception as e:
                assert False, f"Failed to populate test data: {e}"

    return {"db_path": db_path, "db": db, "sample_data": sample_pdf_content}


@pytest.fixture(scope="function")
def database_error_scenarios(isolated_test_db_path):
    """Phase 2 Task 2.2: Database error scenario testing fixtures.

    Tests real database constraint violations and error conditions.
    """
    import sqlite3

    def create_constraint_violation_scenario():
        """
        Create scenario to test unique constraint violations.
        """
        conn = sqlite3.connect(isolated_test_db_path)
        cursor = conn.cursor()

        # Create documents table with real constraints
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

        # Insert initial document to trigger constraint violations
        cursor.execute(
            """
            INSERT INTO documents (chunk_id, file_path, file_name, chunk_index,
                                 text_content, char_count, file_hash)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
            ("test_chunk_1", "/tmp/test.pdf", "test.pdf", 0, "test content", 12, "test_hash"),
        )

        conn.commit()
        conn.close()

    return {
        "db_path": isolated_test_db_path,
        "create_constraint_violation": create_constraint_violation_scenario,
    }
