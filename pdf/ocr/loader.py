"""PDF loader module - handles file operations and basic PDF loading."""

import hashlib
from pathlib import Path
from typing import Any

from loguru import logger

# Logger is now imported globally from loguru


class PDFLoader:
    """Handles PDF file operations and loading."""

    def hash_file(self, file_path: str) -> str:
        """Generate SHA256 hash of file for deduplication."""
        hasher = hashlib.sha256()
        with open(file_path, "rb") as f:
            while chunk := f.read(8192):
                hasher.update(chunk)
        return hasher.hexdigest()

    def find_pdf_files(self, directory: str, recursive: bool = True) -> list[str]:
        """Find all PDF files in directory."""
        pdf_files: list[str] = []
        path = Path(directory)

        if not path.exists():
            logger.error(f"Directory not found: {directory}")
            return pdf_files

        pattern = "**/*.pdf" if recursive else "*.pdf"

        for pdf_path in path.glob(pattern):
            if pdf_path.is_file():
                pdf_files.append(str(pdf_path))

        logger.info(f"Found {len(pdf_files)} PDF files in {directory}")
        return sorted(pdf_files)

    def validate_pdf_file(self, pdf_path: str) -> dict[str, Any]:
        """Validate PDF file exists and is readable."""
        try:
            path = Path(pdf_path)

            if not path.exists():
                return {"success": False, "error": "File does not exist"}

            if not path.is_file():
                return {"success": False, "error": "Path is not a file"}

            if path.suffix.lower() != ".pdf":
                return {"success": False, "error": "File is not a PDF"}

            # Check file size
            size_mb = path.stat().st_size / (1024 * 1024)
            if size_mb > 100:  # 100MB limit
                return {"success": False, "error": f"File too large: {size_mb:.1f}MB"}

            # Try to open file
            with open(pdf_path, "rb") as f:
                header = f.read(5)
                if header != b"%PDF-":
                    return {"success": False, "error": "Invalid PDF header"}

            return {"success": True, "file_size_mb": size_mb}

        except Exception as e:
            logger.error(f"Error validating PDF {pdf_path}: {e}")
            return {"success": False, "error": str(e)}

    def get_pdf_info(self, pdf_path: str) -> dict[str, Any]:
        """Get basic PDF file information."""
        try:
            path = Path(pdf_path)
            stat = path.stat()

            return {
                "success": True,
                "file_name": path.name,
                "file_path": str(path.absolute()),
                "file_size_mb": stat.st_size / (1024 * 1024),
                "created_at": stat.st_ctime,
                "modified_at": stat.st_mtime,
                "file_hash": self.hash_file(pdf_path),
            }

        except Exception as e:
            logger.error(f"Error getting PDF info: {e}")
            return {"success": False, "error": str(e)}
