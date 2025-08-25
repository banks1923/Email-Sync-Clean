"""File operations utility for document processing.

Encapsulates file system operations for better testability.
"""

import shutil
from pathlib import Path

from loguru import logger


class FileOperations:
    """
    Encapsulated file operations for dependency injection.
    """
    
    def move_file(self, source: Path, destination: Path) -> bool:
        """Move file from source to destination.

        Args:
            source: Source file path
            destination: Destination file path

        Returns:
            True if successful, False otherwise
        """
        try:
            # Ensure destination directory exists
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(source), str(destination))
            logger.info(f"Moved file: {source} -> {destination}")
            return True
        except Exception as e:
            logger.error(f"Failed to move file {source} -> {destination}: {e}")
            return False
    
    def copy_file(self, source: Path, destination: Path) -> bool:
        """Copy file from source to destination.

        Args:
            source: Source file path
            destination: Destination file path

        Returns:
            True if successful, False otherwise
        """
        try:
            # Ensure destination directory exists
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(str(source), str(destination))
            logger.info(f"Copied file: {source} -> {destination}")
            return True
        except Exception as e:
            logger.error(f"Failed to copy file {source} -> {destination}: {e}")
            return False
    
    def delete_file(self, path: Path) -> bool:
        """Delete file at specified path.

        Args:
            path: File path to delete

        Returns:
            True if successful, False otherwise
        """
        try:
            if path.exists():
                path.unlink()
                logger.info(f"Deleted file: {path}")
            return True
        except Exception as e:
            logger.error(f"Failed to delete file {path}: {e}")
            return False
    
    def create_directory(self, path: Path) -> bool:
        """Create directory with all parent directories.

        Args:
            path: Directory path to create

        Returns:
            True if successful, False otherwise
        """
        try:
            path.mkdir(parents=True, exist_ok=True)
            logger.info(f"Created directory: {path}")
            return True
        except Exception as e:
            logger.error(f"Failed to create directory {path}: {e}")
            return False
    
    def sanitize_path(self, path_str: str) -> str:
        """Sanitize path string for cross-platform compatibility.

        Args:
            path_str: Raw path string

        Returns:
            Sanitized path string
        """
        # Remove/replace invalid characters
        invalid_chars = '<>:"|?*'
        sanitized = path_str
        
        for char in invalid_chars:
            sanitized = sanitized.replace(char, '_')
        
        # Remove excessive spaces and dots
        sanitized = sanitized.strip('. ')
        
        # Limit length
        if len(sanitized) > 200:
            sanitized = sanitized[:200]
        
        return sanitized
    
    def file_exists(self, path: Path) -> bool:
        """
        Check if file exists.
        """
        return path.exists() and path.is_file()
    
    def directory_exists(self, path: Path) -> bool:
        """
        Check if directory exists.
        """
        return path.exists() and path.is_dir()
    
    def get_file_size(self, path: Path) -> int | None:
        """
        Get file size in bytes.
        """
        try:
            return path.stat().st_size if path.exists() else None
        except Exception as e:
            logger.error(f"Failed to get file size for {path}: {e}")
            return None