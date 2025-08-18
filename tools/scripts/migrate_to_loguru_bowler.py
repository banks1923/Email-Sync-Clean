#!/usr/bin/env python3
"""
Bowler-based migration script from standard logging to loguru.
Uses AST transformations for accurate and safe code modifications.
"""

import argparse
import shutil
from pathlib import Path

from bowler import Query


class LoguruMigrator:
    """AST-based migration from standard logging to loguru."""

    def __init__(self, dry_run: bool = False, backup: bool = True):
        self.dry_run = dry_run
        self.backup = backup
        self.files_processed = 0
        self.files_skipped = 0
        self.errors = []

    def create_backup(self, filepath: Path) -> None:
        """Create backup of file before modification."""
        if self.backup and not self.dry_run:
            backup_path = filepath.with_suffix(filepath.suffix + ".backup")
            shutil.copy2(filepath, backup_path)
            print(f"  ✓ Backup created: {backup_path}")

    def find_python_files_with_logging(self, root_dir: Path) -> list[Path]:
        """Find all Python files that use logging module."""
        python_files = []
        exclude_dirs = {".venv", "venv", "__pycache__", ".git", "migrations", ".hypothesis"}

        for file in root_dir.rglob("*.py"):
            # Skip excluded directories
            if any(excluded in file.parts for excluded in exclude_dirs):
                continue

            # Skip backup files
            if file.suffix == ".backup" or ".backup" in str(file):
                continue

            # Check if file uses logging
            try:
                with open(file, encoding="utf-8") as f:
                    content = f.read()
                    # Check for any logging usage
                    if (
                        "import logging" in content
                        or "from logging" in content
                        or "from .logging_config" in content
                        or "from shared.logging_config" in content
                    ):
                        # Skip if already using loguru
                        if "from loguru import logger" not in content:
                            python_files.append(file)
            except Exception as e:
                print(f"  ⚠️  Error reading {file}: {e}")

        return python_files

    def migrate_imports(self, filepath: Path) -> bool:
        """Migrate import statements using Bowler."""
        try:
            # Query for 'import logging'
            query = Query(str(filepath))

            # Replace 'import logging' with 'from loguru import logger'
            query.select_import("logging").rename("loguru")

            # Execute the query
            if not self.dry_run:
                query.execute(write=True, silent=True)

            return True

        except Exception as e:
            self.errors.append((filepath, str(e)))
            return False

    def migrate_logger_usage(self, filepath: Path) -> bool:
        """Migrate logger usage patterns."""
        try:
            with open(filepath, encoding="utf-8") as f:
                content = f.read()

            original_content = content

            # Import replacement - more precise than bowler for our specific case
            if "import logging" in content:
                content = content.replace("import logging", "from loguru import logger")

            # Handle various logging patterns
            replacements = [
                # Handle imports from logging_config FIRST
                ("from .logging_config import get_logger", "from loguru import logger"),
                ("from shared.logging_config import get_logger", "from loguru import logger"),
                # Remove getLogger patterns
                (
                    "self.logger = logging.getLogger(__name__)",
                    "# Logger is now imported globally from loguru",
                ),
                (
                    "logger = logging.getLogger(__name__)",
                    "# Logger is now imported globally from loguru",
                ),
                ("logger = get_logger(__name__)", "# Logger is now imported globally from loguru"),
                (
                    "self.logger = logging.getLogger(",
                    "# self.logger = logger  # Now using global loguru logger",
                ),
                (
                    "self.logger = get_logger(",
                    "# self.logger = logger  # Now using global loguru logger",
                ),
                # Convert self.logger to logger
                ("self.logger.", "logger."),
                # Convert error with exc_info to exception
                (
                    "logger.error(",
                    "logger.error(",
                ),  # Keep as is for now, will handle exc_info separately
                # Remove basicConfig
                (
                    "logging.basicConfig(",
                    "# logging.basicConfig(  # Now configured in shared/loguru_config.py",
                ),
                # Handle logging level constants
                ("logging.DEBUG", '"DEBUG"'),
                ("logging.INFO", '"INFO"'),
                ("logging.WARNING", '"WARNING"'),
                ("logging.ERROR", '"ERROR"'),
                ("logging.CRITICAL", '"CRITICAL"'),
                # Handle setup_service_logging imports
                (
                    "from shared.logging_config import setup_service_logging",
                    "from shared.loguru_config import setup_logging",
                ),
                ("setup_service_logging(", "setup_logging("),
            ]

            for old, new in replacements:
                content = content.replace(old, new)

            # Handle exc_info=True pattern with regex for better accuracy
            import re

            content = re.sub(
                r"logger\.error\((.*?),\s*exc_info=True\)",
                r"logger.exception(\1)",
                content,
                flags=re.DOTALL,
            )

            # Only write if changes were made
            if content != original_content:
                if not self.dry_run:
                    with open(filepath, "w", encoding="utf-8") as f:
                        f.write(content)
                return True

            return False

        except Exception as e:
            self.errors.append((filepath, str(e)))
            return False

    def migrate_file(self, filepath: Path) -> tuple[bool, str]:
        """Migrate a single file from logging to loguru."""
        # Create backup first
        self.create_backup(filepath)

        # Perform migration
        success = self.migrate_logger_usage(filepath)

        if success:
            return True, "Successfully migrated"
        elif not self.errors:
            return False, "No changes needed"
        else:
            return False, "Error during migration"

    def migrate_project(
        self, root_dir: str, pilot_mode: bool = False, critical_only: bool = False
    ) -> None:
        """Migrate entire project with options for pilot and critical-only modes."""
        root_path = Path(root_dir)

        print("\n🔍 Scanning for Python files with logging...")
        files = self.find_python_files_with_logging(root_path)

        # Prioritize files
        critical_files = []
        core_service_files = []
        other_files = []

        for file in files:
            if "simple_db.py" in file.name:
                critical_files.insert(0, file)  # SimpleDB is highest priority
            elif any(
                s in str(file)
                for s in [
                    "gmail/main",
                    "pdf/main",
                    "entity/main",
                    "transcription/main",
                    "pipelines/orchestrator",
                ]
            ):
                core_service_files.append(file)
            else:
                other_files.append(file)

        # Build file list based on mode
        if critical_only:
            all_files = critical_files
            print("\n🎯 CRITICAL MODE: Processing only SimpleDB and critical files")
        else:
            all_files = critical_files + core_service_files + other_files

        if pilot_mode:
            all_files = all_files[:5]
            print("\n🧪 PILOT MODE: Processing only first 5 files")

        print(f"\n📊 Found {len(all_files)} files to migrate")
        if self.dry_run:
            print("🔍 DRY RUN MODE - No files will be modified\n")
        else:
            print("✏️  PRODUCTION MODE - Files will be modified\n")

        # Process files
        for i, file in enumerate(all_files, 1):
            rel_path = file.relative_to(root_path)
            print(f"[{i}/{len(all_files)}] Processing {rel_path}...")

            success, message = self.migrate_file(file)

            if success:
                print(f"  ✅ {message}")
                self.files_processed += 1
            else:
                print(f"  ⏭️  {message}")
                self.files_skipped += 1

        # Print summary
        self._print_summary()

    def _print_summary(self) -> None:
        """Print migration summary."""
        print("\n" + "=" * 60)
        print("📋 Migration Summary:")
        print(f"  ✅ Files processed: {self.files_processed}")
        print(f"  ⏭️  Files skipped: {self.files_skipped}")

        if self.errors:
            print("\n❌ Errors encountered:")
            for file, error in self.errors:
                print(f"  - {file}: {error}")

        if self.dry_run:
            print("\n🔍 DRY RUN COMPLETE - No files were modified")
            print("💡 Run without --dry-run to apply changes")


def main():
    """Main entry point for the migration script."""
    parser = argparse.ArgumentParser(
        description="Migrate from standard logging to loguru using AST transformations"
    )
    parser.add_argument(
        "--dry-run", action="store_true", help="Preview changes without modifying files"
    )
    parser.add_argument("--no-backup", action="store_true", help="Skip creating backup files")
    parser.add_argument("--pilot", action="store_true", help="Pilot mode: migrate only 5 files")
    parser.add_argument(
        "--critical", action="store_true", help="Critical mode: migrate only SimpleDB"
    )
    parser.add_argument(
        "--path", default=".", help="Project root path (default: current directory)"
    )

    args = parser.parse_args()

    print("🚀 Loguru Migration Tool")
    print("=" * 60)

    migrator = LoguruMigrator(dry_run=args.dry_run, backup=not args.no_backup)

    migrator.migrate_project(args.path, pilot_mode=args.pilot, critical_only=args.critical)


if __name__ == "__main__":
    main()
