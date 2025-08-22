#!/usr/bin/env python3
"""
Fix Duplicate SHA256 Keys in Original PDF Documents

Recalculates SHA256 values for original PDF documents (source_type='pdf') 
that have duplicate SHA256 values due to inconsistent hashing methods.
"""

import sqlite3
import hashlib
import re
from pathlib import Path


def normalize_text(text):
    """Normalize text for consistent hashing"""
    if not text:
        return ""
    # Remove excessive whitespace, normalize line endings
    normalized = re.sub(r'\s+', ' ', text.strip())
    return normalized


def compute_chunk_sha256(file_hash, chunk_index, chunk_text):
    """
    Compute deterministic SHA256 for a document chunk
    Formula: SHA256(file_hash:chunk_index:normalized_text)
    """
    normalized_text = normalize_text(chunk_text)
    content = f"{file_hash}:{chunk_index}:{normalized_text}"
    return hashlib.sha256(content.encode('utf-8')).hexdigest()


def fix_duplicate_sha256(db_path):
    """Fix duplicate SHA256 values in original PDF documents"""
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    print("Fixing Duplicate SHA256 Keys...")
    print("=" * 40)
    
    # Find documents with duplicate SHA256 values
    cursor.execute("""
        SELECT sha256, COUNT(*) as count
        FROM documents
        WHERE sha256 IS NOT NULL
        GROUP BY sha256
        HAVING COUNT(*) > 1
    """)
    duplicate_sha256s = cursor.fetchall()
    
    if not duplicate_sha256s:
        print("✓ No duplicate SHA256 values found")
        conn.close()
        return 0
    
    print(f"Found {len(duplicate_sha256s)} SHA256 values with duplicates")
    
    fixed_count = 0
    
    for dupe_sha256, count in duplicate_sha256s:
        print(f"\nProcessing SHA256: {dupe_sha256[:16]}... ({count} duplicates)")
        
        # Get all documents with this SHA256
        cursor.execute("""
            SELECT chunk_id, file_name, file_hash, chunk_index, text_content, source_type
            FROM documents
            WHERE sha256 = ?
            ORDER BY source_type, chunk_index
        """, (dupe_sha256,))
        
        docs = cursor.fetchall()
        
        # Recalculate SHA256 for each document using deterministic method
        for chunk_id, file_name, file_hash, chunk_index, text_content, source_type in docs:
            new_sha256 = compute_chunk_sha256(file_hash, chunk_index, text_content)
            
            if new_sha256 != dupe_sha256:
                print(f"  Updating {source_type} chunk {chunk_index}: {new_sha256[:16]}...")
                
                cursor.execute("""
                    UPDATE documents 
                    SET sha256 = ? 
                    WHERE chunk_id = ?
                """, (new_sha256, chunk_id))
                
                fixed_count += 1
            else:
                print(f"  {source_type} chunk {chunk_index}: SHA256 unchanged")
    
    # Commit changes
    conn.commit()
    
    # Verify fix
    cursor.execute("""
        SELECT COUNT(*) FROM (
            SELECT sha256 FROM documents
            WHERE sha256 IS NOT NULL
            GROUP BY sha256
            HAVING COUNT(*) > 1
        )
    """)
    remaining_dupes = cursor.fetchone()[0]
    
    conn.close()
    
    print(f"\n✓ Fixed {fixed_count} duplicate SHA256 values")
    print(f"✓ Remaining duplicate SHA256s: {remaining_dupes}")
    
    return fixed_count


def create_missing_content(db_path):
    """Create content_unified entries for PDF documents that lack them"""
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    print("\nCreating Missing Content Entries...")
    print("=" * 40)
    
    # Find PDF documents without content_unified entries
    cursor.execute("""
        SELECT d.file_name, d.file_hash, COUNT(*) as chunk_count
        FROM documents d
        LEFT JOIN content_unified c ON d.sha256 = c.sha256
        WHERE d.source_type = 'pdf' AND c.id IS NULL
        GROUP BY d.file_name, d.file_hash
    """)
    
    missing_files = cursor.fetchall()
    
    if not missing_files:
        print("✓ All PDF documents have content entries")
        conn.close()
        return 0
    
    print(f"Found {len(missing_files)} PDF files without content entries")
    
    content_created = 0
    
    for file_name, file_hash, chunk_count in missing_files:
        print(f"Creating content for: {file_name}")
        
        # Get all chunks for this file, ordered by chunk_index
        cursor.execute("""
            SELECT chunk_index, sha256, text_content
            FROM documents
            WHERE file_name = ? AND file_hash = ? AND source_type = 'pdf'
            ORDER BY chunk_index
        """, (file_name, file_hash))
        
        chunks = cursor.fetchall()
        
        if chunks:
            # Combine all chunk text
            full_text = '\n\n'.join(chunk[2] for chunk in chunks if chunk[2])
            
            # Use the first chunk's SHA256 as document SHA256
            document_sha256 = chunks[0][1]
            
            # Create content_unified entry
            cursor.execute("""
                INSERT INTO content_unified (source_type, source_id, title, body, sha256, chunk_index, ready_for_embedding)
                VALUES ('pdf', ?, ?, ?, ?, 0, 1)
            """, (hash(file_name) % 2147483647, file_name, full_text, document_sha256))
            
            content_created += 1
            print(f"  ✓ Created content entry (SHA256: {document_sha256[:16]}...)")
    
    conn.commit()
    conn.close()
    
    print(f"\n✓ Created {content_created} content entries")
    return content_created


def main():
    """Main entry point"""
    
    from config.settings import DatabaseSettings
    db_path = DatabaseSettings().emails_db_path
    
    if not Path(db_path).exists():
        print(f"❌ Database not found: {db_path}")
        return 1
    
    try:
        # Step 1: Fix duplicate SHA256 values
        fixed_count = fix_duplicate_sha256(db_path)
        
        # Step 2: Create missing content entries
        content_created = create_missing_content(db_path)
        
        print("\n✅ Summary:")
        print(f"   Fixed SHA256 duplicates: {fixed_count}")
        print(f"   Created content entries: {content_created}")
        
        return 0
        
    except Exception as e:
        print(f"❌ Fix failed: {e}")
        return 1


if __name__ == "__main__":
    exit(main())