#!/usr/bin/env python3
"""
Comprehensive service health check and testing script.
Tests all major services in the Email Sync system.
"""

import sys
from datetime import datetime
from loguru import logger

# Configure minimal logging
logger.remove()
logger.add(sys.stderr, level="WARNING")


def test_timeline_service():
    """Test timeline service functionality."""
    print("\n=== Testing Timeline Service ===")
    try:
        from utilities.timeline import TimelineService
        
        ts = TimelineService()
        
        # Test syncing
        result = ts.sync_emails_to_timeline(limit=5)
        print(f"✓ Email sync: {result.get('success', False)}")
        
        # Test timeline view
        timeline = ts.get_timeline_view(limit=5)
        print(f"✓ Timeline view: {len(timeline.get('events', []))} events")
        
        return True
    except Exception as e:
        print(f"✗ Timeline service error: {e}")
        return False


def test_entity_service():
    """Test entity extraction service."""
    print("\n=== Testing Entity Service ===")
    try:
        from entity.main import EntityService
        
        es = EntityService()
        
        # Test processing
        result = es.process_emails(limit=5)
        print(f"✓ Email processing: {result.get('success', False)}")
        
        # Get stats
        stats = es.get_entity_stats()
        print(f"✓ Entity stats: {stats.get('raw_entities', 0)} entities")
        
        return True
    except Exception as e:
        print(f"✗ Entity service error: {e}")
        return False


def test_summarization_service():
    """Test summarization service."""
    print("\n=== Testing Summarization Service ===")
    try:
        from summarization import get_document_summarizer
        
        summarizer = get_document_summarizer()
        
        test_text = "This is a test document. It contains multiple sentences. We need to test the summarization."
        
        # Test extraction
        result = summarizer.extract_summary(test_text, max_sentences=2)
        print(f"✓ Summary extraction: {result.get('summary_type', 'failed')}")
        
        return True
    except Exception as e:
        print(f"✗ Summarization service error: {e}")
        return False


def test_search_intelligence():
    """Test search intelligence service."""
    print("\n=== Testing Search Intelligence ===")
    try:
        from search_intelligence import get_search_intelligence_service
        
        search = get_search_intelligence_service()
        
        # Test search
        results = search.search("test", limit=3)
        print(f"✓ Search: Found {len(results)} results")
        
        # Test health
        health = search.health()
        print(f"✓ Health check: {health.get('status', 'unknown')}")
        
        return True
    except Exception as e:
        print(f"✗ Search intelligence error: {e}")
        return False


def test_vector_store():
    """Test vector store functionality."""
    print("\n=== Testing Vector Store ===")
    try:
        from utilities.vector_store import get_vector_store
        
        get_vector_store('emails')
        print("✓ Vector store connected to collection: emails")
        
        # Check if Qdrant is running
        import requests
        response = requests.get("http://localhost:6333/readyz", timeout=2)
        if response.text == "all shards are ready":
            print("✓ Qdrant is running and ready")
        
        return True
    except Exception as e:
        print(f"✗ Vector store error: {e}")
        return False


def test_embeddings():
    """Test embedding service."""
    print("\n=== Testing Embedding Service ===")
    try:
        from utilities.embeddings import get_embedding_service
        
        emb = get_embedding_service()
        
        # Test encoding
        test_text = "This is a test sentence."
        embedding = emb.encode(test_text)
        print(f"✓ Embedding generated: {len(embedding)} dimensions")
        
        return True
    except Exception as e:
        print(f"✗ Embedding service error: {e}")
        return False


def test_database():
    """Test database connectivity."""
    print("\n=== Testing Database ===")
    try:
        from shared.simple_db import SimpleDB
        
        db = SimpleDB()
        
        # Check tables
        cursor = db.execute("SELECT COUNT(*) FROM sqlite_master WHERE type='table'")
        table_count = cursor.fetchone()[0]
        print(f"✓ Database connected: {table_count} tables")
        
        # Check content
        cursor = db.execute("SELECT COUNT(*) FROM content")
        content_count = cursor.fetchone()[0]
        print(f"✓ Content records: {content_count}")
        
        return True
    except Exception as e:
        print(f"✗ Database error: {e}")
        return False


def main():
    """Run all service tests."""
    print("=" * 50)
    print("Email Sync System - Service Health Check")
    print(f"Timestamp: {datetime.now().isoformat()}")
    print("=" * 50)
    
    results = {}
    
    # Test core services
    results['Database'] = test_database()
    results['Embeddings'] = test_embeddings()
    results['Vector Store'] = test_vector_store()
    results['Search Intelligence'] = test_search_intelligence()
    results['Summarization'] = test_summarization_service()
    results['Entity Service'] = test_entity_service()
    results['Timeline'] = test_timeline_service()
    
    # Summary
    print("\n" + "=" * 50)
    print("SUMMARY")
    print("=" * 50)
    
    passed = sum(1 for v in results.values() if v)
    total = len(results)
    
    for service, status in results.items():
        status_icon = "✓" if status else "✗"
        print(f"{status_icon} {service}: {'PASSED' if status else 'FAILED'}")
    
    print(f"\nOverall: {passed}/{total} services operational")
    
    # Return exit code
    return 0 if passed == total else 1


if __name__ == "__main__":
    sys.exit(main())