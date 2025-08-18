"""
Original File Manager - Date-based organization for original files.

Organizes original files by date and type in originals/ directory.
Separate from ArchiveManager which handles ZIP compression.
"""

import hashlib
import os
import shutil
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Optional, Tuple

from loguru import logger

from .simple_db import SimpleDB
from .date_utils import parse_date_from_filename


class OriginalFileManager:
    """Manages organization of original files by date and type."""

    def __init__(self, base_path: str = "data/originals", use_hard_links: bool = True):
        """Initialize with base originals directory and linking configuration."""
        self.base_path = Path(base_path)
        self.base_path.mkdir(parents=True, exist_ok=True)
        self.use_hard_links = use_hard_links
        
        # Create type-based subdirectories
        self.pdfs_path = self.base_path / "pdfs"
        self.emails_path = self.base_path / "emails"
        self.pdfs_path.mkdir(exist_ok=True)
        self.emails_path.mkdir(exist_ok=True)
        
        # Initialize database for hash tracking
        self.db = SimpleDB()
        self._ensure_hash_table()
        self._ensure_links_table()
        
        logger.info(f"OriginalFileManager initialized at {self.base_path}, hard_links={use_hard_links}")

    def _ensure_hash_table(self):
        """Create hash tracking table if it doesn't exist."""
        self.db.execute("""
            CREATE TABLE IF NOT EXISTS file_hashes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                file_hash TEXT UNIQUE NOT NULL,
                original_path TEXT NOT NULL,
                file_size INTEGER NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        logger.debug("File hash table ensured")

    def _ensure_links_table(self):
        """Create file links tracking table if it doesn't exist."""
        self.db.execute("""
            CREATE TABLE IF NOT EXISTS file_links (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                source_path TEXT NOT NULL,
                target_path TEXT NOT NULL,
                link_type TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                is_valid BOOLEAN DEFAULT 1
            )
        """)
        logger.debug("File links table ensured")

    def create_date_directory(self, file_date: datetime, file_type: str) -> Path:
        """
        Create date-based directory structure.
        
        Args:
            file_date: Date for organization
            file_type: 'pdf' or 'email'
            
        Returns:
            Path to the created directory
        """
        if file_type == 'pdf':
            base_dir = self.pdfs_path
        elif file_type == 'email':
            base_dir = self.emails_path
        else:
            # For other document types, use a generic documents directory
            documents_path = self.base_path / "documents" 
            documents_path.mkdir(exist_ok=True)
            base_dir = documents_path
        
        # Create YYYY-MM-DD structure for PDFs and documents
        if file_type in ['pdf', 'document']:
            date_str = file_date.strftime("%Y-%m-%d")
            target_dir = base_dir / date_str
        else:
            # Thread-based organization for emails
            target_dir = self._create_email_thread_directory(file_date)
        
        target_dir.mkdir(parents=True, exist_ok=True)
        return target_dir

    def get_file_hash(self, file_path: Path) -> str:
        """Calculate SHA-256 hash of file content."""
        hasher = hashlib.sha256()
        with open(file_path, 'rb') as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hasher.update(chunk)
        return hasher.hexdigest()

    def check_duplicate(self, file_path: Path) -> Optional[str]:
        """
        Check if file is duplicate by content hash.
        
        Returns:
            Path to existing file if duplicate, None if unique
        """
        file_hash = self.get_file_hash(file_path)
        
        existing = self.db.fetch_one(
            "SELECT original_path FROM file_hashes WHERE file_hash = ?",
            (file_hash,)
        )
        
        if existing:
            return existing['original_path']
        return None

    def organize_file(self, source_path: Path, file_type: str, 
                     target_date: Optional[datetime] = None) -> Tuple[Path, bool]:
        """
        Organize file into date-based structure.
        
        Args:
            source_path: Source file to organize
            file_type: 'pdf' or 'email'
            target_date: Optional date override
            
        Returns:
            Tuple of (final_path, was_duplicate)
        """
        if not source_path.exists():
            raise FileNotFoundError(f"Source file not found: {source_path}")
        
        # Check for duplicates first
        duplicate_path = self.check_duplicate(source_path)
        if duplicate_path:
            logger.info(f"Duplicate detected: {source_path.name} -> {duplicate_path}")
            
            # For duplicates, create link instead of returning existing path
            # Determine target path for the link
            if target_date:
                file_date = target_date
            else:
                file_date = parse_date_from_filename(source_path.name)
                if not file_date:
                    file_date = datetime.fromtimestamp(source_path.stat().st_mtime)
            
            # Create target directory
            target_dir = self.create_date_directory(file_date, file_type)
            
            # Generate unique filename for link if conflicts exist
            target_path = target_dir / source_path.name
            counter = 1
            while target_path.exists():
                stem = source_path.stem
                suffix = source_path.suffix
                target_path = target_dir / f"{stem}_{counter}{suffix}"
                counter += 1
            
            # Create link to duplicate instead of copying
            success, method = self.create_link_or_copy(Path(duplicate_path), target_path)
            if success:
                logger.info(f"Linked duplicate: {source_path.name} -> {target_path} ({method})")
                return target_path, True
            else:
                logger.warning(f"Failed to link duplicate, returning original path: {duplicate_path}")
                return Path(duplicate_path), True
        
        # Determine date for organization
        if target_date:
            file_date = target_date
        else:
            # Try to parse date from filename or use file modification time
            file_date = parse_date_from_filename(source_path.name)
            if not file_date:
                file_date = datetime.fromtimestamp(source_path.stat().st_mtime)
        
        # Create target directory
        target_dir = self.create_date_directory(file_date, file_type)
        
        # Generate unique filename if conflicts exist
        target_path = target_dir / source_path.name
        counter = 1
        while target_path.exists():
            stem = source_path.stem
            suffix = source_path.suffix
            target_path = target_dir / f"{stem}_{counter}{suffix}"
            counter += 1
        
        # Copy file to target location
        shutil.copy2(source_path, target_path)
        
        # Record hash for deduplication
        file_hash = self.get_file_hash(target_path)
        file_size = target_path.stat().st_size
        
        self.db.execute(
            "INSERT INTO file_hashes (file_hash, original_path, file_size) VALUES (?, ?, ?)",
            (file_hash, str(target_path), file_size)
        )
        
        logger.info(f"Organized file: {source_path.name} -> {target_path}")
        return target_path, False

    def create_hard_link(self, source_path: Path, target_path: Path) -> bool:
        """
        Create hard link to avoid duplicate storage.
        
        Args:
            source_path: Original file path
            target_path: Target path for the link
            
        Returns:
            True if link created successfully, False otherwise
        """
        try:
            # Ensure target directory exists
            target_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Use atomic operation with temporary file
            temp_fd, temp_path = tempfile.mkstemp(dir=target_path.parent)
            os.close(temp_fd)  # Close the file descriptor
            temp_path = Path(temp_path)
            
            # Create hard link
            os.link(source_path, temp_path)
            
            # Atomically replace target
            os.rename(temp_path, target_path)
            
            # Track the link in database
            self.db.execute(
                "INSERT INTO file_links (source_path, target_path, link_type) VALUES (?, ?, ?)",
                (str(source_path), str(target_path), "hard")
            )
            
            logger.info(f"Created hard link: {source_path.name} -> {target_path}")
            return True
            
        except Exception as e:
            logger.warning(f"Hard link creation failed: {e}")
            # Clean up temporary file if it exists
            if 'temp_path' in locals() and temp_path.exists():
                temp_path.unlink()
            return False

    def create_soft_link(self, source_path: Path, target_path: Path) -> bool:
        """
        Create symbolic link to avoid duplicate storage.
        
        Args:
            source_path: Original file path
            target_path: Target path for the symbolic link
            
        Returns:
            True if link created successfully, False otherwise
        """
        try:
            # Ensure target directory exists
            target_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Create symbolic link
            target_path.symlink_to(source_path)
            
            # Track the link in database
            self.db.execute(
                "INSERT INTO file_links (source_path, target_path, link_type) VALUES (?, ?, ?)",
                (str(source_path), str(target_path), "soft")
            )
            
            logger.info(f"Created soft link: {source_path.name} -> {target_path}")
            return True
            
        except Exception as e:
            logger.warning(f"Soft link creation failed: {e}")
            return False

    def verify_link(self, link_path: Path) -> bool:
        """
        Verify that a link is still valid.
        
        Args:
            link_path: Path to the link to verify
            
        Returns:
            True if link exists and target is accessible
        """
        try:
            return link_path.exists() and link_path.resolve().exists()
        except Exception:
            return False

    def cleanup_broken_links(self) -> int:
        """
        Clean up broken symbolic links.
        
        Returns:
            Number of broken links removed
        """
        cleaned_count = 0
        
        try:
            # Get all tracked links
            links = self.db.fetch(
                "SELECT * FROM file_links WHERE is_valid = 1"
            )
            
            for link_record in links:
                link_path = Path(link_record['target_path'])
                
                if not self.verify_link(link_path):
                    # Mark as invalid in database
                    self.db.execute(
                        "UPDATE file_links SET is_valid = 0 WHERE id = ?",
                        (link_record['id'],)
                    )
                    
                    # Remove broken link file
                    if link_path.is_symlink():
                        link_path.unlink()
                        cleaned_count += 1
                        logger.info(f"Removed broken link: {link_path}")
                    
            logger.info(f"Cleaned up {cleaned_count} broken links")
            return cleaned_count
            
        except Exception as e:
            logger.error(f"Error during link cleanup: {e}")
            return cleaned_count

    def create_link_or_copy(self, source_path: Path, target_path: Path) -> Tuple[bool, str]:
        """
        Try to create link, fall back to copy if linking fails.
        
        Args:
            source_path: Source file path
            target_path: Target file path
            
        Returns:
            Tuple of (success, method_used)
        """
        if self.use_hard_links:
            # Try hard link first (more reliable)
            if self.create_hard_link(source_path, target_path):
                return True, "hard_link"
        
        # Try soft link if hard links disabled or failed
        if self.create_soft_link(source_path, target_path):
            return True, "soft_link"
        
        # Fall back to copying
        try:
            target_path.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source_path, target_path)
            logger.info(f"Copied file (linking failed): {source_path.name} -> {target_path}")
            return True, "copy"
        except Exception as e:
            logger.error(f"File copy also failed: {e}")
            return False, "failed"

    def _create_email_thread_directory(self, file_date: datetime, thread_id: Optional[str] = None) -> Path:
        """
        Create thread-based directory structure for emails.
        
        Args:
            file_date: Date for fallback organization
            thread_id: Optional thread identifier
            
        Returns:
            Path to the thread directory
        """
        if thread_id:
            # Use specific thread ID if provided
            thread_dir = self.emails_path / "threads" / thread_id
        else:
            # Fall back to date-based organization for emails without thread info
            year_month = file_date.strftime("%Y-%m")
            thread_dir = self.emails_path / "by_date" / year_month
        
        return thread_dir


# Simple factory function following CLAUDE.md principles
def get_original_file_manager(
    base_path: str = "data/originals", 
    use_hard_links: bool = True
) -> OriginalFileManager:
    """Get or create original file manager instance."""
    return OriginalFileManager(base_path, use_hard_links)