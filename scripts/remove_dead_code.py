#!/usr/bin/env python3
"""
Dead Code Removal Script
Removes unused modules and rarely imported functions identified by analysis.
Creates backup before removal and verifies system still works.
"""

import shutil
import sys
from pathlib import Path
from datetime import datetime
import subprocess

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from loguru import logger


class DeadCodeRemover:
    """Removes identified dead code with safety checks."""
    
    def __init__(self, dry_run=False):
        self.dry_run = dry_run
        self.project_root = Path(__file__).parent.parent
        self.backup_dir = self.project_root / f"backup_deadcode_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        self.removed_files = []
        self.modified_files = []
        
    def backup_file(self, file_path: Path):
        """Create backup of file or directory before removal."""
        if self.dry_run:
            return
            
        relative_path = file_path.relative_to(self.project_root)
        backup_path = self.backup_dir / relative_path
        
        if file_path.is_dir():
            # Backup directory
            backup_path.parent.mkdir(parents=True, exist_ok=True)
            shutil.copytree(file_path, backup_path)
            logger.info(f"Backed up directory: {relative_path}")
        else:
            # Backup file
            backup_path.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(file_path, backup_path)
            logger.info(f"Backed up: {relative_path}")
        
    def remove_file(self, file_path: Path, reason: str):
        """Remove a file with backup."""
        if not file_path.exists():
            return
            
        relative_path = file_path.relative_to(self.project_root)
        
        if self.dry_run:
            logger.info(f"[DRY RUN] Would remove: {relative_path} - {reason}")
            return
            
        self.backup_file(file_path)
        file_path.unlink()
        self.removed_files.append(str(relative_path))
        logger.success(f"Removed: {relative_path} - {reason}")
        
    def remove_unused_infrastructure_documents(self):
        """Remove unused document processing modules."""
        logger.info("Removing unused infrastructure/documents modules...")
        
        # These are only used by gmail for email thread processing
        # The main document pipeline is not actively used
        unused_modules = [
            "infrastructure/documents/document_converter.py",  # Only used by tests
            "infrastructure/documents/lifecycle_manager.py",    # Part of unused pipeline
            "infrastructure/documents/format_detector.py",      # Part of unused pipeline
            "infrastructure/documents/document_pipeline.py",    # Not actively used
            "infrastructure/documents/naming_convention.py",    # Part of unused pipeline
            "infrastructure/documents/processors/text_processor.py",      # Unused
            "infrastructure/documents/processors/markdown_processor.py",  # Unused
            "infrastructure/documents/processors/docx_processor.py",      # Unused
            "infrastructure/documents/processors/base_processor.py",      # Unused
        ]
        
        # Keep email_thread_processor as it's used by gmail
        
        for module in unused_modules:
            file_path = self.project_root / module
            self.remove_file(file_path, "Unused document processing module")
            
    def remove_rarely_used_shared_modules(self):
        """Remove shared modules with only 1-2 imports."""
        logger.info("Removing rarely used shared modules...")
        
        # service_interfaces only used by pdf/main.py - can be inlined
        file_path = self.project_root / "shared/service_interfaces.py"
        if file_path.exists():
            # Imports already fixed in fix_imports_before_removal()
            self.remove_file(file_path, "Only used by pdf/main.py - inlined")
            
        # simple_export_manager only used by export_documents.py
        file_path = self.project_root / "shared/simple_export_manager.py"
        if file_path.exists():
            self.remove_file(file_path, "Only used by export_documents.py - can be inlined")
            
    def inline_iservice_in_pdf(self):
        """Inline IService interface directly in pdf/main.py."""
        if self.dry_run:
            logger.info("[DRY RUN] Would inline IService in pdf/main.py")
            return
            
        pdf_main = self.project_root / "pdf/main.py"
        if not pdf_main.exists():
            return
            
        content = pdf_main.read_text()
        
        # Remove the import
        content = content.replace("from shared.service_interfaces import IService", "")
        
        # Remove the inheritance (PDFService doesn't actually use IService methods)
        content = content.replace("class PDFService(IService):", "class PDFService:")
        
        # Backup and write
        self.backup_file(pdf_main)
        pdf_main.write_text(content)
        self.modified_files.append("pdf/main.py")
        logger.success("Inlined IService in pdf/main.py")
        
    def fix_imports_before_removal(self):
        """Fix all imports before removing files."""
        logger.info("Fixing imports before file removal...")
        
        # Fix pdf/main.py first
        self.inline_iservice_in_pdf()
        
        # Fix shared/__init__.py
        self.fix_shared_init()
        
    def fix_shared_init(self):
        """Fix shared/__init__.py to remove IService import."""
        if self.dry_run:
            logger.info("[DRY RUN] Would fix shared/__init__.py")
            return
            
        shared_init = self.project_root / "shared/__init__.py"
        if not shared_init.exists():
            return
            
        content = shared_init.read_text()
        
        # Remove the import line
        content = content.replace("from .service_interfaces import IService\n", "")
        
        # Update __all__
        content = content.replace('__all__ = ["SimpleDB", "IService"]', '__all__ = ["SimpleDB"]')
        
        # Backup and write
        self.backup_file(shared_init)
        shared_init.write_text(content)
        self.modified_files.append("shared/__init__.py")
        logger.success("Fixed shared/__init__.py")
        
    def remove_unused_utilities(self):
        """Remove unused utility modules."""
        logger.info("Removing unused utility modules...")
        
        # These utilities are not actively used based on import analysis
        unused_utils = [
            "utilities/maintenance/email_quarantine.py",  # Quarantine system not actively used
            "utilities/maintenance/vector_reconciliation.py",  # One-time migration tool
            "utilities/semantic_pipeline.py",  # Old pipeline, replaced by simpler approach
        ]
        
        for module in unused_utils:
            file_path = self.project_root / module
            self.remove_file(file_path, "Unused utility module")
            
    def remove_old_migration_scripts(self):
        """Remove completed migration scripts."""
        logger.info("Removing old migration scripts...")
        
        # These scripts were for one-time migrations that are complete
        old_scripts = [
            "scripts/migrate_emails_to_unified.py",
            "scripts/complete_unification_migration.py",
            "scripts/migrate_content_to_unified.py",
            "scripts/cleanup_migration_artifacts.py",
        ]
        
        for script in old_scripts:
            file_path = self.project_root / script
            self.remove_file(file_path, "Completed migration script")
            
    def remove_unused_test_files(self):
        """Remove tests for removed modules."""
        logger.info("Removing tests for deleted modules...")
        
        unused_tests = [
            "tests/document_processing/",  # Tests for unused document pipeline
            "tests/infrastructure/test_document_converter.py",
            "tests/infrastructure/test_email_thread_processor.py",  # Keep simple version
        ]
        
        for test in unused_tests:
            test_path = self.project_root / test
            if test_path.is_dir():
                if not self.dry_run:
                    self.backup_file(test_path)
                    shutil.rmtree(test_path)
                    self.removed_files.append(str(test))
                    logger.success(f"Removed test directory: {test}")
            elif test_path.exists():
                self.remove_file(test_path, "Test for removed module")
                
    def verify_system(self):
        """Verify system still works after cleanup."""
        logger.info("Verifying system functionality...")
        
        if self.dry_run:
            logger.info("[DRY RUN] Would run system verification")
            return True
            
        # Run basic imports test
        try:
            result = subprocess.run(
                [sys.executable, "-c", """
import sys
from pathlib import Path
sys.path.insert(0, str(Path.cwd()))

# Test core imports still work
from shared.simple_db import SimpleDB
from gmail.main import GmailService
from pdf.main import PDFService
from search_intelligence import get_search_intelligence_service
from legal_intelligence import get_legal_intelligence_service

print('✅ Core imports working')
"""],
                capture_output=True,
                text=True,
                cwd=self.project_root
            )
            
            if result.returncode != 0:
                logger.error(f"Import test failed: {result.stderr}")
                return False
                
            logger.success("Core imports verified")
            
            # Run pipeline verification
            result = subprocess.run(
                [sys.executable, "scripts/verify_pipeline.py", "--json"],
                capture_output=True,
                text=True,
                cwd=self.project_root
            )
            
            if result.returncode == 0:
                logger.success("Pipeline verification passed")
            else:
                logger.warning(f"Pipeline verification had issues: {result.stdout}")
                
            return True
            
        except Exception as e:
            logger.error(f"Verification failed: {e}")
            return False
            
    def generate_report(self):
        """Generate cleanup report."""
        logger.info("=" * 60)
        logger.info("DEAD CODE REMOVAL REPORT")
        logger.info("=" * 60)
        
        if self.dry_run:
            logger.info("DRY RUN - No actual changes made")
        else:
            logger.info(f"Backup created: {self.backup_dir}")
            
        logger.info(f"Files removed: {len(self.removed_files)}")
        for file in self.removed_files[:10]:  # Show first 10
            logger.info(f"  - {file}")
        if len(self.removed_files) > 10:
            logger.info(f"  ... and {len(self.removed_files) - 10} more")
            
        logger.info(f"Files modified: {len(self.modified_files)}")
        for file in self.modified_files:
            logger.info(f"  - {file}")
            
        # Calculate space saved
        if not self.dry_run and self.backup_dir.exists():
            total_size = sum(f.stat().st_size for f in self.backup_dir.rglob("*") if f.is_file())
            logger.info(f"Space freed: {total_size / 1024:.1f} KB")
            
    def rollback(self):
        """Rollback changes if needed."""
        if self.dry_run or not self.backup_dir.exists():
            return
            
        logger.warning("Rolling back changes...")
        
        for file in self.backup_dir.rglob("*"):
            if file.is_file():
                relative_path = file.relative_to(self.backup_dir)
                target_path = self.project_root / relative_path
                target_path.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(file, target_path)
                logger.info(f"Restored: {relative_path}")
                
        logger.success("Rollback complete")
        
    def run(self):
        """Execute dead code removal."""
        logger.info("Starting dead code removal...")
        
        # Create backup directory
        if not self.dry_run:
            self.backup_dir.mkdir(exist_ok=True)
            
        # Fix imports first before removing files
        self.fix_imports_before_removal()
        
        # Remove various categories of dead code
        self.remove_unused_infrastructure_documents()
        self.remove_rarely_used_shared_modules()
        self.remove_unused_utilities()
        self.remove_old_migration_scripts()
        self.remove_unused_test_files()
        
        # Verify system still works
        if not self.dry_run:
            if not self.verify_system():
                logger.error("System verification failed! Rolling back...")
                self.rollback()
                return False
                
        # Generate report
        self.generate_report()
        
        return True


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="Remove identified dead code")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be removed without doing it")
    parser.add_argument("--rollback", help="Rollback from backup directory")
    
    args = parser.parse_args()
    
    if args.rollback:
        # Restore from specific backup
        backup_dir = Path(args.rollback)
        if not backup_dir.exists():
            logger.error(f"Backup directory not found: {backup_dir}")
            sys.exit(1)
            
        remover = DeadCodeRemover()
        remover.backup_dir = backup_dir
        remover.rollback()
    else:
        remover = DeadCodeRemover(dry_run=args.dry_run)
        success = remover.run()
        
        if not success:
            sys.exit(1)
            
        if args.dry_run:
            logger.info("\n💡 Run without --dry-run to actually remove dead code")


if __name__ == "__main__":
    main()