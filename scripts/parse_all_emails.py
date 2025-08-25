#!/usr/bin/env python3
"""Parse the all_emails.txt file and process with message deduplication.

This file has a specific format: TIMESTAMP | FROM | TO | SUBJECT | BODY
"""

import re
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent))

from loguru import logger
from shared.simple_db import SimpleDB
from email_parsing.message_deduplicator import MessageDeduplicator

def parse_all_emails_file(file_path: str):
    """
    Parse the all_emails.txt file which contains all emails in a single file.
    """
    
    db = SimpleDB()
    deduplicator = MessageDeduplicator()
    
    with open(file_path, encoding='utf-8', errors='ignore') as f:
        content = f.read()
    
    # Split by the pattern: TIMESTAMP | FROM | TO | SUBJECT | BODY
    # Pattern: 2024-08-09T17:46:41+00:00 | email@domain | email@domain | subject |
    pattern = r'^(\d{4}-\d{2}-\d{2}T[\d:+-]+)\s*\|\s*([^|]+)\s*\|\s*([^|]+)\s*\|\s*([^|]*)\s*\|\s*(.*?)(?=^\d{4}-\d{2}-\d{2}T|\Z)'
    
    matches = re.findall(pattern, content, re.MULTILINE | re.DOTALL)
    
    logger.info(f"Found {len(matches)} emails in the file")
    
    stats = {
        'total_emails': len(matches),
        'processed': 0,
        'unique_messages': 0,
        'total_occurrences': 0,
        'errors': 0
    }
    
    for i, (timestamp, sender, recipient, subject, body) in enumerate(matches, 1):
        try:
            # Clean the fields
            sender = sender.strip()
            recipient = recipient.strip()
            subject = subject.strip()
            body = body.strip()
            
            # Create email format for parser
            email_content = f"""From: {sender}
To: {recipient}
Subject: {subject}
Date: {timestamp}

{body}"""
            
            # Generate email ID from timestamp and sender
            email_id = f"email_{i:04d}_{sender.split('@')[0]}_{timestamp[:10]}"
            
            logger.debug(f"Processing email {i}/{len(matches)}: {subject[:50]}...")
            
            # Parse messages using deduplicator
            messages = deduplicator.parse_email_thread(email_content, email_id)
            
            if not messages:
                logger.debug(f"No messages extracted from email {i}")
                continue
            
            # Deduplicate messages
            unique_messages = deduplicator.deduplicate_messages(messages)
            
            # Store in database
            for msg_hash, msg_data in unique_messages.items():
                # Add to individual_messages table
                is_new = db.add_individual_message(
                    message_hash=msg_hash,
                    content=msg_data['content'],
                    subject=msg_data.get('subject', subject),
                    sender_email=msg_data.get('sender', sender),
                    sender_name=None,
                    recipients=[recipient] if recipient else None,
                    date_sent=msg_data.get('date'),
                    message_id=None,
                    parent_message_id=None,
                    thread_id=None,
                    content_type=msg_data.get('context_type', 'original'),
                    first_seen_email_id=email_id
                )
                
                if is_new:
                    stats['unique_messages'] += 1
                    
                    # Also add to content_unified for vector search
                    db.add_content(
                        content_type='email_message',
                        title=msg_data.get('subject', subject) or f"Message from {sender}",
                        content=msg_data['content'],
                        message_hash=msg_hash
                    )
                
                # Record all occurrences
                for occurrence in msg_data.get('occurrences', []):
                    db.add_message_occurrence(
                        message_hash=msg_hash,
                        email_id=email_id,
                        position_in_email=occurrence.get('position', 0),
                        context_type=occurrence.get('context_type', 'original'),
                        quote_depth=occurrence.get('quote_depth', 0)
                    )
                    stats['total_occurrences'] += 1
            
            stats['processed'] += 1
            
            # Progress update every 10 emails
            if i % 10 == 0:
                logger.info(f"Progress: {i}/{len(matches)} emails processed, "
                           f"{stats['unique_messages']} unique messages found")
                
        except Exception as e:
            logger.error(f"Error processing email {i}: {e}")
            stats['errors'] += 1
            continue
    
    # Final statistics
    logger.info("=" * 60)
    logger.info("EMAIL PROCESSING COMPLETE")
    logger.info("=" * 60)
    logger.info(f"Total emails found:      {stats['total_emails']}")
    logger.info(f"Successfully processed:  {stats['processed']}")
    logger.info(f"Unique messages:         {stats['unique_messages']}")
    logger.info(f"Total occurrences:       {stats['total_occurrences']}")
    logger.info(f"Errors:                  {stats['errors']}")
    
    if stats['total_occurrences'] > 0:
        dedup_rate = (1 - stats['unique_messages'] / stats['total_occurrences']) * 100
        logger.info(f"Deduplication rate:      {dedup_rate:.1f}%")
    
    return stats

def main():
    file_path = 'data/all_emails.txt'
    
    if not Path(file_path).exists():
        logger.error(f"File not found: {file_path}")
        sys.exit(1)
    
    logger.info(f"Starting to parse {file_path}")
    parse_all_emails_file(file_path)
    
    # Verify in database
    db = SimpleDB()
    msg_count = db.fetch_one("SELECT COUNT(*) as count FROM individual_messages")
    logger.info(f"\nDatabase verification: {msg_count['count']} messages in individual_messages table")

if __name__ == '__main__':
    main()