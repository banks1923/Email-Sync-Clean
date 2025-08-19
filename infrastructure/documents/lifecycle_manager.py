"""
Document Lifecycle Manager - Handles folder structure and file movement.

Manages document flow through lifecycle stages:
raw → staged → processed → export (or quarantine on error)
"""

import shutil
from datetime import datetime
from pathlib import Path
from typing import Any

from loguru import logger

# Import ArchiveManager for integration
try:
    from utilities.enhanced_archive_manager import get_enhanced_archive_manager
    ARCHIVE_ENABLED = True
except ImportError:
    ARCHIVE_ENABLED = False
    logger.warning("EnhancedArchiveManager not available - archiving disabled")


class DocumentLifecycleManager:
    """Manages document lifecycle folders and transitions."""

    def __init__(self, base_path: str = "data", enable_archiving: bool = True):
        """Initialize lifecycle manager with base path."""
        self.base_path = Path(base_path)
        self.folders = {
            "raw": self.base_path / "raw",
            "staged": self.base_path / "staged",
            "processed": self.base_path / "processed",
            "quarantine": self.base_path / "quarantine",
            "export": self.base_path / "export",
        }
        self._ensure_folders_exist()
        
        # Initialize archive manager if available and enabled
        self.archive_manager = None
        if ARCHIVE_ENABLED and enable_archiving:
            self.archive_manager = get_enhanced_archive_manager(
                str(self.base_path / "originals"),
                str(self.base_path / "archives")
            )
            logger.info("Document archiving enabled")

    def _ensure_folders_exist(self):
        """Create lifecycle folders if they don't exist."""
        for folder_name, folder_path in self.folders.items():
            folder_path.mkdir(parents=True, exist_ok=True)
            logger.info(f"Ensured folder exists: {folder_path}")

    def move_to_staged(self, file_path: Path, new_name: str | None = None) -> Path:
        """Move file from raw to staged with optional rename."""
        return self._move_file(file_path, "staged", new_name)

    def move_to_processed(
        self, 
        file_path: Path, 
        new_name: str | None = None,
        archive_original: bool = True,
        case_name: str | None = None,
        metadata: dict | None = None
    ) -> Path:
        """
        Move file from staged to processed with optional archiving.
        
        Args:
            file_path: Path to file to process
            new_name: Optional new name for processed file
            archive_original: Whether to archive the original file
            case_name: Optional case name for archive organization
            metadata: Optional metadata to store with archive
            
        Returns:
            Path to processed file
        """
        # Archive original before moving if enabled
        if archive_original and self.archive_manager and file_path.exists():
            try:
                self.archive_manager.archive_file(
                    file_path,
                    metadata=metadata,
                    case_name=case_name,
                    processing_status="processed"
                )
                logger.debug(f"Archived original: {file_path.name}")
            except Exception as e:
                logger.warning(f"Failed to archive {file_path.name}: {e}")
                # Continue with move even if archiving fails
        
        return self._move_file(file_path, "processed", new_name)

    def move_to_export(self, file_path: Path, new_name: str | None = None) -> Path:
        """Move file from processed to export."""
        return self._move_file(file_path, "export", new_name)

    def quarantine_file(self, file_path: Path, error_msg: str = "") -> Path:
        """Move problematic file to quarantine with error log."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        quarantine_name = f"{timestamp}_{file_path.name}"

        # Create error log
        error_log_path = self.folders["quarantine"] / f"{quarantine_name}.error"
        error_log_path.write_text(f"Error: {error_msg}\nOriginal: {file_path}\nTime: {timestamp}")

        return self._move_file(file_path, "quarantine", quarantine_name)

    def _move_file(
        self, source: Path, destination_folder: str, new_name: str | None = None
    ) -> Path:
        """Generic file mover with atomic operations."""
        if not source.exists():
            raise FileNotFoundError(f"Source file not found: {source}")

        dest_folder = self.folders[destination_folder]
        dest_name = new_name or source.name
        dest_path = dest_folder / dest_name

        # Handle existing files
        if dest_path.exists():
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            dest_path = dest_folder / f"{timestamp}_{dest_name}"

        try:
            shutil.move(str(source), str(dest_path))
            logger.info(f"Moved {source.name} to {destination_folder}/{dest_path.name}")
            return dest_path
        except Exception as e:
            logger.error(f"Failed to move file: {e}")
            raise

    def get_folder_stats(self) -> dict[str, Any]:
        """Get statistics for all lifecycle folders."""
        stats = {}
        for folder_name, folder_path in self.folders.items():
            if folder_path.exists():
                files = list(folder_path.glob("*"))
                stats[folder_name] = {
                    "count": len(files),
                    "size_mb": sum(f.stat().st_size for f in files if f.is_file()) / (1024 * 1024),
                    "path": str(folder_path),
                }
        
        # Add archive stats if available
        if self.archive_manager:
            stats["archives"] = self.archive_manager.get_archive_stats()
        
        return stats

    def list_files(self, stage: str = "raw") -> list:
        """List all files in a specific stage."""
        folder = self.folders.get(stage)
        if not folder or not folder.exists():
            return []

        return [f.name for f in folder.iterdir() if f.is_file()]

    def get_file_path(self, stage: str, filename: str) -> Path | None:
        """Get full path for a file in a specific stage."""
        folder = self.folders.get(stage)
        if not folder:
            return None

        file_path = folder / filename
        return file_path if file_path.exists() else None
