"""
Document Lifecycle Manager - Simplified file processing.

Simplified approach: Process files in place, save clean versions.
No complex folder lifecycle or archiving.
"""

from pathlib import Path
from typing import Any

from loguru import logger
from shared.simple_file_processor import process_file_simple, quarantine_file


class DocumentLifecycleManager:
    """Simplified document processing - no complex lifecycle."""

    def __init__(self, base_path: str = "data"):
        """Initialize with simple folder structure."""
        self.base_path = Path(base_path)
        self.folders = {
            "processed": self.base_path / "processed",
            "quarantine": self.base_path / "quarantine",
        }
        self._ensure_folders_exist()

    def _ensure_folders_exist(self):
        """Create lifecycle folders if they don't exist."""
        for folder_name, folder_path in self.folders.items():
            folder_path.mkdir(parents=True, exist_ok=True)
            logger.info(f"Ensured folder exists: {folder_path}")

    def process_file(
        self,
        file_path: Path,
        content: str,
        file_type: str = "document",
        metadata: dict | None = None
    ) -> dict[str, Any]:
        """
        Process file in place and save clean version.
        
        Args:
            file_path: Original file path (left unchanged)
            content: Extracted content
            file_type: Type of file
            metadata: Optional metadata
            
        Returns:
            Processing result dictionary
        """
        try:
            return process_file_simple(file_path, content, file_type, metadata)
        except Exception as e:
            logger.error(f"Failed to process {file_path.name}: {e}")
            quarantine_path = self.quarantine_file(file_path, str(e))
            return {
                "success": False,
                "error": str(e),
                "quarantine_path": str(quarantine_path)
            }

    def quarantine_file(self, file_path: Path, error_msg: str = "") -> Path:
        """Copy problematic file to quarantine (leave original)."""
        return quarantine_file(file_path, error_msg)

    def get_stats(self) -> dict[str, Any]:
        """Get statistics about processed and quarantined files."""
        stats = {}
        
        for folder_name, folder_path in self.folders.items():
            if folder_path.exists():
                files = [f for f in folder_path.iterdir() if f.is_file()]
                stats[folder_name] = {
                    "count": len(files),
                    "total_size_mb": sum(f.stat().st_size for f in files) / (1024 * 1024)
                }
            else:
                stats[folder_name] = {"count": 0, "total_size_mb": 0}
        
        return stats


# Simple factory function following CLAUDE.md principles
def get_lifecycle_manager(base_path: str = "data") -> DocumentLifecycleManager:
    """Get document lifecycle manager instance."""
    return DocumentLifecycleManager(base_path)
