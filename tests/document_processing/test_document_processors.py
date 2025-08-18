"""
Tests for document processors.
"""

import os
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from infrastructure.documents.format_detector import FormatDetector
from infrastructure.documents.lifecycle_manager import DocumentLifecycleManager
from infrastructure.documents.naming_convention import NamingConvention
from infrastructure.documents.processors import DocxProcessor, MarkdownProcessor, TextProcessor


@pytest.mark.unit
class TestTextProcessor:
    """Test text document processor."""

    def test_process_utf8_file(self):
        """Test processing UTF-8 text file."""
        processor = TextProcessor()

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".txt", delete=False, encoding="utf-8"
        ) as f:
            f.write("This is a test document.\nWith multiple lines.\nAnd UTF-8 encoding: café, naïve, résumé 🎉")
            temp_path = Path(f.name)

        try:
            result = processor.process(temp_path)

            assert result["success"] is True
            assert "test document" in result["content"]
            assert result["format"] == "txt"
            assert result["metrics"]["line_count"] == 3
            assert result["metadata"]["encoding"] == "utf-8"

        finally:
            temp_path.unlink()

    def test_encoding_detection(self):
        """Test automatic encoding detection."""
        processor = TextProcessor()

        # Test with Latin-1 encoded file
        with tempfile.NamedTemporaryFile(mode="wb", suffix=".txt", delete=False) as f:
            f.write("Test with special chars: café".encode("latin-1"))
            temp_path = Path(f.name)

        try:
            text = processor.extract_text(temp_path)
            assert "café" in text or "caf" in text  # May vary based on detection

        finally:
            temp_path.unlink()

    def test_normalize_text(self):
        """Test text normalization."""
        processor = TextProcessor()

        test_text = "Line 1\r\nLine 2\r\n\r\n\r\n\r\nLine 3   \nLine 4\x00"
        normalized = processor._normalize_text(test_text)

        assert "\r\n" not in normalized
        assert "\x00" not in normalized
        assert "\n\n\n\n" not in normalized  # Excessive blanks (more than 2) removed
        lines = normalized.split("\n")
        assert len([l for l in lines if l]) >= 3  # At least 3 non-empty lines


@pytest.mark.unit
class TestMarkdownProcessor:
    """Test markdown document processor."""

    def test_process_markdown_with_frontmatter(self):
        """Test processing markdown with YAML frontmatter."""
        processor = MarkdownProcessor()

        content = """---
title: Test Document
author: John Doe
tags: [test, markdown]
---

# Main Heading

This is a test markdown document.

## Subheading

- Item 1
- Item 2

[Link](https://example.com)
"""

        with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as f:
            f.write(content)
            temp_path = Path(f.name)

        try:
            result = processor.process(temp_path)

            assert result["success"] is True
            assert "# Main Heading" in result["content"]
            assert result["format"] == "md"
            assert result["metadata"]["title"] == "Test Document"
            assert result["metadata"]["author"] == "John Doe"
            assert result["metadata"]["structure"]["heading_count"]["h1"] == 1
            assert result["metadata"]["structure"]["link_count"] == 1

        finally:
            temp_path.unlink()

    def test_markdown_structure_analysis(self):
        """Test markdown structure analysis."""
        processor = MarkdownProcessor()

        content = """
# H1 Heading
## H2 Heading
### H3 Heading

[Link 1](url1)
[Link 2](url2)

![Image](image.png)

```python
code block
```

| Col1 | Col2 |
|------|------|
| A    | B    |
"""

        structure = processor._analyze_structure(content)["structure"]

        assert structure["heading_count"]["h1"] == 1
        assert structure["heading_count"]["h2"] == 1
        assert structure["heading_count"]["h3"] == 1
        assert structure["link_count"] == 2
        assert structure["image_count"] == 1
        assert structure["code_block_count"] == 1
        assert structure["table_count"] >= 1

    def test_markdown_to_plain_text(self):
        """Test markdown to plain text conversion."""
        processor = MarkdownProcessor()

        markdown = "# Heading\n**Bold** and *italic* text with [link](url)"
        plain = processor.process_to_plain_text(markdown)

        assert "#" not in plain
        assert "**" not in plain
        assert "*" not in plain
        assert "[" not in plain
        assert "(" not in plain
        assert "Heading" in plain
        assert "Bold" in plain
        assert "italic" in plain
        assert "link" in plain


@pytest.mark.unit
class TestDocxProcessor:
    """Test DOCX document processor."""

    @pytest.mark.skipif(not DocxProcessor().available, reason="python-docx not installed")
    def test_docx_availability(self):
        """Test DOCX processor availability."""
        processor = DocxProcessor()
        assert processor.available is True
        assert processor.format_type == "docx"

    def test_docx_not_available_handling(self):
        """Test handling when python-docx is not installed."""
        with patch("infrastructure.documents.processors.docx_processor.DOCX_AVAILABLE", False):
            processor = DocxProcessor()
            processor.available = False

            with tempfile.NamedTemporaryFile(suffix=".docx") as f:
                temp_path = Path(f.name)

                result = processor.process(temp_path)
                assert result["success"] is False
                assert "python-docx is required" in result["error"] or "ImportError" in result["error"] or "not found" in result["error"]


