#!/usr/bin/env python3
"""
Comprehensive System Diagnostics - Surface ALL Issues in One Shot
Eliminates whack-a-mole debugging by checking everything systematically.
"""

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import json
import time
import traceback
from collections import defaultdict
from typing import Any, Dict, List, Tuple

from loguru import logger

# Configure diagnostic logging
logger.remove()
logger.add(
    sys.stderr,
    level="DEBUG",
    format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{function}</cyan> - <level>{message}</level>",
    colorize=True,
    diagnose=True,
    backtrace=True
)

from config.settings import settings

# Import all components to test
from lib.db import SimpleDB
from lib.embeddings import get_embedding_service
from lib.search import find_literal, hybrid_search, search
from lib.vector_store import get_vector_store

# Note: Import errors will be caught and reported

try:
    from qdrant_client import QdrantClient
    QDRANT_AVAILABLE = True
except ImportError:
    QDRANT_AVAILABLE = False


class SystemDiagnostics:
    """Comprehensive system health checker."""
    
    def __init__(self):
        self.errors = defaultdict(list)
        self.warnings = defaultdict(list)
        self.info = defaultdict(list)
        self.stats = {}
        
    def log_error(self, category: str, message: str, details: Any = None):
        """Log an error with full context."""
        entry = {
            "message": message,
            "details": details,
            "traceback": traceback.format_exc() if sys.exc_info()[0] else None
        }
        self.errors[category].append(entry)
        logger.error(f"[{category}] {message}")
        
    def log_warning(self, category: str, message: str, details: Any = None):
        """Log a warning."""
        entry = {"message": message, "details": details}
        self.warnings[category].append(entry)
        logger.warning(f"[{category}] {message}")
        
    def log_info(self, category: str, message: str, details: Any = None):
        """Log info."""
        entry = {"message": message, "details": details}
        self.info[category].append(entry)
        logger.info(f"[{category}] {message}")
        
    def check_database_integrity(self) -> bool:
        """Check database structure and data integrity."""
        logger.info("=" * 60)
        logger.info("CHECKING DATABASE INTEGRITY")
        logger.info("=" * 60)
        
        try:
            db = SimpleDB(settings.database.emails_db_path)
            
            # Check table existence
            tables = db.fetch_all("""
                SELECT name FROM sqlite_master 
                WHERE type='table' 
                ORDER BY name
            """)
            table_names = [t['name'] for t in tables]
            
            required_tables = [
                'content_unified',
                'individual_messages', 
                'message_occurrences',
                'document_summaries',
                'entities'
            ]
            
            for table in required_tables:
                if table not in table_names:
                    self.log_error("DATABASE", f"Missing required table: {table}")
                else:
                    self.log_info("DATABASE", f"Table exists: {table}")
                    
            # Check content_unified integrity
            orphaned = db.fetch_all("""
                SELECT COUNT(*) as count 
                FROM content_unified 
                WHERE source_id IS NULL OR source_type IS NULL
            """)
            
            if orphaned[0]['count'] > 0:
                self.log_warning("DATABASE", f"Found {orphaned[0]['count']} records with NULL source info")
                
            # Check for duplicate content
            duplicates = db.fetch_all("""
                SELECT source_id, source_type, COUNT(*) as count
                FROM content_unified
                GROUP BY source_id, source_type
                HAVING COUNT(*) > 1
            """)
            
            if duplicates:
                self.log_error("DATABASE", f"Found {len(duplicates)} duplicate content entries", duplicates[:5])
                
            # Get statistics
            content_count = db.fetch_one("SELECT COUNT(*) as count FROM content_unified")['count']
            message_count = db.fetch_one("SELECT COUNT(*) as count FROM individual_messages")['count']
            
            self.stats['content_count'] = content_count
            self.stats['message_count'] = message_count
            
            self.log_info("DATABASE", f"Total content: {content_count}, Total messages: {message_count}")
            
            return len(self.errors['DATABASE']) == 0
            
        except Exception as e:
            self.log_error("DATABASE", f"Database check failed: {e}")
            return False
            
    def check_vector_store_integrity(self) -> bool:
        """Check vector store health and alignment."""
        logger.info("=" * 60)
        logger.info("CHECKING VECTOR STORE INTEGRITY")
        logger.info("=" * 60)
        
        if not QDRANT_AVAILABLE:
            self.log_error("VECTOR_STORE", "Qdrant client not available")
            return False
            
        try:
            client = QdrantClient(host="localhost", port=6333)
            
            # Check collections
            collections = client.get_collections().collections
            collection_names = [c.name for c in collections]
            
            if 'vectors_v2' not in collection_names:
                self.log_error("VECTOR_STORE", "Missing primary collection: vectors_v2")
                return False
                
            # Get collection info
            info = client.get_collection('vectors_v2')
            vector_count = info.vectors_count
            point_count = info.points_count
            
            self.stats['vector_count'] = vector_count
            self.stats['point_count'] = point_count
            
            self.log_info("VECTOR_STORE", f"Vectors: {vector_count}, Points: {point_count}")
            
            # Check for orphaned vectors
            if self.stats.get('content_count'):
                db = SimpleDB(settings.database.emails_db_path)
                
                # Sample check - get first 100 vectors
                vectors = client.scroll(
                    collection_name='vectors_v2',
                    limit=100,
                    with_payload=True,
                    with_vectors=False
                )[0]
                
                orphaned_vectors = []
                for point in vectors:
                    content_id = point.payload.get('content_id')
                    if content_id:
                        exists = db.fetch_one(
                            "SELECT 1 FROM content_unified WHERE id = ?",
                            (int(content_id),)
                        )
                        if not exists:
                            orphaned_vectors.append(content_id)
                            
                if orphaned_vectors:
                    self.log_error(
                        "VECTOR_STORE", 
                        f"Found {len(orphaned_vectors)} orphaned vectors (sample of 100)",
                        orphaned_vectors[:10]
                    )
                    
            # Check vector dimensions
            if vector_count is not None and vector_count > 0:
                sample = client.retrieve(
                    collection_name='vectors_v2',
                    ids=[vectors[0].id],
                    with_vectors=True
                )[0]
                
                if sample.vector:
                    dim = len(sample.vector)
                    if dim != 1024:
                        self.log_error("VECTOR_STORE", f"Wrong dimension: {dim} (expected 1024)")
                    else:
                        self.log_info("VECTOR_STORE", f"Correct dimension: {dim}")
                        
            return len(self.errors['VECTOR_STORE']) == 0
            
        except Exception as e:
            self.log_error("VECTOR_STORE", f"Vector store check failed: {e}")
            return False
            
    def check_embedding_service(self) -> bool:
        """Check embedding service functionality."""
        logger.info("=" * 60)
        logger.info("CHECKING EMBEDDING SERVICE")
        logger.info("=" * 60)
        
        try:
            service = get_embedding_service(use_mock=False)
            
            # Test encoding
            test_texts = [
                "Short text",
                "Legal document about contracts and agreements",
                "A" * 5000  # Long text
            ]
            
            for text in test_texts:
                start = time.time()
                vector = service.encode(text)
                elapsed = time.time() - start
                
                if len(vector) != 1024:
                    self.log_error(
                        "EMBEDDINGS",
                        f"Wrong dimension for '{text[:50]}': {len(vector)}"
                    )
                else:
                    self.log_info(
                        "EMBEDDINGS",
                        f"Encoded {len(text)} chars in {elapsed:.2f}s"
                    )
                    
            # Check if cloud embeddings configured
            use_cloud = os.getenv("USE_CLOUD_EMBEDDINGS", "").lower() in ("1", "true", "yes")
            hf_token = os.getenv("HF_TOKEN")
            
            if use_cloud and not hf_token:
                self.log_error("EMBEDDINGS", "Cloud embeddings enabled but no HF_TOKEN")
            elif use_cloud:
                self.log_info("EMBEDDINGS", "Cloud embeddings properly configured")
            else:
                self.log_info("EMBEDDINGS", "Using local embeddings")
                
            return len(self.errors['EMBEDDINGS']) == 0
            
        except Exception as e:
            self.log_error("EMBEDDINGS", f"Embedding service check failed: {e}")
            return False
            
    def check_search_functionality(self) -> bool:
        """Check search pipeline end-to-end."""
        logger.info("=" * 60)
        logger.info("CHECKING SEARCH FUNCTIONALITY")
        logger.info("=" * 60)
        
        try:
            # Test queries
            test_queries = [
                ("contract", "keyword"),
                ("legal agreement tenant", "semantic"),
                ("person:john", "filter")
            ]
            
            for query, query_type in test_queries:
                logger.info(f"Testing {query_type} search: '{query}'")
                
                try:
                    # Test hybrid search
                    start = time.time()
                    results = hybrid_search(query, limit=5)
                    elapsed = time.time() - start
                    
                    self.log_info(
                        "SEARCH",
                        f"{query_type} search returned {len(results)} results in {elapsed:.2f}s"
                    )
                    
                    # Check result quality
                    if results:
                        # Check for missing fields
                        for r in results:
                            required = ['id', 'title', 'score']
                            missing = [f for f in required if f not in r]
                            if missing:
                                self.log_warning(
                                    "SEARCH",
                                    f"Result missing fields: {missing}",
                                    r
                                )
                                
                except Exception as e:
                    self.log_error("SEARCH", f"Search failed for '{query}': {e}")
                    
            return len(self.errors['SEARCH']) == 0
            
        except Exception as e:
            self.log_error("SEARCH", f"Search check failed: {e}")
            return False
            
    def check_data_alignment(self) -> bool:
        """Check alignment between database and vector store."""
        logger.info("=" * 60)
        logger.info("CHECKING DATA ALIGNMENT")
        logger.info("=" * 60)
        
        try:
            db = SimpleDB(settings.database.emails_db_path)
            store = get_vector_store('vectors_v2')
            
            # Sample check - get recent content
            recent_content = db.fetch_all("""
                SELECT id, title, source_type 
                FROM content_unified 
                ORDER BY created_at DESC 
                LIMIT 20
            """)
            
            misaligned = []
            for content in recent_content:
                vector = store.get_vector(str(content['id']))
                if not vector:
                    misaligned.append({
                        'id': content['id'],
                        'title': content['title'][:50],
                        'issue': 'No vector'
                    })
                elif vector['payload'].get('content_id') != str(content['id']):
                    misaligned.append({
                        'id': content['id'],
                        'title': content['title'][:50],
                        'issue': 'ID mismatch'
                    })
                    
            if misaligned:
                self.log_error(
                    "ALIGNMENT",
                    f"Found {len(misaligned)} misaligned records",
                    misaligned
                )
            else:
                self.log_info("ALIGNMENT", "Sample check passed - data aligned")
                
            return len(misaligned) == 0
            
        except Exception as e:
            self.log_error("ALIGNMENT", f"Alignment check failed: {e}")
            return False
            
    def check_configuration(self) -> bool:
        """Check system configuration."""
        logger.info("=" * 60)
        logger.info("CHECKING CONFIGURATION")
        logger.info("=" * 60)
        
        critical_paths = [
            settings.database.emails_db_path,
            settings.database.content_db_path,
            settings.gmail.credentials_path
        ]
        
        for path in critical_paths:
            if not Path(path).exists():
                self.log_warning("CONFIG", f"Missing file: {path}")
            else:
                self.log_info("CONFIG", f"Found: {path}")
                
        # Check environment variables
        critical_env = {
            'QDRANT_HOST': os.getenv('QDRANT_HOST', 'localhost'),
            'LOG_LEVEL': os.getenv('LOG_LEVEL', 'INFO'),
            'USE_CLOUD_EMBEDDINGS': os.getenv('USE_CLOUD_EMBEDDINGS', 'false')
        }
        
        for key, value in critical_env.items():
            self.log_info("CONFIG", f"{key}={value}")
            
        return True
        
    def generate_report(self) -> Dict:
        """Generate comprehensive diagnostic report."""
        report = {
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "summary": {
                "total_errors": sum(len(errors) for errors in self.errors.values()),
                "total_warnings": sum(len(warnings) for warnings in self.warnings.values()),
                "categories_with_errors": list(self.errors.keys()),
                "categories_with_warnings": list(self.warnings.keys())
            },
            "errors": dict(self.errors),
            "warnings": dict(self.warnings),
            "info": dict(self.info),
            "statistics": self.stats
        }
        
        return report
        
    def run_all_diagnostics(self) -> Dict:
        """Run all diagnostic checks."""
        logger.info("=" * 60)
        logger.info("STARTING COMPREHENSIVE SYSTEM DIAGNOSTICS")
        logger.info("=" * 60)
        
        checks = [
            ("Configuration", self.check_configuration),
            ("Database Integrity", self.check_database_integrity),
            ("Vector Store", self.check_vector_store_integrity),
            ("Embedding Service", self.check_embedding_service),
            ("Search Functionality", self.check_search_functionality),
            ("Data Alignment", self.check_data_alignment)
        ]
        
        results = {}
        for name, check_func in checks:
            try:
                results[name] = check_func()
            except Exception as e:
                logger.error(f"Check '{name}' crashed: {e}")
                self.log_error(name.upper(), f"Check crashed: {e}")
                results[name] = False
                
        report = self.generate_report()
        report['check_results'] = results
        
        # Print summary
        logger.info("=" * 60)
        logger.info("DIAGNOSTIC SUMMARY")
        logger.info("=" * 60)
        
        if report['summary']['total_errors'] == 0:
            logger.success("✅ NO ERRORS FOUND - System appears healthy")
        else:
            logger.error(f"❌ FOUND {report['summary']['total_errors']} ERRORS")
            
            for category, errors in self.errors.items():
                logger.error(f"\n{category}:")
                for error in errors:
                    logger.error(f"  - {error['message']}")
                    
        if report['summary']['total_warnings'] > 0:
            logger.warning(f"⚠️  FOUND {report['summary']['total_warnings']} WARNINGS")
            
        # Save report
        report_path = Path("diagnostics_report.json")
        with open(report_path, 'w') as f:
            json.dump(report, f, indent=2, default=str)
        logger.info(f"\n📊 Full report saved to: {report_path}")
        
        return report


def main():
    """Run comprehensive diagnostics."""
    diag = SystemDiagnostics()
    report = diag.run_all_diagnostics()
    
    # Exit with error code if issues found
    if report['summary']['total_errors'] > 0:
        sys.exit(1)
    else:
        sys.exit(0)


if __name__ == "__main__":
    main()