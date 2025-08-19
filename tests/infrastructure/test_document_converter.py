"""
Tests for DocumentConverter - Simple, direct tests following CLAUDE.md principles.

Tests various PDF types and scenarios for PDF-to-markdown conversion.
"""

import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

try:
    from infrastructure.documents.document_converter import (
        DocumentConverter,
        get_document_converter,
    )
    CONVERTER_AVAILABLE = True
except ImportError:
    CONVERTER_AVAILABLE = False

# Skip all tests if DocumentConverter not available
pytestmark = pytest.mark.skipif(
    not CONVERTER_AVAILABLE, 
    reason="DocumentConverter not available - PDF infrastructure required"
)


class TestDocumentConverter:
    """Test suite for DocumentConverter."""

    @pytest.fixture
    def temp_dir(self):
        """Create temporary directory for test files."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)

    @pytest.fixture
    def sample_pdf_path(self, temp_dir):
        """Create a sample PDF file path for testing."""
        pdf_path = temp_dir / "sample.pdf"
        # Create minimal PDF content for testing
        pdf_path.write_bytes(b"%PDF-1.4\n%Sample PDF for testing\n%%EOF")
        return pdf_path

    @pytest.fixture
    def mock_converter(self):
        """Create DocumentConverter with mocked dependencies."""
        with patch('infrastructure.documents.document_converter.PDFValidator') as mock_validator, \
             patch('infrastructure.documents.document_converter.EnhancedPDFStorage'), \
             patch('infrastructure.documents.document_converter.OCRCoordinator'), \
             patch('infrastructure.documents.document_converter.EnhancedPDFProcessor'):
            
            # Configure mocks
            mock_validator.return_value.validate_pdf_file.return_value = {"success": True}
            mock_validator.return_value.check_resource_limits.return_value = {"success": True}
            
            converter = DocumentConverter()
            return converter

    def test_initialization(self):
        """Test DocumentConverter initialization."""
        if CONVERTER_AVAILABLE:
            converter = DocumentConverter()
            assert converter.validator is not None
            assert converter.storage is not None
            assert converter.ocr_coordinator is not None
            assert converter.processor is not None

    def test_get_document_converter_factory(self):
        """Test the factory function."""
        converter = get_document_converter()
        if CONVERTER_AVAILABLE:
            assert isinstance(converter, DocumentConverter)
        else:
            assert converter is None

    def test_validate_setup(self, mock_converter):
        """Test setup validation."""
        result = mock_converter.validate_setup()
        
        assert "pdf_available" in result
        assert "frontmatter_available" in result
        assert "dependencies" in result
        assert "ready" in result

    def test_calculate_file_hash(self, mock_converter, sample_pdf_path):
        """Test file hash calculation."""
        file_hash = mock_converter._calculate_file_hash(sample_pdf_path)
        
        # Should return a valid SHA-256 hash (64 hex characters)
        assert len(file_hash) == 64
        assert all(c in '0123456789abcdef' for c in file_hash)

    def test_clean_text_for_markdown(self, mock_converter):
        """Test text cleaning for markdown."""
        # Test basic text cleaning
        messy_text = "  Line 1  \n\n\n  Line 2  \n\n\n\n\nLine 3  "
        cleaned = mock_converter._clean_text_for_markdown(messy_text)
        
        expected = "Line 1\n\nLine 2\n\nLine 3"
        assert cleaned == expected

    def test_clean_text_empty_input(self, mock_converter):
        """Test text cleaning with empty input."""
        assert mock_converter._clean_text_for_markdown("") == ""
        assert mock_converter._clean_text_for_markdown(None) == ""

    def test_clean_text_whitespace_only(self, mock_converter):
        """Test text cleaning with whitespace-only input."""
        whitespace_text = "   \n\n   \n   "
        cleaned = mock_converter._clean_text_for_markdown(whitespace_text)
        assert cleaned == ""

    def test_format_as_markdown_with_metadata(self, mock_converter):
        """Test markdown formatting with metadata."""
        text = "Sample content"
        metadata = {
            "title": "Test Document",
            "author": "Test Author",
            "processed_at": "2025-01-01T00:00:00"
        }
        
        result = mock_converter._format_as_markdown(text, metadata)
        
        # Should contain YAML frontmatter
        assert "---" in result
        assert "title: Test Document" in result
        assert "author: Test Author" in result
        assert "Sample content" in result

    def test_format_as_markdown_without_metadata(self, mock_converter):
        """Test markdown formatting without metadata."""
        text = "Sample content"
        result = mock_converter._format_as_markdown(text)
        
        # Should not contain frontmatter
        assert "---" not in result
        assert result == "Sample content"

    def test_generate_metadata(self, mock_converter, sample_pdf_path):
        """Test metadata generation."""
        extraction_result = {
            "extraction_method": "pypdf2",
            "page_count": 1,
            "legal_metadata": {"case_number": "TEST-001"}
        }
        
        metadata = mock_converter._generate_metadata(sample_pdf_path, extraction_result)
        
        # Check required metadata fields
        assert "title" in metadata
        assert "original_filename" in metadata
        assert "file_hash" in metadata
        assert "file_size_bytes" in metadata
        assert "file_size_mb" in metadata
        assert "page_count" in metadata
        assert "extraction_method" in metadata
        assert "processed_at" in metadata
        assert "document_type" in metadata
        
        # Check specific values
        assert metadata["title"] == "sample"
        assert metadata["original_filename"] == "sample.pdf"
        assert metadata["page_count"] == 1
        assert metadata["extraction_method"] == "pypdf2"
        assert metadata["document_type"] == "pdf"
        assert metadata["ocr_required"] is False

    def test_generate_metadata_with_ocr(self, mock_converter, sample_pdf_path):
        """Test metadata generation with OCR data."""
        extraction_result = {
            "extraction_method": "ocr",
            "page_count": 2,
            "ocr_confidence": 0.95,
            "legal_metadata": {}
        }
        
        metadata = mock_converter._generate_metadata(sample_pdf_path, extraction_result)
        
        assert metadata["extraction_method"] == "ocr"
        assert metadata["ocr_required"] is True
        assert metadata["ocr_confidence"] == 0.95
        assert metadata["page_count"] == 2

    @patch('infrastructure.documents.document_converter.DocumentConverter._extract_text_from_pdf')
    def test_convert_pdf_to_markdown_success(self, mock_extract, mock_converter, sample_pdf_path, temp_dir):
        """Test successful PDF to markdown conversion."""
        # Mock text extraction
        mock_extract.return_value = {
            "success": True,
            "text": "Sample PDF content for testing.",
            "extraction_method": "pypdf2",
            "page_count": 1,
            "legal_metadata": {}
        }
        
        output_path = temp_dir / "output.md"
        result = mock_converter.convert_pdf_to_markdown(sample_pdf_path, output_path)
        
        assert result["success"] is True
        assert result["input_file"] == str(sample_pdf_path)
        assert result["output_file"] == str(output_path)
        assert "metadata" in result
        assert "extraction_method" in result
        assert "page_count" in result
        assert "file_size_mb" in result
        
        # Check that output file was created
        assert output_path.exists()
        
        # Check file content
        content = output_path.read_text()
        assert "---" in content  # YAML frontmatter
        assert "Sample PDF content for testing." in content

    @patch('infrastructure.documents.document_converter.DocumentConverter._extract_text_from_pdf')
    def test_convert_pdf_to_markdown_extraction_failure(self, mock_extract, mock_converter, sample_pdf_path):
        """Test conversion with text extraction failure."""
        mock_extract.return_value = {
            "success": False,
            "error": "Text extraction failed"
        }
        
        result = mock_converter.convert_pdf_to_markdown(sample_pdf_path)
        
        assert result["success"] is False
        assert "Text extraction failed" in result["error"]

    def test_convert_pdf_to_markdown_validation_failure(self, temp_dir):
        """Test conversion with PDF validation failure."""
        with patch('infrastructure.documents.document_converter.PDFValidator') as mock_validator_class:
            mock_validator = Mock()
            mock_validator.validate_pdf_file.return_value = {
                "success": False,
                "error": "Invalid PDF file"
            }
            mock_validator_class.return_value = mock_validator
            
            converter = DocumentConverter()
            
            pdf_path = temp_dir / "invalid.pdf"
            pdf_path.write_text("Not a PDF")
            
            result = converter.convert_pdf_to_markdown(pdf_path)
            
            assert result["success"] is False
            assert "Invalid PDF file" in result["error"]

    @patch('infrastructure.documents.document_converter.DocumentConverter.convert_pdf_to_markdown')
    def test_convert_directory_success(self, mock_convert, mock_converter, temp_dir):
        """Test directory conversion success."""
        # Create sample PDF files
        pdf1 = temp_dir / "doc1.pdf"
        pdf2 = temp_dir / "doc2.pdf"
        pdf1.write_bytes(b"%PDF-1.4\n%%EOF")
        pdf2.write_bytes(b"%PDF-1.4\n%%EOF")
        
        # Mock individual conversions
        mock_convert.side_effect = [
            {"success": True, "output_file": "doc1.md"},
            {"success": True, "output_file": "doc2.md"}
        ]
        
        result = mock_converter.convert_directory(temp_dir)
        
        assert result["success"] is True
        assert result["total_files"] == 2
        assert result["success_count"] == 2
        assert result["error_count"] == 0
        assert len(result["results"]) == 2

    def test_convert_directory_no_pdfs(self, mock_converter, temp_dir):
        """Test directory conversion with no PDF files."""
        # Create non-PDF files
        (temp_dir / "doc.txt").write_text("Not a PDF")
        
        result = mock_converter.convert_directory(temp_dir)
        
        assert result["success"] is True
        assert result["total_files"] == 0
        assert "No PDF files found" in result["message"]

    def test_convert_directory_nonexistent(self, mock_converter):
        """Test directory conversion with non-existent directory."""
        nonexistent_dir = Path("/nonexistent/directory")
        
        result = mock_converter.convert_directory(nonexistent_dir)
        
        assert result["success"] is False
        assert "Directory not found" in result["error"]

    def test_extract_text_from_pdf_ocr(self, mock_converter, sample_pdf_path):
        """Test text extraction using OCR."""
        # Mock the OCR coordinator
        mock_converter.ocr_coordinator.process_pdf_with_ocr.return_value = {
            "success": True,
            "ocr_used": True,
            "text": "OCR extracted text",
            "page_count": 1,
            "confidence": 0.92,
            "metadata": {"detected_language": "en"}
        }
        
        result = mock_converter._extract_text_from_pdf(sample_pdf_path)
        
        assert result["success"] is True
        assert result["text"] == "OCR extracted text"
        assert result["extraction_method"] == "ocr"
        assert result["ocr_confidence"] == 0.92
        assert "detected_language" in result["legal_metadata"]

    def test_extract_text_from_pdf_regular(self, mock_converter, sample_pdf_path):
        """Test text extraction using regular method."""
        # OCR coordinator says no OCR needed
        mock_converter.ocr_coordinator.process_pdf_with_ocr.return_value = {
            "success": True,
            "ocr_used": False
        }
        
        # Mock processor response
        mock_converter.processor.extract_and_chunk_pdf.return_value = {
            "success": True,
            "chunks": [
                {"text": "Chunk 1 text"},
                {"text": "Chunk 2 text"}
            ]
        }
        
        result = mock_converter._extract_text_from_pdf(sample_pdf_path)
        
        assert result["success"] is True
        assert result["text"] == "Chunk 1 text\n\nChunk 2 text"
        assert result["extraction_method"] == "pypdf2"
        assert "ocr_confidence" not in result

    def test_text_cleaning_edge_cases(self, mock_converter):
        """Test text cleaning with edge cases."""
        # Test with special characters
        text_with_special = "Line 1 & \"quotes\" & 'apostrophes'\nLine 2 <html> tags"
        cleaned = mock_converter._clean_text_for_markdown(text_with_special)
        
        # Should preserve special characters but clean whitespace
        assert "Line 1 & \"quotes\" & 'apostrophes'" in cleaned
        assert "Line 2 <html> tags" in cleaned

    def test_metadata_generation_error_handling(self, mock_converter):
        """Test metadata generation with file errors."""
        nonexistent_file = Path("/nonexistent/file.pdf")
        extraction_result = {"extraction_method": "test"}
        
        # Should not crash and return minimal metadata
        metadata = mock_converter._generate_metadata(nonexistent_file, extraction_result)
        
        assert "title" in metadata
        assert "processed_at" in metadata
        # Hash should be "unknown" for non-existent file (check if exists first)
        if "file_hash" in metadata:
            assert metadata["file_hash"] == "unknown"

    def test_conversion_with_include_metadata_false(self, mock_converter, sample_pdf_path, temp_dir):
        """Test conversion without metadata."""
        with patch.object(mock_converter, '_extract_text_from_pdf') as mock_extract:
            mock_extract.return_value = {
                "success": True,
                "text": "Sample content",
                "extraction_method": "pypdf2",
                "page_count": 1,
                "legal_metadata": {}
            }
            
            output_path = temp_dir / "no_metadata.md"
            result = mock_converter.convert_pdf_to_markdown(
                sample_pdf_path, 
                output_path, 
                include_metadata=False
            )
            
            assert result["success"] is True
            
            # Check that output file contains no frontmatter
            content = output_path.read_text()
            assert "---" not in content
            assert content.strip() == "Sample content"

    def test_directory_conversion_recursive(self, mock_converter, temp_dir):
        """Test recursive directory conversion."""
        # Create subdirectory with PDF
        subdir = temp_dir / "subdir"
        subdir.mkdir()
        pdf_in_subdir = subdir / "subdoc.pdf"
        pdf_in_subdir.write_bytes(b"%PDF-1.4\n%%EOF")
        
        with patch.object(mock_converter, 'convert_pdf_to_markdown') as mock_convert:
            mock_convert.return_value = {"success": True, "output_file": "subdoc.md"}
            
            # Test non-recursive (should find 0 files)
            result = mock_converter.convert_directory(temp_dir, recursive=False)
            # Check the correct field based on implementation
            if "total_files" in result:
                assert result["total_files"] == 0
            else:
                # No PDFs found message
                assert "No PDF files found" in result.get("message", "")
            
            # Test recursive (should find 1 file)
            result = mock_converter.convert_directory(temp_dir, recursive=True)
            assert result["total_files"] == 1