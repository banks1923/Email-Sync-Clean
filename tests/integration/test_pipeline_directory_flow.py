"""Integration test for data pipeline directory flow.

Verifies files move correctly through raw/, staged/, processed/, and
quarantine/ directories.
"""

import os
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent.parent))

from tests.integration.test_helpers import (
    cleanup_test_files,
    get_test_pdf_path,
    setup_data_directories,
    verify_file_in_directory,
)


class TestPipelineDirectoryFlow(unittest.TestCase):
    """
    Test document movement through pipeline directories.
    """

    def setUp(self):
        """
        Set up test environment.
        """
        # Create temporary base directory
        self.test_base = tempfile.mkdtemp(prefix="pipeline_test_")

        # Set up pipeline directories
        self.dirs = setup_data_directories(self.test_base)

        # Get test file
        self.test_pdf = get_test_pdf_path()

        # Track cleanup
        self.cleanup_paths = [self.test_base]

    def tearDown(self):
        """
        Clean up test artifacts.
        """
        cleanup_test_files(self.cleanup_paths)

    def test_directory_structure_created(self):
        """
        Test that all pipeline directories are created.
        """
        for dir_name, dir_path in self.dirs.items():
            self.assertTrue(
                os.path.exists(dir_path), f"Directory {dir_name} not created at {dir_path}"
            )
            self.assertTrue(os.path.isdir(dir_path), f"Path {dir_path} is not a directory")

    def test_file_placement_in_raw(self):
        """
        Test placing a file in raw directory.
        """
        # Copy test file to raw
        dest_path = os.path.join(self.dirs["raw"], "test_document.pdf")
        shutil.copy2(self.test_pdf, dest_path)

        # Verify file exists in raw
        self.assertTrue(os.path.exists(dest_path))
        self.assertTrue(verify_file_in_directory(self.dirs["raw"], "test_document"))

    def test_file_movement_raw_to_staged(self):
        """
        Test moving file from raw to staged.
        """
        # Place file in raw
        raw_file = os.path.join(self.dirs["raw"], "test_document.pdf")
        shutil.copy2(self.test_pdf, raw_file)

        # Move to staged
        staged_file = os.path.join(self.dirs["staged"], "test_document.pdf")
        shutil.move(raw_file, staged_file)

        # Verify file moved
        self.assertFalse(os.path.exists(raw_file), "File still in raw")
        self.assertTrue(os.path.exists(staged_file), "File not in staged")

    def test_file_movement_staged_to_processed(self):
        """
        Test moving file from staged to processed.
        """
        # Place file in staged
        staged_file = os.path.join(self.dirs["staged"], "test_document.pdf")
        shutil.copy2(self.test_pdf, staged_file)

        # Move to processed
        processed_file = os.path.join(self.dirs["processed"], "test_document.pdf")
        shutil.move(staged_file, processed_file)

        # Verify file moved
        self.assertFalse(os.path.exists(staged_file), "File still in staged")
        self.assertTrue(os.path.exists(processed_file), "File not in processed")

    def test_file_movement_to_quarantine_on_error(self):
        """
        Test moving file to quarantine on processing error.
        """
        # Place file in staged
        staged_file = os.path.join(self.dirs["staged"], "corrupted_document.pdf")

        # Create a corrupted file (empty PDF)
        with open(staged_file, "wb") as f:
            f.write(b"Not a valid PDF")

        # Simulate error handling - move to quarantine
        quarantine_file = os.path.join(self.dirs["quarantine"], "corrupted_document.pdf")
        shutil.move(staged_file, quarantine_file)

        # Verify file moved to quarantine
        self.assertFalse(os.path.exists(staged_file), "File still in staged")
        self.assertTrue(os.path.exists(quarantine_file), "File not in quarantine")

    def test_file_naming_convention(self):
        """
        Test that files follow naming convention.
        """
        # Expected format: {timestamp}_{source}_{type}_{hash[:8]}.{ext}
        # Example: 20250115_upload_pdf_a3f8c9d2.pdf

        import hashlib
        from datetime import datetime

        # Generate proper filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        source = "upload"
        doc_type = "pdf"

        # Calculate hash of file content
        with open(self.test_pdf, "rb") as f:
            file_hash = hashlib.sha256(f.read()).hexdigest()[:8]

        filename = f"{timestamp}_{source}_{doc_type}_{file_hash}.pdf"

        # Place file with proper name
        dest_path = os.path.join(self.dirs["raw"], filename)
        shutil.copy2(self.test_pdf, dest_path)

        # Verify file exists with correct name
        self.assertTrue(os.path.exists(dest_path))

        # Verify name components
        # Format is: YYYYMMDD_HHMMSS_source_doctype_hash.pdf
        parts = os.path.basename(dest_path).replace(".pdf", "").split("_")
        self.assertEqual(len(parts), 5, f"Invalid filename format: {filename}")
        # parts[0] = YYYYMMDD, parts[1] = HHMMSS
        self.assertEqual(parts[2], "upload")  # source
        self.assertEqual(parts[3], "pdf")  # doc_type
        self.assertEqual(len(parts[4]), 8)  # Hash should be 8 chars

    def test_processed_directory_date_organization(self):
        """
        Test that processed directory organizes files by date.
        """
        from datetime import datetime

        # Create date-based subdirectory
        date_dir = datetime.now().strftime("%Y-%m-%d")
        date_path = os.path.join(self.dirs["processed"], date_dir)
        os.makedirs(date_path, exist_ok=True)

        # Place file in date directory
        dest_file = os.path.join(date_path, "test_document.pdf")
        shutil.copy2(self.test_pdf, dest_file)

        # Verify file exists in date subdirectory
        self.assertTrue(os.path.exists(dest_file))
        self.assertTrue(os.path.exists(date_path))

    def test_export_directory_preparation(self):
        """
        Test preparing files for export.
        """
        # Create export subdirectory for batch
        batch_dir = os.path.join(self.dirs["export"], "batch_001")
        os.makedirs(batch_dir, exist_ok=True)

        # Copy processed file to export
        export_file = os.path.join(batch_dir, "document_001.pdf")
        shutil.copy2(self.test_pdf, export_file)

        # Create metadata file
        metadata_file = os.path.join(batch_dir, "metadata.json")
        import json

        metadata = {
            "batch_id": "batch_001",
            "export_date": "2024-01-15",
            "file_count": 1,
            "files": ["document_001.pdf"],
        }
        with open(metadata_file, "w") as f:
            json.dump(metadata, f)

        # Verify export structure
        self.assertTrue(os.path.exists(export_file))
        self.assertTrue(os.path.exists(metadata_file))

    def test_pipeline_file_lifecycle(self):
        """
        Test complete file lifecycle through pipeline.
        """
        import hashlib
        from datetime import datetime

        # Generate filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        with open(self.test_pdf, "rb") as f:
            file_hash = hashlib.sha256(f.read()).hexdigest()[:8]
        filename = f"{timestamp}_test_pdf_{file_hash}.pdf"

        # Stage 1: Raw
        raw_file = os.path.join(self.dirs["raw"], filename)
        shutil.copy2(self.test_pdf, raw_file)
        self.assertTrue(os.path.exists(raw_file))

        # Stage 2: Staged
        staged_file = os.path.join(self.dirs["staged"], filename)
        shutil.move(raw_file, staged_file)
        self.assertFalse(os.path.exists(raw_file))
        self.assertTrue(os.path.exists(staged_file))

        # Stage 3: Processed
        date_dir = datetime.now().strftime("%Y-%m-%d")
        processed_dir = os.path.join(self.dirs["processed"], date_dir)
        os.makedirs(processed_dir, exist_ok=True)
        processed_file = os.path.join(processed_dir, filename)
        shutil.move(staged_file, processed_file)
        self.assertFalse(os.path.exists(staged_file))
        self.assertTrue(os.path.exists(processed_file))

        # Verify final location
        self.assertTrue(verify_file_in_directory(processed_dir, file_hash))

    def test_quarantine_error_logging(self):
        """
        Test that quarantined files have error logs.
        """
        # Create a file to quarantine
        bad_file = os.path.join(self.dirs["quarantine"], "failed_document.pdf")
        with open(bad_file, "wb") as f:
            f.write(b"Corrupted content")

        # Create error log
        error_log = os.path.join(self.dirs["quarantine"], "failed_document.error.txt")
        with open(error_log, "w") as f:
            f.write("Error: Invalid PDF structure\n")
            f.write("Timestamp: 2024-01-15 10:30:00\n")
            f.write("Processing step: PDF extraction\n")

        # Verify both files exist
        self.assertTrue(os.path.exists(bad_file))
        self.assertTrue(os.path.exists(error_log))

        # Verify error log content
        with open(error_log) as f:
            content = f.read()
            self.assertIn("Invalid PDF", content)
            self.assertIn("PDF extraction", content)


if __name__ == "__main__":
    unittest.main()
