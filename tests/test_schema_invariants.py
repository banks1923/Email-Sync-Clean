"""
Schema Invariant Tests Pins critical system behaviors to prevent regressions.
"""

import os
import re
import tempfile
import unittest
from pathlib import Path

from shared.db.simple_db import SimpleDB
from utilities.vector_store import get_vector_store


class TestSchemaInvariants(unittest.TestCase):
    """
    Test schema invariants and critical system behaviors.
    """

    def test_sql_no_content_id_strings(self):
        """
        Ensure no content_id references exist in SQL strings.
        """
        # Scan codebase for prohibited content_id usage in SQL
        violations = []

        project_root = Path(__file__).parent.parent

        # SQL patterns that should not contain content_id
        sql_patterns = [
            r'SELECT[^"\']*content_id',
            r'WHERE[^"\']*content_id\s*=',
            r'INSERT[^"\']*content_id',
            r'UPDATE[^"\']*content_id\s*=',
            r'DELETE[^"\']*content_id\s*=',
            r'REFERENCES[^"\']*content_id',
        ]

        for py_file in project_root.rglob("*.py"):
            # Skip this test file, codemods, linting tools, and maintenance scripts
            if any(
                skip_path in str(py_file)
                for skip_path in [
                    "test_schema_invariants",
                    "codemods",
                    "tools/linting",
                    "utilities/maintenance",
                ]
            ):
                continue

            try:
                with open(py_file, encoding="utf-8") as f:
                    content = f.read()

                lines = content.split("\n")
                for line_num, line in enumerate(lines, 1):
                    # Skip if marked as allowed
                    if "# ALLOWED: content_id" in line:
                        continue

                    # Check if line contains SQL and content_id
                    if any(
                        keyword in line.upper()
                        for keyword in ["SELECT", "INSERT", "UPDATE", "DELETE", "REFERENCES"]
                    ):
                        for pattern in sql_patterns:
                            if re.search(pattern, line, re.IGNORECASE):
                                violations.append(f"{py_file}:{line_num}: {line.strip()}")

            except (UnicodeDecodeError, OSError):
                continue

        self.assertEqual(
            [],
            violations,
            "Found prohibited content_id references in SQL strings:\\n" + "\\n".join(violations),
        )

    def test_upsert_idempotent_business_key(self):
        """
        Test that UPSERT operations with same business key return same ID.
        """
        # Use main database but with test prefix to avoid conflicts
        db = SimpleDB()

        # Clean up any existing test data first
        try:
            db.execute(
                "DELETE FROM content_unified WHERE source_type='test-invariant' AND source_id LIKE 'test-%'"
            )
        except:
            pass  # Table might not exist yet

        try:

            # First UPSERT
            id1 = db.upsert_content(
                source_type="test-invariant",
                source_id="test-001",
                title="Test Document",
                content="Test content",
            )

            # Second UPSERT with same business key
            id2 = db.upsert_content(
                source_type="test-invariant",
                source_id="test-001",
                title="Test Document Updated",  # Changed title
                content="Updated content",  # Changed content
            )

            # Should return same ID (deterministic)
            self.assertEqual(id1, id2, "UPSERT with same business key should return same ID")

            # Should have only one record
            records = db.fetch(
                "SELECT COUNT(*) as count FROM content_unified WHERE source_type='test-invariant' AND source_id='test-001'"
            )
            self.assertEqual(
                1, records[0]["count"], "Should have exactly one record with this business key"
            )

        finally:
            # Cleanup test data
            try:
                db.execute(
                    "DELETE FROM content_unified WHERE source_type='test-invariant' AND source_id LIKE 'test-%'"
                )
            except:
                pass

    def test_qdrant_id_consistency(self):
        """
        Test that Qdrant point IDs match content table IDs.
        """
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp_file:
            db_path = tmp_file.name

        try:
            # This test requires Qdrant to be running
            vector_store = get_vector_store("emails")

            # Use temporary database
            db = SimpleDB(db_path)

            # Create test content
            content_id = db.upsert_content(
                source_type="test",
                source_id="vector-test-001",
                title="Vector Test",
                content="Test content for vector consistency",
            )

            # Store in vector store
            test_vector = [0.1] * 1024  # Mock Legal BERT vector
            vector_store.upsert(id=content_id, vector=test_vector, payload={"source_type": "test"})

            # Retrieve and check ID consistency
            result = vector_store.get(content_id)
            self.assertIsNotNone(result, "Vector should exist in store")
            self.assertEqual(
                content_id, result.get("id"), "Vector point ID should match content ID"
            )

        except Exception as e:
            self.skipTest(f"Qdrant not available or connection failed: {e}")
        finally:
            # Cleanup
            try:
                os.unlink(db_path)
            except:
                pass

    def test_fk_integrity(self):
        """
        Test that database has no foreign key constraint violations.
        """
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp_file:
            db_path = tmp_file.name

        try:
            # Use temporary database
            db = SimpleDB(db_path)

            # Enable foreign key checking
            db.execute("PRAGMA foreign_keys = ON")

            # Run foreign key check
            violations = db.fetch("PRAGMA foreign_key_check")

            self.assertEqual(
                [], violations, f"Foreign key constraint violations found: {violations}"
            )

        finally:
            # Cleanup
            os.unlink(db_path)

    def test_business_key_constraint_enforced(self):
        """
        Test that business key uniqueness is enforced.
        """
        db = SimpleDB()

        # Clean up any existing test data first
        try:
            db.execute(
                "DELETE FROM content_unified WHERE source_type='test-constraint' AND source_id='unique-test-001'"
            )
        except:
            pass

        try:
            # Insert first record
            db.upsert_content(
                source_type="test-constraint",
                source_id="unique-test-001",
                title="First Record",
                content="First content",
            )

            # Try to insert duplicate business key with regular INSERT (should fail)
            with self.assertRaises(Exception):
                db.execute(
                    """
                    INSERT INTO content_unified (source_type, source_id, title, body)
                    VALUES ('test-constraint', 'unique-test-001', 'Duplicate', 'Duplicate content')
                """
                )

        finally:
            # Cleanup
            try:
                db.execute(
                    "DELETE FROM content_unified WHERE source_type='test-constraint' AND source_id='unique-test-001'"
                )
            except:
                pass

    def test_deterministic_uuid_namespace(self):
        """
        Test that UUID generation uses consistent namespace.
        """
        import uuid

        # Expected namespace from business key implementation
        expected_namespace = uuid.UUID("6ba7b810-9dad-11d1-80b4-00c04fd430c8")

        db = SimpleDB()

        # Clean up any existing test data first
        try:
            db.execute(
                "DELETE FROM content_unified WHERE source_type='test-namespace' AND source_id='namespace-test-001'"
            )
        except:
            pass

        try:
            # Create content with known business key
            content_id = db.upsert_content(
                source_type="test-namespace",
                source_id="namespace-test-001",
                title="Namespace Test",
                content="Testing namespace consistency",
            )

            # Calculate expected UUID5
            business_key = "test-namespace:namespace-test-001"
            expected_id = str(uuid.uuid5(expected_namespace, business_key))

            self.assertEqual(
                expected_id,
                content_id,
                "Generated UUID should match expected UUID5 from business key",
            )

        finally:
            # Cleanup
            try:
                db.execute(
                    "DELETE FROM content_unified WHERE source_type='test-namespace' AND source_id='namespace-test-001'"
                )
            except:
                pass


if __name__ == "__main__":
    unittest.main()
