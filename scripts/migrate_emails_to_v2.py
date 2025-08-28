#!/usr/bin/env python3
"""
Migrate emails from legacy table to v2 schema with proper deduplication.
"""

import hashlib
import json
from datetime import datetime
from loguru import logger
from shared.simple_db import SimpleDB
from shared.email_cleaner import EmailCleaner

def migrate_emails_to_v2():
    """Migrate emails from legacy table to v2 schema."""
    db = SimpleDB()
    cleaner = EmailCleaner()
    
    # Get all emails from legacy table
    emails = db.fetch("SELECT * FROM emails ORDER BY id")
    logger.info(f"Found {len(emails)} emails to migrate")
    
    migrated = 0
    errors = 0
    
    for email in emails:
        try:
            # Extract substantive text (handles cleaning internally)
            content = email.get('content', '')
            full_text, substantive_text = cleaner.extract_substantive_text(
                content, 
                document_type='email'
            )
            
            # Generate message hash from substantive text
            message_hash = hashlib.sha256(substantive_text.encode()).hexdigest()
            
            # Build metadata structure
            metadata = {
                'content': {
                    'full_text': full_text,
                    'substantive_text': substantive_text,
                    'sha256_hash': message_hash,
                    'is_ocr': False
                },
                'source_specific': {
                    'email_details': {
                        'message_id': email.get('message_id'),
                        'thread_id': None,  # Not in legacy table
                        'in_reply_to': None,
                        'reference_ids': [],
                        'cc': [],
                        'bcc': [],
                        'importance': 'normal',
                        'labels': []
                    }
                },
                'search_metadata': {
                    'creation_date': email.get('datetime_utc'),
                    'tags': []
                }
            }
            
            # Insert into individual_messages
            db.execute("""
                INSERT OR IGNORE INTO individual_messages (
                    message_hash, content, subject, sender_email,
                    date_sent, message_id, content_type
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                message_hash,
                substantive_text,
                email.get('subject', ''),
                email.get('sender', ''),
                email.get('datetime_utc'),
                email.get('message_id'),
                'email'
            ))
            
            # Insert into content_unified (now foreign key will work)
            db.execute("""
                INSERT OR IGNORE INTO content_unified (
                    source_type, source_id, title, body, 
                    substantive_text, sha256, metadata,
                    created_at, quality_score
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                'email_message',
                message_hash,  # Use message_hash as source_id
                email.get('subject', ''),
                full_text,
                substantive_text,
                message_hash,
                json.dumps(metadata),
                datetime.now().isoformat(),
                1.0
            ))
            
            migrated += 1
            
        except Exception as e:
            logger.error(f"Failed to migrate email {email.get('id')}: {e}")
            errors += 1
    
    logger.info(f"Migration complete: {migrated} migrated, {errors} errors")
    
    # Check results
    v2_count = db.fetch_one("SELECT COUNT(*) as cnt FROM content_unified")['cnt']
    msg_count = db.fetch_one("SELECT COUNT(*) as cnt FROM individual_messages")['cnt']
    
    logger.info(f"Final counts - content_unified: {v2_count}, individual_messages: {msg_count}")
    
    return {
        'success': True,
        'migrated': migrated,
        'errors': errors,
        'content_unified_count': v2_count,
        'individual_messages_count': msg_count
    }

if __name__ == "__main__":
    result = migrate_emails_to_v2()
    print(f"\n✅ Migration Results:")
    print(f"   Migrated: {result['migrated']}")
    print(f"   Errors: {result['errors']}")
    print(f"   Content Unified: {result['content_unified_count']}")
    print(f"   Individual Messages: {result['individual_messages_count']}")