#!/usr/bin/env python3
"""
Improved export of text-only versions of all documents to specified directory.
- Combines PDF chunks into complete documents
- Better HTML cleaning for emails
- Organized file structure
"""

import os
import re
import html
from pathlib import Path
from collections import defaultdict
from shared.simple_db import SimpleDB
from loguru import logger

def clean_html_content(html_content):
    """Enhanced HTML cleaning for email content."""
    if not html_content or not isinstance(html_content, str):
        return ""
    
    text = html_content
    
    # Remove script and style tags completely
    text = re.sub(r'<script[^>]*>.*?</script>', '', text, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r'<style[^>]*>.*?</style>', '', text, flags=re.DOTALL | re.IGNORECASE)
    
    # Remove Microsoft Office XML and namespace declarations
    text = re.sub(r'<o:[^>]*>', '', text, flags=re.IGNORECASE)
    text = re.sub(r'</o:[^>]*>', '', text, flags=re.IGNORECASE)
    text = re.sub(r'<!--\[if[^>]*>.*?<!\[endif\]-->', '', text, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r'<xml>.*?</xml>', '', text, flags=re.DOTALL | re.IGNORECASE)
    
    # Convert common block elements to line breaks
    block_elements = ['div', 'p', 'br', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'blockquote']
    for element in block_elements:
        text = re.sub(f'<{element}[^>]*>', '\n', text, flags=re.IGNORECASE)
        text = re.sub(f'</{element}>', '\n', text, flags=re.IGNORECASE)
    
    # Convert list items to bullet points
    text = re.sub(r'<li[^>]*>', '\n• ', text, flags=re.IGNORECASE)
    text = re.sub(r'</li>', '', text, flags=re.IGNORECASE)
    
    # Remove all remaining HTML tags
    text = re.sub(r'<[^>]+>', '', text)
    
    # Decode HTML entities after removing tags
    text = html.unescape(text)
    
    # Clean up whitespace
    text = re.sub(r'[ \t]+', ' ', text)  # Multiple spaces to single
    text = re.sub(r'\n\s*\n\s*\n+', '\n\n', text)  # Max 2 consecutive newlines
    text = re.sub(r'&nbsp;', ' ', text)  # Non-breaking spaces
    
    # Clean up common email artifacts
    text = re.sub(r'^\s*>', '', text, flags=re.MULTILINE)  # Remove quote markers
    text = re.sub(r'\n\s*\n\s*On.*wrote:\s*\n', '\n\n[Previous email content]\n', text, flags=re.IGNORECASE)
    
    return text.strip()

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

def group_pdf_chunks(content_items):
    """Group PDF chunks by SHA256 hash to combine into complete documents."""
    chunks_by_sha = defaultdict(list)
    other_content = []
    
    for item in content_items:
        content_id, source_type, title, body, created_at, sha256, chunk_index = item
        
        if source_type == 'pdf' and sha256 and chunk_index is not None:
            chunks_by_sha[sha256].append(item)
        else:
            other_content.append(item)
    
    # Sort chunks within each document by chunk_index
    for sha256_hash in chunks_by_sha:
        chunks_by_sha[sha256_hash].sort(key=lambda x: x[6])  # Sort by chunk_index
    
    return dict(chunks_by_sha), other_content

def combine_pdf_chunks(chunks):
    """Combine PDF chunks into a single document."""
    if not chunks:
        return None
    
    # Use first chunk for metadata, combine all content
    first_chunk = chunks[0]
    content_id, source_type, title, _, created_at, sha256, _ = first_chunk
    
    # Combine all chunk content
    combined_content = []
    for chunk in chunks:
        if chunk[3]:  # If body content exists
            combined_content.append(chunk[3])
    
    full_content = '\n\n'.join(combined_content)
    
    # Create combined item with metadata from first chunk
    return (content_id, source_type, title, full_content, created_at, sha256, f"combined_{len(chunks)}_chunks")

