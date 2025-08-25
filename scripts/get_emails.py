#!/usr/bin/env python3
"""Simple script to extract Stoneman-related emails from database."""

import sqlite3

# Connect to database
db_path = "/Users/jim/Projects/Litigator_solo/data/system_data/emails.db"
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# Run query
query = """
SELECT datetime_utc, sender, recipient_to, subject, content 
FROM emails 
WHERE subject LIKE '%Stoneman%' OR content LIKE '%Stoneman%' 
ORDER BY datetime_utc
"""

cursor.execute(query)
results = cursor.fetchall()

# Write to file
with open("all_emails.txt", "w") as f:
    for row in results:
        date, sender, recipient, subject, body = row
        # Handle None values
        date = date or ""
        sender = sender or ""
        recipient = recipient or ""
        subject = subject or ""
        body = body or ""
        
        f.write(f"{date} | {sender} | {recipient} | {subject} | {body}\n")

# Print count
print(f"Found {len(results)} emails")

conn.close()