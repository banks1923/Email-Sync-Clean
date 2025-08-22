#!/usr/bin/env python3
"""
Rebuild Embeddings for Repaired Content

Generates embeddings for content_unified entries that lack embeddings,
particularly focusing on the repaired upload documents and PDF files.
"""

import sqlite3
import os
import sys
from datetime import datetime
from pathlib import Path

# Add project root to path to import services
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from utilities.embeddings import get_embedding_service
from shared.simple_db import SimpleDB


def generate_missing_embeddings(db_path):
    """Generate embeddings for content that lacks them"""
    
    print("Rebuilding Missing Embeddings...")
    print("=" * 40)
    
    # Initialize services
    try:
        SimpleDB()
        embedding_service = get_embedding_service()
        print("✓ Services initialized")
    except Exception as e:
        print(f"❌ Failed to initialize services: {e}")
        return 0
    
    # Get content entries without embeddings
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT c.id, c.title, c.body, c.source_type
        FROM content_unified c
        LEFT JOIN embeddings e ON e.content_id = c.id
        WHERE c.ready_for_embedding = 1 AND e.id IS NULL
        ORDER BY c.id
    """)
    
    missing_embeddings = cursor.fetchall()
    conn.close()
    
    if not missing_embeddings:
        print("✓ All content already has embeddings")
        return 0
    
    print(f"Found {len(missing_embeddings)} content entries without embeddings")
    
    embeddings_created = 0
    
    for content_id, title, body, source_type in missing_embeddings:
        print(f"Generating embedding for: {title} ({source_type})")
        
        try:
            # Generate embedding using the embedding service
            vector = embedding_service.get_embedding(body)
            
            if vector is not None:
                # Store embedding in database using direct SQL
                try:
                    import pickle
                    
                    # Convert vector to blob for storage
                    vector_blob = pickle.dumps(vector)
                    
                    # Insert directly into embeddings table
                    conn = sqlite3.connect(db_path)
                    cursor = conn.cursor()
                    
                    cursor.execute("""
                        INSERT INTO embeddings (content_id, vector, dim, model, created_at)
                        VALUES (?, ?, ?, ?, ?)
                    """, (content_id, vector_blob, len(vector), 'legal-bert', datetime.now().isoformat()))
                    
                    conn.commit()
                    conn.close()
                    
                    embeddings_created += 1
                    print(f"  ✓ Embedding stored (ID: {content_id}, dim: {len(vector)})")
                    
                except Exception as e:
                    print(f"  ❌ Failed to store embedding for {title}: {e}")
            else:
                print(f"  ❌ Failed to generate embedding for {title}")
                
        except Exception as e:
            print(f"  ❌ Error processing {title}: {e}")
    
    print(f"\n✓ Generated {embeddings_created} embeddings")
    return embeddings_created


def sync_vectors_to_qdrant(db_path):
    """Sync embeddings to Qdrant vector store"""
    
    print("\nSyncing Vectors to Qdrant...")
    print("=" * 30)
    
    try:
        from utilities.vector_store import get_vector_store
        vector_store = get_vector_store()
        print("✓ Vector store connected")
    except Exception as e:
        print(f"❌ Failed to connect to vector store: {e}")
        return 0
    
    # Get embeddings that need to be synced using direct SQL
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Get all embeddings with their content
        cursor.execute("""
            SELECT e.id, e.content_id, e.vector, c.title, c.body, c.source_type
            FROM embeddings e
            JOIN content_unified c ON e.content_id = c.id
            ORDER BY e.id
        """)
        embeddings_data = cursor.fetchall()
        conn.close()
        
        if not embeddings_data:
            print("✓ No embeddings to sync")
            return 0
        
        print(f"Syncing {len(embeddings_data)} embeddings to Qdrant...")
        
        synced_count = 0
        
        for embedding_id, content_id, vector_blob, title, body, source_type in embeddings_data:
            try:
                import pickle
                
                # Deserialize vector from blob
                vector = pickle.loads(vector_blob)
                
                # Create point ID using content_id
                point_id = f"content_{content_id}"
                
                # Prepare metadata
                metadata = {
                    "content_id": content_id,
                    "title": title,
                    "source_type": source_type,
                    "embedding_id": embedding_id
                }
                
                # Upsert to vector store
                success = vector_store.upsert_point(point_id, vector, metadata)
                
                if success:
                    synced_count += 1
                    if synced_count % 10 == 0:
                        print(f"  Synced {synced_count} vectors...")
                else:
                    print(f"  ❌ Failed to sync {title}")
                    
            except Exception as e:
                print(f"  ❌ Error syncing {title}: {e}")
        
        print(f"✓ Synced {synced_count} vectors to Qdrant")
        return synced_count
        
    except Exception as e:
        print(f"❌ Failed to sync vectors: {e}")
        return 0


def main():
    """Main entry point"""
    
    db_path = os.getenv("APP_DB_PATH", "data/emails.db")
    
    if not Path(db_path).exists():
        print(f"❌ Database not found: {db_path}")
        return 1
    
    try:
        # Step 1: Generate missing embeddings
        embeddings_created = generate_missing_embeddings(db_path)
        
        # Step 2: Sync vectors to Qdrant (if embeddings were created)
        vectors_synced = 0
        if embeddings_created > 0:
            vectors_synced = sync_vectors_to_qdrant(db_path)
        else:
            print("\nSkipping vector sync (no new embeddings)")
        
        # Step 3: Final verification
        print("\n📊 Final Summary:")
        print(f"   Embeddings created: {embeddings_created}")
        print(f"   Vectors synced to Qdrant: {vectors_synced}")
        
        # Quick verification
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        cursor.execute("SELECT COUNT(*) FROM embeddings")
        total_embeddings = cursor.fetchone()[0]
        
        cursor.execute("""
            SELECT COUNT(*) FROM content_unified c
            LEFT JOIN embeddings e ON e.content_id = c.id
            WHERE c.ready_for_embedding = 1 AND e.id IS NULL
        """)
        remaining_missing = cursor.fetchone()[0]
        
        conn.close()
        
        print(f"   Total embeddings in database: {total_embeddings}")
        print(f"   Content still missing embeddings: {remaining_missing}")
        
        if remaining_missing == 0:
            print("✅ All content now has embeddings!")
        else:
            print(f"⚠️  {remaining_missing} content entries still missing embeddings")
        
        return 0
        
    except Exception as e:
        print(f"❌ Embedding rebuild failed: {e}")
        return 1


if __name__ == "__main__":
    exit(main())