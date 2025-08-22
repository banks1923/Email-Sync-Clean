#!/usr/bin/env python3
"""
Simple Upload Processor - Direct file processing without pipeline complexity.

Replaces DataPipelineOrchestrator.add_to_raw() with direct SimpleDB processing.
Follows CLAUDE.md principles: Simple > Complex, Working > Perfect.
"""

import hashlib
import shutil
from datetime import datetime
from pathlib import Path
from typing import Dict, Any

from loguru import logger
from .simple_db import SimpleDB


class SimpleUploadProcessor:
    """Direct file upload processing. No pipeline directories, no state management."""

    def __init__(self, quarantine_dir: str = "data/quarantine"):
        self.quarantine_dir = Path(quarantine_dir)
        self.quarantine_dir.mkdir(parents=True, exist_ok=True)
        self.db = SimpleDB()

    def process_file(self, file_path: Path, source: str = "upload") -> Dict[str, Any]:
        """
        Process file directly to database. No intermediate directories.
        
        Args:
            file_path: Path to file to process
            source: Source type (upload, pdf, email, etc.)
            
        Returns:
            Processing result with content_id or error info
        """
        if not file_path.exists():
            return {"success": False, "error": f"File not found: {file_path}"}

        try:
            # Extract content based on file type
            content = self._extract_content(file_path)
            
            # Generate file hash for deduplication
            file_hash = self._get_file_hash(file_path)
            
            # Store directly in database
            content_id = self.db.add_content(
                content_type=source,
                title=file_path.name,
                content=content,
                metadata={
                    "original_path": str(file_path),
                    "file_hash": file_hash,
                    "file_size": file_path.stat().st_size,
                    "source": source,
                    "processed_at": datetime.now().isoformat()
                }
            )

            logger.info(f"Processed {file_path.name} -> content_id: {content_id}")
            
            return {
                "success": True,
                "content_id": content_id,
                "file_hash": file_hash,
                "message": f"File processed successfully: {file_path.name}"
            }

        except Exception as e:
            logger.error(f"Failed to process {file_path.name}: {e}")
            quarantine_path = self._quarantine_file(file_path, str(e))
            
            return {
                "success": False,
                "error": str(e),
                "quarantine_path": str(quarantine_path),
                "message": f"File quarantined due to error: {e}"
            }

    def process_directory(self, dir_path: Path, limit: int = None) -> Dict[str, Any]:
        """Process all supported files in a directory."""
        if not dir_path.exists() or not dir_path.is_dir():
            return {"success": False, "error": f"Directory not found: {dir_path}"}

        supported_extensions = {'.pdf', '.txt', '.md', '.docx'}
        files = [f for f in dir_path.iterdir() 
                if f.is_file() and f.suffix.lower() in supported_extensions]
        
        if limit:
            files = files[:limit]

        results = {
            "total_files": len(files),
            "success_count": 0,
            "failed_count": 0,
            "processed_files": [],
            "failed_files": []
        }

        for file_path in files:
            result = self.process_file(file_path)
            
            if result["success"]:
                results["success_count"] += 1
                results["processed_files"].append({
                    "file": file_path.name,
                    "content_id": result["content_id"]
                })
            else:
                results["failed_count"] += 1
                results["failed_files"].append({
                    "file": file_path.name,
                    "error": result["error"]
                })

        logger.info(f"Directory processing complete: {results['success_count']}/{results['total_files']} successful")
        results["success"] = results["failed_count"] == 0
        
        return results

    def _extract_content(self, file_path: Path) -> str:
        """Extract text content from file based on extension."""
        suffix = file_path.suffix.lower()
        
        if suffix == '.txt' or suffix == '.md':
            return file_path.read_text(encoding='utf-8')
        elif suffix == '.pdf':
            # Use existing PDF service for extraction
            from pdf.pdf_processor import PDFProcessor
            processor = PDFProcessor()
            return processor.extract_text(str(file_path))
        elif suffix == '.docx':
            # Simple docx extraction (could be enhanced)
            try:
                import docx
                doc = docx.Document(file_path)
                return '\n'.join([para.text for para in doc.paragraphs])
            except ImportError:
                logger.warning("python-docx not available, treating as binary")
                return f"[Binary DOCX file: {file_path.name}]"
        else:
            # Fallback for unsupported types
            return f"[Unsupported file type: {suffix}]"

    def _get_file_hash(self, file_path: Path) -> str:
        """Calculate SHA256 hash of file content."""
        sha256_hash = hashlib.sha256()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                sha256_hash.update(chunk)
        return sha256_hash.hexdigest()

    def _quarantine_file(self, file_path: Path, error_msg: str) -> Path:
        """Move problematic file to quarantine with error log."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        quarantine_filename = f"{file_path.stem}_{timestamp}_failed{file_path.suffix}"
        quarantine_path = self.quarantine_dir / quarantine_filename

        # Copy file to quarantine (preserve original)
        shutil.copy2(file_path, quarantine_path)

        # Create error log
        error_log_path = quarantine_path.with_suffix('.error.txt')
        error_info = f"""Error processing file: {file_path}
Timestamp: {datetime.now().isoformat()}
Error: {error_msg}
Original path: {file_path}
Quarantine path: {quarantine_path}
"""
        error_log_path.write_text(error_info)

        logger.warning(f"File quarantined: {file_path.name} -> {quarantine_filename}")
        return quarantine_path


def get_upload_processor() -> SimpleUploadProcessor:
    """Get upload processor instance. Simple factory following CLAUDE.md principles."""
    return SimpleUploadProcessor()