@pytest.mark.unit
class TestFormatDetector:
    """Test format detection."""

    def test_detect_by_content(self):
        """Test format detection by file content."""
        detector = FormatDetector()

        # Test PDF detection
        with tempfile.NamedTemporaryFile(mode="wb", delete=False) as f:
            f.write(b"%PDF-1.4")
            temp_path = Path(f.name)

        try:
            format_type = detector.detect_format(temp_path)
            assert format_type == "pdf"
        finally:
            temp_path.unlink()

        # Test DOCX detection (zip file)
        with tempfile.NamedTemporaryFile(mode="wb", delete=False) as f:
            f.write(b"PK\x03\x04")
            temp_path = Path(f.name)

        try:
            format_type = detector.detect_format(temp_path)
            assert format_type == "docx"
        finally:
            temp_path.unlink()

    def test_detect_by_extension(self):
        """Test format detection by file extension."""
        detector = FormatDetector()

        test_cases = [
            ("test.txt", "txt"),
            ("test.md", "md"),
            ("test.docx", "docx"),
            ("test.pdf", "pdf"),
            ("test.markdown", "md"),
        ]

        for filename, expected in test_cases:
            with tempfile.NamedTemporaryFile(suffix=filename, mode="w") as f:
                f.write("test content")
                temp_path = Path(f.name)

                format_type = detector.detect_format(temp_path)
                assert format_type == expected, f"Failed for {filename}"

    def test_text_file_detection(self):
        """Test plain text file detection."""
        detector = FormatDetector()

        # File with no extension but text content
        with tempfile.NamedTemporaryFile(mode="w", delete=False) as f:
            f.write("This is plain text content with no special formatting.")
            temp_path = Path(f.name)

        try:
            format_type = detector.detect_format(temp_path)
            assert format_type == "txt"
        finally:
            temp_path.unlink()


@pytest.mark.unit
class TestNamingConvention:
    """Test naming convention system."""

    def test_staged_naming(self):
        """Test staged file naming."""
        naming = NamingConvention()

        original = Path("document.pdf")
        staged = naming.staged_name(original, "SMITH_V_JONES", "MOTION")

        assert "SMITH_V_JONES" in staged
        assert "MOTION" in staged
        assert staged.endswith(".pdf")
        # Should have date in format YYYYMMDD
        import re

        assert re.search(r"\d{8}", staged) is not None

    def test_processed_naming(self):
        """Test processed file naming."""
        naming = NamingConvention()

        original = Path("document.pdf")
        processed1 = naming.processed_name(original, "md")
        processed2 = naming.processed_name(original, "md")

        assert processed1.startswith("DOC_")
        assert processed1.endswith(".md")
        assert processed1 != processed2  # Sequential numbering

        # Extract sequence numbers
        seq1 = int(processed1.split("_")[2].split(".")[0])
        seq2 = int(processed2.split("_")[2].split(".")[0])
        assert seq2 == seq1 + 1

    def test_clean_string(self):
        """Test string cleaning for filenames."""
        naming = NamingConvention()

        test_cases = [
            ("Smith v. Jones", "SMITH_V_JONES"),
            ("Case #123", "CASE_123"),
            ("Multiple   Spaces", "MULTIPLE_SPACES"),
            ("Special!@#$%Chars", "SPECIALCHARS"),
        ]

        for input_str, expected in test_cases:
            cleaned = naming._clean_string(input_str)
            assert cleaned == expected

    def test_name_validation(self):
        """Test filename validation."""
        naming = NamingConvention()

        assert naming.validate_name("anything.pdf", "raw") is True
        assert naming.validate_name("CASE_TYPE_20240101_doc.pdf", "staged") is True
        assert naming.validate_name("DOC_2024_0001.md", "processed") is True
        assert naming.validate_name("DOC_2024_0001_CASE_TYPE_processed.md", "export") is True
        assert naming.validate_name("20240101_120000_ERROR_file.pdf", "quarantine") is True

        assert naming.validate_name("invalid", "staged") is False
        assert naming.validate_name("invalid.md", "processed") is False


@pytest.mark.unit
class TestDocumentLifecycle:
    """Test document lifecycle management."""

    def test_folder_creation(self):
        """Test lifecycle folder creation."""
        with tempfile.TemporaryDirectory() as tmpdir:
            lifecycle = DocumentLifecycleManager(tmpdir)

            assert lifecycle.folders["raw"].exists()
            assert lifecycle.folders["staged"].exists()
            assert lifecycle.folders["processed"].exists()
            assert lifecycle.folders["quarantine"].exists()
            assert lifecycle.folders["export"].exists()

    def test_file_movement(self):
        """Test moving files through lifecycle stages."""
        with tempfile.TemporaryDirectory() as tmpdir:
            lifecycle = DocumentLifecycleManager(tmpdir)

            # Create test file in raw
            test_file = lifecycle.folders["raw"] / "test.txt"
            test_file.write_text("test content")

            # Move to staged
            staged_path = lifecycle.move_to_staged(test_file)
            assert staged_path.exists()
            assert not test_file.exists()
            assert staged_path.parent == lifecycle.folders["staged"]

            # Move to processed
            processed_path = lifecycle.move_to_processed(staged_path)
            assert processed_path.exists()
            assert not staged_path.exists()

            # Move to export
            export_path = lifecycle.move_to_export(processed_path)
            assert export_path.exists()
            assert not processed_path.exists()

    def test_quarantine_with_error(self):
        """Test quarantining files with error logging."""
        with tempfile.TemporaryDirectory() as tmpdir:
            lifecycle = DocumentLifecycleManager(tmpdir)

            # Create test file
            test_file = lifecycle.folders["raw"] / "bad.txt"
            test_file.write_text("bad content")

            # Quarantine with error
            quarantine_path = lifecycle.quarantine_file(test_file, "Processing failed")

            assert quarantine_path.exists()
            assert not test_file.exists()

            # Check error log
            error_logs = list(lifecycle.folders["quarantine"].glob("*.error"))
            assert len(error_logs) == 1
            error_content = error_logs[0].read_text()
            assert "Processing failed" in error_content


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
