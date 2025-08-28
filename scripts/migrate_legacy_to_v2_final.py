#!/usr/bin/env python3
"""
Nuclear Reset v2: Final migration from emails_legacy to v2 schema.
Ensures all legacy email data is properly migrated to individual_messages + content_unified.
"""

import hashlib
import json
import sqlite3
from datetime import datetime
from pathlib import Path
import sys

# Add parent directory for imports
sys.path.append(str(Path(__file__).parent.parent))

from loguru import logger
from shared.simple_db import SimpleDB
from shared.email_cleaner import EmailCleaner


def compute_message_hash(row: sqlite3.Row) -> str:
    """
    Compute deterministic message hash from email content.
    Uses normalized key fields to ensure consistent hashing.
    """
    def norm(val):
        """Normalize value for hashing."""
        return (val or "").strip().lower()
    
    # Build deterministic key from core email fields
    key_parts = [
        norm(row.get("message_id", "")),
        norm(row.get("datetime_utc", "")),
        norm(row.get("sender", "")),
        norm(row.get("recipient", "")),
        norm(row.get("subject", "")),
        norm(row.get("content", ""))[:1000]  # First 1000 chars of content
    ]
    
    key = "|".join(key_parts)
    return hashlib.sha256(key.encode("utf-8")).hexdigest()


