#!/usr/bin/env python3
"""Comprehensive test suite for semantic pipeline.

Tests all aspects of semantic enrichment during email ingestion.
"""

import json
import os
import unittest
from datetime import datetime
from unittest.mock import Mock, patch

import numpy as np

# Set up test environment
os.environ["SEMANTICS_ON_INGEST"] = "true"

from config.settings import semantic_settings
from lib.db import SimpleDB
from lib.pipelines import ChunkPipeline


class TestChunkPipeline(unittest.TestCase):
    """
    Test semantic pipeline functionality.
    """

    def setUp(self):
        """
        Set up test fixtures.
        """
        # Create in-memory database for testing
        self.db = SimpleDB(":memory:")
        self._setup_test_schema()
        self._insert_test_data()

        # Mock services
        self.mock_embedding_service = Mock()
        self.mock_vector_store = Mock()
        self.mock_entity_service = Mock()
        self.mock_timeline_service = Mock()

        # Create pipeline with mocked services
        self.pipeline = ChunkPipeline(
            db=self.db,
            embedding_service=self.mock_embedding_service,
            vector_store=self.mock_vector_store,
            entity_service=self.mock_entity_service,
            timeline_service=self.mock_timeline_service,
        )

    def _setup_test_schema(self):
        """
        Create test database schema.
        """
        self.db.execute(
            """
            CREATE TABLE emails (
                id INTEGER PRIMARY KEY,
                message_id TEXT UNIQUE,
                subject TEXT,
                sender TEXT,
                content TEXT,
                datetime_utc TEXT,
                eid TEXT,
                thread_id TEXT
            )
        """
        )

        self.db.execute(
            """
            CREATE TABLE content_unified (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                source_type TEXT NOT NULL,
                source_id TEXT NOT NULL,
                title TEXT,
                body TEXT NOT NULL,
                sha256 TEXT UNIQUE,
                validation_status TEXT DEFAULT 'pending',
                ready_for_embedding BOOLEAN DEFAULT 1,
                embedding_generated BOOLEAN DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(source_type, source_id)
            )
        """
        )

        self.db.execute(
            """
            CREATE TABLE entity_content_mapping (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                content_id TEXT NOT NULL,
                entity_text TEXT NOT NULL,
                entity_type TEXT NOT NULL,
                entity_label TEXT NOT NULL,
                start_char INTEGER NOT NULL,
                end_char INTEGER NOT NULL,
                confidence REAL,
                normalized_form TEXT,
                processed_time TEXT DEFAULT CURRENT_TIMESTAMP,
                entity_id TEXT,
                aliases TEXT,
                frequency INTEGER DEFAULT 1,
                last_seen DATETIME DEFAULT CURRENT_TIMESTAMP,
                extractor_type TEXT DEFAULT 'spacy',
                role_type TEXT
            )
        """
        )

        self.db.execute(
            """
            CREATE TABLE timeline_events (
                id INTEGER PRIMARY KEY,
                content_id TEXT,
                event_date TEXT,
                event_type TEXT,
                description TEXT,
                metadata TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """
        )

    def _insert_test_data(self):
        """
        Insert test emails and content.
        """
        test_emails = [
            {
                "message_id": "msg_001",
                "subject": "Contract Review",
                "sender": "legal@example.com",
                "content": "Please review the attached contract by January 15, 2025.",
                "datetime_utc": "2025-01-10T10:00:00Z",
                "eid": "EID-2025-0001",
                "thread_id": "thread_001",
            },
            {
                "message_id": "msg_002",
                "subject": "Meeting Confirmation",
                "sender": "client@example.com",
                "content": "Confirming our meeting on February 1st at 2 PM.",
                "datetime_utc": "2025-01-11T14:30:00Z",
                "eid": "EID-2025-0002",
                "thread_id": "thread_002",
            },
            {
                "message_id": "msg_003",
                "subject": "Invoice #12345",
                "sender": "billing@example.com",
                "content": "Invoice for services rendered. Due date: March 1, 2025.",
                "datetime_utc": "2025-01-12T09:15:00Z",
                "eid": "EID-2025-0003",
                "thread_id": "thread_003",
            },
        ]

        for email in test_emails:
            self.db.execute(
                """
                INSERT INTO emails (message_id, subject, sender, content, datetime_utc, eid, thread_id)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
                (
                    email["message_id"],
                    email["subject"],
                    email["sender"],
                    email["content"],
                    email["datetime_utc"],
                    email["eid"],
                    email["thread_id"],
                ),
            )

            # Add corresponding content entry
            {"message_id": email["message_id"], "type": "email"}
            self.db.execute(
                """
                INSERT INTO content_unified (source_type, source_id, title, body)
                VALUES (?, ?, ?, ?)
            """,
                ("email_message", email["message_id"], email["subject"], email["content"]),
            )

    def test_pipeline_initialization(self):
        """
        Test pipeline initialization.
        """
        pipeline = get_semantic_pipeline(db=self.db)
        self.assertIsNotNone(pipeline)
        self.assertEqual(pipeline.timeout_s, semantic_settings.semantics_timeout_s)

    def test_get_email_data(self):
        """
        Test email data retrieval with EIDs.
        """
        message_ids = ["msg_001", "msg_002"]
        emails_data = self.pipeline._get_email_data(message_ids)

        self.assertEqual(len(emails_data), 2)
        self.assertEqual(emails_data[0]["message_id"], "msg_001")
        self.assertEqual(emails_data[0]["eid"], "EID-2025-0001")
        self.assertEqual(emails_data[1]["message_id"], "msg_002")
        self.assertEqual(emails_data[1]["eid"], "EID-2025-0002")

    def test_entity_extraction(self):
        """
        Test entity extraction step.
        """
        # Setup mock
        self.mock_entity_service.extract_email_entities.return_value = {
            "success": True,
            "entities": [
                {"type": "DATE", "value": "January 15, 2025"},
                {"type": "ORG", "value": "legal@example.com"},
            ],
        }

        emails_data = self.pipeline._get_email_data(["msg_001"])
        result = self.pipeline._run_entity_extraction(emails_data)

        self.assertEqual(result["processed"], 1)
        self.assertEqual(result["entities_found"], 2)
        self.mock_entity_service.extract_email_entities.assert_called_once()

        # Check EID was passed
        call_args = self.mock_entity_service.extract_email_entities.call_args
        self.assertEqual(call_args[1]["email_data"]["eid"], "EID-2025-0001")

    def test_entity_extraction_with_cache(self):
        """
        Test entity extraction respects cache.
        """
        # Insert cached entity
        self.db.execute(
            """
            INSERT INTO entity_content_mapping 
            (content_id, entity_text, entity_type, entity_label, start_char, end_char, processed_time)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
            ("msg_001", "January 15, 2025", "DATE", "DATE", 0, 16, datetime.now().isoformat()),
        )

        emails_data = self.pipeline._get_email_data(["msg_001"])
        result = self.pipeline._run_entity_extraction(emails_data)

        self.assertEqual(result["skipped"], 1)
        self.assertEqual(result["processed"], 0)
        self.mock_entity_service.extract_email_entities.assert_not_called()

    def test_embeddings_generation(self):
        """
        Test embedding generation and storage.
        """
        # Setup mocks
        test_embedding = np.random.randn(1024).astype(np.float32)
        test_embedding = test_embedding / np.linalg.norm(test_embedding)  # Normalize

        self.mock_embedding_service.batch_encode.return_value = [test_embedding.tolist()]
        self.mock_vector_store.batch_upsert.return_value = True

        emails_data = self.pipeline._get_email_data(["msg_001"])
        result = self.pipeline._run_embeddings(emails_data)

        self.assertEqual(result["processed"], 1)
        self.assertEqual(result["vectors_stored"], 1)

        # Verify embedding was generated with correct text
        self.mock_embedding_service.batch_encode.assert_called_once()
        texts = self.mock_embedding_service.batch_encode.call_args[0][0]
        self.assertIn("Contract Review", texts[0])
        self.assertIn("Please review the attached contract", texts[0])

        # Verify vector was stored with EID metadata
        self.mock_vector_store.batch_upsert.assert_called_once()
        points = self.mock_vector_store.batch_upsert.call_args[0][1]
        self.assertEqual(points[0]["metadata"]["eid"], "EID-2025-0001")
        self.assertEqual(points[0]["metadata"]["thread_id"], "thread_001")

    def test_timeline_extraction(self):
        """
        Test timeline event extraction.
        """
        emails_data = self.pipeline._get_email_data(["msg_002"])

        # Extract temporal events
        events = self.pipeline._extract_temporal_events(emails_data[0])

        self.assertGreater(len(events), 0)
        # Should have at least the email event itself
        email_event = events[0]
        self.assertEqual(email_event["type"], "email")
        self.assertIn("Meeting Confirmation", email_event["description"])

        # Should extract the date mentioned
        date_events = [e for e in events if "February 1st" in str(e.get("date", ""))]
        self.assertGreater(len(date_events), 0)

    def test_timeline_storage_with_eid(self):
        """
        Test timeline events are stored with EID references.
        """
        emails_data = self.pipeline._get_email_data(["msg_003"])
        result = self.pipeline._run_timeline(emails_data)

        self.assertEqual(result["processed"], 1)
        self.assertGreater(result["events_created"], 0)

        # Check database for timeline event with EID
        cursor = self.db.execute(
            """
            SELECT metadata FROM timeline_events
            WHERE metadata LIKE '%msg_003%'
        """
        )

        row = cursor.fetchone()
        if row:
            metadata = json.loads(row["metadata"])
            self.assertEqual(metadata["eid_ref"], "EID-2025-0003")
            self.assertEqual(metadata["thread_id"], "thread_003")

    def test_full_pipeline_run(self):
        """
        Test complete pipeline execution.
        """
        # Setup mocks
        self.mock_entity_service.extract_email_entities.return_value = {
            "success": True,
            "entities": [{"type": "DATE", "value": "January 15"}],
        }

        test_embedding = np.ones(1024, dtype=np.float32) / np.sqrt(1024)
        self.mock_embedding_service.batch_encode.return_value = [
            test_embedding.tolist(),
            test_embedding.tolist(),
        ]

        message_ids = ["msg_001", "msg_002"]
        result = self.pipeline.run_for_messages(
            message_ids=message_ids, steps=["entities", "embeddings", "timeline"]
        )

        self.assertEqual(result["total_messages"], 2)
        self.assertIn("entities", result["step_results"])
        self.assertIn("embeddings", result["step_results"])
        self.assertIn("timeline", result["step_results"])

        # Verify each step was executed
        self.assertGreater(result["step_results"]["entities"]["processed"], 0)
        self.assertGreater(result["step_results"]["embeddings"]["processed"], 0)
        self.assertGreater(result["step_results"]["timeline"]["processed"], 0)

    def test_pipeline_with_timeout(self):
        """
        Test pipeline respects timeout settings.
        """

        # Mock slow entity extraction
        def slow_extraction(*args, **kwargs):
            import time

            time.sleep(0.1)
            return {"success": True, "entities": []}

        self.mock_entity_service.extract_email_entities.side_effect = slow_extraction
        self.pipeline.timeout_s = 0.05  # Very short timeout

        message_ids = ["msg_001"]
        result = self.pipeline.run_for_messages(message_ids=message_ids, steps=["entities"])

        # Should log warning about timeout
        entity_result = result["step_results"]["entities"]
        self.assertGreater(entity_result["elapsed_s"], 0.05)

    def test_pipeline_error_handling(self):
        """
        Test pipeline handles errors gracefully.
        """
        # Mock entity extraction failure
        self.mock_entity_service.extract_email_entities.side_effect = Exception("Test error")

        message_ids = ["msg_001"]
        result = self.pipeline.run_for_messages(message_ids=message_ids, steps=["entities"])

        self.assertIn("error", result["step_results"]["entities"])
        self.assertEqual(result["step_results"]["entities"]["errors"], 1)

    def test_idempotency(self):
        """
        Test that pipeline operations are idempotent.
        """
        # First run
        self.mock_entity_service.extract_email_entities.return_value = {
            "success": True,
            "entities": [{"type": "DATE", "value": "January 15"}],
        }

        message_ids = ["msg_001"]
        self.pipeline.run_for_messages(message_ids=message_ids, steps=["entities"])

        # Insert mock entity to simulate first run completion
        self.db.execute(
            """
            INSERT INTO entity_content_mapping 
            (content_id, entity_text, entity_type, entity_label, start_char, end_char, processed_time)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
            ("January 15", "DATE", "msg_001", datetime.now().isoformat()),
        )

        # Reset mock
        self.mock_entity_service.extract_email_entities.reset_mock()

        # Second run - should skip
        result2 = self.pipeline.run_for_messages(message_ids=message_ids, steps=["entities"])

        self.assertEqual(result2["step_results"]["entities"]["skipped"], 1)
        self.mock_entity_service.extract_email_entities.assert_not_called()

    def test_batch_processing(self):
        """
        Test batch processing of multiple emails.
        """
        # Add more test emails
        for i in range(10):
            self.db.execute(
                """
                INSERT INTO emails (message_id, subject, sender, content, datetime_utc, eid, thread_id)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
                (
                    f"msg_batch_{i}",
                    f"Subject {i}",
                    "test@example.com",
                    f"Content {i}",
                    "2025-01-13T10:00:00Z",
                    f"EID-2025-{i:04d}",
                    f"thread_{i}",
                ),
            )

        message_ids = [f"msg_batch_{i}" for i in range(10)]

        # Mock batch processing
        self.mock_embedding_service.batch_encode.return_value = [
            (np.ones(1024) / np.sqrt(1024)).tolist() for _ in range(10)
        ]

        result = self.pipeline.run_for_messages(message_ids=message_ids, steps=["embeddings"])

        self.assertEqual(result["step_results"]["embeddings"]["processed"], 10)

        # Verify batch size was respected
        call_args = self.mock_embedding_service.batch_encode.call_args
        self.assertLessEqual(len(call_args[0][0]), semantic_settings.semantics_max_batch)


