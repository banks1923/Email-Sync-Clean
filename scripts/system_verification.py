#!/usr/bin/env python3
"""
System Verification Script - Verify all components are operational after recovery
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from shared.simple_db import SimpleDB
from utilities.vector_store.qdrant_store import QdrantStore
from search_intelligence.main import SearchService
from loguru import logger
import json

def check_database():
    """Check database state and integrity"""
    logger.info("=== Database Verification ===")
    
    db = SimpleDB()
    
    # Check table existence
    tables = db.execute("""
        SELECT name FROM sqlite_master 
        WHERE type='table' 
        ORDER BY name
    """).fetchall()
    
    logger.info(f"Tables: {[t[0] for t in tables]}")
    
    # Check row counts
    stats = {}
    for table_name in ['content_unified', 'individual_messages', 'message_occurrences', 'entities']:
        try:
            count = db.execute(f"SELECT COUNT(*) FROM {table_name}").fetchone()[0]
            stats[table_name] = count
            logger.info(f"  {table_name}: {count} records")
        except Exception as e:
            logger.warning(f"  {table_name}: Error - {e}")
    
    # Check foreign key integrity
    fk_status = db.execute("PRAGMA foreign_keys").fetchone()[0]
    logger.info(f"Foreign keys enabled: {bool(fk_status)}")
    
    # Check email content quality
    email_stats = db.execute("""
        SELECT 
            COUNT(*) as total,
            COUNT(CASE WHEN ready_for_embedding = 1 THEN 1 END) as ready,
            COUNT(CASE WHEN validation_status = 'validated' THEN 1 END) as validated
        FROM content_unified
        WHERE source_type = 'email_message'
    """).fetchone()
    
    logger.info(f"Email content: {email_stats[0]} total, {email_stats[1]} ready for embedding, {email_stats[2]} validated")
    
    return stats

def check_vector_store():
    """Check vector store status"""
    logger.info("\n=== Vector Store Verification ===")
    
    try:
        store = QdrantStore()
        info = store.get_collection_info()
        
        if info:
            logger.info(f"Collection exists: Yes")
            logger.info(f"Vectors count: {info.get('vectors_count', 0)}")
            logger.info(f"Points count: {info.get('points_count', 0)}")
            return True
        else:
            logger.warning("Collection does not exist")
            return False
    except Exception as e:
        logger.error(f"Vector store error: {e}")
        return False

def check_search():
    """Test search functionality"""
    logger.info("\n=== Search Verification ===")
    
    try:
        search = SearchService()
        
        # Test keyword search
        logger.info("Testing keyword search...")
        keyword_results = search.search("lease", search_type="keyword", limit=3)
        logger.info(f"  Keyword search returned {len(keyword_results)} results")
        
        # Test semantic search (if embeddings exist)
        logger.info("Testing semantic search...")
        try:
            semantic_results = search.search("rental agreement", search_type="semantic", limit=3)
            logger.info(f"  Semantic search returned {len(semantic_results)} results")
        except Exception as e:
            logger.warning(f"  Semantic search not ready: {e}")
        
        # Test hybrid search
        logger.info("Testing hybrid search...")
        try:
            hybrid_results = search.search("tenant", search_type="hybrid", limit=3)
            logger.info(f"  Hybrid search returned {len(hybrid_results)} results")
        except Exception as e:
            logger.warning(f"  Hybrid search not ready: {e}")
        
        return True
        
    except Exception as e:
        logger.error(f"Search service error: {e}")
        return False

def check_entities():
    """Check entity extraction status"""
    logger.info("\n=== Entity Extraction Verification ===")
    
    db = SimpleDB()
    
    # Get entity statistics
    entity_stats = db.execute("""
        SELECT entity_type, COUNT(DISTINCT entity_value) as count
        FROM entities
        GROUP BY entity_type
        ORDER BY count DESC
        LIMIT 10
    """).fetchall()
    
    if entity_stats:
        logger.info("Entity types found:")
        for entity_type, count in entity_stats:
            logger.info(f"  {entity_type}: {count} unique values")
        return True
    else:
        logger.warning("No entities found in database")
        return False

def main():
    """Run all verification checks"""
    logger.info("Starting system verification after recovery...")
    
    results = {}
    
    # Database check
    db_stats = check_database()
    results['database'] = bool(db_stats.get('content_unified', 0) > 0)
    
    # Vector store check
    results['vector_store'] = check_vector_store()
    
    # Search check
    results['search'] = check_search()
    
    # Entity check
    results['entities'] = check_entities()
    
    # Summary
    logger.info("\n=== VERIFICATION SUMMARY ===")
    all_good = True
    for component, status in results.items():
        status_str = "✓ WORKING" if status else "✗ NEEDS ATTENTION"
        logger.info(f"{component}: {status_str}")
        if not status:
            all_good = False
    
    if all_good:
        logger.info("\n🎉 System fully operational!")
    else:
        logger.warning("\n⚠️ Some components need attention")
    
    return all_good

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)