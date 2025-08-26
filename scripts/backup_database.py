#!/usr/bin/env python3
"""Database backup utility for Terminal AI.

Creates timestamped backups with verification and compression.
"""

import argparse
import gzip
import hashlib
import shutil
import sqlite3
import sys
from datetime import datetime
from pathlib import Path

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))

from loguru import logger


class DatabaseBackup:
    """
    Handles database backup operations with integrity checks.
    """

    def __init__(self, db_path: str = None, backup_dir: str = None):
        """Initialize backup utility.

        Args:
            db_path: Path to database file (default: data/system_data/emails.db)
            backup_dir: Directory for backups (default: data/system_data/backups)
        """
        self.db_path = Path(db_path or "data/system_data/emails.db")
        self.backup_dir = Path(backup_dir or "data/system_data/backups")

        # Create backup directory if it doesn't exist
        self.backup_dir.mkdir(parents=True, exist_ok=True)

    def create_backup(
        self, compress: bool = True, verify: bool = True, description: str = None
    ) -> Path:
        """Create a timestamped backup of the database.

        Args:
            compress: Whether to compress the backup with gzip
            verify: Whether to verify backup integrity
            description: Optional description for the backup

        Returns:
            Path to the created backup file
        """
        if not self.db_path.exists():
            raise FileNotFoundError(f"Database not found: {self.db_path}")

        # Generate timestamp for backup filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_name = f"emails_backup_{timestamp}.db"

        if compress:
            backup_name += ".gz"

        backup_path = self.backup_dir / backup_name

        logger.info(f"Creating backup: {backup_path}")

        try:
            # Use SQLite backup API for consistency
            source_conn = sqlite3.connect(self.db_path)

            if compress:
                # Create temporary uncompressed backup first
                temp_backup = self.backup_dir / f"temp_{timestamp}.db"
                dest_conn = sqlite3.connect(temp_backup)

                # Perform backup
                with dest_conn:
                    source_conn.backup(dest_conn)

                dest_conn.close()
                source_conn.close()

                # Compress the backup
                with open(temp_backup, "rb") as f_in:
                    with gzip.open(backup_path, "wb", compresslevel=9) as f_out:
                        shutil.copyfileobj(f_in, f_out)

                # Remove temporary file
                temp_backup.unlink()

            else:
                # Direct backup without compression
                dest_conn = sqlite3.connect(backup_path)

                with dest_conn:
                    source_conn.backup(dest_conn)

                dest_conn.close()
                source_conn.close()

            # Calculate checksum
            checksum = self._calculate_checksum(backup_path)

            # Create metadata file
            metadata_path = backup_path.with_suffix(".meta")
            self._write_metadata(
                metadata_path,
                {
                    "timestamp": timestamp,
                    "source_path": str(self.db_path),
                    "backup_path": str(backup_path),
                    "compressed": compress,
                    "checksum": checksum,
                    "description": description or "Manual backup",
                    "size_bytes": backup_path.stat().st_size,
                    "original_size_bytes": self.db_path.stat().st_size,
                },
            )

            # Verify backup if requested
            if verify:
                if not self._verify_backup(backup_path, checksum):
                    raise ValueError("Backup verification failed")

            logger.info(f"Backup created successfully: {backup_path}")
            logger.info(f"Checksum: {checksum}")

            return backup_path

        except Exception as e:
            logger.error(f"Backup failed: {e}")
            # Clean up partial backup
            if backup_path.exists():
                backup_path.unlink()
            raise

    def _calculate_checksum(self, file_path: Path) -> str:
        """
        Calculate SHA256 checksum of a file.
        """
        sha256_hash = hashlib.sha256()
        with open(file_path, "rb") as f:
            for byte_block in iter(lambda: f.read(4096), b""):
                sha256_hash.update(byte_block)
        return sha256_hash.hexdigest()

    def _write_metadata(self, metadata_path: Path, metadata: dict):
        """
        Write backup metadata to file.
        """
        import json

        with open(metadata_path, "w") as f:
            json.dump(metadata, f, indent=2)

    def _verify_backup(self, backup_path: Path, expected_checksum: str) -> bool:
        """
        Verify backup integrity.
        """
        actual_checksum = self._calculate_checksum(backup_path)
        if actual_checksum != expected_checksum:
            logger.error(f"Checksum mismatch: expected {expected_checksum}, got {actual_checksum}")
            return False

        # For SQLite backups, also verify database integrity
        if backup_path.suffix == ".db":
            try:
                conn = sqlite3.connect(backup_path)
                cursor = conn.execute("PRAGMA integrity_check")
                result = cursor.fetchone()[0]
                conn.close()

                if result != "ok":
                    logger.error(f"Database integrity check failed: {result}")
                    return False

            except Exception as e:
                logger.error(f"Failed to verify database integrity: {e}")
                return False

        logger.info("Backup verification passed")
        return True

    def list_backups(self) -> list:
        """
        List all available backups with metadata.
        """
        import json

        backups = []
        for backup_file in sorted(self.backup_dir.glob("emails_backup_*.db*")):
            if backup_file.suffix == ".meta":
                continue

            info = {
                "file": backup_file.name,
                "path": str(backup_file),
                "size": backup_file.stat().st_size,
                "modified": datetime.fromtimestamp(backup_file.stat().st_mtime),
            }

            # Load metadata if available
            metadata_path = backup_file.with_suffix(".meta")
            if metadata_path.exists():
                with open(metadata_path) as f:
                    metadata = json.load(f)
                    info.update(metadata)

            backups.append(info)

        return backups

    def restore_backup(self, backup_path: Path, target_path: Path = None, verify: bool = True):
        """Restore a database from backup.

        Args:
            backup_path: Path to backup file
            target_path: Where to restore (default: original location with .restored suffix)
            verify: Whether to verify the backup before restoring
        """
        if not backup_path.exists():
            raise FileNotFoundError(f"Backup not found: {backup_path}")

        if target_path is None:
            target_path = self.db_path.with_suffix(".restored.db")

        logger.info(f"Restoring backup from {backup_path} to {target_path}")

        # Load metadata if available
        metadata_path = backup_path.with_suffix(".meta")
        if metadata_path.exists():
            import json

            with open(metadata_path) as f:
                metadata = json.load(f)

            # Verify checksum if requested
            if verify and "checksum" in metadata:
                if not self._verify_backup(backup_path, metadata["checksum"]):
                    raise ValueError("Backup verification failed")

        # Decompress if needed
        if backup_path.suffix == ".gz":
            logger.info("Decompressing backup...")
            with gzip.open(backup_path, "rb") as f_in:
                with open(target_path, "wb") as f_out:
                    shutil.copyfileobj(f_in, f_out)
        else:
            # Direct copy
            shutil.copy2(backup_path, target_path)

        # Verify restored database
        try:
            conn = sqlite3.connect(target_path)
            cursor = conn.execute("SELECT COUNT(*) FROM individual_messages")
            count = cursor.fetchone()[0]
            conn.close()

            logger.info(f"Restored database contains {count} individual messages")
            logger.info(f"Restoration complete: {target_path}")

        except Exception as e:
            logger.error(f"Failed to verify restored database: {e}")
            if target_path.exists():
                target_path.unlink()
            raise

    def cleanup_old_backups(self, keep_count: int = 10):
        """Remove old backups, keeping the most recent ones.

        Args:
            keep_count: Number of recent backups to keep
        """
        backups = self.list_backups()

        if len(backups) <= keep_count:
            logger.info(f"Found {len(backups)} backups, keeping all (threshold: {keep_count})")
            return

        # Sort by timestamp (newest first)
        backups.sort(key=lambda x: x.get("timestamp", ""), reverse=True)

        # Remove old backups
        to_remove = backups[keep_count:]

        for backup in to_remove:
            backup_path = Path(backup["path"])
            metadata_path = backup_path.with_suffix(".meta")

            logger.info(f"Removing old backup: {backup_path.name}")

            if backup_path.exists():
                backup_path.unlink()

            if metadata_path.exists():
                metadata_path.unlink()

        logger.info(f"Removed {len(to_remove)} old backups")


