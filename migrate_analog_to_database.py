#!/usr/bin/env python3
"""
Migrate analog database content to SQL database tables.

Processes markdown files from analog_db and populates the database tables
needed for search intelligence and vector search integration.
"""

import os
import sys
import sqlite3
import frontmatter
import json
from pathlib import Path
from typing import Dict, List, Any
from datetime import datetime

# Add project root to path
sys.path.append(str(Path(__file__).parent))

from loguru import logger
from shared.simple_db import SimpleDB


class AnalogMigrator:
    """Migrate analog database content to SQL database."""
    
    def __init__(self, project_root: Path = None):
        """Initialize migrator."""
        self.project_root = project_root or Path.cwd()
        self.analog_db_path = self.project_root / "analog_db"
        self.db = SimpleDB()
        
        # Migration statistics
        self.stats = {
            "processed": 0,
            "emails": 0,
            "documents": 0,
            "threads": 0,
            "errors": 0,
            "skipped": 0
        }
    
    def migrate_all_content(self):
        """Migrate all analog content to database."""
        logger.info("Starting analog database migration...")
        
        # Process documents directory
        documents_path = self.analog_db_path / "documents"
        if documents_path.exists():
            self._process_documents_directory(documents_path)
        
        # Process email threads directory  
        threads_path = self.analog_db_path / "threads"
        if threads_path.exists():
            self._process_threads_directory(threads_path)
        
        # Print migration summary
        self._print_migration_summary()
        
        return self.stats
    
    def _process_documents_directory(self, path: Path):
        """Process documents directory."""
        logger.info(f"Processing documents from: {path}")
        
        for md_file in path.rglob("*.md"):
            try:
                self._process_document_file(md_file)
                self.stats["documents"] += 1
            except Exception as e:
                logger.error(f"Error processing document {md_file}: {e}")
                self.stats["errors"] += 1
    
    def _process_threads_directory(self, path: Path):
        """Process email threads directory."""
        logger.info(f"Processing email threads from: {path}")
        
        for md_file in path.rglob("*.md"):
            try:
                self._process_thread_file(md_file)
                self.stats["threads"] += 1
            except Exception as e:
                logger.error(f"Error processing thread {md_file}: {e}")
                self.stats["errors"] += 1
    
    def _process_document_file(self, file_path: Path):
        """Process a single document markdown file."""
        with open(file_path, 'r', encoding='utf-8') as f:
            post = frontmatter.load(f)
        
        metadata = post.metadata
        content = post.content
        
        # Extract document metadata
        doc_type = metadata.get('doc_type', 'document')
        title = metadata.get('title', file_path.stem)
        doc_id = metadata.get('doc_id', file_path.stem)
        
        # Check if this is an email document
        if doc_type == 'email':
            self._insert_email_content(doc_id, metadata, content, file_path)
            self.stats["emails"] += 1
        else:
            self._insert_document_content(doc_id, metadata, content, file_path)
        
        # Insert into unified content table
        self._insert_unified_content(doc_id, doc_type, title, content, metadata)
        
        self.stats["processed"] += 1
        
        if self.stats["processed"] % 10 == 0:
            logger.info(f"Processed {self.stats['processed']} files...")
    
    def _process_thread_file(self, file_path: Path):
        """Process an email thread markdown file."""
        with open(file_path, 'r', encoding='utf-8') as f:
            post = frontmatter.load(f)
        
        metadata = post.metadata
        content = post.content
        
        # Extract thread metadata
        thread_id = metadata.get('thread_id', file_path.stem)
        title = metadata.get('title', metadata.get('subject', file_path.stem))
        
        # Insert as email content
        self._insert_email_content(thread_id, metadata, content, file_path, is_thread=True)
        
        # Insert into unified content table
        self._insert_unified_content(thread_id, 'email_thread', title, content, metadata)
        
        self.stats["processed"] += 1
        self.stats["emails"] += 1
    
    def _insert_email_content(self, email_id: str, metadata: Dict, content: str, file_path: Path, is_thread: bool = False):
        """Insert email content into emails table."""
        try:
            # Extract email fields
            sender = metadata.get('sender', 'unknown@unknown.com')
            recipient = metadata.get('recipient', metadata.get('recipient_to', ''))
            subject = metadata.get('subject', metadata.get('title', ''))
            datetime_utc = metadata.get('datetime_utc', metadata.get('date_created', datetime.now().isoformat()))
            
            # Insert into emails table
            query = """
                INSERT OR REPLACE INTO emails 
                (message_id, sender, recipient_to, subject, content, datetime_utc, created_at)
                VALUES (?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            """
            
            self.db.execute(query, (email_id, sender, recipient, subject, content, datetime_utc))
            
        except Exception as e:
            logger.error(f"Error inserting email {email_id}: {e}")
            raise
    
    def _insert_document_content(self, doc_id: str, metadata: Dict, content: str, file_path: Path):
        """Insert document content into documents table."""
        try:
            # Extract document fields
            file_name = file_path.name
            char_count = len(content)
            file_size = file_path.stat().st_size if file_path.exists() else 0
            modified_time = file_path.stat().st_mtime if file_path.exists() else 0
            
            # Create chunk (for now, treat each document as one chunk)
            chunk_id = f"{doc_id}_0"
            
            query = """
                INSERT OR REPLACE INTO documents 
                (chunk_id, file_path, file_name, chunk_index, text_content, char_count, 
                 file_size, modified_time, processed_time, content_type)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP, ?)
            """
            
            content_type = metadata.get('doc_type', 'document')
            
            self.db.execute(query, (
                chunk_id, str(file_path), file_name, 0, content, char_count,
                file_size, modified_time, content_type
            ))
            
        except Exception as e:
            logger.error(f"Error inserting document {doc_id}: {e}")
            raise
    
    def _insert_unified_content(self, content_id: str, content_type: str, title: str, content: str, metadata: Dict):
        """Insert into unified content table for search intelligence."""
        try:
            # Serialize metadata
            metadata_json = json.dumps(metadata, default=str)
            
            query = """
                INSERT OR REPLACE INTO content 
                (id, type, title, content, metadata, content_type, char_count, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            """
            
            self.db.execute(query, (
                content_id, content_type, title, content, metadata_json, 
                content_type, len(content)
            ))
            
        except Exception as e:
            logger.error(f"Error inserting unified content {content_id}: {e}")
            raise
    
    def _print_migration_summary(self):
        """Print migration statistics."""
        logger.info("\n" + "="*50)
        logger.info("MIGRATION SUMMARY")
        logger.info("="*50)
        logger.info(f"Total files processed: {self.stats['processed']}")
        logger.info(f"Documents: {self.stats['documents']}")
        logger.info(f"Emails: {self.stats['emails']}")
        logger.info(f"Threads: {self.stats['threads']}")
        logger.info(f"Errors: {self.stats['errors']}")
        logger.info(f"Skipped: {self.stats['skipped']}")
        
        # Verify database counts
        try:
            email_count = self.db.fetch("SELECT COUNT(*) as count FROM emails")[0]["count"]
            doc_count = self.db.fetch("SELECT COUNT(*) as count FROM documents")[0]["count"]
            content_count = self.db.fetch("SELECT COUNT(*) as count FROM content")[0]["count"]
            
            logger.info(f"\nDatabase verification:")
            logger.info(f"Emails table: {email_count} rows")
            logger.info(f"Documents table: {doc_count} rows")
            logger.info(f"Content table: {content_count} rows")
            
        except Exception as e:
            logger.error(f"Error verifying database: {e}")


def main():
    """Run the migration."""
    migrator = AnalogMigrator()
    
    # Check if analog database exists
    if not migrator.analog_db_path.exists():
        logger.error(f"Analog database not found at: {migrator.analog_db_path}")
        sys.exit(1)
    
    logger.info(f"Migrating analog database from: {migrator.analog_db_path}")
    
    try:
        stats = migrator.migrate_all_content()
        
        if stats["errors"] == 0:
            logger.info("✅ Migration completed successfully!")
        else:
            logger.warning(f"⚠️ Migration completed with {stats['errors']} errors")
        
        return 0 if stats["errors"] == 0 else 1
        
    except Exception as e:
        logger.error(f"Migration failed: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())