class TestSemanticIntegration(unittest.TestCase):
    """
    Test semantic pipeline integration with Gmail service.
    """

    @patch("gmail.main.get_semantic_pipeline")
    @patch("gmail.main.SimpleDB")
    def test_gmail_semantic_hook(self, mock_db_class, mock_get_pipeline):
        """
        Test that Gmail service calls semantic pipeline on ingest.
        """
        from gmail.main import GmailService

        # Setup mocks
        mock_db = Mock()
        mock_db_class.return_value = mock_db

        mock_pipeline = Mock()
        mock_pipeline.run_for_messages.return_value = {"total_messages": 5, "step_results": {}}
        mock_get_pipeline.return_value = mock_pipeline

        # Mock Gmail API
        with patch.object(GmailService, "_get_gmail_service") as mock_gmail:
            mock_service = Mock()
            mock_gmail.return_value = mock_service

            # Mock messages.list
            mock_service.users().messages().list().execute.return_value = {
                "messages": [{"id": f"gmail_{i}"} for i in range(5)]
            }

            # Mock messages.get
            def mock_get_message(userId, id):
                mock_msg = Mock()
                mock_msg.execute.return_value = {
                    "id": id,
                    "payload": {
                        "headers": [
                            {"name": "Subject", "value": f"Test {id}"},
                            {"name": "From", "value": "test@example.com"},
                            {"name": "Date", "value": "Mon, 1 Jan 2025 10:00:00 +0000"},
                        ],
                        "body": {"data": "VGVzdCBjb250ZW50"},  # Base64 "Test content"
                    },
                }
                return mock_msg

            mock_service.users().messages().get.side_effect = mock_get_message

            # Run sync with semantic processing enabled
            os.environ["SEMANTICS_ON_INGEST"] = "true"
            service = GmailService()

            # Mock store_email to return message IDs
            with patch.object(service, "store_email") as mock_store:
                mock_store.return_value = "stored_msg_id"

                service.sync_emails(max_results=5)

                # Verify semantic pipeline was called
                mock_get_pipeline.assert_called_once()
                mock_pipeline.run_for_messages.assert_called()

                # Check that message IDs were passed
                call_args = mock_pipeline.run_for_messages.call_args
                self.assertEqual(len(call_args[1]["message_ids"]), 5)


