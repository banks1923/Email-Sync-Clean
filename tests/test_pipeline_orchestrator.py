"""Tests for Pipeline Orchestrator

Tests document lifecycle, metadata tracking, and error handling.
"""

import json
import shutil

# Add parent directory to path
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from infrastructure.pipelines import get_pipeline_orchestrator, reset_pipeline_orchestrator
from infrastructure.pipelines.formats import get_document_formatter
from infrastructure.pipelines.orchestrator import PipelineOrchestrator
from infrastructure.pipelines.processors import EmailProcessor, PDFProcessor, get_processor


class TestPipelineOrchestrator(unittest.TestCase):
    """Test PipelineOrchestrator functionality."""

    def setUp(self):
        """Set up test environment."""
        # Create temporary directory
        self.temp_dir = tempfile.mkdtemp()
        self.data_dir = Path(self.temp_dir) / "data"

        # Reset singleton
        reset_pipeline_orchestrator()

        # Create orchestrator with temp directory
        self.orchestrator = PipelineOrchestrator(str(self.data_dir))

    def tearDown(self):
        """Clean up test environment."""
        # Remove temporary directory
        shutil.rmtree(self.temp_dir, ignore_errors=True)

        # Reset singleton
        reset_pipeline_orchestrator()

    def test_folder_structure_creation(self):
        """Test that pipeline folders are created correctly."""
        # Check all stage directories exist
        for stage in ["raw", "staged", "processed", "quarantine", "export"]:
            stage_dir = self.data_dir / stage
            self.assertTrue(stage_dir.exists(), f"Stage directory {stage} not created")
            self.assertTrue(stage_dir.is_dir(), f"Stage {stage} is not a directory")

    def test_pipeline_id_generation(self):
        """Test unique pipeline ID generation."""
        # Generate multiple IDs
        id1 = self.orchestrator.generate_pipeline_id()
        id2 = self.orchestrator.generate_pipeline_id()
        id3 = self.orchestrator.generate_pipeline_id()

        # Check uniqueness
        self.assertNotEqual(id1, id2)
        self.assertNotEqual(id2, id3)
        self.assertNotEqual(id1, id3)

        # Check format (UUID)
        self.assertEqual(len(id1), 36)  # UUID with hyphens
        self.assertIn("-", id1)

    def test_metadata_tracking(self):
        """Test metadata creation and updates."""
        pipeline_id = self.orchestrator.generate_pipeline_id()

        # Create metadata
        metadata = {"title": "Test Document", "content_type": "test", "author": "Test Author"}

        meta_path = self.orchestrator.create_metadata(pipeline_id, "raw", metadata)
        self.assertTrue(Path(meta_path).exists())

        # Read metadata
        retrieved = self.orchestrator.get_metadata(pipeline_id, "raw")
        self.assertIsNotNone(retrieved)
        self.assertEqual(retrieved["title"], "Test Document")
        self.assertEqual(retrieved["pipeline_id"], pipeline_id)
        self.assertIn("created_at", retrieved)

        # Update metadata
        updates = {"status": "processing", "word_count": 100}
        success = self.orchestrator.update_metadata(pipeline_id, "raw", updates)
        self.assertTrue(success)

        # Verify updates
        updated = self.orchestrator.get_metadata(pipeline_id, "raw")
        self.assertEqual(updated["status"], "processing")
        self.assertEqual(updated["word_count"], 100)
        self.assertIn("updated_at", updated)

    def test_document_lifecycle(self):
        """Test moving documents through pipeline stages."""
        pipeline_id = self.orchestrator.generate_pipeline_id()

        # Save document to raw
        content = "This is a test document."
        saved_id = self.orchestrator.save_document_to_stage(
            content=content,
            filename="test.txt",
            stage="raw",
            pipeline_id=pipeline_id,
            metadata={"content_type": "text"},
        )

        self.assertEqual(saved_id, pipeline_id)

        # Check document exists in raw
        raw_file = self.data_dir / "raw" / f"{pipeline_id}_test.txt"
        self.assertTrue(raw_file.exists())

        # Move to staged
        success = self.orchestrator.move_to_stage(pipeline_id, "raw", "staged")
        self.assertTrue(success)

        # Check document moved
        self.assertFalse(raw_file.exists())
        staged_file = self.data_dir / "staged" / f"{pipeline_id}_test.txt"
        self.assertTrue(staged_file.exists())

        # Move to processed
        success = self.orchestrator.move_to_stage(pipeline_id, "staged", "processed")
        self.assertTrue(success)

        # Check in processed
        self.assertFalse(staged_file.exists())
        processed_file = self.data_dir / "processed" / f"{pipeline_id}_test.txt"
        self.assertTrue(processed_file.exists())

    def test_error_quarantine(self):
        """Test document quarantine on error."""
        pipeline_id = self.orchestrator.generate_pipeline_id()

        # Save document to raw
        self.orchestrator.save_document_to_stage(
            content="Error document", filename="error.txt", stage="raw", pipeline_id=pipeline_id
        )

        # Quarantine with error info
        error_info = {
            "error": "validation_failed",
            "message": "Invalid document format",
            "timestamp": "2025-08-16T12:00:00Z",
        }

        success = self.orchestrator.quarantine_document(pipeline_id, "raw", error_info)
        self.assertTrue(success)

        # Check document in quarantine
        quarantine_file = self.data_dir / "quarantine" / f"{pipeline_id}_error.txt"
        self.assertTrue(quarantine_file.exists())

        # Check error metadata
        metadata = self.orchestrator.get_metadata(pipeline_id, "quarantine")
        self.assertIsNotNone(metadata)
        self.assertEqual(metadata["status"], "quarantined")
        self.assertEqual(metadata["quarantined_from"], "raw")
        self.assertEqual(metadata["error_info"]["error"], "validation_failed")

    def test_unified_formats(self):
        """Test Markdown and JSON formatting."""
        formatter = get_document_formatter()

        # Test data
        pipeline_id = "test-123"
        title = "Test Document"
        content = "This is the document content.\n\nWith multiple paragraphs."
        metadata = {
            "date": "2025-08-16",
            "content_type": "test",
            "tags": ["test", "example"],
            "summary": "A test document",
        }
        intelligence = {
            "entities": {"persons": ["John Doe"], "organizations": ["Test Corp"]},
            "summary": {"tf_idf_keywords": {"test": 0.8, "document": 0.6}},
        }

        # Format document
        formatted = formatter.format_document(
            pipeline_id=pipeline_id,
            title=title,
            content=content,
            metadata=metadata,
            intelligence=intelligence,
        )

        # Check Markdown format
        self.assertIn("markdown", formatted)
        markdown = formatted["markdown"]
        self.assertIn("---", markdown)  # YAML frontmatter
        self.assertIn("pipeline_id: test-123", markdown)
        self.assertIn("# Test Document", markdown)
        self.assertIn("This is the document content", markdown)

        # Check JSON format
        self.assertIn("json", formatted)
        json_data = json.loads(formatted["json"])
        self.assertEqual(json_data["pipeline_id"], pipeline_id)
        self.assertIn("intelligence", json_data)
        self.assertEqual(json_data["intelligence"]["entities"]["persons"], ["John Doe"])

    def test_get_stage_stats(self):
        """Test getting document counts by stage."""
        # Add documents to different stages
        id1 = self.orchestrator.generate_pipeline_id()
        id2 = self.orchestrator.generate_pipeline_id()
        id3 = self.orchestrator.generate_pipeline_id()

        self.orchestrator.save_document_to_stage("doc1", "doc1.txt", "raw", id1)
        self.orchestrator.save_document_to_stage("doc2", "doc2.txt", "raw", id2)
        self.orchestrator.save_document_to_stage("doc3", "doc3.txt", "staged", id3)

        # Get stats
        stats = self.orchestrator.get_stage_stats()

        self.assertEqual(stats["raw"], 2)
        self.assertEqual(stats["staged"], 1)
        self.assertEqual(stats["processed"], 0)
        self.assertEqual(stats["quarantine"], 0)
        self.assertEqual(stats["export"], 0)

    def test_singleton_pattern(self):
        """Test that get_pipeline_orchestrator returns singleton."""
        # Get orchestrator twice
        orch1 = get_pipeline_orchestrator(str(self.data_dir))
        orch2 = get_pipeline_orchestrator(str(self.data_dir))

        # Should be same instance
        self.assertIs(orch1, orch2)

        # Reset and get new instance
        reset_pipeline_orchestrator()
        orch3 = get_pipeline_orchestrator(str(self.data_dir))

        # Should be different instance after reset
        self.assertIsNot(orch1, orch3)


