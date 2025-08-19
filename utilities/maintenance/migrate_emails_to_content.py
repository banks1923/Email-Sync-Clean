#!/usr/bin/env python3
"""
Migrate emails from emails table to content table with business keys.
This script handles the core data migration.
"""

import hashlib
import json
from uuid import UUID, uuid5

from loguru import logger
from shared.simple_db import SimpleDB

# UUID namespace for deterministic ID generation
UUID_NAMESPACE = UUID('6ba7b810-9dad-11d1-80b4-00c04fd430c8')

def migrate_emails_to_content(dry_run: bool = True) -> dict:
    """Migrate all emails to content table using business keys."""
    
    db = SimpleDB()
    metrics = {
        'emails_found': 0,
        'emails_migrated': 0,
        'emails_updated': 0,
        'emails_skipped': 0,
        'errors': []
    }
    
    # Get all emails
    try:
        emails = db.fetch("""
            SELECT message_id, subject, sender, recipient_to, content, 
                   datetime_utc, content_hash, created_at
            FROM emails
            ORDER BY datetime_utc
        """)
        
        metrics['emails_found'] = len(emails)
        logger.info(f"Found {len(emails)} emails to migrate")
        
        # Create UNIQUE index on business key if not exists
        if not dry_run:
            try:
                db.execute("""
                    CREATE UNIQUE INDEX IF NOT EXISTS content_uniq_business 
                    ON content(source_type, external_id)
                """)
                logger.info("Created business key unique index")
            except Exception as e:
                logger.warning(f"Could not create index: {e}")
        
        # Process emails in batches
        batch_size = 200
        for i in range(0, len(emails), batch_size):
            batch = emails[i:i+batch_size]
            logger.info(f"Processing batch {i//batch_size + 1} ({len(batch)} emails)")
            
            for email in batch:
                try:
                    # Generate deterministic UUID from message_id
                    content_id = str(uuid5(UUID_NAMESPACE, f"email:{email['message_id']}"))
                    
                    # Prepare content
                    title = email['subject'] or f"Email from {email['sender']}"
                    body = email['content'] or ""
                    
                    # Calculate content hash
                    content_hash = hashlib.sha256(body.encode('utf-8')).hexdigest()
                    
                    # Prepare metadata
                    metadata = {
                        'sender': email['sender'],
                        'recipient_to': email['recipient_to'],
                        'datetime_utc': email['datetime_utc'],
                        'original_hash': email['content_hash']
                    }
                    metadata_json = json.dumps(metadata, ensure_ascii=False)
                    
                    if not dry_run:
                        # UPSERT into content table
                        cursor = db.execute("""
                            INSERT INTO content (
                                id, source_type, external_id, content_type, type, 
                                title, content, metadata, content_hash, char_count,
                                created_at, updated_at
                            )
                            VALUES (?, 'email', ?, 'email', 'email', ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                            ON CONFLICT(source_type, external_id) DO UPDATE SET
                                title = excluded.title,
                                content = excluded.content,
                                metadata = excluded.metadata,
                                content_hash = excluded.content_hash,
                                char_count = excluded.char_count,
                                updated_at = CURRENT_TIMESTAMP
                        """, (
                            content_id,
                            email['message_id'],
                            title,
                            body,
                            metadata_json,
                            content_hash,
                            len(body),
                            email['created_at']
                        ))
                        
                        if cursor.rowcount > 0:
                            # Check if this was an INSERT or UPDATE
                            check_existing = db.fetch_one(
                                "SELECT COUNT(*) as count FROM content WHERE source_type='email' AND external_id=? AND updated_at < CURRENT_TIMESTAMP",
                                (email['message_id'],)
                            )
                            if check_existing and check_existing['count'] > 0:
                                metrics['emails_updated'] += 1
                            else:
                                metrics['emails_migrated'] += 1
                        else:
                            metrics['emails_skipped'] += 1
                    else:
                        # Dry run - just count
                        metrics['emails_migrated'] += 1
                        
                except Exception as e:
                    error_msg = f"Error migrating email {email['message_id']}: {e}"
                    logger.error(error_msg)
                    metrics['errors'].append(error_msg)
        
        logger.info("=== EMAIL MIGRATION COMPLETE ===")
        logger.info(f"Found: {metrics['emails_found']}")
        logger.info(f"Migrated: {metrics['emails_migrated']}")
        logger.info(f"Updated: {metrics['emails_updated']}")
        logger.info(f"Skipped: {metrics['emails_skipped']}")
        logger.info(f"Errors: {len(metrics['errors'])}")
        
        if not dry_run and metrics['emails_migrated'] > 0:
            # Trigger maintenance
            logger.info("Running database maintenance...")
            db.db_maintenance(force=True)
            
        return metrics
        
    except Exception as e:
        logger.error(f"Email migration failed: {e}")
        metrics['errors'].append(str(e))
        return metrics


def verify_migration() -> dict:
    """Verify the email migration was successful."""
    
    db = SimpleDB()
    results = {}
    
    # Check counts
    email_count = db.fetch_one("SELECT COUNT(*) as count FROM emails")['count']
    email_content_count = db.fetch_one(
        "SELECT COUNT(*) as count FROM content WHERE source_type = 'email'"
    )['count']
    
    results['email_count'] = email_count
    results['email_content_count'] = email_content_count
    results['migration_complete'] = email_content_count >= email_count
    
    # Check for duplicates
    duplicates = db.fetch("""
        SELECT external_id, COUNT(*) as count
        FROM content 
        WHERE source_type = 'email'
        GROUP BY external_id 
        HAVING COUNT(*) > 1
    """)
    results['duplicates'] = len(duplicates)
    
    # Sample verification - check a few emails exist in content
    sample_emails = db.fetch("SELECT message_id FROM emails LIMIT 5")
    sample_found = 0
    for email in sample_emails:
        content_exists = db.fetch_one(
            "SELECT id FROM content WHERE source_type='email' AND external_id=?",
            (email['message_id'],)
        )
        if content_exists:
            sample_found += 1
    
    results['sample_verification'] = f"{sample_found}/{len(sample_emails)} sample emails found in content"
    
    logger.info("=== MIGRATION VERIFICATION ===")
    for key, value in results.items():
        logger.info(f"{key}: {value}")
    
    return results


def main():
    """Run email migration."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Migrate emails to content table")
    parser.add_argument('--dry-run', action='store_true',
                       help='Show what would be done without making changes')
    parser.add_argument('--verify', action='store_true',
                       help='Verify migration results')
    
    args = parser.parse_args()
    
    if args.verify:
        verify_migration()
        return 0
    
    metrics = migrate_emails_to_content(dry_run=args.dry_run)
    
    if metrics['errors']:
        logger.error(f"Migration completed with {len(metrics['errors'])} errors")
        return 1
    else:
        logger.info("Migration completed successfully")
        
        if not args.dry_run:
            logger.info("Running verification...")
            verify_migration()
        
        return 0


if __name__ == "__main__":
    exit(main())