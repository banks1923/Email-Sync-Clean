#!/usr/bin/env python3
"""
Check summary generation status for emails.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from shared.simple_db import SimpleDB
import sqlite3

def check_summary_status():
    """Check current status of email summaries."""
    db = SimpleDB()
    
    with sqlite3.connect(db.db_path) as conn:
        cursor = conn.cursor()
        
        # Total emails
        cursor.execute("""
            SELECT COUNT(*) FROM content_unified 
            WHERE source_type = 'email'
        """)
        total_emails = cursor.fetchone()[0]
        
        # Emails with summaries
        cursor.execute("""
            SELECT COUNT(DISTINCT cu.id)
            FROM content_unified cu
            INNER JOIN document_summaries ds ON cu.id = ds.document_id
            WHERE cu.source_type = 'email'
        """)
        emails_with_summaries = cursor.fetchone()[0]
        
        # Total summaries (could be multiple per doc)
        cursor.execute("""
            SELECT COUNT(*)
            FROM document_summaries
        """)
        total_summaries = cursor.fetchone()[0]
        
        # Recent summaries
        cursor.execute("""
            SELECT ds.summary_id, cu.title, ds.created_at
            FROM document_summaries ds
            INNER JOIN content_unified cu ON ds.document_id = cu.id
            WHERE cu.source_type = 'email'
            ORDER BY ds.created_at DESC
            LIMIT 5
        """)
        recent = cursor.fetchall()
        
        print(f"\nEmail Summary Status:")
        print(f"  Total emails: {total_emails}")
        print(f"  Emails with summaries: {emails_with_summaries}")
        print(f"  Coverage: {emails_with_summaries/total_emails*100:.1f}%" if total_emails > 0 else "  Coverage: N/A")
        print(f"  Total summaries in DB: {total_summaries}")
        print(f"\nMost recent email summaries:")
        for sid, title, created in recent:
            print(f"  • {title[:50]:50} {created}")

if __name__ == "__main__":
    check_summary_status()