class TestDocumentProcessors(unittest.TestCase):
    """Test document processor classes."""

    def test_email_processor(self):
        """Test EmailProcessor functionality."""
        processor = EmailProcessor()

        # Test email content
        content = """From: sender@example.com
To: recipient@example.com
Subject: Test Email
Date: 2025-08-16
Message-ID: <123@example.com>

This is the email body.
With multiple lines.
"""

        # Validate
        is_valid, error = processor.validate(content, {})
        self.assertTrue(is_valid)
        self.assertIsNone(error)

        # Process
        processed, metadata = processor.process(content, {})

        self.assertIn("This is the email body", processed)
        self.assertEqual(metadata["subject"], "Test Email")
        self.assertEqual(metadata["from"], "sender@example.com")
        self.assertEqual(metadata["content_type"], "email")
        self.assertIn("word_count", metadata)

    def test_pdf_processor(self):
        """Test PDFProcessor functionality."""
        processor = PDFProcessor()

        # Test PDF content
        content = """Legal Document Title

This is page 1 content.

Page 1

This is page 2 content.

Page 2
"""

        # Validate
        is_valid, error = processor.validate(content, {"filename": "test.pdf"})
        self.assertTrue(is_valid)

        # Process
        processed, metadata = processor.process(content, {"filename": "test.pdf"})

        self.assertIn("Legal Document Title", processed)
        self.assertEqual(metadata["content_type"], "pdf")
        self.assertEqual(metadata["extracted_title"], "Legal Document Title")

        # Should remove standalone page numbers
        self.assertNotIn("\nPage 1\n", processed)
        self.assertNotIn("\nPage 2\n", processed)

    def test_get_processor_factory(self):
        """Test get_processor factory function."""
        # Test valid types
        email_proc = get_processor("email")
        self.assertIsInstance(email_proc, EmailProcessor)

        pdf_proc = get_processor("pdf")
        self.assertIsInstance(pdf_proc, PDFProcessor)

        # Test invalid type
        with self.assertRaises(ValueError):
            get_processor("invalid")


if __name__ == "__main__":
    unittest.main()
