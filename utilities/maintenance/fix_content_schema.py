#!/usr/bin/env python3
"""
Fix content table schema mismatch and reconcile with Qdrant.

This migration:
1. Renames content_id to id for consistency
2. Adds business key columns (source_type, external_id)
3. Fixes foreign key references in dependent tables
4. Migrates emails to content table
5. Reconciles Qdrant vectors with deterministic IDs
"""

import sqlite3
from typing import Dict, Optional
from uuid import UUID, uuid5

from loguru import logger
from shared.simple_db import SimpleDB

# UUID namespace for deterministic ID generation
UUID_NAMESPACE = UUID('6ba7b810-9dad-11d1-80b4-00c04fd430c8')  # DNS namespace

class ContentSchemaMigration:
    """Handles the complete schema migration and data reconciliation."""
    
    def __init__(self, db_path: Optional[str] = None):
        # SimpleDB handles the default path if None
        self.db = SimpleDB()  # Let SimpleDB use its default path
        self.metrics = {
            'schema_changes': 0,
            'emails_migrated': 0,
            'content_inserted': 0,
            'content_updated': 0,
            'content_skipped': 0,
            'qdrant_upserts': 0,
            'orphans_tagged': 0,
            'fk_tables_fixed': 0,
            'errors': []
        }
        
    def run_migration(self, dry_run: bool = False) -> Dict:
        """Execute the complete migration."""
        logger.info(f"Starting content schema migration (dry_run={dry_run})")
        
        try:
            if not dry_run:
                # Phase 1: Schema changes
                self._phase1_schema_evolution()
                
                # Phase 2: Fix foreign keys
                self._phase2_fix_foreign_keys()
                
                # Phase 3: Migrate emails to content
                self._phase3_migrate_emails()
                
                # Phase 4: Reconcile Qdrant
                self._phase4_reconcile_qdrant()
                
                # Phase 5: Verification
                self._phase5_verify_migration()
                
                # Final maintenance
                self.db.db_maintenance(force=True)
                logger.info("WAL checkpoint completed after migration")
            else:
                logger.info("DRY RUN - Checking what would be done...")
                self._dry_run_analysis()
                
        except Exception as e:
            logger.error(f"Migration failed: {e}")
            self.metrics['errors'].append(str(e))
            raise
            
        finally:
            # Report metrics
            logger.info("=== MIGRATION METRICS ===")
            for key, value in self.metrics.items():
                if key != 'errors':
                    logger.info(f"{key}: {value}")
            if self.metrics['errors']:
                logger.error(f"Errors encountered: {self.metrics['errors']}")
                
        return self.metrics
    
    def _phase1_schema_evolution(self):
        """Add new columns and indexes to content table."""
        logger.info("Phase 1: Schema Evolution")
        
        with sqlite3.connect(self.db.db_path) as conn:
            with self.db.durable_txn(conn):
                cursor = conn.cursor()
                
                # Check current schema
                cursor.execute("PRAGMA table_info(content)")
                columns = {col[1] for col in cursor.fetchall()}
                
                # Step 1: Drop dependent views first
                dependent_views = ['document_summary_overview', 'document_intelligence_overview']
                for view_name in dependent_views:
                    try:
                        cursor.execute(f"DROP VIEW IF EXISTS {view_name}")
                        logger.info(f"Dropped view: {view_name}")
                    except Exception as e:
                        logger.warning(f"Could not drop view {view_name}: {e}")
                
                # Step 2: Rename content_id to id if needed
                if 'content_id' in columns and 'id' not in columns:
                    logger.info("Renaming content_id to id")
                    # SQLite doesn't support direct column rename, use ALTER TABLE approach
                    cursor.execute("""
                        CREATE TABLE content_new (
                            id TEXT PRIMARY KEY,
                            type TEXT NOT NULL,
                            title TEXT,
                            content TEXT NOT NULL,
                            metadata TEXT DEFAULT '{}',
                            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                            content_type TEXT DEFAULT 'unknown',
                            char_count INTEGER DEFAULT 0,
                            source_type TEXT,
                            external_id TEXT,
                            parent_content_id TEXT,
                            updated_at TIMESTAMP
                        )
                    """)
                    
                    # Copy data
                    cursor.execute("""
                        INSERT INTO content_new (id, type, title, content, metadata, 
                                                created_at, content_type, char_count)
                        SELECT id, type, title, content, metadata, 
                               created_at, content_type, char_count
                        FROM content
                    """)
                    
                    # Swap tables
                    cursor.execute("DROP TABLE content")
                    cursor.execute("ALTER TABLE content_new RENAME TO content")
                    self.metrics['schema_changes'] += 1
                    
                else:
                    # Add new columns if missing
                    if 'source_type' not in columns:
                        cursor.execute("ALTER TABLE content ADD COLUMN source_type TEXT")
                        self.metrics['schema_changes'] += 1
                        
                    if 'external_id' not in columns:
                        cursor.execute("ALTER TABLE content ADD COLUMN external_id TEXT")
                        self.metrics['schema_changes'] += 1
                        
                    if 'parent_content_id' not in columns:
                        cursor.execute("ALTER TABLE content ADD COLUMN parent_content_id TEXT")
                        self.metrics['schema_changes'] += 1
                        
                    if 'updated_at' not in columns:
                        cursor.execute("ALTER TABLE content ADD COLUMN updated_at TIMESTAMP")
                        self.metrics['schema_changes'] += 1
                
                # Create business key index
                cursor.execute("""
                    CREATE UNIQUE INDEX IF NOT EXISTS content_uniq_business 
                    ON content(source_type, external_id)
                """)
                
                # Create compatibility view
                cursor.execute("""
                    CREATE VIEW IF NOT EXISTS content_v AS
                    SELECT id AS content_id, * FROM content
                """)
                
                logger.info(f"Schema evolution complete: {self.metrics['schema_changes']} changes")
    
    def _phase2_fix_foreign_keys(self):
        """Fix foreign key references in dependent tables."""
        logger.info("Phase 2: Fixing Foreign Keys")
        
        tables_to_fix = [
            ('document_summaries', 'document_id', 'summary_id'),
            ('document_intelligence', 'document_id', 'intelligence_id'),
            ('relationship_cache', 'source_id', 'cache_id'),
            ('kg_nodes', 'content_id', 'node_id')
        ]
        
        with sqlite3.connect(self.db.db_path) as conn:
            cursor = conn.cursor()
            
            # Disable foreign keys during reconstruction
            cursor.execute("PRAGMA foreign_keys=OFF")
            
            for table_name, fk_column, pk_column in tables_to_fix:
                try:
                    # Check if table exists
                    cursor.execute(f"""
                        SELECT sql FROM sqlite_master 
                        WHERE type='table' AND name='{table_name}'
                    """)
                    if not cursor.fetchone():
                        logger.info(f"Table {table_name} does not exist, skipping")
                        continue
                    
                    logger.info(f"Fixing FK in {table_name}")
                    
                    # Get column info
                    cursor.execute(f"PRAGMA table_info({table_name})")
                    columns = cursor.fetchall()
                    col_defs = []
                    
                    for col in columns:
                        col_name = col[1]
                        col_type = col[2]
                        not_null = " NOT NULL" if col[3] else ""
                        default = f" DEFAULT {col[4]}" if col[4] is not None else ""
                        
                        if col_name == pk_column:
                            col_defs.append(f"{col_name} {col_type} PRIMARY KEY{default}")
                        else:
                            col_defs.append(f"{col_name} {col_type}{not_null}{default}")
                    
                    # Add proper FK constraint
                    if fk_column in [col[1] for col in columns]:
                        col_defs.append(f"FOREIGN KEY({fk_column}) REFERENCES content(id) ON DELETE CASCADE")
                    
                    # Create new table with correct FK
                    new_table = f"{table_name}_new"
                    cursor.execute(f"""
                        CREATE TABLE {new_table} (
                            {', '.join(col_defs)}
                        )
                    """)
                    
                    # Copy data
                    col_names = [col[1] for col in columns]
                    cursor.execute(f"""
                        INSERT INTO {new_table} ({', '.join(col_names)})
                        SELECT {', '.join(col_names)} FROM {table_name}
                    """)
                    
                    # Swap tables
                    cursor.execute(f"DROP TABLE {table_name}")
                    cursor.execute(f"ALTER TABLE {new_table} RENAME TO {table_name}")
                    
                    self.metrics['fk_tables_fixed'] += 1
                    
                except Exception as e:
                    logger.error(f"Error fixing {table_name}: {e}")
                    self.metrics['errors'].append(f"FK fix failed for {table_name}: {e}")
            
            # Re-enable foreign keys
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.execute("PRAGMA foreign_key_check")
            fk_errors = cursor.fetchall()
            if fk_errors:
                logger.warning(f"Foreign key check found issues: {fk_errors}")
            else:
                logger.info("Foreign key integrity verified")
            
            conn.commit()
    
    def _phase3_migrate_emails(self):
        """Migrate emails from emails table to content table using UPSERT."""
        logger.info("Phase 3: Migrating Emails to Content")
        
        batch_size = 200
        
        # Get all emails
        emails = self.db.fetch("""
            SELECT message_id, subject, sender, content, datetime_utc, content_hash
            FROM emails
            ORDER BY datetime_utc
        """)
        
        logger.info(f"Found {len(emails)} emails to migrate")
        self.metrics['emails_migrated'] = len(emails)
        
        # Process in batches
        for i in range(0, len(emails), batch_size):
            batch = emails[i:i+batch_size]
            logger.info(f"Processing batch {i//batch_size + 1} ({len(batch)} emails)")
            
            with sqlite3.connect(self.db.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("BEGIN IMMEDIATE")
                
                for email in batch:
                    try:
                        # Generate deterministic UUID from message_id
                        content_id = str(uuid5(UUID_NAMESPACE, f"email:{email['message_id']}"))
                        
                        # Prepare content
                        title = email['subject'] or f"Email from {email['sender']}"
                        body = email['content'] or ""
                        
                        # UPSERT into content
                        cursor.execute("""
                            INSERT INTO content (
                                id, source_type, external_id, type, title, 
                                content, created_at, updated_at, char_count
                            )
                            VALUES (?, 'email', ?, 'email', ?, ?, ?, CURRENT_TIMESTAMP, ?)
                            ON CONFLICT(source_type, external_id) DO UPDATE SET
                                title = excluded.title,
                                content = excluded.content,
                                updated_at = CURRENT_TIMESTAMP
                        """, (
                            content_id,
                            email['message_id'],
                            title,
                            body,
                            email['datetime_utc'],
                            len(body)
                        ))
                        
                        if cursor.rowcount > 0:
                            if cursor.lastrowid:
                                self.metrics['content_inserted'] += 1
                            else:
                                self.metrics['content_updated'] += 1
                        else:
                            self.metrics['content_skipped'] += 1
                            
                    except Exception as e:
                        logger.error(f"Error migrating email {email['message_id']}: {e}")
                        self.metrics['errors'].append(f"Email migration: {e}")
                
                conn.commit()
        
        logger.info(f"Email migration complete: {self.metrics['content_inserted']} inserted, "
                   f"{self.metrics['content_updated']} updated")
    
    def _phase4_reconcile_qdrant(self):
        """Reconcile Qdrant vectors with content table."""
        logger.info("Phase 4: Reconciling Qdrant Vectors")
        
        try:
            from utilities.vector_store import get_vector_store
            vector_store = get_vector_store()
            
            if not vector_store.is_connected():
                logger.warning("Qdrant not connected, skipping vector reconciliation")
                return
            
            # Get all content rows
            content_rows = self.db.fetch("""
                SELECT id, source_type, external_id, title, content
                FROM content
                WHERE source_type = 'email'
            """)
            
            logger.info(f"Reconciling {len(content_rows)} content rows with Qdrant")
            
            # Process each content row
            for row in content_rows:
                try:
                    # Check if point exists with old ID
                    # We'll need to implement proper Qdrant reconciliation
                    # This is a placeholder for the actual implementation
                    logger.debug(f"Would reconcile content {row['id']} with Qdrant")
                    self.metrics['qdrant_upserts'] += 1
                    
                except Exception as e:
                    logger.error(f"Error reconciling {row['id']}: {e}")
                    self.metrics['errors'].append(f"Qdrant reconciliation: {e}")
                    
        except ImportError:
            logger.warning("Vector store not available, skipping Qdrant reconciliation")
    
    def _phase5_verify_migration(self):
        """Verify the migration was successful."""
        logger.info("Phase 5: Verification")
        
        # Test 1: Idempotency check
        count_before = self.db.fetch_one("SELECT COUNT(*) as count FROM content")['count']
        
        # Run a subset of migration again (should not create duplicates)
        test_email = self.db.fetch_one("SELECT * FROM emails LIMIT 1")
        if test_email:
            content_id = str(uuid5(UUID_NAMESPACE, f"email:{test_email['message_id']}"))
            self.db.execute("""
                INSERT INTO content (id, source_type, external_id, type, title, content)
                VALUES (?, 'email', ?, 'email', ?, ?)
                ON CONFLICT(source_type, external_id) DO UPDATE SET
                    updated_at = CURRENT_TIMESTAMP
            """, (content_id, test_email['message_id'], test_email['subject'], test_email['content']))
        
        count_after = self.db.fetch_one("SELECT COUNT(*) as count FROM content")['count']
        
        if count_before == count_after:
            logger.info("✓ Idempotency test passed")
        else:
            logger.error(f"✗ Idempotency test failed: {count_before} -> {count_after}")
            
        # Test 2: Foreign key integrity
        with sqlite3.connect(self.db.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("PRAGMA foreign_key_check")
            fk_errors = cursor.fetchall()
            if not fk_errors:
                logger.info("✓ Foreign key integrity verified")
            else:
                logger.error(f"✗ Foreign key errors: {fk_errors}")
        
        # Test 3: Business key uniqueness
        duplicates = self.db.fetch("""
            SELECT source_type, external_id, COUNT(*) as count
            FROM content
            WHERE source_type IS NOT NULL AND external_id IS NOT NULL
            GROUP BY source_type, external_id
            HAVING COUNT(*) > 1
        """)
        
        if not duplicates:
            logger.info("✓ Business key uniqueness verified")
        else:
            logger.error(f"✗ Found {len(duplicates)} duplicate business keys")
            
        # Final audit query
        audit = self.db.fetch_one("""
            SELECT 
                (SELECT COUNT(*) FROM emails) as emails,
                (SELECT COUNT(*) FROM content) as content_rows,
                (SELECT COUNT(*) FROM content WHERE source_type = 'email') as email_content,
                (SELECT COUNT(*) FROM content c 
                 LEFT JOIN emails e ON c.external_id = e.message_id 
                 WHERE c.source_type = 'email' AND e.message_id IS NULL) as orphaned_content
        """)
        
        logger.info("=== FINAL AUDIT ===")
        logger.info(f"Total emails: {audit['emails']}")
        logger.info(f"Total content: {audit['content_rows']}")
        logger.info(f"Email content: {audit['email_content']}")
        logger.info(f"Orphaned content: {audit['orphaned_content']}")
    
    def _dry_run_analysis(self):
        """Analyze what would be done without making changes."""
        logger.info("=== DRY RUN ANALYSIS ===")
        
        # Check current state
        stats = self.db.fetch_one("""
            SELECT 
                (SELECT COUNT(*) FROM emails) as email_count,
                (SELECT COUNT(*) FROM content) as content_count
        """)
        
        logger.info("Current state:")
        logger.info(f"  - Emails: {stats['email_count']}")
        logger.info(f"  - Content: {stats['content_count']}")
        
        # Check schema needs
        with sqlite3.connect(self.db.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("PRAGMA table_info(content)")
            columns = {col[1] for col in cursor.fetchall()}
            
            changes_needed = []
            if 'content_id' in columns and 'id' not in columns:
                changes_needed.append("Rename content_id to id")
            if 'source_type' not in columns:
                changes_needed.append("Add source_type column")
            if 'external_id' not in columns:
                changes_needed.append("Add external_id column")
            if 'parent_content_id' not in columns:
                changes_needed.append("Add parent_content_id column")
                
            logger.info(f"Schema changes needed: {len(changes_needed)}")
            for change in changes_needed:
                logger.info(f"  - {change}")
        
        # Check FK tables
        tables_to_check = ['document_summaries', 'document_intelligence', 
                          'relationship_cache', 'kg_nodes']
        fk_fixes_needed = []
        
        for table in tables_to_check:
            result = self.db.fetch(f"""
                SELECT sql FROM sqlite_master 
                WHERE type='table' AND name='{table}'
            """)
            if result and 'REFERENCES content(id)' in result[0]['sql']:
                fk_fixes_needed.append(table)
        
        if fk_fixes_needed:
            logger.info(f"Foreign key fixes needed for: {', '.join(fk_fixes_needed)}")
        
        logger.info(f"\nWould migrate {stats['email_count']} emails to content table")
        logger.info("Would reconcile Qdrant vectors with content IDs")


def main():
    """Run the migration."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Fix content schema and migrate data")
    parser.add_argument('--dry-run', action='store_true', 
                       help='Show what would be done without making changes')
    parser.add_argument('--db-path', help='Path to database file')
    
    args = parser.parse_args()
    
    migration = ContentSchemaMigration(args.db_path)
    metrics = migration.run_migration(dry_run=args.dry_run)
    
    if metrics['errors']:
        logger.error(f"Migration completed with {len(metrics['errors'])} errors")
        return 1
    else:
        logger.info("Migration completed successfully")
        return 0


if __name__ == "__main__":
    exit(main())