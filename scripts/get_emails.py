#!/usr/bin/env python3

import sqlite3
import sys


def extract_stoneman_emails():
    """
    Extract emails containing 'Stoneman' from the database.
    """
    db_path = "/Users/jim/Projects/Litigator_solo/data/system_data/emails.db"
    output_file = "all_emails.txt"
    
    # SQL query with correct column names
    query = """
    SELECT datetime_utc, sender, recipient_to, subject, content 
    FROM emails 
    WHERE subject LIKE '%Stoneman%' OR content LIKE '%Stoneman%' 
    ORDER BY datetime_utc
    """
    
    try:
        # Connect to database
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Execute query
        cursor.execute(query)
        results = cursor.fetchall()
        
        # Write results to file
        with open(output_file, 'w', encoding='utf-8') as f:
            for row in results:
                datetime_utc, sender, recipient_to, subject, content = row
                # Format: date | sender | recipient | subject | body
                f.write(f"{datetime_utc} | {sender} | {recipient_to} | {subject} | {content}\n")
        
        # Print count
        email_count = len(results)
        print(f"Found {email_count} emails containing 'Stoneman'")
        print(f"Results written to {output_file}")
        
        conn.close()
        
    except sqlite3.Error as e:
        print(f"Database error: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    extract_stoneman_emails()