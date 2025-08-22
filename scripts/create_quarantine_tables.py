#!/usr/bin/env python3
"""
Create quarantine tables for email corpus sanitation.
Migration script to add quarantine infrastructure.
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from loguru import logger

from shared.simple_db import SimpleDB


class QuarantineMigration:
    """Migration to add email quarantine infrastructure."""
    
    def __init__(self, db_path: str = "data/emails.db"):
        self.db_path = db_path
        self.db = SimpleDB(db_path)
        
    def run_migration(self) -> bool:
        """Execute the quarantine migration."""
        logger.info("Starting quarantine tables migration")
        
        try:
            # Create emails_quarantine table
            self._create_emails_quarantine_table()
            
            # Create batch tracking table
            self._create_quarantine_batches_table()
            
            # Create indexes for performance
            self._create_indexes()
            
            # Add metadata tracking
            self._add_migration_metadata()
            
            logger.info("✓ Quarantine migration completed successfully")
            return True
            
        except Exception as e:
            logger.error(f"✗ Quarantine migration failed: {e}")
            return False
    
    def _create_emails_quarantine_table(self):
        """Create the main quarantine table."""
        sql = """
        CREATE TABLE IF NOT EXISTS emails_quarantine (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email_id INTEGER NOT NULL,
            message_id TEXT NOT NULL,
            reason TEXT NOT NULL,
            quarantined_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            batch_id TEXT NOT NULL,
            original_data TEXT,  -- JSON backup of original email
            error_details TEXT,  -- Additional error information
            retry_count INTEGER DEFAULT 0,
            last_retry_at DATETIME,
            status TEXT DEFAULT 'quarantined' CHECK (status IN ('quarantined', 'reviewed', 'restored', 'deleted')),
            reviewer TEXT,
            review_notes TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (email_id) REFERENCES emails(id)
        )
        """
        
        self.db.execute(sql)
        logger.debug("Created emails_quarantine table")
    
    def _create_quarantine_batches_table(self):
        """Create batch tracking table."""
        sql = """
        CREATE TABLE IF NOT EXISTS quarantine_batches (
            batch_id TEXT PRIMARY KEY,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            total_quarantined INTEGER DEFAULT 0,
            reason_summary TEXT,
            operator TEXT,
            rollback_possible INTEGER DEFAULT 1,
            rolled_back_at DATETIME,
            notes TEXT
        )
        """
        
        self.db.execute(sql)
        logger.debug("Created quarantine_batches table")
    
    def _create_indexes(self):
        """Create performance indexes."""
        indexes = [
            "CREATE INDEX IF NOT EXISTS idx_quarantine_batch_id ON emails_quarantine(batch_id)",
            "CREATE INDEX IF NOT EXISTS idx_quarantine_reason ON emails_quarantine(reason)",
            "CREATE INDEX IF NOT EXISTS idx_quarantine_status ON emails_quarantine(status)",
            "CREATE INDEX IF NOT EXISTS idx_quarantine_email_id ON emails_quarantine(email_id)",
            "CREATE INDEX IF NOT EXISTS idx_quarantine_message_id ON emails_quarantine(message_id)",
        ]
        
        for index_sql in indexes:
            self.db.execute(index_sql)
        
        logger.debug("Created quarantine indexes")
    
    def _add_migration_metadata(self):
        """Add migration tracking metadata."""
        sql = """
        CREATE TABLE IF NOT EXISTS migration_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            migration_name TEXT NOT NULL UNIQUE,
            applied_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            version TEXT DEFAULT '1.0',
            description TEXT
        )
        """
        
        self.db.execute(sql)
        
        # Record this migration
        self.db.execute(
            """
            INSERT OR IGNORE INTO migration_history 
            (migration_name, description, version) 
            VALUES (?, ?, ?)
            """,
            ("create_quarantine_tables", 
             "Add email quarantine infrastructure with batch tracking", 
             "1.0")
        )
        
        logger.debug("Added migration metadata")
    
    def verify_migration(self) -> bool:
        """Verify the migration was successful."""
        required_tables = ["emails_quarantine", "quarantine_batches", "migration_history"]
        
        for table in required_tables:
            result = self.db.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
                (table,)
            )
            if not result:
                logger.error(f"Missing table: {table}")
                return False
        
        logger.info("✓ Migration verification passed")
        return True
    
    def rollback_migration(self) -> bool:
        """Rollback the migration (for testing)."""
        logger.warning("Rolling back quarantine migration")
        
        try:
            # Drop tables in reverse order
            tables_to_drop = ["emails_quarantine", "quarantine_batches"]
            
            for table in tables_to_drop:
                self.db.execute(f"DROP TABLE IF EXISTS {table}")
            
            # Remove migration record
            self.db.execute(
                "DELETE FROM migration_history WHERE migration_name = ?",
                ("create_quarantine_tables",)
            )
            
            logger.info("✓ Migration rolled back successfully")
            return True
            
        except Exception as e:
            logger.error(f"✗ Rollback failed: {e}")
            return False


def main():
    """Run the migration."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Create quarantine tables migration")
    parser.add_argument("--rollback", action="store_true", help="Rollback the migration")
    parser.add_argument("--verify", action="store_true", help="Verify migration")
    parser.add_argument("--db-path", default="data/emails.db", help="Database path")
    
    args = parser.parse_args()
    
    migration = QuarantineMigration(args.db_path)
    
    if args.rollback:
        success = migration.rollback_migration()
    elif args.verify:
        success = migration.verify_migration()
    else:
        success = migration.run_migration()
        if success:
            success = migration.verify_migration()
    
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()