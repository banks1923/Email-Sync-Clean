#!/usr/bin/env python3
"""Preflight check for semantic pipeline.

Verifies:
- Qdrant is running
- Database schema is at head
- Embedding dimensions match
- L2 norm is approximately 1.0
"""

import sys
import os
from pathlib import Path
import numpy as np

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from loguru import logger
from shared.simple_db import SimpleDB
from utilities.embeddings import get_embedding_service
from utilities.vector_store import get_vector_store


def check_qdrant_connection():
    """Check if Qdrant is running and accessible."""
    print("\n🔍 Checking Qdrant connection...")
    try:
        vector_store = get_vector_store('emails')
        # Try to get collection info
        info = vector_store.client.get_collection('emails')
        print(f"  ✅ Qdrant connected")
        print(f"  Collection 'emails': {info.points_count} points")
        return True
    except Exception as e:
        print(f"  ❌ Qdrant not accessible: {e}")
        print("  Run: QDRANT__STORAGE__PATH=./qdrant_data ~/bin/qdrant &")
        return False


def check_database_schema():
    """Check if database schema has all required tables and columns."""
    print("\n🔍 Checking database schema...")
    db = SimpleDB()
    
    required_tables = {
        'emails': ['id', 'message_id', 'subject', 'sender', 'content', 'datetime_utc', 'eid', 'thread_id'],
        'content': ['id', 'content_type', 'content', 'metadata'],
        'entity_content_mapping': ['id', 'entity_id', 'entity_value', 'entity_type', 'content_id', 'message_id'],
        'timeline_events': ['id', 'content_id', 'event_date', 'event_type', 'description', 'metadata'],
        'consolidated_entities': ['entity_id', 'primary_name', 'entity_type'],
        'entity_relationships': ['id', 'source_entity_id', 'target_entity_id', 'relationship_type']
    }
    
    all_good = True
    
    for table, required_cols in required_tables.items():
        cursor = db.execute(f"SELECT name FROM sqlite_master WHERE type='table' AND name=?", (table,))
        if not cursor.fetchone():
            print(f"  ❌ Missing table: {table}")
            all_good = False
            continue
            
        # Check columns
        cursor = db.execute(f"PRAGMA table_info({table})")
        columns = [col[1] for col in cursor.fetchall()]
        
        missing_cols = [col for col in required_cols if col not in columns]
        if missing_cols:
            print(f"  ⚠️  Table '{table}' missing columns: {', '.join(missing_cols)}")
            # Not a failure if optional columns like eid, thread_id
            if table == 'emails' and set(missing_cols).issubset({'eid', 'thread_id'}):
                print(f"     (Optional columns - run 'python scripts/setup_evidence_schema.py' to add)")
            else:
                all_good = False
        else:
            print(f"  ✅ Table '{table}' schema OK")
            
    return all_good


def check_embedding_dimensions():
    """Check that embeddings are 1024 dimensions and L2 normalized."""
    print("\n🔍 Checking embedding service...")
    
    try:
        embedding_service = get_embedding_service()
        
        # Test with sample text
        test_text = "This is a test for checking embedding dimensions and normalization."
        embedding = embedding_service.encode(test_text)
        
        # Check dimensions
        dims = len(embedding)
        if dims != 1024:
            print(f"  ❌ Wrong dimensions: {dims} (expected 1024)")
            return False
        print(f"  ✅ Dimensions: {dims}")
        
        # Check L2 norm
        l2_norm = np.linalg.norm(embedding)
        if abs(l2_norm - 1.0) > 0.01:  # Allow 1% tolerance
            print(f"  ⚠️  L2 norm: {l2_norm:.4f} (expected ≈1.0)")
            print("     Embeddings may not be properly normalized")
        else:
            print(f"  ✅ L2 norm: {l2_norm:.4f} (properly normalized)")
            
        # Check vector store collection config
        try:
            vector_store = get_vector_store('emails')
            info = vector_store.client.get_collection('emails')
            
            if info.config.params.vectors.size != 1024:
                print(f"  ❌ Vector store dimension mismatch: {info.config.params.vectors.size}")
                return False
            print(f"  ✅ Vector store configured for 1024 dimensions")
            
        except Exception as e:
            print(f"  ⚠️  Could not verify vector store dimensions: {e}")
            
        return True
        
    except Exception as e:
        print(f"  ❌ Embedding service error: {e}")
        return False


