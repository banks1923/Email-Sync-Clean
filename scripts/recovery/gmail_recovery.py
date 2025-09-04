#!/usr/bin/env python3
"""
Gmail Recovery Script - Populate database from Gmail API
Handles proper foreign key constraints for v2 schema
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from gmail.gmail_api import GmailAPI
from gmail.config import GmailConfig
from shared.simple_db import SimpleDB
from loguru import logger
import hashlib
from datetime import datetime
import json

def normalize_message_content(text):
    """Normalize message for consistent hashing"""
    if not text:
        return ""
    # Basic normalization
    text = text.strip()
    text = '\n'.join(line.strip() for line in text.split('\n'))
    text = ' '.join(text.split())
    return text

def process_gmail_message(api, msg_id, db):
    """Process a single Gmail message"""
    try:
        # Get message details
        result = api.get_message_detail(msg_id)
        if not result or not result.get('success'):
            return False
            
        message = result.get('data', {})
        if not message:
            return False
            
        # Extract basic info
        headers = {h['name']: h['value'] for h in message.get('payload', {}).get('headers', [])}
        subject = headers.get('Subject', 'No Subject')
        sender = headers.get('From', '')
        date_str = headers.get('Date', '')
        message_id_header = headers.get('Message-ID', f'<{msg_id}@gmail>')
        
        # Parse message and get body content
        parsed = api.parse_message(message)
        body = parsed.get('content', '')
        if not body:
            logger.warning(f"No body found for message {msg_id}")
            return False
            
        # Normalize and hash
        normalized = normalize_message_content(body)
        message_hash = hashlib.sha256(normalized.encode()).hexdigest()
        
        # Parse date
        try:
            from email.utils import parsedate_to_datetime
            date_sent = parsedate_to_datetime(date_str) if date_str else datetime.now()
        except:
            date_sent = datetime.now()
            
        # Extract recipients
        recipients = []
        for field in ['To', 'Cc', 'Bcc']:
            if field in headers:
                recipients.extend([r.strip() for r in headers[field].split(',')])
                
        # Store in individual_messages first (required for FK)
        db.execute("""
            INSERT OR IGNORE INTO individual_messages 
            (message_hash, content, subject, sender_email, recipients, 
             date_sent, message_id, thread_id, content_type)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            message_hash, 
            body,
            subject,
            sender,
            json.dumps(recipients),
            date_sent.isoformat(),
            message_id_header,
            message.get('threadId', ''),
            'original'
        ))
        
        # Then store in content_unified
        content_hash = hashlib.sha256(body.encode()).hexdigest()
        db.execute("""
            INSERT OR IGNORE INTO content_unified
            (source_type, source_id, title, body, sha256, 
             ready_for_embedding, validation_status, metadata)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            'email_message',
            message_hash,  # Use message_hash as source_id
            subject,
            body,
            content_hash,
            1,  # Ready for embedding
            'validated',
            json.dumps({
                'sender': sender,
                'date': date_sent.isoformat(),
                'gmail_id': msg_id,
                'thread_id': message.get('threadId', '')
            })
        ))
        
        return True
        
    except Exception as e:
        logger.error(f"Error processing message {msg_id}: {e}")
        return False

def main():
    """Main recovery function"""
    logger.info("Starting Gmail recovery process...")
    
    # Initialize
    api = GmailAPI()
    db = SimpleDB()
    config = GmailConfig()
    
    # Get messages
    query = config.build_query()
    logger.info(f"Gmail query: {query}")
    
    result = api.get_messages(query=query, max_results=500)
    if not result.get('success'):
        logger.error("Failed to fetch messages from Gmail")
        return
        
    messages = result.get('data', [])
    logger.info(f"Found {len(messages)} messages to process")
    
    # Process messages
    success = 0
    failed = 0
    
    for i, msg in enumerate(messages, 1):
        msg_id = msg['id']
        if i % 10 == 0:
            logger.info(f"Processing message {i}/{len(messages)}...")
            
        if process_gmail_message(api, msg_id, db):
            success += 1
        else:
            failed += 1
            
    # Final stats
    logger.info(f"Recovery complete: {success} success, {failed} failed")
    
    # Check database state
    msg_count = db.execute("SELECT COUNT(*) FROM individual_messages").fetchone()[0]
    content_count = db.execute("SELECT COUNT(*) FROM content_unified WHERE source_type='email_message'").fetchone()[0]
    
    logger.info(f"Database state: {msg_count} messages, {content_count} content records")
    
if __name__ == "__main__":
    main()