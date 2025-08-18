"""
Analog Database Manager - File-based storage system for documents and email threads.

This module replaces the complex pipeline system with a simple, human-readable
file-based approach using markdown files organized in a clear directory structure.
"""

import os
from pathlib import Path
from typing import Dict, Optional, Tuple
from loguru import logger


class AnalogDBManager:
    """Manages the file-based analog database structure."""
    
    def __init__(self, base_path: Optional[Path] = None):
        """
        Initialize the Analog Database Manager.
        
        Args:
            base_path: Base directory for the analog database. 
                      Defaults to current working directory.
        """
        self.base_path = Path(base_path) if base_path else Path.cwd()
        self.analog_db_path = self.base_path / "analog_db"
        self.data_path = self.base_path / "data"
        self.originals_path = self.data_path / "originals"
        
        # Define subdirectory structure
        self.directories = {
            "documents": self.analog_db_path / "documents",
            "email_threads": self.analog_db_path / "email_threads",
            "pdfs": self.originals_path / "pdfs",
            "emails": self.originals_path / "emails"
        }
        
        logger.info(f"Initialized AnalogDBManager with base path: {self.base_path}")
    
    def create_directory_structure(self) -> Dict[str, bool]:
        """
        Create the complete analog database directory structure.
        
        Returns:
            Dictionary mapping directory names to creation success status.
        """
        results = {}
        
        for name, path in self.directories.items():
            try:
                # Create directory with parents, don't error if exists
                path.mkdir(parents=True, exist_ok=True)
                results[name] = True
                logger.info(f"✅ Created/verified directory: {path}")
            except PermissionError as e:
                results[name] = False
                logger.error(f"❌ Permission denied creating {path}: {e}")
            except OSError as e:
                results[name] = False
                logger.error(f"❌ OS error creating {path}: {e}")
            except Exception as e:
                results[name] = False
                logger.error(f"❌ Unexpected error creating {path}: {e}")
        
        # Log summary
        success_count = sum(1 for v in results.values() if v)
        total_count = len(results)
        if success_count == total_count:
            logger.success(f"✅ All {total_count} directories created successfully")
        else:
            logger.warning(f"⚠️ Created {success_count}/{total_count} directories")
        
        return results
    
    def validate_directory_structure(self) -> Tuple[bool, Dict[str, Dict[str, bool]]]:
        """
        Validate that all required directories exist and are accessible.
        
        Returns:
            Tuple of (all_valid, detailed_status) where detailed_status contains
            existence and write permission status for each directory.
        """
        status = {}
        all_valid = True
        
        for name, path in self.directories.items():
            dir_status = {
                "exists": path.exists(),
                "is_directory": path.is_dir() if path.exists() else False,
                "writable": False,
                "readable": False
            }
            
            if dir_status["exists"] and dir_status["is_directory"]:
                # Check permissions
                dir_status["readable"] = os.access(path, os.R_OK)
                dir_status["writable"] = os.access(path, os.W_OK)
            
            # Directory is valid if it exists, is a directory, and is writable
            is_valid = (
                dir_status["exists"] and 
                dir_status["is_directory"] and 
                dir_status["writable"]
            )
            
            if not is_valid:
                all_valid = False
                logger.warning(f"⚠️ Directory validation failed for {name}: {dir_status}")
            else:
                logger.debug(f"✅ Directory validated: {name}")
            
            status[name] = dir_status
        
        return all_valid, status
    
    def get_directory_info(self) -> Dict[str, Dict[str, any]]:
        """
        Get detailed information about all directories.
        
        Returns:
            Dictionary with directory information including paths, 
            file counts, and sizes.
        """
        info = {}
        
        for name, path in self.directories.items():
            dir_info = {
                "path": str(path),
                "exists": path.exists(),
                "file_count": 0,
                "total_size": 0,
                "subdirs": []
            }
            
            if path.exists() and path.is_dir():
                try:
                    # Count files and calculate size
                    for item in path.iterdir():
                        if item.is_file():
                            dir_info["file_count"] += 1
                            dir_info["total_size"] += item.stat().st_size
                        elif item.is_dir():
                            dir_info["subdirs"].append(item.name)
                    
                    # Convert size to human-readable format
                    dir_info["size_readable"] = self._format_bytes(dir_info["total_size"])
                except (PermissionError, OSError) as e:
                    logger.error(f"Error reading directory {path}: {e}")
            
            info[name] = dir_info
        
        return info
    
    def _format_bytes(self, size: int) -> str:
        """Convert bytes to human-readable format."""
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if size < 1024.0:
                return f"{size:.2f} {unit}"
            size /= 1024.0
        return f"{size:.2f} PB"
    
    def setup(self) -> bool:
        """
        Complete setup of the analog database system.
        
        Returns:
            True if setup was successful, False otherwise.
        """
        logger.info("🚀 Setting up Analog Database structure...")
        
        # Create directories
        self.create_directory_structure()
        
        # Validate structure
        is_valid, validation_status = self.validate_directory_structure()
        
        if is_valid:
            logger.success("✅ Analog Database setup complete!")
            
            # Log directory info
            info = self.get_directory_info()
            for name, details in info.items():
                logger.info(f"📁 {name}: {details['path']}")
                if details['exists']:
                    logger.info(f"   Files: {details['file_count']}, "
                              f"Size: {details.get('size_readable', '0 B')}")
        else:
            logger.error("❌ Analog Database setup failed - some directories are invalid")
            for name, status in validation_status.items():
                if not (status["exists"] and status["is_directory"] and status["writable"]):
                    logger.error(f"   {name}: {status}")
        
        return is_valid


def initialize_analog_db(base_path: Optional[Path] = None) -> AnalogDBManager:
    """
    Initialize and set up the analog database system.
    
    Args:
        base_path: Base directory for the analog database.
                  Defaults to current working directory.
    
    Returns:
        Configured AnalogDBManager instance.
    """
    manager = AnalogDBManager(base_path)
    manager.setup()
    return manager


if __name__ == "__main__":
    # Setup the analog database when run directly
    manager = initialize_analog_db()
    
    # Show current status
    info = manager.get_directory_info()
    print("\n📊 Analog Database Status:")
    print("-" * 50)
    for name, details in info.items():
        print(f"{name}:")
        print(f"  Path: {details['path']}")
        print(f"  Exists: {details['exists']}")
        if details['exists']:
            print(f"  Files: {details['file_count']}")
            print(f"  Size: {details.get('size_readable', '0 B')}")
        print()