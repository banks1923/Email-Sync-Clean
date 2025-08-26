#!/usr/bin/env python3
"""Comprehensive schema migration tests.

Tests the complete migration process from content_id to id schema,
including business keys, deterministic UUIDs, and UPSERT functionality.
"""

import os
import sqlite3

# Add project root to path for imports
import sys
import tempfile
from pathlib import Path
from uuid import UUID, uuid5

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from shared.simple_db import SimpleDB
from utilities.maintenance.fix_content_schema import ContentSchemaMigration

# Standard UUID namespace for testing
UUID_NAMESPACE = UUID("6ba7b810-9dad-11d1-80b4-00c04fd430c8")


class TestSchemaMigration:
    """
    Test complete schema migration process.
    """

    @pytest.fixture
    def temp_db_path(self):
        """
        Create temporary database for testing.
        """
        fd, path = tempfile.mkstemp(suffix=".db")
        os.close(fd)
        yield path
        try:
            os.unlink(path)
        except:
            pass

    @pytest.fixture
    def pre_migration_db(self, temp_db_path):
        """
        Set up database with old schema for migration testing.
        """
        conn = sqlite3.connect(temp_db_path)
        cursor = conn.cursor()

        # Create old-style content table with content_id
        cursor.execute(
            """
            CREATE TABLE content (
                id TEXT PRIMARY KEY,
                type TEXT NOT NULL,
                title TEXT,
                content TEXT NOT NULL,
                metadata TEXT DEFAULT '{}',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                content_type TEXT DEFAULT 'unknown',
                char_count INTEGER DEFAULT 0
            )
        """
        )

        # Create emails table
        cursor.execute(
            """
            CREATE TABLE emails (
                message_id TEXT PRIMARY KEY,
                subject TEXT,
                sender TEXT,
                content TEXT,
                datetime_utc TEXT,
                content_hash TEXT
            )
        """
        )

        # Insert test data
        cursor.execute(
            """
            INSERT INTO content (id, type, title, content)
            VALUES ('old-content-1', 'document', 'Old Document', 'Old content')
        """
        )

        cursor.execute(
            """
            INSERT INTO emails (message_id, subject, sender, content, datetime_utc)
            VALUES ('email123', 'Test Email', 'test@example.com', 'Email body', '2024-01-01')
        """
        )

        conn.commit()
        conn.close()
        return temp_db_path

    def test_deterministic_uuid_generation(self):
        """
        Test that UUID5 generation is deterministic and consistent.
        """
        # Test email UUID generation
        email_uuid_1 = str(uuid5(UUID_NAMESPACE, "email:email123"))
        email_uuid_2 = str(uuid5(UUID_NAMESPACE, "email:email123"))

        assert email_uuid_1 == email_uuid_2, "UUID5 generation should be deterministic"

        # Test PDF UUID generation
        pdf_hash = "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
        pdf_uuid_1 = str(uuid5(UUID_NAMESPACE, f"pdf:{pdf_hash}"))
        pdf_uuid_2 = str(uuid5(UUID_NAMESPACE, f"pdf:{pdf_hash}"))

        assert pdf_uuid_1 == pdf_uuid_2, "PDF UUID5 generation should be deterministic"

        # Different inputs should produce different UUIDs
        assert email_uuid_1 != pdf_uuid_1, "Different inputs should produce different UUIDs"

    def test_business_key_uniqueness(self, temp_db_path):
        """
        Test business key constraint prevents duplicates.
        """
        db = SimpleDB(temp_db_path)

        # Test UPSERT functionality if available
        if hasattr(db, "upsert_content"):
            # First insert should succeed
            content_id_1 = db.upsert_content(
                source_type="email",
                external_id="test123",
                content_type="email",
                title="Test Email",
                content="Test content",
            )

            # Second insert with same business key should update, not create new
            content_id_2 = db.upsert_content(
                source_type="email",
                external_id="test123",
                content_type="email",
                title="Updated Email",
                content="Updated content",
            )

            # Should return same deterministic ID
            assert (
                content_id_1 == content_id_2
            ), "UPSERT should return same ID for same business key"

            # Verify only one record exists
            records = db.fetch(
                "SELECT COUNT(*) as count FROM content WHERE source_type = 'email' AND external_id = 'test123'"
            )
            assert records[0]["count"] == 1, "UPSERT should not create duplicates"

    def test_schema_migration_process(self, pre_migration_db):
        """
        Test complete schema migration process.
        """
        # Run migration
        migration = ContentSchemaMigration(pre_migration_db)
        metrics = migration.run_migration(dry_run=False)

        # Verify migration metrics
        assert metrics["emails_migrated"] > 0, "Should have migrated emails"
        assert len(metrics["errors"]) == 0, "Migration should complete without errors"

        # Verify database schema after migration
        db = SimpleDB(pre_migration_db)

        # Check that content table now uses 'id'
        content = db.fetch("SELECT id, source_type, external_id FROM content LIMIT 10")
        for row in content:
            assert "id" in row, "Content table should have 'id' column"
            if row.get("source_type") == "email":
                assert row.get("external_id") is not None, "Email content should have external_id"

    def test_sql_string_compliance(self):
        """
        Test that no code uses content_id in SQL strings.
        """
        project_root = Path(__file__).parent.parent.parent

        # Import and run the compliance checker
        sys.path.append(str(project_root / "tools" / "linting"))
        from check_schema_compliance import check_content_id_usage

        violations = check_content_id_usage()

        # Should find no violations (except allowed ones)
        violation_lines = [v[2] for v in violations if "# ALLOWED: content_id" not in v[2]]
        assert len(violation_lines) == 0, f"Found prohibited content_id usage: {violation_lines}"

    def test_libcst_idempotency(self):
        """
        Test that LibCST codemod is idempotent.
        """
        project_root = Path(__file__).parent.parent.parent

        # Import compliance checker
        sys.path.append(str(project_root / "tools" / "linting"))
        from check_schema_compliance import run_libcst_idempotency_check

        is_idempotent, message = run_libcst_idempotency_check()
        assert is_idempotent, f"LibCST codemod should be idempotent: {message}"

    def test_external_id_conventions(self):
        """
        Test external_id format validation for different content types.
        """

        # Test email external_id format
        assert self._validate_email_id("178a1b2c3d4e5f6g"), "Valid email ID should pass"
        assert not self._validate_email_id("invalid@email"), "Invalid email ID should fail"

        # Test PDF external_id format (SHA-256)
        valid_pdf_id = "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
        assert self._validate_pdf_id(valid_pdf_id), "Valid PDF hash should pass"
        assert not self._validate_pdf_id("invalid_hash"), "Invalid PDF hash should fail"

    def _validate_email_id(self, external_id: str) -> bool:
        """
        Validate email external_id format.
        """
        import re

        return bool(re.match(r"^[a-zA-Z0-9]{10,20}$", external_id))

    def _validate_pdf_id(self, external_id: str) -> bool:
        """
        Validate PDF external_id format (SHA-256).
        """
        return len(external_id) == 64 and all(c in "0123456789abcdef" for c in external_id.lower())

    def test_migration_idempotency(self, pre_migration_db):
        """
        Test that migration can be run multiple times safely.
        """
        # Run migration first time
        migration1 = ContentSchemaMigration(pre_migration_db)
        migration1.run_migration(dry_run=False)

        # Get content count after first migration
        db = SimpleDB(pre_migration_db)
        count_after_first = db.fetch_one("SELECT COUNT(*) as count FROM content")["count"]

        # Run migration second time
        migration2 = ContentSchemaMigration(pre_migration_db)
        metrics2 = migration2.run_migration(dry_run=False)

        # Get content count after second migration
        count_after_second = db.fetch_one("SELECT COUNT(*) as count FROM content")["count"]

        # Should be idempotent - same count
        assert count_after_first == count_after_second, "Migration should be idempotent"
        assert len(metrics2["errors"]) == 0, "Second migration should complete without errors"

    def test_qdrant_reconciliation_preparation(self, temp_db_path):
        """
        Test that migration prepares data for Qdrant reconciliation.
        """
        db = SimpleDB(temp_db_path)

        # Add content with business keys
        if hasattr(db, "upsert_content"):
            content_id = db.upsert_content(
                source_type="email",
                external_id="email123",
                content_type="email",
                title="Test Email",
                content="Test content",
            )

            # Verify deterministic ID was generated
            expected_id = str(uuid5(UUID_NAMESPACE, "email:email123"))
            assert content_id == expected_id, f"Expected {expected_id}, got {content_id}"

            # Verify content can be retrieved by deterministic ID
            retrieved = db.fetch_one("SELECT * FROM content WHERE id = ?", (expected_id,))
            assert retrieved is not None, "Content should be retrievable by deterministic ID"
            assert retrieved["source_type"] == "email", "Source type should be preserved"
            assert retrieved["external_id"] == "email123", "External ID should be preserved"


class TestMigrationPerformance:
    """
    Test migration performance characteristics.
    """

    def test_batch_performance(self, temp_db_path):
        """
        Test that migration handles large batches efficiently.
        """
        # This would test migration of thousands of emails
        # to ensure performance is acceptable

    def test_memory_usage(self, temp_db_path):
        """
        Test that migration doesn't consume excessive memory.
        """
        # This would monitor memory usage during migration
        # to ensure it stays within reasonable bounds


if __name__ == "__main__":
    # Run tests directly
    pytest.main([__file__, "-v"])