def export_improved_documents(target_dir):
    """Export all documents with improved processing."""
    
    target_path = Path(target_dir)
    target_path.mkdir(parents=True, exist_ok=True)
    
    # Create organized subdirectories
    (target_path / "emails").mkdir(exist_ok=True)
    (target_path / "pdfs").mkdir(exist_ok=True) 
    (target_path / "uploads").mkdir(exist_ok=True)
    
    db = SimpleDB()
    
    logger.info(f"Starting improved text export to {target_dir}")
    
    # Get all content
    with db.get_connection() as conn:
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT id, source_type, title, body, created_at, sha256, chunk_index
            FROM content_unified
            WHERE body IS NOT NULL AND body != ''
            ORDER BY source_type, created_at, chunk_index
        ''')
        
        content_items = cursor.fetchall()
    
    logger.info(f"Found {len(content_items)} content items to process")
    
    # Group PDF chunks and get other content
    pdf_chunks_by_sha, other_content = group_pdf_chunks(content_items)
    
    # Combine PDF chunks into complete documents
    combined_pdfs = []
    for sha256_hash, chunks in pdf_chunks_by_sha.items():
        combined_pdf = combine_pdf_chunks(chunks)
        if combined_pdf:
            combined_pdfs.append(combined_pdf)
    
    logger.info(f"Combined {len(pdf_chunks_by_sha)} PDF documents from {sum(len(chunks) for chunks in pdf_chunks_by_sha.values())} chunks")
    
    # Process all content (combined PDFs + other content)
    all_content = combined_pdfs + other_content
    
    exported_count = 0
    source_counts = {}
    
    for item in all_content:
        content_id, source_type, title, body, created_at, sha256, chunk_info = item
        
        # Count by source type
        source_counts[source_type] = source_counts.get(source_type, 0) + 1
        
        # Apply HTML cleaning for emails
        if source_type == 'email':
            cleaned_body = clean_html_content(body)
        else:
            cleaned_body = body
        
        # Create filename
        safe_title = sanitize_filename(title) if title else f"content_{content_id}"
        
        # Add chunk info if it's a combined PDF
        if isinstance(chunk_info, str) and chunk_info.startswith('combined_'):
            safe_title += f"_{chunk_info}"
        
        # Determine subdirectory and filename
        if source_type == 'email':
            subdir = "emails"
            filename = f"email_{content_id:04d}_{safe_title}.txt"
        elif source_type == 'pdf':
            subdir = "pdfs"
            filename = f"pdf_{content_id:04d}_{safe_title}.txt"
        elif source_type == 'upload':
            subdir = "uploads"
            filename = f"upload_{content_id:04d}_{safe_title}.txt"
        else:
            subdir = ""  # Root directory for other types
            filename = f"{source_type}_{content_id:04d}_{safe_title}.txt"
        
        # Full file path
        if subdir:
            filepath = target_path / subdir / filename
        else:
            filepath = target_path / filename
        
        # Create content header
        header = f"""Document ID: {content_id}
Source Type: {source_type}
Title: {title or 'Untitled'}
Created: {created_at}
SHA256: {sha256 or 'N/A'}
Chunk Info: {chunk_info if chunk_info is not None else 'N/A'}
Content Length: {len(cleaned_body):,} characters

{'=' * 80}

"""
        
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(header)
                f.write(cleaned_body)
            
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
    
    # Directory summary
    logger.info("\nOrganized into directories:")
    for subdir in ["emails", "pdfs", "uploads"]:
        subdir_path = target_path / subdir
        if subdir_path.exists():
            file_count = len([f for f in subdir_path.iterdir() if f.is_file()])
            logger.info(f"  {subdir}/: {file_count} files")
    
    return exported_count, source_counts

if __name__ == "__main__":
    target_directory = "/Users/jim/Projects/EmailSyncData/Cleaned_Docs"
    os.chdir('/Users/jim/Projects/Email-Sync-Clean-Backup')
    
    count, sources = export_improved_documents(target_directory)
    print(f"\nExported {count} text documents to {target_directory}")
    print("\nBreakdown by source:")
    for source, count in sorted(sources.items()):
        print(f"  {source}: {count} documents")