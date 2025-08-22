#!/usr/bin/env python3
"""
SHA256 Backfill Migration - Assignment 1

Repairs 581 uploaded PDF chunks with NULL SHA256 by:
1. Computing deterministic SHA256 using: file_hash:chunk_index:normalized_text
2. Updating documents.sha256 for all 581 chunks
3. Creating/updating content_unified entries with matching SHA256
4. Preparing for embedding rebuild

Idempotent: Can be run multiple times safely.
"""

import sqlite3
import hashlib
import json
import os
import re
from datetime import datetime
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


def backup_database(db_path):
    """Create a backup of the database before migration"""
    backup_path = f"{db_path}.backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    
    # Use SQLite backup API for consistent backup
    source = sqlite3.connect(db_path)
    backup = sqlite3.connect(backup_path)
    source.backup(backup)
    backup.close()
    source.close()
    
    print(f"✓ Database backed up to: {backup_path}")
    return backup_path


def get_null_documents(cursor):
    """Get all documents with NULL SHA256"""
    cursor.execute("""
        SELECT chunk_id, file_name, file_hash, chunk_index, text_content, source_type
        FROM documents 
        WHERE sha256 IS NULL AND source_type = 'upload'
        ORDER BY file_name, chunk_index
    """)
    return cursor.fetchall()


def check_content_unified_schema(cursor):
    """Check if content_unified has sha256 column, add if missing"""
    cursor.execute("PRAGMA table_info(content_unified)")
    columns = [row[1] for row in cursor.fetchall()]
    
    if 'sha256' not in columns:
        print("Adding sha256 column to content_unified...")
        cursor.execute("ALTER TABLE content_unified ADD COLUMN sha256 TEXT")
        cursor.execute("CREATE INDEX idx_content_unified_sha256 ON content_unified(sha256)")
        print("✓ Added sha256 column and index to content_unified")
    
    if 'chunk_index' not in columns:
        print("Adding chunk_index column to content_unified...")
        cursor.execute("ALTER TABLE content_unified ADD COLUMN chunk_index INTEGER DEFAULT 0")
        cursor.execute("CREATE INDEX idx_content_unified_sha256_chunk ON content_unified(sha256, chunk_index)")
        print("✓ Added chunk_index column and composite index to content_unified")


def backfill_sha256_values(cursor):
    """Backfill SHA256 values for NULL documents"""
    
    # Get all NULL documents
    null_docs = get_null_documents(cursor)
    print(f"Found {len(null_docs)} documents with NULL SHA256")
    
    if not null_docs:
        print("No documents to backfill")
        return 0, {}
    
    # Group by file for progress tracking
    files_processed = {}
    updates_made = 0
    
    for chunk_id, file_name, file_hash, chunk_index, text_content, source_type in null_docs:
        # Compute deterministic SHA256
        new_sha256 = compute_chunk_sha256(file_hash, chunk_index, text_content)
        
        # Update documents table
        cursor.execute("""
            UPDATE documents 
            SET sha256 = ? 
            WHERE chunk_id = ? AND sha256 IS NULL
        """, (new_sha256, chunk_id))
        
        if cursor.rowcount > 0:
            updates_made += 1
            
            # Track file progress
            if file_name not in files_processed:
                files_processed[file_name] = {'chunks': 0, 'file_hash': file_hash}
            files_processed[file_name]['chunks'] += 1
            
            if updates_made % 50 == 0:
                print(f"  Updated {updates_made} documents...")
    
    print(f"✓ Updated SHA256 for {updates_made} documents")
    
    # Print file summary
    print(f"Files processed:")
    for file_name, info in files_processed.items():
        print(f"  {file_name}: {info['chunks']} chunks")
    
    return updates_made, files_processed


