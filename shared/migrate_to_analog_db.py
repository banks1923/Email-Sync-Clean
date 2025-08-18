#!/usr/bin/env python3
"""
Migration script to clean up data directory and move files to analog database structure.
"""

import shutil
from pathlib import Path
from datetime import datetime
from loguru import logger
from analog_db import AnalogDBManager


class DataMigrator:
    """Handles migration from old pipeline structure to new analog database."""
    
    def __init__(self, base_path: Path = None):
        """Initialize the migrator with base path."""
        self.base_path = Path(base_path) if base_path else Path.cwd()
        self.data_path = self.base_path / "data"
        self.analog_db = AnalogDBManager(self.base_path)
        
        # Old pipeline directories
        self.old_dirs = {
            "raw": self.data_path / "raw",
            "staged": self.data_path / "staged", 
            "processed": self.data_path / "processed",
            "export": self.data_path / "export",
            "quarantine": self.data_path / "quarantine"
        }
        
        # Files to keep in data directory
        self.keep_in_data = {
            "cache", "sequential_thinking", "README.md", 
            ".doc_counter", ".DS_Store", "emails.db", ".gitkeep"
        }
        
        self.migrated_files = []
        self.errors = []
    
    def migrate(self):
        """Execute the complete migration process."""
        logger.info("🚀 Starting migration to analog database structure...")
        
        # Step 1: Setup new structure
        logger.info("Step 1: Creating analog database structure...")
        self.analog_db.setup()
        
        # Step 2: Migrate PDFs to originals/pdfs
        logger.info("Step 2: Migrating PDF files...")
        self._migrate_pdfs()
        
        # Step 3: Migrate markdown exports to analog_db/documents
        logger.info("Step 3: Migrating markdown documents...")
        self._migrate_markdown_docs()
        
        # Step 4: Archive old pipeline directories
        logger.info("Step 4: Archiving old pipeline directories...")
        self._archive_old_directories()
        
        # Step 5: Clean up data directory
        logger.info("Step 5: Cleaning up data directory...")
        self._cleanup_data_directory()
        
        # Report results
        self._report_results()
    
    def _migrate_pdfs(self):
        """Migrate all PDFs to data/originals/pdfs."""
        pdf_dest = self.analog_db.originals_path / "pdfs"
        pdf_count = 0
        
        for old_dir_name, old_dir_path in self.old_dirs.items():
            if not old_dir_path.exists():
                continue
                
            # Find all PDFs recursively
            for pdf_file in old_dir_path.rglob("*.pdf"):
                try:
                    # Create date-based subdirectory
                    file_date = datetime.fromtimestamp(pdf_file.stat().st_mtime)
                    date_dir = pdf_dest / file_date.strftime("%Y-%m")
                    date_dir.mkdir(parents=True, exist_ok=True)
                    
                    # Generate unique name if needed
                    dest_file = date_dir / pdf_file.name
                    if dest_file.exists():
                        base = pdf_file.stem
                        ext = pdf_file.suffix
                        counter = 1
                        while dest_file.exists():
                            dest_file = date_dir / f"{base}_{counter}{ext}"
                            counter += 1
                    
                    # Copy file
                    shutil.copy2(pdf_file, dest_file)
                    self.migrated_files.append((str(pdf_file), str(dest_file)))
                    pdf_count += 1
                    logger.debug(f"Migrated PDF: {pdf_file.name} → {dest_file}")
                    
                except Exception as e:
                    self.errors.append((str(pdf_file), str(e)))
                    logger.error(f"Failed to migrate {pdf_file}: {e}")
        
        logger.info(f"✅ Migrated {pdf_count} PDF files")
    
    def _migrate_markdown_docs(self):
        """Migrate markdown documents from export to analog_db/documents."""
        docs_dest = self.analog_db.analog_db_path / "documents"
        md_count = 0
        
        # Look for markdown files in export directory
        export_dir = self.old_dirs.get("export")
        if export_dir and export_dir.exists():
            for md_file in export_dir.glob("*.md"):
                try:
                    # Skip README files
                    if "README" in md_file.name.upper():
                        continue
                    
                    # Clean up filename (remove counter prefixes like 0250_)
                    clean_name = md_file.name
                    if clean_name[:4].isdigit() and clean_name[4] == "_":
                        clean_name = clean_name[5:]
                    
                    # Add date prefix if not present
                    if not clean_name[:4].isdigit():
                        file_date = datetime.fromtimestamp(md_file.stat().st_mtime)
                        clean_name = f"{file_date.strftime('%Y-%m-%d')}_{clean_name}"
                    
                    dest_file = docs_dest / clean_name
                    
                    # Handle duplicates
                    if dest_file.exists():
                        base = dest_file.stem
                        ext = dest_file.suffix
                        counter = 1
                        while dest_file.exists():
                            dest_file = docs_dest / f"{base}_{counter}{ext}"
                            counter += 1
                    
                    # Copy file
                    shutil.copy2(md_file, dest_file)
                    self.migrated_files.append((str(md_file), str(dest_file)))
                    md_count += 1
                    logger.debug(f"Migrated markdown: {md_file.name} → {dest_file.name}")
                    
                except Exception as e:
                    self.errors.append((str(md_file), str(e)))
                    logger.error(f"Failed to migrate {md_file}: {e}")
        
        logger.info(f"✅ Migrated {md_count} markdown documents")
    
    def _archive_old_directories(self):
        """Archive old pipeline directories."""
        archive_path = self.data_path / "archive_old_pipeline"
        archive_path.mkdir(exist_ok=True)
        
        archived = []
        for dir_name, dir_path in self.old_dirs.items():
            if dir_path.exists():
                try:
                    # Move to archive
                    archive_dest = archive_path / dir_name
                    if archive_dest.exists():
                        shutil.rmtree(archive_dest)
                    shutil.move(str(dir_path), str(archive_dest))
                    archived.append(dir_name)
                    logger.debug(f"Archived {dir_name} directory")
                except Exception as e:
                    logger.error(f"Failed to archive {dir_name}: {e}")
        
        if archived:
            logger.info(f"✅ Archived old directories: {', '.join(archived)}")
    
    def _cleanup_data_directory(self):
        """Clean up data directory, keeping only essential files."""
        if not self.data_path.exists():
            return
        
        cleaned = []
        for item in self.data_path.iterdir():
            # Skip items we want to keep
            if item.name in self.keep_in_data or item.name == "originals" or item.name == "archive_old_pipeline":
                continue
            
            # Remove other items
            try:
                if item.is_file():
                    item.unlink()
                    cleaned.append(item.name)
                elif item.is_dir() and item.name not in ["originals", "archive_old_pipeline"]:
                    shutil.rmtree(item)
                    cleaned.append(item.name)
            except Exception as e:
                logger.error(f"Failed to clean up {item}: {e}")
        
        if cleaned:
            logger.info(f"🧹 Cleaned up: {', '.join(cleaned)}")
    
    def _report_results(self):
        """Report migration results."""
        logger.info("=" * 60)
        logger.success("📊 Migration Complete!")
        logger.info(f"✅ Files migrated: {len(self.migrated_files)}")
        
        if self.errors:
            logger.warning(f"⚠️ Errors encountered: {len(self.errors)}")
            for file_path, error in self.errors[:5]:  # Show first 5 errors
                logger.error(f"  - {Path(file_path).name}: {error}")
        
        # Show new structure
        logger.info("\n📁 New Directory Structure:")
        info = self.analog_db.get_directory_info()
        for name, details in info.items():
            if details['exists']:
                logger.info(f"  {name}: {details['file_count']} files, {details.get('size_readable', '0 B')}")
        
        logger.info("\n💡 Next steps:")
        logger.info("  1. Verify migrated files in analog_db/documents and data/originals/pdfs")
        logger.info("  2. Check data/archive_old_pipeline for any files you might need")
        logger.info("  3. Once verified, you can safely delete data/archive_old_pipeline")


def main():
    """Execute the migration."""
    migrator = DataMigrator()
    
    # Confirm before proceeding
    logger.warning("⚠️ This will reorganize your data directory!")
    logger.info("Files will be moved to:")
    logger.info("  - PDFs → data/originals/pdfs/")
    logger.info("  - Markdown exports → analog_db/documents/")
    logger.info("  - Old pipeline dirs → data/archive_old_pipeline/")
    
    response = input("\nProceed with migration? (yes/no): ")
    if response.lower() in ['yes', 'y']:
        migrator.migrate()
    else:
        logger.info("Migration cancelled.")


if __name__ == "__main__":
    main()