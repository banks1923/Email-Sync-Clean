#!/usr/bin/env python3
"""Database Migration Runner.

Applies SQL migration files safely with tracking.
Usage: python3 shared/migrations/migrate.py [--dry-run]
"""

import argparse
import sqlite3
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from loguru import logger


class MigrationRunner:
    """
    Simple migration runner for SQLite database.
    """
    
    def __init__(self, db_path: str = "data/emails.db"):
        self.db_path = db_path
        self.migrations_dir = Path(__file__).parent
        
    def _ensure_migration_table(self, conn):
        """
        Create migrations table if it doesn't exist.
        """
        conn.execute("""
            CREATE TABLE IF NOT EXISTS migrations (
                filename TEXT PRIMARY KEY,
                applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                checksum TEXT
            )
        """)
        conn.commit()
    
    def _get_applied_migrations(self, conn):
        """
        Get list of already applied migrations.
        """
        cursor = conn.execute("SELECT filename FROM migrations ORDER BY filename")
        return {row[0] for row in cursor.fetchall()}
    
    def _get_migration_files(self):
        """
        Get list of migration SQL files.
        """
        return sorted(self.migrations_dir.glob("*.sql"))
    
    def _calculate_checksum(self, file_path):
        """
        Calculate checksum of migration file.
        """
        import hashlib
        with open(file_path, 'rb') as f:
            return hashlib.md5(f.read()).hexdigest()
    
    def run_migrations(self, dry_run: bool = False):
        """
        Run pending migrations.
        """
        logger.info(f"Running migrations on database: {self.db_path}")
        
        if dry_run:
            logger.info("DRY RUN MODE - No changes will be made")
        
        with sqlite3.connect(self.db_path) as conn:
            self._ensure_migration_table(conn)
            applied = self._get_applied_migrations(conn)
            migration_files = self._get_migration_files()
            
            if not migration_files:
                logger.info("No migration files found")
                return
            
            pending = [f for f in migration_files if f.name not in applied]
            
            if not pending:
                logger.info("No pending migrations")
                return
            
            logger.info(f"Found {len(pending)} pending migrations")
            
            for migration_file in pending:
                logger.info(f"Applying migration: {migration_file.name}")
                
                with open(migration_file) as f:
                    sql_content = f.read()
                
                if dry_run:
                    logger.info(f"Would execute: {migration_file.name}")
                    logger.debug(f"SQL content:\n{sql_content}")
                    continue
                
                try:
                    # Execute migration
                    conn.executescript(sql_content)
                    
                    # Record successful migration
                    checksum = self._calculate_checksum(migration_file)
                    conn.execute(
                        "INSERT INTO migrations (filename, checksum) VALUES (?, ?)",
                        (migration_file.name, checksum)
                    )
                    conn.commit()
                    
                    logger.info(f"✅ Migration {migration_file.name} applied successfully")
                    
                except Exception as e:
                    logger.error(f"❌ Migration {migration_file.name} failed: {e}")
                    conn.rollback()
                    raise
            
            if not dry_run:
                logger.info("All migrations completed successfully")


def main():
    parser = argparse.ArgumentParser(description="Run database migrations")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be done without applying changes")
    parser.add_argument("--db-path", default="data/emails.db", help="Database file path")
    
    args = parser.parse_args()
    
    runner = MigrationRunner(args.db_path)
    runner.run_migrations(dry_run=args.dry_run)


if __name__ == "__main__":
    main()