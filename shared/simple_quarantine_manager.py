#!/usr/bin/env python3
"""
Simple Quarantine Manager - Direct file quarantine without pipeline complexity.

Replaces complex pipeline quarantine with simple file operations.
"""

import json
import shutil
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

from loguru import logger


class SimpleQuarantineManager:
    """Simple quarantine management. Copy files, log errors, enable recovery."""

    def __init__(self, quarantine_dir: str = "data/system_data/quarantine"):
        self.quarantine_dir = Path(quarantine_dir)
        self.quarantine_dir.mkdir(parents=True, exist_ok=True)

    def quarantine_file(self, file_path: Path, error_msg: str, metadata: dict = None) -> dict[str, Any]:
        """
        Quarantine a problematic file with error information.
        
        Args:
            file_path: Path to file that failed processing
            error_msg: Error message explaining the failure
            metadata: Optional metadata about the failure
            
        Returns:
            Quarantine result with paths and error info
        """
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            quarantine_filename = f"{file_path.stem}_{timestamp}_failed{file_path.suffix}"
            quarantine_path = self.quarantine_dir / quarantine_filename

            # Copy file to quarantine (preserve original)
            shutil.copy2(file_path, quarantine_path)

            # Create detailed error log
            error_info = {
                "timestamp": datetime.now().isoformat(),
                "original_path": str(file_path),
                "quarantine_path": str(quarantine_path),
                "error_message": error_msg,
                "file_size": file_path.stat().st_size if file_path.exists() else 0,
                "metadata": metadata or {}
            }

            error_log_path = quarantine_path.with_suffix('.error.json')
            with open(error_log_path, 'w') as f:
                json.dump(error_info, f, indent=2)

            logger.warning(f"File quarantined: {file_path.name} -> {quarantine_filename}")
            
            return {
                "success": True,
                "quarantine_path": str(quarantine_path),
                "error_log_path": str(error_log_path),
                "error_info": error_info
            }

        except Exception as e:
            logger.error(f"Failed to quarantine file {file_path}: {e}")
            return {
                "success": False,
                "error": str(e),
                "message": f"Could not quarantine {file_path.name}"
            }

    def list_quarantined_files(self) -> list[dict[str, Any]]:
        """List all quarantined files with their error information."""
        quarantined_files = []
        
        for error_file in self.quarantine_dir.glob("*.error.json"):
            try:
                with open(error_file) as f:
                    error_info = json.load(f)
                
                # Find corresponding quarantined file
                quarantine_file = error_file.with_suffix('')
                if not quarantine_file.exists():
                    # Try to find file with different extension
                    base_name = error_file.stem[:-6]  # Remove .error
                    possible_files = list(self.quarantine_dir.glob(f"{base_name}*"))
                    quarantine_file = next((f for f in possible_files if not f.name.endswith('.error.json')), None)
                
                file_info = {
                    "error_log": str(error_file),
                    "quarantined_file": str(quarantine_file) if quarantine_file and quarantine_file.exists() else None,
                    "original_path": error_info.get("original_path"),
                    "timestamp": error_info.get("timestamp"),
                    "error_message": error_info.get("error_message"),
                    "file_size": error_info.get("file_size", 0),
                    "can_retry": quarantine_file and quarantine_file.exists()
                }
                
                quarantined_files.append(file_info)
                
            except Exception as e:
                logger.warning(f"Could not read quarantine info from {error_file}: {e}")
        
        # Sort by timestamp (newest first)
        quarantined_files.sort(key=lambda x: x.get("timestamp", ""), reverse=True)
        return quarantined_files

    def retry_quarantined_file(self, quarantine_path: Path) -> dict[str, Any]:
        """
        Attempt to retry processing a quarantined file.
        
        Args:
            quarantine_path: Path to quarantined file
            
        Returns:
            Retry result information
        """
        if not quarantine_path.exists():
            return {"success": False, "error": "Quarantined file not found"}

        try:
            # Use SimpleUploadProcessor to retry
            from .simple_upload_processor import SimpleUploadProcessor
            
            processor = SimpleUploadProcessor()
            result = processor.process_file(quarantine_path, source="retry")
            
            if result["success"]:
                # Move quarantined file to a "recovered" subdirectory
                recovered_dir = self.quarantine_dir / "recovered"
                recovered_dir.mkdir(exist_ok=True)
                
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                recovered_path = recovered_dir / f"{quarantine_path.stem}_recovered_{timestamp}{quarantine_path.suffix}"
                shutil.move(quarantine_path, recovered_path)
                
                # Move error log too
                error_log = quarantine_path.with_suffix('.error.json')
                if error_log.exists():
                    recovered_error_log = recovered_path.with_suffix('.error.json')
                    shutil.move(error_log, recovered_error_log)
                
                logger.info(f"Successfully recovered quarantined file: {quarantine_path.name}")
                
                return {
                    "success": True,
                    "content_id": result["content_id"],
                    "recovered_path": str(recovered_path),
                    "message": "File successfully recovered and processed"
                }
            else:
                logger.warning(f"Retry failed for {quarantine_path.name}: {result['error']}")
                return {
                    "success": False,
                    "error": result["error"],
                    "message": "Retry processing failed"
                }
                
        except Exception as e:
            logger.error(f"Error during retry of {quarantine_path}: {e}")
            return {
                "success": False,
                "error": str(e),
                "message": f"Exception during retry: {e}"
            }

    def get_quarantine_stats(self) -> dict[str, Any]:
        """Get statistics about quarantined files."""
        quarantined_files = self.list_quarantined_files()
        
        total_files = len(quarantined_files)
        retryable_files = sum(1 for f in quarantined_files if f["can_retry"])
        
        # Count by error type (simple categorization)
        error_categories = {}
        for file_info in quarantined_files:
            error_msg = file_info.get("error_message", "").lower()
            if "pdf" in error_msg:
                category = "PDF Processing"
            elif "permission" in error_msg or "access" in error_msg:
                category = "File Access"
            elif "corrupt" in error_msg or "invalid" in error_msg:
                category = "File Corruption"
            elif "timeout" in error_msg:
                category = "Timeout"
            else:
                category = "Other"
            
            error_categories[category] = error_categories.get(category, 0) + 1
        
        return {
            "total_quarantined": total_files,
            "retryable_files": retryable_files,
            "error_categories": error_categories,
            "quarantine_directory": str(self.quarantine_dir),
            "directory_exists": self.quarantine_dir.exists()
        }

    def cleanup_old_quarantine(self, days_old: int = 30) -> dict[str, Any]:
        """Clean up quarantine files older than specified days."""
        cutoff_timestamp = datetime.now().timestamp() - (days_old * 24 * 60 * 60)
        
        cleaned_files = []
        total_size_freed = 0
        
        for file_path in self.quarantine_dir.glob("*"):
            if file_path.is_file():
                file_age = file_path.stat().st_mtime
                if file_age < cutoff_timestamp:
                    try:
                        file_size = file_path.stat().st_size
                        file_path.unlink()
                        cleaned_files.append(str(file_path))
                        total_size_freed += file_size
                        logger.debug(f"Cleaned old quarantine file: {file_path.name}")
                    except Exception as e:
                        logger.warning(f"Could not clean {file_path}: {e}")
        
        logger.info(f"Quarantine cleanup: removed {len(cleaned_files)} files, freed {total_size_freed:,} bytes")
        
        return {
            "success": True,
            "files_removed": len(cleaned_files),
            "bytes_freed": total_size_freed,
            "days_threshold": days_old
        }


def get_quarantine_manager() -> SimpleQuarantineManager:
    """Get quarantine manager instance."""
    return SimpleQuarantineManager()