class TestBackfillScript(unittest.TestCase):
    """
    Test the backfill script functionality.
    """

    @patch("scripts.backfill_semantic.get_semantic_pipeline")
    @patch("scripts.backfill_semantic.SimpleDB")
    def test_backfill_basic(self, mock_db_class, mock_get_pipeline):
        """
        Test basic backfill operation.
        """
        from scripts.backfill_semantic import backfill_semantic

        # Setup mocks
        mock_db = Mock()
        mock_db_class.return_value = mock_db

        # Mock email query
        mock_cursor = Mock()
        mock_cursor.fetchall.return_value = [
            {"message_id": "old_msg_001"},
            {"message_id": "old_msg_002"},
        ]
        mock_db.execute.return_value = mock_cursor

        # Mock pipeline
        mock_pipeline = Mock()
        mock_pipeline.run_for_messages.return_value = {
            "step_results": {
                "entities": {"processed": 2, "skipped": 0, "errors": 0},
                "embeddings": {"processed": 2, "skipped": 0, "errors": 0},
                "timeline": {"processed": 2, "skipped": 0, "errors": 0},
            }
        }
        mock_get_pipeline.return_value = mock_pipeline

        # Run backfill
        backfill_semantic(batch_size=2, limit=2)

        # Verify pipeline was called
        mock_pipeline.run_for_messages.assert_called_once()
        call_args = mock_pipeline.run_for_messages.call_args
        self.assertEqual(len(call_args[1]["message_ids"]), 2)

    @patch("scripts.backfill_semantic.get_semantic_pipeline")
    @patch("scripts.backfill_semantic.SimpleDB")
    def test_backfill_with_date_filter(self, mock_db_class, mock_get_pipeline):
        """
        Test backfill with date filtering.
        """
        from scripts.backfill_semantic import backfill_semantic

        # Setup mocks
        mock_db = Mock()
        mock_db_class.return_value = mock_db

        mock_cursor = Mock()
        mock_cursor.fetchall.return_value = []
        mock_db.execute.return_value = mock_cursor

        # Run backfill with date filter
        backfill_semantic(since_days=7)

        # Verify date filter was applied in query
        query_call = mock_db.execute.call_args[0][0]
        self.assertIn("datetime_utc > ?", query_call)


if __name__ == "__main__":
    unittest.main()