def sync_content_unified(cursor, files_processed):
    """Create/update content_unified entries for repaired documents"""
    
    content_entries_created = 0
    content_entries_updated = 0
    
    for file_name, info in files_processed.items():
        file_hash = info['file_hash']
        
        # Get all chunks for this file (now with SHA256)
        cursor.execute("""
            SELECT chunk_id, chunk_index, sha256, text_content, file_name
            FROM documents 
            WHERE file_hash = ? AND source_type = 'upload' AND sha256 IS NOT NULL
            ORDER BY chunk_index
        """, (file_hash,))
        
        chunks = cursor.fetchall()
        
        if chunks:
            # Combine all chunk text for full document content
            full_text = '\n\n'.join(chunk[3] for chunk in chunks if chunk[3])
            title = file_name
            
            # Use the first chunk's SHA256 as the document SHA256
            document_sha256 = chunks[0][2]
            
            # Check if content_unified entry exists
            cursor.execute("""
                SELECT id FROM content_unified 
                WHERE source_type = 'upload' AND title = ?
            """, (file_name,))
            
            existing = cursor.fetchone()
            
            if existing:
                # Update existing entry
                cursor.execute("""
                    UPDATE content_unified 
                    SET body = ?, sha256 = ?, chunk_index = ?, ready_for_embedding = 1
                    WHERE id = ?
                """, (full_text, document_sha256, 0, existing[0]))
                content_entries_updated += 1
                print(f"  Updated content for: {file_name}")
            else:
                # Create new entry
                cursor.execute("""
                    INSERT INTO content_unified (source_type, source_id, title, body, sha256, chunk_index, ready_for_embedding)
                    VALUES ('upload', ?, ?, ?, ?, 0, 1)
                """, (hash(file_name) % 2147483647, title, full_text, document_sha256))  # Use hash as source_id
                content_entries_created += 1
                print(f"  Created content for: {file_name}")
    
    print(f"✓ Content unified: {content_entries_created} created, {content_entries_updated} updated")
    return content_entries_created, content_entries_updated


def run_migration(db_path):
    """Run the complete SHA256 backfill migration"""
    
    print("SHA256 Backfill Migration Starting...")
    print("=" * 50)
    
    # Backup database
    backup_path = backup_database(db_path)
    
    try:
        # Connect to database
        conn = sqlite3.connect(db_path)
        conn.execute("PRAGMA foreign_keys = ON")  # Enable foreign key constraints
        cursor = conn.cursor()
        
        # Step 1: Check/update schema
        print("\n1. Checking schema...")
        check_content_unified_schema(cursor)
        
        # Step 2: Backfill SHA256 values
        print("\n2. Backfilling SHA256 values...")
        updates_made, files_processed = backfill_sha256_values(cursor)
        
        # Step 3: Sync content_unified
        print("\n3. Syncing content_unified...")
        content_created, content_updated = sync_content_unified(cursor, files_processed)
        
        # Commit changes
        conn.commit()
        
        # Step 4: Verification
        print("\n4. Verification...")
        cursor.execute("SELECT COUNT(*) FROM documents WHERE sha256 IS NULL")
        remaining_nulls = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM documents WHERE source_type = 'upload'")
        total_uploads = cursor.fetchone()[0]
        
        cursor.execute("""
            SELECT COUNT(*) FROM documents d 
            LEFT JOIN content_unified c ON d.sha256 = c.sha256 
            WHERE d.source_type = 'upload' AND d.sha256 IS NOT NULL AND c.id IS NULL
        """)
        docs_without_content = cursor.fetchone()[0]
        
        # Generate results
        results = {
            "migration_timestamp": datetime.now().isoformat(),
            "backup_path": backup_path,
            "docs_total": total_uploads,
            "docs_fixed_sha256": updates_made,
            "docs_null_sha256": remaining_nulls,
            "docs_without_content": docs_without_content,
            "content_entries_created": content_created,
            "content_entries_updated": content_updated,
            "files_processed": len(files_processed),
            "files_detail": files_processed
        }
        
        print(f"\n✓ Migration completed successfully!")
        print(f"✓ Fixed SHA256 for {updates_made} documents")
        print(f"✓ Remaining NULL SHA256: {remaining_nulls}")
        print(f"✓ Documents without content: {docs_without_content}")
        
        conn.close()
        return results
        
    except Exception as e:
        print(f"\n❌ Migration failed: {e}")
        print(f"Database backup available at: {backup_path}")
        if 'conn' in locals():
            conn.rollback()
            conn.close()
        raise


def main():
    """Main migration entry point"""
    
    # Use environment variable or default path
    from config.settings import DatabaseSettings
    db_path = DatabaseSettings().emails_db_path
    
    if not Path(db_path).exists():
        print(f"❌ Database not found: {db_path}")
        return 1
    
    try:
        results = run_migration(db_path)
        
        # Save results to file
        os.makedirs("logs", exist_ok=True)
        results_path = "logs/migration_results.json"
        with open(results_path, 'w') as f:
            json.dump(results, f, indent=2)
        
        print(f"\n✓ Results saved to: {results_path}")
        
        # Print final summary
        print(f"\nFinal Migration Summary:")
        print(f"  Documents fixed: {results['docs_fixed_sha256']}")
        print(f"  NULL SHA256 remaining: {results['docs_null_sha256']}")
        print(f"  Content entries created: {results['content_entries_created']}")
        print(f"  Content entries updated: {results['content_entries_updated']}")
        
        return 0
        
    except Exception as e:
        print(f"❌ Migration failed: {e}")
        return 1


if __name__ == "__main__":
    exit(main())