#!/usr/bin/env python3
"""
Production Preflight Check System

Validates all system components before production operations.
Usage: python3 tools/preflight.py [--verbose]
"""

import argparse
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from loguru import logger


class PreflightChecker:
    """Comprehensive system validation for production readiness."""
    
    def __init__(self, verbose: bool = False):
        self.verbose = verbose
        self.checks_passed = 0
        self.checks_failed = 0
        self.warnings = 0
        
    def _print_check(self, name: str, status: bool, message: str = "", warning: bool = False):
        """Print check result with consistent formatting."""
        if warning:
            icon = "⚠️"
            self.warnings += 1
        elif status:
            icon = "✅"
            self.checks_passed += 1
        else:
            icon = "❌"
            self.checks_failed += 1
            
        print(f"{icon} {name}")
        if message:
            if warning:
                print(f"   Warning: {message}")
            else:
                print(f"   {message}")
        if self.verbose and not status and not warning:
            # In verbose mode, log details for failures
            logger.debug(f"Check '{name}' failed: {message}")
    
    def check_database_schema(self):
        """Verify database has all required columns."""
        print("\n=== Database Schema Checks ===")
        
        try:
            import sqlite3
            conn = sqlite3.connect('data/emails.db')
            
            # Check content table columns
            cursor = conn.execute('PRAGMA table_info(content)')
            columns = {row[1]: row[2] for row in cursor.fetchall()}
            
            required_columns = {
                'id': 'TEXT',
                'eid': 'TEXT',
                'message_id': 'TEXT', 
                'word_count': 'INTEGER',
                'source_path': 'TEXT',
                'vector_processed': 'INTEGER'
            }
            
            all_present = True
            for col, expected_type in required_columns.items():
                if col not in columns:
                    self._print_check(f"Column '{col}' exists", False, f"Missing column: {col}")
                    all_present = False
                else:
                    self._print_check(f"Column '{col}' exists", True)
            
            self._print_check("All required columns present", all_present)
            
            # Check indexes
            cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='index' AND name LIKE 'ix_content_%'")
            indexes = {row[0] for row in cursor.fetchall()}
            
            required_indexes = {
                'ix_content_message_id',
                'ix_content_vector_processed', 
                'ix_content_eid'
            }
            
            all_indexes = True
            for idx in required_indexes:
                if idx not in indexes:
                    self._print_check(f"Index '{idx}' exists", False)
                    all_indexes = False
                else:
                    self._print_check(f"Index '{idx}' exists", True)
            
            conn.close()
            return all_present and all_indexes
            
        except Exception as e:
            self._print_check("Database access", False, f"Cannot access database: {e}")
            return False
    
    def check_simpledb_methods(self):
        """Verify SimpleDB has all required batch methods."""
        print("\n=== SimpleDB Methods Checks ===")
        
        try:
            from shared.simple_db import SimpleDB
            db = SimpleDB()
            
            required_methods = [
                'get_all_content_ids',
                'get_content_by_ids', 
                'mark_content_vectorized',
                'batch_mark_vectorized'
            ]
            
            all_present = True
            for method in required_methods:
                exists = hasattr(db, method) and callable(getattr(db, method))
                self._print_check(f"Method '{method}' exists", exists)
                if not exists:
                    all_present = False
            
            # Test basic functionality
            if all_present:
                try:
                    ids = db.get_all_content_ids()
                    self._print_check("get_all_content_ids() works", True, f"Found {len(ids)} content IDs")
                    
                    if len(ids) >= 1:
                        content = db.get_content_by_ids(ids[:1])
                        self._print_check("get_content_by_ids() works", True, f"Retrieved {len(content)} items")
                        
                        result = db.mark_content_vectorized(ids[0])
                        self._print_check("mark_content_vectorized() works", result)
                        
                        updated = db.batch_mark_vectorized(ids[:2])
                        self._print_check("batch_mark_vectorized() works", updated >= 0, f"Updated {updated} items")
                    
                except Exception as e:
                    self._print_check("Method functionality test", False, f"Runtime error: {e}")
                    all_present = False
            
            return all_present
            
        except Exception as e:
            self._print_check("SimpleDB import", False, f"Cannot import SimpleDB: {e}")
            return False
    
    def check_services(self):
        """Verify all services initialize correctly."""
        print("\n=== Service Initialization Checks ===")
        
        services = [
            ('Gmail Service', 'gmail', 'get_gmail_service'),
            ('PDF Service', 'pdf', 'get_pdf_service'),
            ('Search Intelligence', 'search_intelligence.main', 'SearchIntelligenceService'),
            ('Knowledge Graph', 'knowledge_graph.main', 'KnowledgeGraphService'),
            ('Legal Intelligence', 'legal_intelligence.main', 'LegalIntelligenceService'),
        ]
        
        all_services_ok = True
        for name, module, service_class in services:
            try:
                if 'get_' in service_class:
                    # It's a getter function
                    exec(f'from {module} import {service_class}')
                    exec(f'service = {service_class}()')
                else:
                    # It's a class
                    exec(f'from {module} import {service_class}')
                    exec(f'service = {service_class}()')
                self._print_check(f"{name} initialization", True)
            except Exception as e:
                self._print_check(f"{name} initialization", False, str(e))
                all_services_ok = False
        
        return all_services_ok
    
    def check_qdrant_connection(self):
        """Verify Qdrant vector store is accessible."""
        print("\n=== Qdrant Vector Store Checks ===")
        
        try:
            from utilities.vector_store import get_vector_store
            vector_store = get_vector_store()
            
            # Test basic connection
            try:
                # This should work without raising an exception if Qdrant is accessible
                info = vector_store.client.get_collections()
                self._print_check("Qdrant connection", True, f"Connected to Qdrant")
                
                # Check collection exists
                collections = [c.name for c in info.collections]
                emails_exists = 'emails' in collections
                self._print_check("'emails' collection exists", emails_exists)
                
                if emails_exists:
                    # Check collection info
                    collection_info = vector_store.client.get_collection('emails')
                    vector_count = collection_info.vectors_count or 0
                    self._print_check("Vector collection ready", vector_count > 0, 
                                    f"{vector_count} vectors in collection")
                
                return emails_exists
                
            except Exception as e:
                self._print_check("Qdrant connection", False, f"Connection failed: {e}")
                return False
                
        except Exception as e:
            self._print_check("Vector store import", False, f"Cannot import vector store: {e}")
            return False
    
    def check_embedding_service(self):
        """Verify embedding service produces correct dimensions."""
        print("\n=== Embedding Service Checks ===")
        
        try:
            from utilities.embeddings import get_embedding_service
            
            # Test without loading model yet
            self._print_check("Embedding service import", True)
            
            # Optionally test model loading (can be slow)
            if self.verbose:
                print("   Loading Legal BERT model (this may take a few seconds)...")
                embedding_service = get_embedding_service()
                
                # Test embedding generation
                test_text = "This is a test document for legal analysis."
                embedding = embedding_service.get_embedding(test_text)
                
                # Check dimensions
                expected_dim = 1024
                actual_dim = len(embedding)
                self._print_check("Embedding dimensions", actual_dim == expected_dim, 
                                f"Got {actual_dim}, expected {expected_dim}")
                
                # Check L2 normalization
                import numpy as np
                norm = np.linalg.norm(embedding)
                is_normalized = abs(norm - 1.0) < 1e-6
                self._print_check("L2 normalization", is_normalized, f"L2 norm: {norm:.6f}")
                
                return actual_dim == expected_dim and is_normalized
            else:
                # Skip model loading in fast mode
                self._print_check("Embedding model test", True, "Skipped (use --verbose to test)")
                return True
                
        except Exception as e:
            self._print_check("Embedding service", False, f"Error: {e}")
            return False
    
    def check_cli_tools(self):
        """Verify CLI tools work without timeout."""
        print("\n=== CLI Tools Checks ===")
        
        try:
            import subprocess
            
            # Test vsearch help loads quickly
            result = subprocess.run(['python3', 'tools/scripts/vsearch', '--help'], 
                                  capture_output=True, text=True, timeout=3)
            
            if result.returncode == 0:
                self._print_check("vsearch CLI loads quickly", True, "No timeout after 3 seconds")
                return True
            else:
                self._print_check("vsearch CLI loads", False, "Non-zero exit code")
                return False
                
        except subprocess.TimeoutExpired:
            self._print_check("vsearch CLI timeout", False, "Took longer than 3 seconds")
            return False
        except Exception as e:
            self._print_check("vsearch CLI test", False, f"Error: {e}")
            return False
    
    def check_vector_parity(self):
        """Verify vector store is in sync with database."""
        print("\n=== Vector Parity Checks ===")
        
        try:
            import subprocess
            import json
            import os
            
            # Set environment variables for the check
            env = os.environ.copy()
            env.update({
                'APP_DB_PATH': 'data/emails.db',
                'VSTORE_COLLECTION': 'emails',
                'ALLOW_EMPTY_COLLECTION': 'false',
                'EXPECTED_DIM': '1024'
            })
            
            # Run the vector parity check
            result = subprocess.run(['python3', 'tools/preflight/vector_parity_check.py'], 
                                  capture_output=True, text=True, timeout=30, env=env)
            
            if result.returncode in [0, 1]:  # 0 = OK, 1 = Warning
                # Parse the JSON output to get details
                try:
                    data = json.loads(result.stdout)
                    qdrant_info = data.get('qdrant', {})
                    db_info = data.get('db', {})
                    reconciliation = data.get('reconciliation', {})
                    
                    health = qdrant_info.get('health', 'unknown')
                    point_count = qdrant_info.get('point_count', 0)
                    eligible_content = db_info.get('eligible_content', 0)
                    delta = reconciliation.get('delta', 0)
                    
                    self._print_check("Qdrant health", health == "green", f"Status: {health}")
                    self._print_check("Collection exists", qdrant_info.get('collection_exists', False))
                    self._print_check("Vector dimensions", qdrant_info.get('dimension') == 1024, 
                                    f"Expected 1024, got {qdrant_info.get('dimension')}")
                    
                    # Handle delta warnings vs errors
                    if result.returncode == 1 and "warning" in data:
                        self._print_check("Vector count sync", True, data["warning"], warning=True)
                    else:
                        self._print_check("Vector count sync", delta == 0, 
                                        f"DB: {eligible_content}, Qdrant: {point_count}, Delta: {delta}")
                    
                    # Return True for warnings (exit code 1) and success (exit code 0)
                    return health == "green" and qdrant_info.get('collection_exists', False)
                except json.JSONDecodeError:
                    self._print_check("Vector parity parsing", False, "Invalid JSON output")
                    return False
            else:
                # Parse error output if available
                try:
                    error_data = json.loads(result.stdout)
                    error_msg = error_data.get('error', 'Unknown error')
                except:
                    error_msg = result.stderr.strip() or "Check failed"
                
                self._print_check("Vector parity check", False, error_msg)
                return False
                
        except subprocess.TimeoutExpired:
            self._print_check("Vector parity timeout", False, "Check took longer than 30 seconds")
            return False
        except Exception as e:
            self._print_check("Vector parity check", False, f"Error: {e}")
            return False
    
    def run_all_checks(self):
        """Run comprehensive preflight checks."""
        print("=" * 60)
        print("🚀 PRODUCTION PREFLIGHT CHECK SYSTEM")
        print("=" * 60)
        
        all_checks = [
            self.check_database_schema,
            self.check_simpledb_methods, 
            self.check_services,
            self.check_qdrant_connection,
            self.check_embedding_service,
            self.check_cli_tools,
            self.check_vector_parity,
        ]
        
        results = []
        for check in all_checks:
            try:
                result = check()
                results.append(result)
            except Exception as e:
                logger.error(f"Preflight check failed with exception: {e}")
                results.append(False)
        
        # Final summary
        print("\n" + "=" * 60)
        print("PREFLIGHT CHECK SUMMARY")
        print("=" * 60)
        
        all_passed = all(results)
        
        print(f"✅ Checks passed: {self.checks_passed}")
        print(f"❌ Checks failed: {self.checks_failed}")
        print(f"⚠️  Warnings: {self.warnings}")
        
        if all_passed:
            print("\n🎉 ALL SYSTEMS GO - Ready for production!")
            return True
        else:
            print(f"\n❌ SYSTEM NOT READY - {self.checks_failed} checks failed")
            print("   Fix the failed checks before proceeding to production.")
            return False


def main():
    parser = argparse.ArgumentParser(description="Run production preflight checks")
    parser.add_argument("--verbose", "-v", action="store_true", 
                       help="Run comprehensive tests including model loading")
    
    args = parser.parse_args()
    
    checker = PreflightChecker(verbose=args.verbose)
    success = checker.run_all_checks()
    
    # Exit with appropriate code
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()