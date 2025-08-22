#!/usr/bin/env python3
"""
Export text-only versions of all documents to specified directory.
"""

import os
import re
from pathlib import Path
from shared.simple_db import SimpleDB
from loguru import logger

def sanitize_filename(filename):
    """Sanitize filename for safe filesystem usage."""
    if not filename:
        return "untitled"
    
    # Remove HTML tags if present
    filename = re.sub(r'<[^>]+>', '', filename)
    
    # Replace problematic characters
    filename = re.sub(r'[<>:"/\\|?*]', '_', filename)
    filename = re.sub(r'\s+', ' ', filename)  # Normalize whitespace
    filename = filename.strip()
    
    # Limit length
    if len(filename) > 100:
        filename = filename[:97] + "..."
    
    return filename or "untitled"

def export_text_documents(target_dir):
    """Export all documents as text files to target directory."""
    
    target_path = Path(target_dir)
    target_path.mkdir(parents=True, exist_ok=True)
    
    db = SimpleDB()
    
    logger.info(f"Starting text export to {target_dir}")
    
    # Get all content with proper text
    with db.get_connection() as conn:
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT id, source_type, title, body, created_at, sha256, chunk_index
            FROM content_unified
            WHERE body IS NOT NULL AND body != ''
            ORDER BY source_type, created_at, chunk_index
        ''')
        
        content_items = cursor.fetchall()
    
    logger.info(f"Found {len(content_items)} content items to export")
    
    exported_count = 0
    source_counts = {}
    
    for item in content_items:
        content_id, source_type, title, body, created_at, sha256, chunk_index = item
        
        # Count by source type
        source_counts[source_type] = source_counts.get(source_type, 0) + 1
        
        # Create filename
        safe_title = sanitize_filename(title) if title else f"content_{content_id}"
        
        # Add chunk index if present
        if chunk_index is not None and chunk_index > 0:
            safe_title += f"_chunk_{chunk_index}"
        
        # Add source prefix and ID
        filename = f"{source_type}_{content_id:04d}_{safe_title}.txt"
        
        filepath = target_path / filename
        
        # Create content header
        header = f"""Document ID: {content_id}
Source Type: {source_type}
Title: {title or 'Untitled'}
Created: {created_at}
SHA256: {sha256 or 'N/A'}
Chunk Index: {chunk_index if chunk_index is not None else 'N/A'}
Content Length: {len(body):,} characters

{'=' * 80}

"""
        
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(header)
                f.write(body)
            
            exported_count += 1
            
            if exported_count % 50 == 0:
                logger.info(f"Exported {exported_count} files...")
                
        except Exception as e:
            logger.error(f"Failed to export {filename}: {e}")
    
    # Summary
    logger.info(f"Export complete: {exported_count} files exported to {target_dir}")
    logger.info("Files by source type:")
    for source_type, count in sorted(source_counts.items()):
        logger.info(f"  {source_type}: {count} files")
    
    return exported_count, source_counts

if __name__ == "__main__":
    target_directory = "/Users/jim/Projects/EmailSyncData/Cleaned_Docs"
    os.chdir('/Users/jim/Projects/Email-Sync-Clean-Backup')
    
    count, sources = export_text_documents(target_directory)
    print(f"\nExported {count} text documents to {target_directory}")
    print("\nBreakdown by source:")
    for source, count in sorted(sources.items()):
        print(f"  {source}: {count} documents")