def main():
    """
    Main entry point for backup utility.
    """
    parser = argparse.ArgumentParser(description="Database backup utility")

    subparsers = parser.add_subparsers(dest="command", help="Commands")

    # Create backup command
    create_parser = subparsers.add_parser("create", help="Create a new backup")
    create_parser.add_argument("--no-compress", action="store_true", help="Skip compression")
    create_parser.add_argument("--no-verify", action="store_true", help="Skip verification")
    create_parser.add_argument("--description", help="Backup description")

    # List backups command
    list_parser = subparsers.add_parser("list", help="List available backups")

    # Restore backup command
    restore_parser = subparsers.add_parser("restore", help="Restore from backup")
    restore_parser.add_argument("backup_file", help="Backup file to restore")
    restore_parser.add_argument("--target", help="Target database path")
    restore_parser.add_argument("--no-verify", action="store_true", help="Skip verification")

    # Cleanup command
    cleanup_parser = subparsers.add_parser("cleanup", help="Remove old backups")
    cleanup_parser.add_argument("--keep", type=int, default=10, help="Number of backups to keep")

    # Common arguments
    parser.add_argument("--db-path", help="Database path")
    parser.add_argument("--backup-dir", help="Backup directory")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    # Initialize backup utility
    backup = DatabaseBackup(args.db_path, args.backup_dir)

    try:
        if args.command == "create":
            backup_path = backup.create_backup(
                compress=not args.no_compress,
                verify=not args.no_verify,
                description=args.description,
            )
            print(f"✅ Backup created: {backup_path}")

        elif args.command == "list":
            backups = backup.list_backups()

            if not backups:
                print("No backups found")
            else:
                print(f"\nFound {len(backups)} backups:\n")
                print(f"{'Timestamp':<20} {'Size':<10} {'Description':<30}")
                print("-" * 60)

                for b in backups:
                    timestamp = b.get("timestamp", "Unknown")
                    size = f"{b['size'] / 1024 / 1024:.1f} MB"
                    desc = b.get("description", "No description")[:30]
                    print(f"{timestamp:<20} {size:<10} {desc:<30}")

        elif args.command == "restore":
            backup_path = Path(args.backup_file)
            backup.restore_backup(
                backup_path, Path(args.target) if args.target else None, verify=not args.no_verify
            )
            print("✅ Restore complete")

        elif args.command == "cleanup":
            backup.cleanup_old_backups(args.keep)
            print(f"✅ Cleanup complete (keeping {args.keep} most recent backups)")

    except Exception as e:
        logger.error(f"Operation failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