def check_settings():
    """Check semantic pipeline settings."""
    print("\n🔍 Checking semantic pipeline settings...")
    
    from config.settings import semantic_settings
    
    print(f"  SEMANTICS_ON_INGEST: {semantic_settings.semantics_on_ingest}")
    print(f"  Steps configured: {', '.join(semantic_settings.semantics_steps)}")
    print(f"  Max batch size: {semantic_settings.semantics_max_batch}")
    print(f"  Timeout per step: {semantic_settings.semantics_timeout_s}s")
    print(f"  Entity cache days: {semantic_settings.entity_cache_days}")
    
    if not semantic_settings.semantics_on_ingest:
        print("  ⚠️  Semantic processing is DISABLED for new emails")
        print("     Set SEMANTICS_ON_INGEST=true to enable")
    else:
        print("  ✅ Semantic processing ENABLED for new emails")
        
    return True


def check_data_stats():
    """Show current data statistics."""
    print("\n📊 Current data statistics:")
    
    db = SimpleDB()
    
    cursor = db.execute("SELECT COUNT(*) FROM emails")
    email_count = cursor.fetchone()[0]
    print(f"  Total emails: {email_count}")
    
    cursor = db.execute("SELECT COUNT(*) FROM emails WHERE eid IS NOT NULL")
    eid_count = cursor.fetchone()[0]
    print(f"  Emails with EIDs: {eid_count}")
    
    cursor = db.execute("SELECT COUNT(DISTINCT thread_id) FROM emails WHERE thread_id IS NOT NULL")
    thread_count = cursor.fetchone()[0]
    print(f"  Conversation threads: {thread_count}")
    
    cursor = db.execute("SELECT COUNT(*) FROM entity_content_mapping")
    entity_count = cursor.fetchone()[0]
    print(f"  Entities extracted: {entity_count}")
    
    cursor = db.execute("SELECT COUNT(*) FROM content WHERE metadata LIKE '%vectorized%'")
    vector_count = cursor.fetchone()[0]
    print(f"  Vectorized content: {vector_count}")
    
    cursor = db.execute("SELECT COUNT(*) FROM timeline_events")
    timeline_count = cursor.fetchone()[0]
    print(f"  Timeline events: {timeline_count}")
    
    # Calculate coverage
    if email_count > 0:
        eid_coverage = 100 * eid_count / email_count
        vector_coverage = 100 * vector_count / email_count
        
        print(f"\n  Coverage:")
        print(f"    EID assignment: {eid_coverage:.1f}%")
        print(f"    Vectorization: {vector_coverage:.1f}%")
        
        if eid_coverage < 100:
            print(f"    Run: tools/scripts/vsearch evidence assign-eids")
        if vector_coverage < 100:
            print(f"    Run: tools/scripts/vsearch semantic backfill")


def main():
    """Run all preflight checks."""
    print("=" * 60)
    print("Semantic Pipeline Preflight Check")
    print("=" * 60)
    
    all_checks_passed = True
    
    # Check Qdrant
    if not check_qdrant_connection():
        all_checks_passed = False
        
    # Check database schema
    if not check_database_schema():
        all_checks_passed = False
        print("\n  To fix schema issues, run:")
        print("    python scripts/setup_semantic_schema.py")
        print("    python scripts/setup_evidence_schema.py")
        
    # Check embeddings
    if not check_embedding_dimensions():
        all_checks_passed = False
        
    # Check settings
    check_settings()
    
    # Show data stats
    check_data_stats()
    
    # Final status
    print("\n" + "=" * 60)
    if all_checks_passed:
        print("✅ All critical checks passed - ready for semantic pipeline")
    else:
        print("❌ Some checks failed - please fix issues above")
    print("=" * 60)
    
    return 0 if all_checks_passed else 1


if __name__ == "__main__":
    sys.exit(main())