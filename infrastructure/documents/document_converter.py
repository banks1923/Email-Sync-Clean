"""
DocumentConverter - Converts PDF files to well-formatted markdown with YAML frontmatter.

Simple, direct implementation following CLAUDE.md principles.
Leverages existing PDF service infrastructure for text extraction and validation.
"""

import hashlib
from datetime import datetime
from pathlib import Path
from typing import Any

import frontmatter
from loguru import logger

# PDF service factories - to be injected from higher layers
_pdf_service_factories = None
PDF_AVAILABLE = True

def set_pdf_service_factories(factories):
    """Inject PDF service factories from higher layers.
    
    Args:
        factories: Dict with keys: 'validator', 'storage', 'ocr_coordinator', 'processor'
    """
    global _pdf_service_factories
    _pdf_service_factories = factories
    logger.info("PDF service factories configured")


class DocumentConverter:
    """Converts PDF files to markdown with YAML frontmatter metadata."""

    def __init__(self, db_path: str = "emails.db"):
        """Initialize converter with PDF infrastructure."""
        if not PDF_AVAILABLE:
            raise ImportError("PDF infrastructure required for DocumentConverter")
        
        if not _pdf_service_factories:
            raise ImportError("PDF service factories not configured - must be injected from higher layer")
        
        # Use injected factories to create service instances
        self.validator = _pdf_service_factories['validator']()
        self.storage = _pdf_service_factories['storage'](db_path)
        self.ocr_coordinator = _pdf_service_factories['ocr_coordinator']()
        self.processor = _pdf_service_factories['processor']()
        logger.info("DocumentConverter initialized with injected PDF services")

    def convert_pdf_to_markdown(
        self, 
        pdf_path: Path, 
        output_path: Path | None = None,
        include_metadata: bool = True
    ) -> dict[str, Any]:
        """
        Convert PDF to markdown with YAML frontmatter.
        
        Args:
            pdf_path: Path to PDF file
            output_path: Optional output path for markdown file
            include_metadata: Whether to include YAML frontmatter
            
        Returns:
            Conversion result with success status and paths
        """
        try:
            # Validate PDF file
            validation_result = self.validator.validate_pdf_file(str(pdf_path))
            if not validation_result["success"]:
                return validation_result

            # Check resource limits
            resource_check = self.validator.check_resource_limits(str(pdf_path))
            if not resource_check["success"]:
                return resource_check

            # Extract text using existing infrastructure
            extraction_result = self._extract_text_from_pdf(pdf_path)
            if not extraction_result["success"]:
                return extraction_result

            # Generate metadata
            metadata = self._generate_metadata(pdf_path, extraction_result)

            # Format content as markdown
            markdown_content = self._format_as_markdown(
                extraction_result["text"], 
                metadata if include_metadata else None
            )

            # Determine output path
            if not output_path:
                output_path = pdf_path.with_suffix('.md')

            # Write markdown file
            output_path.write_text(markdown_content, encoding='utf-8')
            
            logger.info(f"Converted {pdf_path.name} to {output_path.name}")
            
            return {
                "success": True,
                "input_file": str(pdf_path),
                "output_file": str(output_path),
                "metadata": metadata,
                "extraction_method": extraction_result["extraction_method"],
                "page_count": extraction_result.get("page_count", 1),
                "file_size_mb": round(pdf_path.stat().st_size / (1024 * 1024), 2)
            }

        except Exception as e:
            logger.error(f"PDF conversion failed for {pdf_path}: {e}")
            return {"success": False, "error": f"Conversion failed: {str(e)}"}

    def _extract_text_from_pdf(self, pdf_path: Path) -> dict[str, Any]:
        """Extract text using existing PDF infrastructure."""
        try:
            # Use OCR coordinator for automatic text/OCR detection
            ocr_result = self.ocr_coordinator.process_pdf_with_ocr(str(pdf_path))
            
            if not ocr_result["success"]:
                return ocr_result

            # Use OCR text if available, otherwise use regular extraction
            if ocr_result.get("ocr_used"):
                return {
                    "success": True,
                    "text": ocr_result["text"],
                    "extraction_method": "ocr",
                    "page_count": ocr_result.get("page_count", 1),
                    "ocr_confidence": ocr_result.get("confidence", 0.0),
                    "legal_metadata": ocr_result.get("metadata", {})
                }
            else:
                # Use enhanced processor for regular text extraction
                processor_result = self.processor.extract_and_chunk_pdf(str(pdf_path))
                if not processor_result["success"]:
                    return processor_result

                # Combine chunks into full text
                chunks = processor_result.get("chunks", [])
                full_text = "\n\n".join([chunk.get("text", "") for chunk in chunks])
                
                return {
                    "success": True,
                    "text": full_text,
                    "extraction_method": "pypdf2",
                    "page_count": len(chunks) if chunks else 1,
                    "legal_metadata": {}
                }

        except Exception as e:
            logger.error(f"Text extraction failed for {pdf_path}: {e}")
            return {"success": False, "error": f"Text extraction failed: {str(e)}"}

    def _generate_metadata(self, pdf_path: Path, extraction_result: dict) -> dict[str, Any]:
        """Generate comprehensive metadata for YAML frontmatter."""
        try:
            # Calculate file hash
            file_hash = self._calculate_file_hash(pdf_path)
            
            # Get file stats
            stat = pdf_path.stat()
            
            # Basic metadata
            metadata = {
                "title": pdf_path.stem,
                "original_filename": pdf_path.name,
                "file_hash": file_hash,
                "file_size_bytes": stat.st_size,
                "file_size_mb": round(stat.st_size / (1024 * 1024), 2),
                "page_count": extraction_result.get("page_count", 1),
                "extraction_method": extraction_result.get("extraction_method", "unknown"),
                "processed_at": datetime.now().isoformat(),
                "document_type": "pdf"
            }

            # Add OCR-specific metadata if available
            if "ocr_confidence" in extraction_result:
                metadata["ocr_required"] = True
                metadata["ocr_confidence"] = extraction_result["ocr_confidence"]
            else:
                metadata["ocr_required"] = False

            # Add legal metadata if available
            legal_metadata = extraction_result.get("legal_metadata", {})
            if legal_metadata:
                metadata["legal_metadata"] = legal_metadata

            return metadata

        except Exception as e:
            logger.warning(f"Metadata generation failed for {pdf_path}: {e}")
            return {"title": pdf_path.stem, "processed_at": datetime.now().isoformat()}

    def _calculate_file_hash(self, file_path: Path) -> str:
        """Calculate SHA-256 hash of file."""
        try:
            sha256_hash = hashlib.sha256()
            with open(file_path, "rb") as f:
                for chunk in iter(lambda: f.read(4096), b""):
                    sha256_hash.update(chunk)
            return sha256_hash.hexdigest()
        except Exception as e:
            logger.warning(f"Hash calculation failed for {file_path}: {e}")
            return "unknown"

    def _format_as_markdown(self, text: str, metadata: dict | None = None) -> str:
        """Format text as markdown with optional YAML frontmatter."""
        try:
            if metadata:
                # Create frontmatter document
                post = frontmatter.Post(self._clean_text_for_markdown(text), **metadata)
                return frontmatter.dumps(post)
            else:
                # Return plain markdown without frontmatter
                return self._clean_text_for_markdown(text)

        except Exception as e:
            logger.warning(f"Markdown formatting failed: {e}")
            return text

    def _clean_text_for_markdown(self, text: str) -> str:
        """Clean and format text for markdown output."""
        try:
            if not text:
                return ""

            # Basic text cleaning
            lines = text.split('\n')
            cleaned_lines = []

            for line in lines:
                # Strip excessive whitespace
                cleaned_line = line.strip()
                
                # Skip empty lines (but preserve paragraph breaks)
                if not cleaned_line:
                    if cleaned_lines and cleaned_lines[-1] != "":
                        cleaned_lines.append("")
                    continue

                # Add line to output
                cleaned_lines.append(cleaned_line)

            # Join lines and normalize paragraph breaks
            cleaned_text = '\n'.join(cleaned_lines)
            
            # Remove excessive empty lines (more than 2 consecutive)
            while '\n\n\n' in cleaned_text:
                cleaned_text = cleaned_text.replace('\n\n\n', '\n\n')

            return cleaned_text.strip()

        except Exception as e:
            logger.warning(f"Text cleaning failed: {e}")
            return text

    def convert_directory(
        self, 
        directory_path: Path, 
        output_dir: Path | None = None,
        recursive: bool = False
    ) -> dict[str, Any]:
        """
        Convert all PDFs in a directory to markdown.
        
        Args:
            directory_path: Directory containing PDF files
            output_dir: Optional output directory for markdown files
            recursive: Whether to process subdirectories
            
        Returns:
            Batch conversion results
        """
        try:
            if not directory_path.exists() or not directory_path.is_dir():
                return {"success": False, "error": "Directory not found or not a directory"}

            # Find PDF files
            pattern = "**/*.pdf" if recursive else "*.pdf"
            pdf_files = list(directory_path.glob(pattern))

            if not pdf_files:
                return {"success": True, "message": "No PDF files found", "results": []}

            # Set output directory
            if not output_dir:
                output_dir = directory_path / "markdown_output"
            output_dir.mkdir(exist_ok=True)

            # Process each file
            results = []
            success_count = 0
            error_count = 0

            for pdf_file in pdf_files:
                output_file = output_dir / pdf_file.with_suffix('.md').name
                result = self.convert_pdf_to_markdown(pdf_file, output_file)
                
                if result["success"]:
                    success_count += 1
                else:
                    error_count += 1

                results.append({
                    "file": pdf_file.name,
                    "success": result["success"],
                    "output": str(output_file) if result["success"] else None,
                    "error": result.get("error")
                })

            logger.info(f"Directory conversion complete: {success_count} success, {error_count} errors")

            return {
                "success": True,
                "total_files": len(pdf_files),
                "success_count": success_count,
                "error_count": error_count,
                "output_directory": str(output_dir),
                "results": results
            }

        except Exception as e:
            logger.error(f"Directory conversion failed: {e}")
            return {"success": False, "error": f"Directory conversion failed: {str(e)}"}

    def validate_setup(self) -> dict[str, Any]:
        """Validate DocumentConverter setup and dependencies."""
        try:
            validation_result = {
                "pdf_available": PDF_AVAILABLE,
                "frontmatter_available": True,  # We imported it successfully
                "dependencies": {}
            }

            if PDF_AVAILABLE:
                validation_result["dependencies"] = {
                    "validator": self.validator is not None,
                    "storage": self.storage is not None,
                    "ocr_coordinator": self.ocr_coordinator is not None,
                    "processor": self.processor is not None
                }

            validation_result["ready"] = all([
                PDF_AVAILABLE,
                validation_result["dependencies"].get("validator", False),
                validation_result["dependencies"].get("ocr_coordinator", False)
            ])

            return validation_result

        except Exception as e:
            logger.error(f"Setup validation failed: {e}")
            return {"ready": False, "error": str(e)}


# Simple factory function following CLAUDE.md principles
def get_document_converter(db_path: str = "emails.db") -> DocumentConverter | None:
    """Get or create DocumentConverter instance."""
    try:
        return DocumentConverter(db_path)
    except ImportError as e:
        logger.warning(f"DocumentConverter not available: {e}")
        return None