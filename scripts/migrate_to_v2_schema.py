#!/usr/bin/env python3
"""
Migration script for Semantic Search v2 schema changes.
Adds quality_score column and indices for chunk-based pipeline.

Usage:
    python scripts/migrate_to_v2_schema.py --dry-run  # Preview changes
    python scripts/migrate_to_v2_schema.py           # Apply migration
"""

import argparse
import sqlite3
import sys
from pathlib import Path
from datetime import datetime
import json

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from shared.simple_db import SimpleDB
from loguru import logger


class SchemaV2Migration:
    """Handles migration to v2 schema for semantic search."""
    
    def __init__(self, db_path: str = "data/system_data/emails.db", dry_run: bool = False):
        """
        Initialize migration handler.
        
        Args:
            db_path: Path to database
            dry_run: If True, preview changes without applying
        """
        self.db_path = db_path
        self.dry_run = dry_run
        self.db = SimpleDB()
        
        # Migration checkpoint file
        self.checkpoint_file = Path("data/system_data/.migration_v2_checkpoint.json")
        self.checkpoint = self._load_checkpoint()
        
        logger.info(f"SchemaV2Migration initialized (dry_run={dry_run})")
    
    def _load_checkpoint(self) -> dict:
        """Load migration checkpoint if exists."""
        if self.checkpoint_file.exists():
            with open(self.checkpoint_file, 'r') as f:
                return json.load(f)
        return {
            "started_at": None,
            "steps_completed": [],
            "finished_at": None
        }
    
    def _save_checkpoint(self):
        """Save migration checkpoint."""
        if not self.dry_run:
            self.checkpoint_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self.checkpoint_file, 'w') as f:
                json.dump(self.checkpoint, f, indent=2)
    
    def _mark_step_complete(self, step: str):
        """Mark a migration step as complete."""
        if step not in self.checkpoint["steps_completed"]:
            self.checkpoint["steps_completed"].append(step)
            self._save_checkpoint()
            logger.info(f"✅ Completed step: {step}")
    
    def check_column_exists(self, table: str, column: str) -> bool:
        """Check if a column exists in a table."""
        query = f"PRAGMA table_info({table})"
        result = self.db.fetch(query, [])
        for row in result:
            if row['name'] == column:
                return True
        return False
    
    def check_index_exists(self, index_name: str) -> bool:
        """Check if an index exists."""
        query = """
        SELECT name FROM sqlite_master 
        WHERE type='index' AND name=?
        """
        result = self.db.fetch(query, [index_name])
        return len(result) > 0
    
    def add_metadata_column(self):
        """Add metadata column to content_unified table if not exists."""
        step = "add_metadata_column"
        
        if step in self.checkpoint["steps_completed"]:
            logger.info(f"Step already completed: {step}")
            return
        
        # Check if column already exists
        if self.check_column_exists("content_unified", "metadata"):
            logger.info("metadata column already exists")
            self._mark_step_complete(step)
            return
        
        query = """
        ALTER TABLE content_unified 
        ADD COLUMN metadata TEXT
        """
        
        if self.dry_run:
            logger.info(f"[DRY RUN] Would execute: {query}")
        else:
            try:
                # Use raw SQLite connection for ALTER TABLE
                conn = sqlite3.connect(self.db_path)
                conn.execute("PRAGMA foreign_keys=ON")
                conn.execute(query)
                conn.commit()
                conn.close()
                logger.success("Added metadata column to content_unified")
                self._mark_step_complete(step)
            except Exception as e:
                logger.error(f"Failed to add metadata column: {e}")
                raise
    
    def add_quality_score_column(self):
        """Add quality_score column to content_unified table."""
        step = "add_quality_score_column"
        
        if step in self.checkpoint["steps_completed"]:
            logger.info(f"Step already completed: {step}")
            return
        
        # Check if column already exists
        if self.check_column_exists("content_unified", "quality_score"):
            logger.info("quality_score column already exists")
            self._mark_step_complete(step)
            return
        
        query = """
        ALTER TABLE content_unified 
        ADD COLUMN quality_score REAL DEFAULT 1.0
        """
        
        if self.dry_run:
            logger.info(f"[DRY RUN] Would execute: {query}")
        else:
            try:
                # Use raw SQLite connection for ALTER TABLE
                conn = sqlite3.connect(self.db_path)
                conn.execute("PRAGMA foreign_keys=ON")
                conn.execute(query)
                conn.commit()
                conn.close()
                logger.success("Added quality_score column to content_unified")
                self._mark_step_complete(step)
            except Exception as e:
                logger.error(f"Failed to add quality_score column: {e}")
                raise
    
    def add_quality_score_index(self):
        """Add index on quality_score for efficient filtering."""
        step = "add_quality_score_index"
        
        if step in self.checkpoint["steps_completed"]:
            logger.info(f"Step already completed: {step}")
            return
        
        index_name = "idx_content_quality"
        
        # Check if index already exists
        if self.check_index_exists(index_name):
            logger.info(f"Index {index_name} already exists")
            self._mark_step_complete(step)
            return
        
        query = f"""
        CREATE INDEX {index_name} 
        ON content_unified(quality_score)
        WHERE quality_score IS NOT NULL
        """
        
        if self.dry_run:
            logger.info(f"[DRY RUN] Would execute: {query}")
        else:
            try:
                # Use raw SQLite connection for CREATE INDEX
                conn = sqlite3.connect(self.db_path)
                conn.execute("PRAGMA foreign_keys=ON")
                conn.execute(query)
                conn.commit()
                conn.close()
                logger.success(f"Created index: {index_name}")
                self._mark_step_complete(step)
            except Exception as e:
                logger.error(f"Failed to create index: {e}")
                raise
    
    def add_chunk_indices(self):
        """Add indices for chunk queries."""
        step = "add_chunk_indices"
        
        if step in self.checkpoint["steps_completed"]:
            logger.info(f"Step already completed: {step}")
            return
        
        indices = [
            {
                "name": "idx_content_chunks",
                "query": """
                CREATE INDEX idx_content_chunks 
                ON content_unified(source_type, source_id)
                WHERE source_type = 'document_chunk'
                """
            },
            {
                "name": "idx_content_ready_quality",
                "query": """
                CREATE INDEX idx_content_ready_quality 
                ON content_unified(ready_for_embedding, quality_score)
                WHERE ready_for_embedding = 1 AND quality_score >= 0.35
                """
            }
        ]
        
        for index_def in indices:
            if self.check_index_exists(index_def["name"]):
                logger.info(f"Index {index_def['name']} already exists")
                continue
            
            if self.dry_run:
                logger.info(f"[DRY RUN] Would create index: {index_def['name']}")
            else:
                try:
                    # Use raw SQLite connection for CREATE INDEX
                    conn = sqlite3.connect(self.db_path)
                    conn.execute("PRAGMA foreign_keys=ON")
                    conn.execute(index_def["query"])
                    conn.commit()
                    conn.close()
                    logger.success(f"Created index: {index_def['name']}")
                except Exception as e:
                    logger.error(f"Failed to create index {index_def['name']}: {e}")
                    raise
        
        if not self.dry_run:
            self._mark_step_complete(step)
    
    def create_migration_tracking_table(self):
        """Create table to track chunk migration progress."""
        step = "create_migration_tracking"
        
        if step in self.checkpoint["steps_completed"]:
            logger.info(f"Step already completed: {step}")
            return
        
        query = """
        CREATE TABLE IF NOT EXISTS v2_migration_progress (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            source_id TEXT UNIQUE,
            source_type TEXT,
            chunks_created INTEGER DEFAULT 0,
            processing_status TEXT DEFAULT 'pending',
            error_message TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
        
        if self.dry_run:
            logger.info("[DRY RUN] Would create v2_migration_progress table")
        else:
            try:
                # Use raw SQLite connection for CREATE TABLE
                conn = sqlite3.connect(self.db_path)
                conn.execute("PRAGMA foreign_keys=ON")
                conn.execute(query)
                conn.commit()
                conn.close()
                logger.success("Created v2_migration_progress table")
                self._mark_step_complete(step)
            except Exception as e:
                logger.error(f"Failed to create migration tracking table: {e}")
                raise
    
    def verify_foreign_keys(self):
        """Verify foreign keys are enabled."""
        step = "verify_foreign_keys"
        
        if step in self.checkpoint["steps_completed"]:
            logger.info(f"Step already completed: {step}")
            return
        
        result = self.db.fetch("PRAGMA foreign_keys", [])
        if result and result[0]['foreign_keys'] == 1:
            logger.success("Foreign keys are enabled")
            self._mark_step_complete(step)
        else:
            logger.warning("Foreign keys are NOT enabled")
            if not self.dry_run:
                self.db.execute("PRAGMA foreign_keys=ON", [])
                logger.info("Enabled foreign keys")
                self._mark_step_complete(step)
    
    def get_migration_stats(self) -> dict:
        """Get statistics about current data."""
        stats = {}
        
        # Total items in content_unified
        result = self.db.fetch("SELECT COUNT(*) as count FROM content_unified", [])
        stats['total_content'] = result[0]['count']
        
        # Items ready for embedding
        result = self.db.fetch(
            "SELECT COUNT(*) as count FROM content_unified WHERE ready_for_embedding = 1", 
            []
        )
        stats['ready_for_embedding'] = result[0]['count']
        
        # Items already embedded
        result = self.db.fetch(
            "SELECT COUNT(*) as count FROM content_unified WHERE embedding_generated = 1", 
            []
        )
        stats['already_embedded'] = result[0]['count']
        
        # Check for existing chunks
        result = self.db.fetch(
            "SELECT COUNT(*) as count FROM content_unified WHERE source_type = 'document_chunk'",
            []
        )
        stats['existing_chunks'] = result[0]['count']
        
        # Check quality scores if column exists
        if self.check_column_exists("content_unified", "quality_score"):
            result = self.db.fetch(
                """
                SELECT 
                    MIN(quality_score) as min_score,
                    MAX(quality_score) as max_score,
                    AVG(quality_score) as avg_score,
                    COUNT(*) as scored_count
                FROM content_unified 
                WHERE quality_score IS NOT NULL
                """,
                []
            )
            if result:
                stats['quality_scores'] = {
                    'min': result[0]['min_score'],
                    'max': result[0]['max_score'],
                    'avg': result[0]['avg_score'],
                    'count': result[0]['scored_count']
                }
        
        return stats
    
    def run_migration(self):
        """Run the complete migration."""
        logger.info("=" * 60)
        logger.info("Starting Semantic Search v2 Schema Migration")
        logger.info("=" * 60)
        
        if self.dry_run:
            logger.warning("🔍 DRY RUN MODE - No changes will be made")
        
        # Record start time
        if not self.checkpoint["started_at"]:
            self.checkpoint["started_at"] = datetime.now().isoformat()
            self._save_checkpoint()
        
        # Show current stats
        logger.info("\n📊 Current Database Statistics:")
        stats = self.get_migration_stats()
        for key, value in stats.items():
            if key == 'quality_scores' and isinstance(value, dict):
                logger.info(f"  {key}:")
                for k, v in value.items():
                    logger.info(f"    {k}: {v}")
            else:
                logger.info(f"  {key}: {value}")
        
        # Run migration steps
        logger.info("\n🚀 Running Migration Steps:")
        
        try:
            # Step 1: Verify foreign keys
            self.verify_foreign_keys()
            
            # Step 2: Add metadata column
            self.add_metadata_column()
            
            # Step 3: Add quality_score column
            self.add_quality_score_column()
            
            # Step 4: Add quality score index
            self.add_quality_score_index()
            
            # Step 5: Add chunk indices
            self.add_chunk_indices()
            
            # Step 6: Create migration tracking table
            self.create_migration_tracking_table()
            
            # Mark migration complete
            if not self.dry_run:
                self.checkpoint["finished_at"] = datetime.now().isoformat()
                self._save_checkpoint()
            
            # Show final stats
            logger.info("\n📊 Final Database Statistics:")
            final_stats = self.get_migration_stats()
            for key, value in final_stats.items():
                if key == 'quality_scores' and isinstance(value, dict):
                    logger.info(f"  {key}:")
                    for k, v in value.items():
                        logger.info(f"    {k}: {v}")
                else:
                    logger.info(f"  {key}: {value}")
            
            logger.success("\n✅ Migration completed successfully!")
            
            if self.dry_run:
                logger.info("\n💡 To apply these changes, run without --dry-run flag")
            
        except Exception as e:
            logger.error(f"\n❌ Migration failed: {e}")
            if not self.dry_run:
                logger.info("Migration checkpoint saved - can resume from last successful step")
            raise


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Migrate database schema for Semantic Search v2"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview changes without applying them"
    )
    parser.add_argument(
        "--db-path",
        default="data/system_data/emails.db",
        help="Path to database file"
    )
    parser.add_argument(
        "--reset",
        action="store_true",
        help="Reset migration checkpoint and start fresh"
    )
    
    args = parser.parse_args()
    
    # Reset checkpoint if requested
    if args.reset:
        checkpoint_file = Path("data/system_data/.migration_v2_checkpoint.json")
        if checkpoint_file.exists():
            checkpoint_file.unlink()
            logger.info("Reset migration checkpoint")
    
    # Run migration
    migration = SchemaV2Migration(db_path=args.db_path, dry_run=args.dry_run)
    
    try:
        migration.run_migration()
        return 0
    except Exception as e:
        logger.error(f"Migration failed: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())