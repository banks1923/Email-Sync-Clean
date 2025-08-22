#!/usr/bin/env python3
"""
Generate embeddings for individual email messages.
"""

import sys
from pathlib import Path

# Add project root to Python path (scripts/ is one level down)
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from utilities.embeddings import get_embedding_service
from shared.simple_db import SimpleDB

def generate_email_message_embeddings():
    """Generate embeddings for all individual email messages."""
    
    print("🧠 Generating Embeddings for Individual Email Messages")
    print("=" * 60)
    
    # Initialize services
    db = SimpleDB("data/emails.db")
    embedding_service = get_embedding_service()
    
    # Get messages needing embeddings
    print("🔍 Finding individual messages needing embeddings...")
    messages_needing_embeddings = db.fetch("""
        SELECT id, title, body 
        FROM content_unified 
        WHERE source_type = 'email_message' 
        AND ready_for_embedding = 1
        ORDER BY id
    """)
    
    if not messages_needing_embeddings:
        print("✅ No messages need embeddings - all up to date!")
        return True
    
    print(f"📧 Found {len(messages_needing_embeddings)} individual messages needing embeddings")
    print()
    
    successful = 0
    failed = 0
    
    print("🚀 Generating embeddings...")
    for i, message in enumerate(messages_needing_embeddings, 1):
        try:
            content_id = message['id']
            title = message['title'] or ""
            body = message['body'] or ""
            
            # Combine title and body for embedding
            text_content = f"{title}\n{body}".strip()
            if not text_content:
                print(f"⚠️  Skipping message {content_id}: No content")
                continue
            
            # Generate embedding
            embedding = embedding_service.get_embedding(text_content)
            
            # Store embedding directly in database
            import pickle
            vector_blob = pickle.dumps(embedding)
            
            db.execute("""
                INSERT OR REPLACE INTO embeddings (content_id, vector, dim, model)
                VALUES (?, ?, ?, ?)
            """, (content_id, vector_blob, len(embedding), "legal-bert"))
            
            # Mark as processed
            db.execute(
                "UPDATE content_unified SET ready_for_embedding = 0 WHERE id = ?",
                (content_id,)
            )
            
            successful += 1
            
            # Progress update every 50 messages
            if i % 50 == 0 or i == len(messages_needing_embeddings):
                print(f"   📈 Progress: {i}/{len(messages_needing_embeddings)} ({successful} successful, {failed} failed)")
            
        except Exception as e:
            failed += 1
            print(f"   ❌ Failed to process message {content_id}: {e}")
            continue
    
    print()
    print("✅ Embedding generation completed!")
    print(f"   📈 Successful: {successful}")
    print(f"   ❌ Failed: {failed}")
    print(f"   📊 Success rate: {(successful/(successful+failed)*100):.1f}%")
    
    # Verify final counts
    final_embeddings = db.fetch_one("SELECT COUNT(*) as count FROM embeddings")['count']
    remaining_to_process = db.fetch_one("SELECT COUNT(*) as count FROM content_unified WHERE source_type = 'email_message' AND ready_for_embedding = 1")['count']
    
    print()
    print("📊 Final Status:")
    print(f"   🧠 Total embeddings in database: {final_embeddings}")
    print(f"   ⏳ Individual messages still needing embeddings: {remaining_to_process}")
    
    return failed == 0

if __name__ == "__main__":
    success = generate_email_message_embeddings()
    
    if success:
        print("\n🎉 All individual email message embeddings generated successfully!")
        print("Ready for vector store reindexing...")
    else:
        print("\n⚠️ Some embeddings failed - check logs above")
        sys.exit(1)