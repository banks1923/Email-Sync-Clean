#!/usr/bin/env python3
"""
Clean Bad Transcripts

Remove obviously problematic transcripts from the database based on quality metrics.
Focus on empty content, very low confidence, and wrong language detection.
"""

import sqlite3
import json

def clean_bad_transcripts(db_path: str = "emails.db", dry_run: bool = True):
    """Clean problematic transcripts from database.
    
    Args:
        db_path: Database file path
        dry_run: If True, only show what would be deleted
    """
    
    print("=== TRANSCRIPT CLEANUP ===")
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Find problematic transcripts
    cursor.execute('''
        SELECT content_id, title, content, metadata, word_count
        FROM content 
        WHERE content_type = "transcript"
    ''')
    
    all_transcripts = cursor.fetchall()
    to_delete = []
    
    print(f"Analyzing {len(all_transcripts)} transcripts...")
    
    for content_id, title, content, metadata_str, word_count in all_transcripts:
        
        delete_reasons = []
        
        # Parse metadata
        metadata = {}
        if metadata_str:
            try:
                metadata = json.loads(metadata_str)
            except:
                delete_reasons.append("Invalid metadata")
        
        confidence = metadata.get('confidence', 0)
        language = metadata.get('language', 'unknown')
        
        # Deletion criteria
        
        # 1. Empty or near-empty content
        if not content or len(content.strip()) < 10:
            delete_reasons.append("Empty/minimal content")
        
        # 2. Very low confidence
        elif confidence < -4.0:
            delete_reasons.append(f"Very low confidence ({confidence:.3f})")
        
        # 3. Wrong language detection (should be English)
        elif language not in ['en', 'english', 'unknown']:
            delete_reasons.append(f"Wrong language ({language})")
        
        # 4. Very short word count
        elif word_count and word_count < 5:
            delete_reasons.append(f"Too few words ({word_count})")
        
        if delete_reasons:
            to_delete.append({
                'id': content_id,
                'title': title,
                'reasons': delete_reasons,
                'content_preview': content[:50] if content else "EMPTY"
            })
    
    print(f"\nFound {len(to_delete)} problematic transcripts:")
    
    for item in to_delete:
        print(f"- {item['title']}: {', '.join(item['reasons'])}")
        print(f"  Content: \"{item['content_preview']}\"")
    
    if not to_delete:
        print("✅ No problematic transcripts found!")
        conn.close()
        return
    
    if dry_run:
        print(f"\n🔍 DRY RUN: Would delete {len(to_delete)} transcripts")
        print("Run with dry_run=False to actually delete them")
    else:
        print(f"\n🗑️  DELETING {len(to_delete)} problematic transcripts...")
        
        for item in to_delete:
            cursor.execute('DELETE FROM content WHERE content_id = ?', (item['id'],))
            print(f"Deleted: {item['title']}")
        
        conn.commit()
        print("✅ Cleanup complete!")
    
    conn.close()

if __name__ == "__main__":
    import sys
    
    # Check command line args
    dry_run = "--execute" not in sys.argv
    
    if dry_run:
        print("🔍 DRY RUN MODE - use --execute to actually delete")
    
    clean_bad_transcripts(dry_run=dry_run)