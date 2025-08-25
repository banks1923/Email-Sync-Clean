#!/usr/bin/env python3
"""
Email Consolidation Script
Extracts all emails from SQLite database and creates consolidated outputs
"""

import sqlite3
import json
from pathlib import Path
import sys

def main():
    # Database path
    db_path = Path("data/system_data/emails.db")
    
    if not db_path.exists():
        print(f"❌ Database not found at {db_path}")
        sys.exit(1)
    
    print(f"📧 Connecting to database: {db_path}")
    
    # Connect to database
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    # Query all emails ordered by date
    query = """
    SELECT 
        id,
        message_id,
        thread_id,
        subject,
        sender,
        recipient_to,
        content,
        datetime_utc,
        content_hash,
        created_at,
        eid
    FROM emails
    ORDER BY datetime_utc ASC
    """
    
    print("📊 Fetching all emails...")
    cursor.execute(query)
    emails = cursor.fetchall()
    
    print(f"✅ Found {len(emails)} emails")
    
    # Prepare outputs
    text_lines = []
    json_data = []
    
    for email in emails:
        # Parse date
        email_date = email['datetime_utc'] if email['datetime_utc'] else 'NO_DATE'
        
        # Parse recipients
        recipients = email['recipient_to'] if email['recipient_to'] else 'NO_RECIPIENTS'
        
        # Clean body text
        body = (email['content'] or '').strip()
        body = body.replace('\n', ' ').replace('\r', ' ')
        # Truncate very long bodies for text format
        body_preview = body[:500] + '...' if len(body) > 500 else body
        
        # Format for text file
        text_line = f"{email_date} | {email['sender']} | {recipients} | {email['subject'] or 'NO_SUBJECT'} | {body_preview}"
        text_lines.append(text_line)
        
        # Full data for JSON
        json_entry = {
            'id': email['id'],
            'message_id': email['message_id'],
            'thread_id': email['thread_id'],
            'datetime_utc': email['datetime_utc'],
            'sender': email['sender'],
            'recipient_to': email['recipient_to'],
            'subject': email['subject'],
            'content': email['content'],
            'content_hash': email['content_hash'],
            'created_at': email['created_at'],
            'eid': email['eid']
        }
        json_data.append(json_entry)
    
    # Write text file
    text_output = Path("consolidated_emails.txt")
    with open(text_output, 'w', encoding='utf-8') as f:
        f.write("DATE | FROM | TO | SUBJECT | BODY\n")
        f.write("=" * 100 + "\n")
        for line in text_lines:
            f.write(line + "\n")
    
    print(f"✅ Wrote text format to {text_output}")
    print(f"   File size: {text_output.stat().st_size:,} bytes")
    
    # Write JSON file
    json_output = Path("consolidated_emails.json")
    with open(json_output, 'w', encoding='utf-8') as f:
        json.dump(json_data, f, indent=2, ensure_ascii=False, default=str)
    
    print(f"✅ Wrote JSON format to {json_output}")
    print(f"   File size: {json_output.stat().st_size:,} bytes")
    
    # Summary statistics
    print("\n📊 Summary Statistics:")
    print(f"   Total emails: {len(emails)}")
    
    if emails:
        # Date range
        dates = [e['datetime_utc'] for e in emails if e['datetime_utc']]
        if dates:
            print(f"   Date range: {min(dates)} to {max(dates)}")
        
        # Top senders
        senders = {}
        for email in emails:
            sender = email['sender'] or 'Unknown'
            senders[sender] = senders.get(sender, 0) + 1
        
        print("\n   Top 5 senders:")
        for sender, count in sorted(senders.items(), key=lambda x: x[1], reverse=True)[:5]:
            print(f"      {sender}: {count} emails")
    
    conn.close()
    print("\n✅ Email consolidation complete!")

if __name__ == "__main__":
    main()