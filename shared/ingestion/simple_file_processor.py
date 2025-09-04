"""
Simple File Processor - Process files in place, save clean versions.

Replaces complex OriginalFileManager (848 lines) with simple approach:
- Leave files where users put them
- Process in place
- Save clean version to data/processed/
- Track both paths in database
"""

import hashlib
from datetime import datetime
from pathlib import Path
from typing import Any

from loguru import logger

from shared.db.simple_db import SimpleDB


def process_file_simple(
    file_path: Path,
    content: str,
    file_type: str = "document",
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Process file in place and save clean version.

    Args:
        file_path: Original file path (left unchanged)
        content: Extracted/cleaned content
        file_type: Type of file ('pdf', 'email', 'document')
        metadata: Optional metadata

    Returns:
        Dictionary with processing results
    """
    if not file_path.exists():
        raise FileNotFoundError(f"Source file not found: {file_path}")

    # Create processed directory
    processed_dir = Path("data/processed")
    processed_dir.mkdir(parents=True, exist_ok=True)

    # Generate clean filename
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    safe_name = file_path.stem.replace(" ", "_")[:50]  # Limit length
    clean_filename = f"{safe_name}_{timestamp}_clean.txt"

    # Save clean content
    clean_path = processed_dir / clean_filename
    clean_path.write_text(content, encoding="utf-8")

    # Track in database
    db = SimpleDB()
    content_id = db.add_content(
        content_type=file_type,
        title=file_path.name,
        content=content,
        metadata={
            "original_path": str(file_path),
            "processed_path": str(clean_path),
            "file_type": file_type,
            **(metadata or {}),
        },
    )

    logger.info(f"Processed file: {file_path.name} -> {clean_filename}")

    return {
        "success": True,
        "content_id": content_id,
        "original_path": str(file_path),
        "processed_path": str(clean_path),
        "file_type": file_type,
    }


def get_content_hash(content: str) -> str:
    """
    Calculate SHA-256 hash of content for deduplication.
    """
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


def check_content_duplicate(content: str) -> str | None:
    """Check if content already exists by hash.

    Returns:
        Content ID if duplicate exists, None if unique
    """
    content_hash = get_content_hash(content)
    db = SimpleDB()

    # Check if content hash already exists
    existing = db.fetch_one(
        "SELECT id FROM content_unified WHERE content_hash = ?", (content_hash,)
    )

    return existing["id"] if existing else None


def quarantine_file(file_path: Path, error_msg: str) -> Path:
    """
    Move problematic file to quarantine with error log.
    """
    quarantine_dir = Path("data/quarantine")
    quarantine_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    quarantine_path = quarantine_dir / f"{file_path.stem}_{timestamp}_failed{file_path.suffix}"

    # Copy to quarantine (don't move original)
    import shutil

    shutil.copy2(file_path, quarantine_path)

    # Log error
    error_log = quarantine_path.with_suffix(".error.txt")
    error_log.write_text(f"Error: {error_msg}\nOriginal: {file_path}\nTime: {datetime.now()}")

    logger.error(f"Quarantined file: {file_path.name} -> {quarantine_path.name}")
    return quarantine_path


# Simple factory function following CLAUDE.md principles
def get_simple_processor():
    """
    Get simple file processor (no complex instantiation needed).
    """
    return {
        "process_file": process_file_simple,
        "check_duplicate": check_content_duplicate,
        "quarantine": quarantine_file,
    }