def migrate_legacy_emails():
    """
    One-shot migration from emails_legacy_backup_20250828 to v2 schema.
    """
    db = SimpleDB()
    cleaner = EmailCleaner()
    
    # Statistics
    stats = {
        "legacy_total": 0,
        "migrated_messages": 0,
        "migrated_content": 0,
        "duplicates_skipped": 0,
        "errors": 0,
        "error_details": []
    }
    
    # Get all legacy emails
    legacy_emails = db.fetch("""
        SELECT * FROM emails_legacy_backup_20250828 
        ORDER BY id
    """)
    
    stats["legacy_total"] = len(legacy_emails)
    logger.info(f"Found {stats['legacy_total']} legacy emails to migrate")
    
    # Process each email
    for idx, email in enumerate(legacy_emails, 1):
        try:
            # Compute message hash
            message_hash = compute_message_hash(email)
            
            # Extract clean content using EmailCleaner
            content = email.get('content', '') or email.get('body', '')
            full_text, substantive_text = cleaner.extract_substantive_text(
                content, 
                document_type='email'
            )
            
            # Prepare metadata
            metadata = {
                "content": {
                    "full_text": full_text,
                    "substantive_text": substantive_text,
                    "sha256_hash": message_hash,
                    "is_ocr": False
                },
                "source_specific": {
                    "email_details": {
                        "message_id": email.get('message_id'),
                        "thread_id": email.get('thread_id'),
                        "in_reply_to": email.get('in_reply_to'),
                        "reference_ids": json.loads(email.get('references', '[]')) if email.get('references') else [],
                        "cc": json.loads(email.get('cc', '[]')) if email.get('cc') else [],
                        "bcc": json.loads(email.get('bcc', '[]')) if email.get('bcc') else [],
                        "importance": email.get('importance', 'normal'),
                        "labels": json.loads(email.get('labels', '[]')) if email.get('labels') else []
                    }
                },
                "legacy_migration": {
                    "original_id": email.get('id'),
                    "migrated_at": datetime.now().isoformat(),
                    "migration_version": "v2_final"
                }
            }
            
            # Step 1: Insert into individual_messages (deduplication table)
            existing_msg = db.fetch_one(
                "SELECT message_hash FROM individual_messages WHERE message_hash = ?",
                (message_hash,)
            )
            
            if not existing_msg:
                # Parse recipients
                recipients = []
                if email.get('recipient'):
                    recipients.append(email['recipient'])
                if email.get('recipient_to'):
                    recipients.append(email['recipient_to'])
                if email.get('cc'):
                    cc_list = json.loads(email['cc']) if isinstance(email['cc'], str) else email['cc']
                    recipients.extend(cc_list if isinstance(cc_list, list) else [cc_list])
                
                db.execute("""
                    INSERT INTO individual_messages (
                        message_hash, content, subject, sender_email,
                        recipients, date_sent, message_id, thread_id,
                        content_type, created_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    message_hash,
                    substantive_text,
                    email.get('subject', ''),
                    email.get('sender', ''),
                    json.dumps(list(set(recipients))),  # Deduplicate recipients
                    email.get('datetime_utc'),
                    email.get('message_id'),
                    email.get('thread_id'),
                    'original',  # content_type
                    datetime.now().isoformat()
                ))
                stats["migrated_messages"] += 1
            else:
                stats["duplicates_skipped"] += 1
            
            # Step 2: Insert into content_unified (main content table)
            existing_content = db.fetch_one(
                "SELECT id FROM content_unified WHERE source_id = ? AND source_type = ?",
                (message_hash, 'email_message')
            )
            
            if not existing_content:
                db.execute("""
                    INSERT INTO content_unified (
                        source_type, source_id, title, body,
                        substantive_text, sha256, metadata,
                        created_at, quality_score, ready_for_embedding
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    'email_message',  # Correct singular form
                    message_hash,     # Use message_hash as source_id
                    email.get('subject', ''),
                    full_text,
                    substantive_text,
                    message_hash,
                    json.dumps(metadata),
                    email.get('datetime_utc', datetime.now().isoformat()),
                    1.0,  # quality_score
                    1     # ready_for_embedding
                ))
                stats["migrated_content"] += 1
            
            # Progress indicator
            if idx % 50 == 0:
                logger.info(f"Progress: {idx}/{stats['legacy_total']} emails processed")
                
        except Exception as e:
            stats["errors"] += 1
            error_detail = f"Email ID {email.get('id')}: {str(e)}"
            stats["error_details"].append(error_detail)
            logger.error(error_detail)
    
    # Final statistics
    logger.info("=" * 60)
    logger.info("Migration Complete!")
    logger.info(f"Legacy emails found: {stats['legacy_total']}")
    logger.info(f"Messages migrated: {stats['migrated_messages']}")
    logger.info(f"Content records created: {stats['migrated_content']}")
    logger.info(f"Duplicates skipped: {stats['duplicates_skipped']}")
    logger.info(f"Errors: {stats['errors']}")
    
    # Verification queries
    verification = db.fetch_one("""
        SELECT 
            (SELECT COUNT(*) FROM emails_legacy_backup_20250828) as legacy_count,
            (SELECT COUNT(*) FROM individual_messages) as messages_count,
            (SELECT COUNT(*) FROM content_unified WHERE source_type='email_message') as content_count
    """)
    
    logger.info("=" * 60)
    logger.info("Verification:")
    logger.info(f"Legacy table: {verification['legacy_count']} records")
    logger.info(f"individual_messages: {verification['messages_count']} records")
    logger.info(f"content_unified (email_message): {verification['content_count']} records")
    
    # Check for orphans
    orphans = db.fetch_one("""
        SELECT COUNT(*) as orphan_count
        FROM content_unified cu
        LEFT JOIN individual_messages im ON cu.source_id = im.message_hash
        WHERE cu.source_type='email_message' AND im.message_hash IS NULL
    """)
    
    if orphans['orphan_count'] > 0:
        logger.warning(f"⚠️  Found {orphans['orphan_count']} orphaned content_unified records")
    else:
        logger.info("✅ No orphaned content_unified records")
    
    return stats


if __name__ == "__main__":
    logger.info("Starting Nuclear Reset v2: Legacy Email Migration")
    logger.info("=" * 60)
    
    # Run migration
    result = migrate_legacy_emails()
    
    # Print summary
    print("\n" + "=" * 60)
    print("MIGRATION SUMMARY")
    print("=" * 60)
    print(f"✅ Messages migrated: {result['migrated_messages']}")
    print(f"✅ Content records: {result['migrated_content']}")
    print(f"⏭️  Duplicates skipped: {result['duplicates_skipped']}")
    if result['errors'] > 0:
        print(f"❌ Errors: {result['errors']}")
        for error in result['error_details'][:5]:  # Show first 5 errors
            print(f"   - {error}")
    print("=" * 60)