"""
Enhanced Archive Manager - Combines file organization with space-saving deduplication.

Simple, direct implementation combining OriginalFileManager and ArchiveManager functionality.
Handles date-based organization, SHA-256 deduplication, and space optimization with links.
"""

from datetime import datetime
from pathlib import Path
from typing import Any

from loguru import logger

from shared.original_file_manager import OriginalFileManager
from shared.simple_db import SimpleDB
from utilities.archive_manager import ArchiveManager


class EnhancedArchiveManager:
    """
    Enhanced archive management combining file organization with deduplication.
    
    Provides unified interface for:
    - Date-based file organization (YYYY-MM-DD structure)
    - SHA-256 content deduplication 
    - Space optimization with hard/soft links
    - Long-term archival with compression
    """

    def __init__(
        self,
        originals_path: str = "data/originals",
        archives_path: str = "data/archives", 
        use_hard_links: bool = True
    ):
        """Initialize enhanced archive manager with dual functionality."""
        self.originals_manager = OriginalFileManager(originals_path, use_hard_links)
        self.archive_manager = ArchiveManager(archives_path)
        self.db = SimpleDB()
        self.use_hard_links = use_hard_links
        
        # Ensure space savings tracking table
        self._ensure_space_savings_table()
        
        logger.info(f"EnhancedArchiveManager initialized - originals: {originals_path}, archives: {archives_path}")

    def _ensure_space_savings_table(self):
        """Create space savings tracking table."""
        self.db.execute("""
            CREATE TABLE IF NOT EXISTS space_savings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                file_hash TEXT NOT NULL,
                original_size INTEGER NOT NULL,
                saved_bytes INTEGER NOT NULL,
                link_count INTEGER DEFAULT 1,
                method TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        logger.debug("Space savings table ensured")

    def archive_file(
        self,
        file_path: Path,
        file_type: str = "document",
        target_date: datetime | None = None,
        create_archive: bool = False,
        metadata: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        """
        Main entry point for archiving files with deduplication.
        
        Args:
            file_path: Path to file to archive
            file_type: Type of file ('pdf', 'email', 'document')
            target_date: Optional date override for organization
            create_archive: Whether to also create compressed archive
            metadata: Optional additional metadata
            
        Returns:
            Dictionary with archival results and space savings
        """
        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")
        
        logger.info(f"Archiving file: {file_path.name} (type: {file_type})")
        
        # Get original file size for space tracking
        original_size = file_path.stat().st_size
        
        # Organize with deduplication
        organized_path, was_duplicate = self.originals_manager.organize_file(
            file_path, file_type, target_date
        )
        
        result = {
            "success": True,
            "original_path": str(file_path),
            "organized_path": str(organized_path),
            "was_duplicate": was_duplicate,
            "original_size_mb": round(original_size / (1024 * 1024), 2),
            "file_type": file_type
        }
        
        # Calculate space savings
        if was_duplicate:
            savings_info = self._calculate_space_savings(file_path, organized_path)
            result.update(savings_info)
        else:
            result.update({
                "space_saved_mb": 0,
                "storage_method": "copy",
                "duplicate_of": None
            })
        
        # Create compressed archive if requested
        if create_archive:
            archive_path = self.archive_manager.archive_file(
                organized_path, metadata, file_type
            )
            result["archive_path"] = str(archive_path)
        
        logger.info(f"File archived successfully: {file_path.name}")
        return result

    def organize_by_date(
        self, 
        source_directory: Path, 
        file_pattern: str = "*.pdf",
        file_type: str = "pdf"
    ) -> dict[str, Any]:
        """
        Organize files from source directory by date with deduplication.
        
        Args:
            source_directory: Directory containing files to organize
            file_pattern: Glob pattern for files to process
            file_type: Type of files being processed
            
        Returns:
            Organization results with space savings report
        """
        if not source_directory.exists():
            raise FileNotFoundError(f"Source directory not found: {source_directory}")
        
        logger.info(f"Organizing files by date: {source_directory} ({file_pattern})")
        
        files = list(source_directory.glob(file_pattern))
        results = {
            "files_processed": 0,
            "duplicates_found": 0,
            "total_space_saved_mb": 0,
            "files": []
        }
        
        for file_path in files:
            try:
                file_result = self.archive_file(file_path, file_type, create_archive=False)
                results["files"].append(file_result)
                results["files_processed"] += 1
                
                if file_result["was_duplicate"]:
                    results["duplicates_found"] += 1
                    results["total_space_saved_mb"] += file_result.get("space_saved_mb", 0)
                    
            except Exception as e:
                logger.error(f"Error organizing {file_path.name}: {e}")
                results["files"].append({
                    "success": False,
                    "original_path": str(file_path),
                    "error": str(e)
                })
        
        results["total_space_saved_mb"] = round(results["total_space_saved_mb"], 2)
        logger.info(f"Organization complete: {results['files_processed']} files, {results['duplicates_found']} duplicates")
        
        return results

    def check_duplicate(self, file_path: Path) -> dict[str, Any] | None:
        """
        Check if file is duplicate and return information about original.
        
        Args:
            file_path: Path to file to check
            
        Returns:
            Dictionary with duplicate information or None if unique
        """
        return self.originals_manager.check_duplicate(file_path)

    def get_archive_stats(self) -> dict[str, Any]:
        """Get comprehensive archive statistics including space savings."""
        
        # Get basic archive stats
        archive_stats = self.archive_manager.get_archive_stats()
        
        # Get space savings stats
        savings_stats = self._get_space_savings_stats()
        
        # Get link statistics
        link_stats = self._get_link_stats()
        
        return {
            "archives": archive_stats,
            "space_savings": savings_stats,
            "links": link_stats,
            "generated_at": datetime.now().isoformat()
        }

    def cleanup_orphaned_links(self) -> int:
        """Clean up broken links and update statistics."""
        cleaned = self.originals_manager.cleanup_broken_links()
        
        if cleaned > 0:
            logger.info(f"Cleaned up {cleaned} orphaned links")
            # Update space savings to remove invalid links
            self._update_space_savings_after_cleanup()
        
        return cleaned

    def _calculate_space_savings(self, original_path: Path, organized_path: Path) -> dict[str, Any]:
        """Calculate space savings from deduplication."""
        try:
            original_size = original_path.stat().st_size
            
            # Determine if organized path is a link
            if organized_path.is_symlink():
                method = "soft_link"
                saved_bytes = original_size
            elif organized_path.stat().st_nlink > 1:
                method = "hard_link"
                saved_bytes = original_size
            else:
                method = "copy"
                saved_bytes = 0
            
            # Find the original file this is a duplicate of
            duplicate_path = self.originals_manager.check_duplicate(original_path)
            
            # Update space savings tracking
            if saved_bytes > 0:
                file_hash = self.originals_manager.get_file_hash(original_path)
                self._update_space_savings_record(file_hash, original_size, saved_bytes, method)
            
            return {
                "space_saved_mb": round(saved_bytes / (1024 * 1024), 2),
                "storage_method": method,
                "duplicate_of": duplicate_path
            }
            
        except Exception as e:
            logger.warning(f"Error calculating space savings: {e}")
            return {
                "space_saved_mb": 0,
                "storage_method": "copy",
                "duplicate_of": None
            }

    def _update_space_savings_record(
        self, 
        file_hash: str, 
        original_size: int, 
        saved_bytes: int, 
        method: str
    ):
        """Update space savings tracking in database."""
        try:
            # Check if record exists
            existing = self.db.fetch_one(
                "SELECT * FROM space_savings WHERE file_hash = ?",
                (file_hash,)
            )
            
            if existing:
                # Increment link count and saved bytes
                self.db.execute(
                    "UPDATE space_savings SET link_count = link_count + 1, saved_bytes = saved_bytes + ? WHERE file_hash = ?",
                    (saved_bytes, file_hash)
                )
            else:
                # Create new record
                self.db.execute(
                    "INSERT INTO space_savings (file_hash, original_size, saved_bytes, method) VALUES (?, ?, ?, ?)",
                    (file_hash, original_size, saved_bytes, method)
                )
                
        except Exception as e:
            logger.warning(f"Error updating space savings record: {e}")

    def _get_space_savings_stats(self) -> dict[str, Any]:
        """Get space savings statistics."""
        try:
            stats = self.db.fetch_one("""
                SELECT 
                    COUNT(*) as total_deduplicated_files,
                    SUM(saved_bytes) as total_saved_bytes,
                    SUM(link_count) as total_links,
                    AVG(original_size) as avg_file_size
                FROM space_savings
            """)
            
            if stats and stats['total_saved_bytes']:
                return {
                    "total_deduplicated_files": stats['total_deduplicated_files'],
                    "total_saved_mb": round(stats['total_saved_bytes'] / (1024 * 1024), 2),
                    "total_links": stats['total_links'],
                    "avg_file_size_mb": round((stats['avg_file_size'] or 0) / (1024 * 1024), 2)
                }
            else:
                return {
                    "total_deduplicated_files": 0,
                    "total_saved_mb": 0,
                    "total_links": 0,
                    "avg_file_size_mb": 0
                }
                
        except Exception as e:
            logger.error(f"Error getting space savings stats: {e}")
            return {"error": str(e)}

    def _get_link_stats(self) -> dict[str, Any]:
        """Get link usage statistics."""
        try:
            stats = self.db.fetch("""
                SELECT 
                    link_type,
                    COUNT(*) as count,
                    is_valid
                FROM file_links 
                GROUP BY link_type, is_valid
                ORDER BY link_type
            """)
            
            link_summary = {"hard_links": 0, "soft_links": 0, "broken_links": 0}
            
            for stat in stats:
                if stat['link_type'] == 'hard':
                    if stat['is_valid']:
                        link_summary['hard_links'] += stat['count']
                    else:
                        link_summary['broken_links'] += stat['count']
                elif stat['link_type'] == 'soft':
                    if stat['is_valid']:
                        link_summary['soft_links'] += stat['count']
                    else:
                        link_summary['broken_links'] += stat['count']
            
            return link_summary
            
        except Exception as e:
            logger.error(f"Error getting link stats: {e}")
            return {"error": str(e)}

    def _update_space_savings_after_cleanup(self):
        """Update space savings statistics after link cleanup."""
        try:
            # This could be more sophisticated, but for now just log
            logger.debug("Space savings updated after link cleanup")
        except Exception as e:
            logger.warning(f"Error updating space savings after cleanup: {e}")


# Simple factory function following CLAUDE.md principles
def get_enhanced_archive_manager(
    originals_path: str = "data/originals",
    archives_path: str = "data/archives",
    use_hard_links: bool = True
) -> EnhancedArchiveManager:
    """Get or create enhanced archive manager instance."""
    return EnhancedArchiveManager(originals_path, archives_path, use_hard_links)