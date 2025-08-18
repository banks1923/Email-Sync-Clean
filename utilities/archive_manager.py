"""
Archive Manager - Handles long-term archival of original documents.

Simple, direct implementation for archiving processed documents with metadata.
Archives original files after successful processing to preserve source data.
"""

import json
import zipfile
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Optional

from loguru import logger


class ArchiveManager:
    """Manages document archival with compression and metadata."""

    def __init__(self, archive_path: str = "data/archives"):
        """Initialize archive manager with base path."""
        self.archive_path = Path(archive_path)
        self.archive_path.mkdir(parents=True, exist_ok=True)
        
        # Create subdirectories for organization
        self.yearly_archives = self.archive_path / "yearly"
        self.monthly_archives = self.archive_path / "monthly"
        self.yearly_archives.mkdir(exist_ok=True)
        self.monthly_archives.mkdir(exist_ok=True)
        
        logger.info(f"ArchiveManager initialized at {self.archive_path}")

    def archive_file(
        self,
        file_path: Path,
        metadata: Optional[dict] = None,
        case_name: Optional[str] = None,
        processing_status: str = "processed"
    ) -> Path:
        """
        Archive a single file with metadata.
        
        Args:
            file_path: Path to file to archive
            metadata: Optional metadata about the file
            case_name: Optional case/project name for organization
            processing_status: Status of processing (processed, failed, etc)
            
        Returns:
            Path to created archive
        """
        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")
        
        # Generate archive name based on date and file
        timestamp = datetime.now()
        archive_name = self._generate_archive_name(file_path, timestamp, case_name)
        archive_path = self.monthly_archives / archive_name
        
        # Create archive with compression
        with zipfile.ZipFile(archive_path, 'w', zipfile.ZIP_DEFLATED) as archive:
            # Add the original file
            archive.write(file_path, arcname=file_path.name)
            
            # Add metadata
            meta_info = {
                "original_path": str(file_path),
                "original_name": file_path.name,
                "archived_at": timestamp.isoformat(),
                "processing_status": processing_status,
                "case_name": case_name,
                "file_size": file_path.stat().st_size,
                "custom_metadata": metadata or {}
            }
            
            # Write metadata as JSON
            archive.writestr("metadata.json", json.dumps(meta_info, indent=2))
            
        logger.info(f"Archived {file_path.name} to {archive_path}")
        return archive_path

    def archive_batch(
        self,
        file_paths: list[Path],
        batch_name: Optional[str] = None,
        metadata: Optional[dict] = None
    ) -> Path:
        """
        Archive multiple files together.
        
        Args:
            file_paths: List of paths to archive
            batch_name: Optional name for the batch archive
            metadata: Optional batch metadata
            
        Returns:
            Path to created archive
        """
        if not file_paths:
            raise ValueError("No files provided for batch archive")
        
        timestamp = datetime.now()
        if not batch_name:
            batch_name = f"batch_{timestamp.strftime('%Y%m%d_%H%M%S')}"
        
        archive_name = f"{batch_name}.zip"
        archive_path = self.monthly_archives / archive_name
        
        with zipfile.ZipFile(archive_path, 'w', zipfile.ZIP_DEFLATED) as archive:
            # Add all files
            for file_path in file_paths:
                if file_path.exists():
                    archive.write(file_path, arcname=file_path.name)
                    logger.debug(f"Added {file_path.name} to batch archive")
            
            # Add batch metadata
            batch_info = {
                "batch_name": batch_name,
                "archived_at": timestamp.isoformat(),
                "file_count": len(file_paths),
                "files": [str(p) for p in file_paths],
                "custom_metadata": metadata or {}
            }
            
            archive.writestr("batch_metadata.json", json.dumps(batch_info, indent=2))
        
        logger.info(f"Created batch archive with {len(file_paths)} files: {archive_path}")
        return archive_path

    def retrieve_archived(self, archive_name: str, extract_to: Optional[Path] = None) -> Path:
        """
        Retrieve and extract an archived file.
        
        Args:
            archive_name: Name of the archive file
            extract_to: Optional extraction directory
            
        Returns:
            Path to extracted files
        """
        # Search for archive in both monthly and yearly directories
        archive_path = None
        for search_dir in [self.monthly_archives, self.yearly_archives]:
            potential_path = search_dir / archive_name
            if potential_path.exists():
                archive_path = potential_path
                break
        
        if not archive_path:
            raise FileNotFoundError(f"Archive not found: {archive_name}")
        
        # Default extraction path
        if not extract_to:
            extract_to = self.archive_path / "extracted" / archive_name.replace('.zip', '')
        
        extract_to.mkdir(parents=True, exist_ok=True)
        
        # Extract archive
        with zipfile.ZipFile(archive_path, 'r') as archive:
            archive.extractall(extract_to)
        
        logger.info(f"Extracted {archive_name} to {extract_to}")
        return extract_to

    def list_archives(
        self,
        case_name: Optional[str] = None,
        since: Optional[datetime] = None,
        until: Optional[datetime] = None
    ) -> list[dict]:
        """
        List available archives with optional filtering.
        
        Args:
            case_name: Filter by case name
            since: Filter archives created after this date
            until: Filter archives created before this date
            
        Returns:
            List of archive information dictionaries
        """
        archives = []
        
        # Search both monthly and yearly archives
        for archive_dir in [self.monthly_archives, self.yearly_archives]:
            for archive_file in archive_dir.glob("*.zip"):
                try:
                    # Get basic info
                    stat = archive_file.stat()
                    created = datetime.fromtimestamp(stat.st_mtime)
                    
                    # Apply date filters
                    if since and created < since:
                        continue
                    if until and created > until:
                        continue
                    
                    # Try to read metadata for case filtering
                    archive_info = {
                        "name": archive_file.name,
                        "path": str(archive_file),
                        "size_mb": stat.st_size / (1024 * 1024),
                        "created": created.isoformat(),
                        "type": "yearly" if archive_dir == self.yearly_archives else "monthly"
                    }
                    
                    # Read metadata if needed for filtering
                    if case_name:
                        with zipfile.ZipFile(archive_file, 'r') as zf:
                            if "metadata.json" in zf.namelist():
                                meta = json.loads(zf.read("metadata.json"))
                                if meta.get("case_name") != case_name:
                                    continue
                                archive_info["case_name"] = meta.get("case_name")
                    
                    archives.append(archive_info)
                    
                except Exception as e:
                    logger.warning(f"Error reading archive {archive_file}: {e}")
        
        # Sort by creation date
        archives.sort(key=lambda x: x["created"], reverse=True)
        return archives

    def cleanup_old_archives(self, days_to_keep: int = 365) -> int:
        """
        Remove archives older than specified days.
        
        Args:
            days_to_keep: Number of days to keep archives
            
        Returns:
            Number of archives deleted
        """
        cutoff_date = datetime.now() - timedelta(days=days_to_keep)
        deleted_count = 0
        
        for archive_dir in [self.monthly_archives, self.yearly_archives]:
            for archive_file in archive_dir.glob("*.zip"):
                try:
                    created = datetime.fromtimestamp(archive_file.stat().st_mtime)
                    if created < cutoff_date:
                        archive_file.unlink()
                        deleted_count += 1
                        logger.info(f"Deleted old archive: {archive_file.name}")
                except Exception as e:
                    logger.error(f"Error deleting archive {archive_file}: {e}")
        
        logger.info(f"Cleanup complete: deleted {deleted_count} old archives")
        return deleted_count

    def promote_to_yearly(self, older_than_days: int = 90) -> int:
        """
        Move older monthly archives to yearly storage.
        
        Args:
            older_than_days: Age threshold for promotion to yearly
            
        Returns:
            Number of archives promoted
        """
        cutoff_date = datetime.now() - timedelta(days=older_than_days)
        promoted_count = 0
        
        for archive_file in self.monthly_archives.glob("*.zip"):
            try:
                created = datetime.fromtimestamp(archive_file.stat().st_mtime)
                if created < cutoff_date:
                    # Move to yearly directory
                    yearly_path = self.yearly_archives / archive_file.name
                    archive_file.rename(yearly_path)
                    promoted_count += 1
                    logger.info(f"Promoted to yearly: {archive_file.name}")
            except Exception as e:
                logger.error(f"Error promoting archive {archive_file}: {e}")
        
        logger.info(f"Promoted {promoted_count} archives to yearly storage")
        return promoted_count

    def get_archive_stats(self) -> dict[str, Any]:
        """Get statistics about archived files."""
        stats = {
            "monthly": {"count": 0, "size_mb": 0},
            "yearly": {"count": 0, "size_mb": 0},
            "total": {"count": 0, "size_mb": 0}
        }
        
        for archive_type, archive_dir in [("monthly", self.monthly_archives), 
                                          ("yearly", self.yearly_archives)]:
            archives = list(archive_dir.glob("*.zip"))
            count = len(archives)
            size = sum(f.stat().st_size for f in archives) / (1024 * 1024)
            
            stats[archive_type] = {"count": count, "size_mb": round(size, 2)}
            stats["total"]["count"] += count
            stats["total"]["size_mb"] += size
        
        stats["total"]["size_mb"] = round(stats["total"]["size_mb"], 2)
        return stats

    def _generate_archive_name(
        self,
        file_path: Path,
        timestamp: datetime,
        case_name: Optional[str] = None
    ) -> str:
        """Generate standardized archive name."""
        date_str = timestamp.strftime("%Y%m%d")
        time_str = timestamp.strftime("%H%M%S")
        
        # Build name components
        components = [date_str]
        if case_name:
            # Sanitize case name for filename
            safe_case = "".join(c for c in case_name if c.isalnum() or c in "-_")[:50]
            components.append(safe_case)
        components.append(file_path.stem[:50])  # Limit filename length
        components.append(time_str)
        
        return "_".join(components) + ".zip"


# Simple factory function following CLAUDE.md principles
def get_archive_manager(archive_path: str = "data/archives") -> ArchiveManager:
    """Get or create archive manager instance."""
    return ArchiveManager(archive_path)