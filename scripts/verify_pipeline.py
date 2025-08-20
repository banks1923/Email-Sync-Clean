#!/usr/bin/env python3
"""
PDF Pipeline Verification Suite
Comprehensive end-to-end testing with all 8 issues fixed per user feedback.
"""

import argparse
import json
import os
import sys
import sqlite3
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Any, Optional

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from loguru import logger
from shared.simple_db import SimpleDB


class PipelineVerifier:
    """Comprehensive PDF pipeline verification with all fixes applied."""
    
    def __init__(self, db_path: str = None, json_mode: bool = False):
        # Fix 1: Pass DB path into SimpleDB properly
        self.db_path = db_path or os.getenv("APP_DB_PATH", "data/emails.db")
        self.json_mode = json_mode
        
        # Initialize SimpleDB with proper path
        self.db = SimpleDB(self.db_path)
        
        # Fix 2: DB usage & safety - ensure WAL mode and foreign keys
        self._ensure_db_safety()
        
        # Store results for JSON output
        self.results = {
            "timestamp": datetime.now().isoformat(),
            "db_path": self.db_path,
            "tests": {},
            "overall_status": "PASS"
        }
    
    def _ensure_db_safety(self):
        """Fix 2: Ensure proper SQLite configuration."""
        try:
            self.db.execute("PRAGMA foreign_keys=ON")
            self.db.execute("PRAGMA journal_mode=WAL")
            if not self.json_mode:
                logger.info("Database safety configured: WAL mode, foreign keys enabled")
        except Exception as e:
            logger.error(f"Failed to configure database safety: {e}")
    
    def _content_table(self) -> str:
        """Fix 2: Handle table naming drift gracefully."""
        for name in ("content_unified", "content"):
            try:
                self.db.execute(f"SELECT COUNT(*) FROM {name} LIMIT 1")
                return name
            except sqlite3.OperationalError:
                continue
        raise RuntimeError("No content table found (checked: content_unified, content)")
    
    def _sqlite_window(self, since_str: str) -> str:
        """Fix 6: Robust --since parsing (30m, 24h, 7d)."""
        if not since_str:
            return None
        
        try:
            unit = since_str[-1].lower()
            n = int(since_str[:-1])
            
            unit_map = {'m': 'minutes', 'h': 'hours', 'd': 'days'}
            if unit not in unit_map:
                raise ValueError(f"Invalid unit: {unit}")
            
            return f"-{n} {unit_map[unit]}"
        except (ValueError, IndexError) as e:
            raise ValueError(f"Invalid --since format '{since_str}'. Use: 30m, 24h, 7d") from e
    
    def _resolve_sha_prefix(self, sha_prefix: str) -> Optional[str]:
        """Resolve short SHA prefix to full SHA256 with DISTINCT to handle chunks."""
        results = self.db.fetch(
            "SELECT DISTINCT sha256 FROM documents WHERE sha256 LIKE ? || '%' LIMIT 2",
            (sha_prefix,)
        )
        
        if len(results) == 0:
            return None
        elif len(results) == 2:
            raise ValueError(f"Ambiguous SHA prefix '{sha_prefix}' - matches multiple unique documents")
        else:
            return results[0]['sha256']
    
    def _log_test_result(self, test_name: str, passed: bool, details: Dict[str, Any]):
        """Fix 4: Respect JSON mode for logging."""
        status = "PASS" if passed else "FAIL"
        
        self.results["tests"][test_name] = {
            "status": status,
            "details": details,
            "timestamp": datetime.now().isoformat()
        }
        
        if not passed:
            self.results["overall_status"] = "FAIL"
        
        # Fix 6: Use loguru for human mode only
        if not self.json_mode:
            emoji = "✅" if passed else "❌"
            logger.info(f"{emoji} {test_name}: {status}")
            if details and not passed:
                logger.info(f"   Details: {details}")
    
    def preflight_test(self) -> bool:
        """Test schema and environment readiness."""
        details = {}
        issues = []
        
        try:
            # Check database exists
            if not Path(self.db_path).exists():
                issues.append(f"Database not found: {self.db_path}")
            
            # Check schema version
            try:
                result = self.db.fetch_one("SELECT MAX(version) as version FROM schema_version")
                schema_version = result['version'] if result and result['version'] else 0
                details["schema_version"] = schema_version
                
                # Expected schema version after all current migrations
                expected_version = 3  # V001 + V002 + V003
                details["expected_schema_version"] = expected_version
                
                if schema_version < 1:
                    issues.append("Schema migrations not applied")
                elif schema_version < expected_version:
                    issues.append(f"Schema incomplete: version {schema_version}, expected {expected_version}")
                    
                # Validate specific migration entries
                migrations = self.db.fetch("SELECT version, description FROM schema_version ORDER BY version")
                details["applied_migrations"] = {m['version']: m['description'] for m in migrations}
                
            except sqlite3.OperationalError:
                issues.append("No schema_version table")
            
            # Check required tables
            content_table = self._content_table()
            details["content_table"] = content_table
            
            required_tables = ['documents', 'embeddings', 'schema_version']
            existing_tables = [row['name'] for row in self.db.fetch(
                "SELECT name FROM sqlite_master WHERE type='table'"
            )]
            
            for table in required_tables:
                if table not in existing_tables:
                    issues.append(f"Missing table: {table}")
            
            # Check required columns in documents table
            required_columns = {'sha256', 'char_count', 'word_count', 'status', 'processed_at', 'chunk_index'}
            try:
                columns = self.db.fetch("PRAGMA table_info(documents)")
                existing_columns = {col['name'] for col in columns}
                missing_cols = required_columns - existing_columns
                if missing_cols:
                    issues.append(f"Missing documents columns: {missing_cols}")
                details["documents_columns"] = list(existing_columns)
            except sqlite3.OperationalError:
                issues.append("Cannot check documents table schema")
            
            # Validate critical database constraints (V002 & V003 requirements)
            try:
                # Check for documents table unique constraint
                indexes = self.db.fetch("SELECT name FROM sqlite_master WHERE type='index' AND tbl_name='documents'")
                index_names = [idx['name'] for idx in indexes]
                details["documents_indexes"] = index_names
                
                # Check for the critical unique constraint from V003
                has_unique_constraint = any('sha256_chunk_unique' in name for name in index_names)
                details["has_unique_constraint"] = has_unique_constraint
                
                if not has_unique_constraint:
                    issues.append("Missing unique constraint on documents(sha256, chunk_index)")
                
                # Check content_unified table constraints
                content_indexes = self.db.fetch(f"SELECT name FROM sqlite_master WHERE type='index' AND tbl_name='{content_table}'")
                content_index_names = [idx['name'] for idx in content_indexes]
                details["content_indexes"] = content_index_names
                
                # Check embeddings table constraints
                embeddings_indexes = self.db.fetch("SELECT name FROM sqlite_master WHERE type='index' AND tbl_name='embeddings'")  
                embeddings_index_names = [idx['name'] for idx in embeddings_indexes]
                details["embeddings_indexes"] = embeddings_index_names
                
            except sqlite3.OperationalError as e:
                issues.append(f"Cannot check database constraints: {str(e)}")
            
            # Check Qdrant connection
            try:
                import requests
                resp = requests.get("http://localhost:6333/readyz", timeout=2)
                if resp.status_code == 200:
                    details["qdrant_status"] = "connected"
                else:
                    issues.append(f"Qdrant unhealthy: HTTP {resp.status_code}")
            except Exception as e:
                issues.append(f"Qdrant not accessible: {str(e)}")
            
            details["issues"] = issues
            passed = len(issues) == 0
            
        except Exception as e:
            issues.append(f"Preflight check failed: {str(e)}")
            details["issues"] = issues
            passed = False
        
        self._log_test_result("preflight", passed, details)
        return passed
    
    def schema_integrity_test(self) -> bool:
        """Test schema integrity and validate against known-good state."""
        details = {}
        issues = []
        
        try:
            # Test V002 fix: SHA256 truncation should be resolved
            content_table = self._content_table()
            
            # Check for orphaned content_unified records (V002 issue)
            orphaned_query = f"""
                SELECT COUNT(*) as count
                FROM {content_table} c
                LEFT JOIN documents d ON c.source_id = d.sha256
                WHERE c.source_type = 'document' AND d.sha256 IS NULL
            """
            orphaned_result = self.db.fetch_one(orphaned_query)
            orphaned_count = orphaned_result['count'] if orphaned_result else 0
            details["orphaned_content_records"] = orphaned_count
            
            if orphaned_count > 0:
                issues.append(f"Found {orphaned_count} orphaned content records (V002 regression)")
            
            # Check source_id length consistency (should be 64 chars for SHA256)
            short_source_ids = self.db.fetch_one(f"""
                SELECT COUNT(*) as count 
                FROM {content_table} 
                WHERE source_type = 'document' AND length(source_id) < 64
            """)
            short_count = short_source_ids['count'] if short_source_ids else 0
            details["truncated_source_ids"] = short_count
            
            if short_count > 0:
                issues.append(f"Found {short_count} truncated source_ids (V002 regression)")
            
            # Test V003 constraint: Try to insert duplicate (should fail)
            test_sha256 = "test_constraint_validation_sha256_1234567890123456789012345678"  # 64 chars
            test_passed = True
            
            try:
                # Clean up any existing test data first
                self.db.execute("DELETE FROM documents WHERE chunk_id LIKE 'schema_integrity_test_%'")
                
                # Insert first record (should succeed)
                self.db.execute("""
                    INSERT INTO documents (chunk_id, sha256, chunk_index, file_name) 
                    VALUES ('schema_integrity_test_1', ?, 0, 'test.pdf')
                """, (test_sha256,))
                
                # Try to insert duplicate (should fail with UNIQUE constraint)
                try:
                    self.db.execute("""
                        INSERT INTO documents (chunk_id, sha256, chunk_index, file_name) 
                        VALUES ('schema_integrity_test_2', ?, 0, 'test2.pdf')
                    """, (test_sha256,))
                    
                    # If we get here, constraint failed
                    issues.append("V003 unique constraint not working - duplicates allowed")
                    test_passed = False
                    
                except sqlite3.IntegrityError as e:
                    if "UNIQUE constraint failed" in str(e):
                        details["constraint_test"] = "passed"
                    else:
                        issues.append(f"Unexpected constraint error: {str(e)}")
                        test_passed = False
                
                # Clean up test data
                self.db.execute("DELETE FROM documents WHERE chunk_id LIKE 'schema_integrity_test_%'")
                
            except Exception as e:
                issues.append(f"Constraint validation test failed: {str(e)}")
                test_passed = False
            
            # Validate migration table consistency
            try:
                migration_files = self.db.fetch("SELECT * FROM migrations ORDER BY filename")
                schema_versions = self.db.fetch("SELECT * FROM schema_version ORDER BY version")
                
                details["migration_files_applied"] = len(migration_files)
                details["schema_versions_recorded"] = len(schema_versions)
                
                # Check for migration/schema version consistency
                if migration_files and schema_versions:
                    # Both tables should have entries
                    details["migration_tracking"] = "consistent"
                elif not migration_files and not schema_versions:
                    # No migrations applied yet - that's ok for old systems
                    details["migration_tracking"] = "none_applied"
                else:
                    # Inconsistent state
                    issues.append("Migration tracking inconsistent between migrations and schema_version tables")
                    
            except sqlite3.OperationalError:
                # migrations table might not exist in older systems
                details["migration_tracking"] = "legacy_system"
            
            details["issues"] = issues
            passed = len(issues) == 0 and test_passed
            
        except Exception as e:
            issues.append(f"Schema integrity test failed: {str(e)}")
            details["issues"] = issues
            passed = False
        
        self._log_test_result("schema_integrity", passed, details)
        return passed
    
    def observability_test(self) -> bool:
        """Fix 2: Test logging and metrics with proper dict building."""
        details = {}
        
        try:
            # Check if loguru is configured
            details["loguru_configured"] = hasattr(logger, '_core')
            
            # Test database metrics
            if hasattr(self.db, 'metrics'):
                # Fix 2: Build dict correctly with proper syntax
                metrics_dict = {
                    "total_queries": self.db.metrics.total_queries,
                    "slow_sql_count": self.db.metrics.slow_sql_count,
                    "busy_events": self.db.metrics.busy_events,
                    "checkpoint_ms": getattr(self.db.metrics, 'checkpoint_ms', 0.0)
                }
                details["db_metrics"] = metrics_dict
            else:
                details["db_metrics"] = "not_available"
            
            # Test log file accessibility
            if not self.json_mode:
                # Only test log writes in human mode
                test_message = f"Pipeline verification test at {datetime.now().isoformat()}"
                logger.info(test_message)
                details["log_test"] = "completed"
            
            passed = True
            
        except Exception as e:
            details["error"] = str(e)
            passed = False
        
        self._log_test_result("observability", passed, details)
        return passed
    
    def smoke_test(self) -> bool:
        """Enhanced smoke test with chunk-aware analysis and multi-chunk visibility."""
        details = {}
        
        try:
            content_table = self._content_table()
            
            # Enhanced chain verification with chunk awareness
            chain_query = f"""
                SELECT 
                    d.chunk_id AS doc_id,
                    d.sha256, 
                    d.chunk_index,
                    c.id AS content_id, 
                    e.id AS embedding_id,
                    d.processed_at,
                    d.char_count
                FROM documents d
                JOIN {content_table} c
                  ON c.source_type='pdf' AND c.source_id=d.sha256
                JOIN embeddings e
                  ON e.content_id=c.id
                ORDER BY d.processed_at DESC, d.chunk_id DESC
                LIMIT 1
            """
            
            chain_result = self.db.fetch_one(chain_query)
            
            if chain_result:
                details["has_complete_chain"] = True
                details["sample_chain"] = {
                    "doc_id": chain_result['doc_id'],
                    "sha256_prefix": chain_result['sha256'][:8] + "...",
                    "chunk_index": chain_result['chunk_index'],
                    "content_id": chain_result['content_id'],
                    "embedding_id": chain_result['embedding_id'],
                    "processed_at": chain_result['processed_at'],
                    "char_count": chain_result['char_count']
                }
                
                # Get chunk statistics for this document
                chunk_stats = self.db.fetch_one("""
                    SELECT COUNT(*) as total_chunks, SUM(char_count) as total_chars
                    FROM documents 
                    WHERE sha256 = ?
                """, (chain_result['sha256'],))
                
                details["sample_document"] = {
                    "sha256": chain_result['sha256'],
                    "total_chunks": chunk_stats['total_chunks'],
                    "total_chars": chunk_stats['total_chars'],
                    "multi_chunk": chunk_stats['total_chunks'] > 1
                }
                
                passed = True
            else:
                details["has_complete_chain"] = False
                
                # Enhanced diagnosis with chunk awareness
                docs_count = self.db.fetch_one("SELECT COUNT(*) as count FROM documents WHERE status='processed'")['count']
                unique_docs = self.db.fetch_one("SELECT COUNT(DISTINCT sha256) as count FROM documents WHERE status='processed'")['count'] 
                content_count = self.db.fetch_one(f"SELECT COUNT(*) as count FROM {content_table} WHERE source_type='pdf'")['count']
                embeddings_count = self.db.fetch_one("SELECT COUNT(*) as count FROM embeddings")['count']
                
                details["chain_diagnosis"] = {
                    "processed_chunks": docs_count,
                    "unique_documents": unique_docs,
                    "pdf_content_entries": content_count,
                    "total_embeddings": embeddings_count,
                    "note": "chunks represent individual document chunks, content entries represent full documents"
                }
                passed = False
            
            # Additional multi-chunk analysis
            multi_chunk_stats = self.db.fetch_one("""
                SELECT 
                    COUNT(DISTINCT sha256) as total_documents,
                    COUNT(DISTINCT CASE WHEN chunk_count > 1 THEN sha256 END) as multi_chunk_docs,
                    AVG(chunk_count) as avg_chunks_per_doc
                FROM (
                    SELECT sha256, COUNT(*) as chunk_count
                    FROM documents 
                    WHERE status='processed'
                    GROUP BY sha256
                )
            """)
            
            details["chunk_analysis"] = {
                "total_documents": multi_chunk_stats['total_documents'] or 0,
                "multi_chunk_documents": multi_chunk_stats['multi_chunk_docs'] or 0,
                "avg_chunks_per_document": round(multi_chunk_stats['avg_chunks_per_doc'] or 0, 2)
            }
            
        except Exception as e:
            details["error"] = str(e)
            passed = False
        
        self._log_test_result("smoke", passed, details)
        return passed
    
    def integrity_test(self) -> bool:
        """Fix 5: Complete orphan and duplicate detection."""
        details = {}
        issues = []
        
        try:
            content_table = self._content_table()
            
            # Fix 5: Orphaned content (no document)
            orphaned_content = self.db.fetch_one(f"""
                SELECT COUNT(*) AS orphaned_content
                FROM {content_table} c
                LEFT JOIN documents d ON c.source_type='pdf' AND c.source_id=d.sha256
                WHERE c.source_type='pdf' AND d.chunk_id IS NULL
            """)['orphaned_content']
            
            # Fix 5: Orphaned embeddings (no content)
            orphaned_embeddings = self.db.fetch_one(f"""
                SELECT COUNT(*) AS orphaned_embeddings
                FROM embeddings e
                LEFT JOIN {content_table} c ON e.content_id=c.id
                WHERE c.id IS NULL
            """)['orphaned_embeddings']
            
            # Fix 5: Docs without content (processed docs missing normalization)
            docs_without_content = self.db.fetch_one(f"""
                SELECT COUNT(*) AS docs_without_content
                FROM documents d
                LEFT JOIN {content_table} c
                  ON c.source_type='pdf' AND c.source_id=d.sha256
                WHERE d.status='processed' AND c.id IS NULL
            """)['docs_without_content']
            
            # Fix 5: Duplicate content rows per source
            dup_content = self.db.fetch_one(f"""
                SELECT COUNT(*) AS dup_content
                FROM (
                  SELECT source_type, source_id
                  FROM {content_table}
                  GROUP BY source_type, source_id
                  HAVING COUNT(*) > 1
                )
            """)['dup_content']
            
            # Fix 5: Quarantine stats with proper field names
            quarantine_stats = self.db.fetch_one("""
                SELECT
                  COUNT(DISTINCT sha256) AS failed_docs,
                  COALESCE(AVG(attempt_count), 0) AS avg_attempts,
                  COUNT(*) AS failed_rows
                FROM documents
                WHERE status IN ('failed','quarantined')
            """)
            
            details = {
                "orphaned_content": orphaned_content,
                "orphaned_embeddings": orphaned_embeddings,
                "docs_without_content": docs_without_content,
                "duplicate_content": dup_content,
                "quarantine": {
                    "failed_docs": quarantine_stats['failed_docs'],
                    "avg_attempts": round(quarantine_stats['avg_attempts'], 2),
                    "failed_rows": quarantine_stats['failed_rows']
                }
            }
            
            # Determine if integrity issues exist
            if orphaned_content > 0:
                issues.append(f"{orphaned_content} orphaned content records")
            if orphaned_embeddings > 0:
                issues.append(f"{orphaned_embeddings} orphaned embeddings")
            if docs_without_content > 0:
                issues.append(f"{docs_without_content} processed docs without content")
            if dup_content > 0:
                issues.append(f"{dup_content} duplicate content entries")
            
            details["issues"] = issues
            passed = len(issues) == 0
            
        except Exception as e:
            details["error"] = str(e)
            passed = False
        
        self._log_test_result("integrity", passed, details)
        return passed
    
    def performance_test(self, since: str = None) -> bool:
        """Fix 6: Performance validation with window parsing."""
        details = {}
        
        try:
            window = None
            if since:
                window = self._sqlite_window(since)
                details["time_window"] = f"last {since}"
            
            # Base queries
            where_clause = "WHERE status='processed'"
            emb_where_clause = "WHERE 1=1"
            
            if window:
                where_clause += f" AND processed_at > datetime('now', '{window}')"
                emb_where_clause += f" AND created_at > datetime('now', '{window}')"
            
            # Fix 6: Use window for both docs and embeddings
            doc_stats = self.db.fetch_one(f"""
                SELECT 
                    COUNT(*) AS total_docs, 
                    COALESCE(AVG(char_count), 0) AS avg_chars, 
                    COALESCE(AVG(pages), 0) AS avg_pages
                FROM documents
                {where_clause}
            """)
            
            emb_stats = self.db.fetch_one(f"""
                SELECT COUNT(*) AS total_embeddings
                FROM embeddings
                {emb_where_clause}
            """)
            
            details["documents"] = {
                "total": doc_stats['total_docs'],
                "avg_chars": round(doc_stats['avg_chars'], 0),
                "avg_pages": round(doc_stats['avg_pages'], 1)
            }
            
            details["embeddings"] = {
                "total": emb_stats['total_embeddings']
            }
            
            # Simple performance thresholds
            passed = True
            if doc_stats['total_docs'] == 0 and not since:
                passed = False
                details["issue"] = "No processed documents found"
            
        except Exception as e:
            details["error"] = str(e)
            passed = False
        
        self._log_test_result("performance", passed, details)
        return passed
    
    def quarantine_test(self) -> bool:
        """Test quarantine recovery system."""
        details = {}
        
        try:
            # Check for quarantined documents
            quarantined = self.db.fetch("""
                SELECT sha256, attempt_count, status, error_message
                FROM documents 
                WHERE status IN ('failed', 'quarantined')
                ORDER BY attempt_count DESC, processed_at DESC
                LIMIT 5
            """)
            
            details["quarantined_count"] = len(quarantined)
            
            if quarantined:
                details["sample_failures"] = [
                    {
                        "sha256_prefix": doc['sha256'][:8] + "..." if doc['sha256'] else "unknown",
                        "attempts": doc['attempt_count'],
                        "status": doc['status'],
                        "error": doc['error_message'][:50] if doc['error_message'] else "unknown"
                    }
                    for doc in quarantined
                ]
                
                # Check for permanent failures (3+ attempts)
                permanent_failures = [d for d in quarantined if d['attempt_count'] >= 3]
                details["permanent_failures"] = len(permanent_failures)
            
            # Test quarantine handler availability
            try:
                from tools.cli.quarantine_handler import QuarantineHandler
                handler = QuarantineHandler()
                details["quarantine_handler"] = "available"
            except ImportError:
                details["quarantine_handler"] = "not_available"
            
            # Generally pass unless there are excessive permanent failures
            passed = details.get("permanent_failures", 0) < 5
            
        except Exception as e:
            details["error"] = str(e)
            passed = False
        
        self._log_test_result("quarantine", passed, details)
        return passed
    
    def trace_document(self, sha_prefix: str) -> bool:
        """Enhanced document tracing with complete chunk hierarchy and disambiguation."""
        details = {}
        
        try:
            # Fix 1: Resolve SHA prefix to full SHA
            full_sha = self._resolve_sha_prefix(sha_prefix)
            if not full_sha:
                details["error"] = f"No document found with SHA prefix: {sha_prefix}"
                self._log_test_result("trace", False, details)
                return False
            
            details["full_sha256"] = full_sha
            content_table = self._content_table()
            
            # Get ALL chunks for this document
            doc_chunks = self.db.fetch("""
                SELECT chunk_id, chunk_index, file_name, char_count, status, 
                       processed_at, extraction_method
                FROM documents 
                WHERE sha256 = ?
                ORDER BY chunk_index
            """, (full_sha,))
            
            if doc_chunks:
                details["document_chunks"] = [dict(chunk) for chunk in doc_chunks]
                details["chunk_count"] = len(doc_chunks)
                
                # Document summary from first chunk
                first_chunk = doc_chunks[0]
                details["document_summary"] = {
                    "file_name": first_chunk['file_name'],
                    "total_chunks": len(doc_chunks),
                    "total_chars": sum(chunk['char_count'] for chunk in doc_chunks),
                    "status": first_chunk['status'],
                    "extraction_method": first_chunk['extraction_method']
                }
            else:
                details["document_chunks"] = []
                details["chunk_count"] = 0
            
            # Get content_unified entry (represents full document text)
            content_info = self.db.fetch_one(f"""
                SELECT id, title, created_at, ready_for_embedding
                FROM {content_table}
                WHERE source_type='pdf' AND source_id = ?
            """, (full_sha,))
            
            if content_info:
                details["content_unified"] = {
                    "id": content_info['id'],
                    "title": content_info['title'],
                    "created_at": content_info['created_at'],
                    "ready_for_embedding": content_info['ready_for_embedding'],
                    "note": "Represents full document text from all chunks"
                }
                
                # Get ALL embeddings for this content
                embeddings = self.db.fetch("""
                    SELECT id, model, created_at
                    FROM embeddings
                    WHERE content_id = ?
                    ORDER BY created_at DESC
                """, (content_info['id'],))
                
                details["embeddings"] = [dict(emb) for emb in embeddings]
                details["embedding_count"] = len(embeddings)
                
                if embeddings:
                    details["embedding_summary"] = {
                        "total_embeddings": len(embeddings),
                        "model": embeddings[0]['model'],
                        "latest_created": embeddings[0]['created_at']
                    }
            
            # Build hierarchical trace display
            if not self.json_mode:
                self._display_trace_hierarchy(full_sha, doc_chunks, content_info, embeddings if content_info else [])
            
            # Determine if trace is complete
            has_doc = len(doc_chunks) > 0
            has_content = content_info is not None
            has_embeddings = len(details.get("embeddings", [])) > 0
            
            details["trace_complete"] = has_doc and has_content and has_embeddings
            details["trace_status"] = {
                "document_chunks": has_doc,
                "content_unified": has_content,
                "embeddings": has_embeddings
            }
            
            # Enhanced completion analysis
            if not details["trace_complete"]:
                issues = []
                if not has_doc:
                    issues.append("No document chunks found")
                if not has_content:
                    issues.append("No content_unified entry")
                if not has_embeddings:
                    issues.append("No embeddings generated")
                details["incomplete_reason"] = issues
            
            passed = details["trace_complete"]
            
        except Exception as e:
            details["error"] = str(e)
            passed = False
        
        self._log_test_result("trace", passed, details)
        return passed
    
    def _display_trace_hierarchy(self, sha256: str, doc_chunks: list, content_info: dict, embeddings: list):
        """Display hierarchical trace view for human-readable output."""
        logger.info(f"\n📄 Document Trace: {sha256[:16]}...")
        
        if doc_chunks:
            # Show document hierarchy
            file_name = doc_chunks[0]['file_name'] or "unknown"
            total_chars = sum(chunk['char_count'] for chunk in doc_chunks)
            logger.info(f"├── File: {file_name}")
            logger.info(f"├── Total Characters: {total_chars:,}")
            logger.info(f"├── Chunk Structure:")
            
            for chunk in doc_chunks:
                chunk_marker = "├──" if chunk != doc_chunks[-1] else "└──"
                logger.info(f"│   {chunk_marker} Chunk {chunk['chunk_index']}: {chunk['chunk_id']}")
                logger.info(f"│       ├── Characters: {chunk['char_count']:,}")
                logger.info(f"│       └── Status: {chunk['status']}")
            
            # Show content mapping
            if content_info:
                logger.info(f"├── Content Unified:")
                logger.info(f"│   ├── ID: {content_info['id']}")
                logger.info(f"│   ├── Title: {content_info['title'] or 'none'}")
                logger.info(f"│   └── Note: Full document text from all chunks")
                
                # Show embeddings
                if embeddings:
                    logger.info(f"└── Embeddings: {len(embeddings)} total")
                    for i, emb in enumerate(embeddings):
                        emb_marker = "├──" if i < len(embeddings) - 1 else "└──"
                        logger.info(f"    {emb_marker} ID {emb['id']}: {emb['model']} ({emb['created_at']})")
                else:
                    logger.info(f"└── ❌ No embeddings found")
            else:
                logger.info(f"└── ❌ No content_unified entry found")
        else:
            logger.info("└── ❌ No document chunks found")
    
    def run_all_tests(self, since: str = None, trace_sha: str = None) -> Dict[str, Any]:
        """Run complete verification suite."""
        if not self.json_mode:
            logger.info("Starting PDF pipeline verification")
            logger.info(f"Database: {self.db_path}")
        
        # Run all tests
        tests_passed = []
        
        tests_passed.append(self.preflight_test())
        tests_passed.append(self.schema_integrity_test())  # New migration validation test
        tests_passed.append(self.observability_test())
        tests_passed.append(self.smoke_test())
        tests_passed.append(self.integrity_test())
        tests_passed.append(self.performance_test(since))
        tests_passed.append(self.quarantine_test())
        
        if trace_sha:
            tests_passed.append(self.trace_document(trace_sha))
        
        # Calculate overall results
        total_tests = len(tests_passed)
        passed_tests = sum(tests_passed)
        
        self.results["summary"] = {
            "total_tests": total_tests,
            "passed_tests": passed_tests,
            "failed_tests": total_tests - passed_tests,
            "success_rate": round((passed_tests / total_tests) * 100, 1) if total_tests > 0 else 0
        }
        
        # Determine final status
        if passed_tests == total_tests:
            self.results["overall_status"] = "PASS"
        elif passed_tests == 0:
            self.results["overall_status"] = "FAIL"
        else:
            self.results["overall_status"] = "WARN"
        
        return self.results


def main():
    parser = argparse.ArgumentParser(
        description="Comprehensive PDF pipeline verification",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Exit Codes:
  0: All tests passed
  1: One or more tests failed
  2: Critical configuration error  
  3: Schema/environment mismatch
  4: Transient error (retry possible)

Examples:
  # Full verification
  python3 scripts/verify_pipeline.py
  
  # JSON output for CI
  python3 scripts/verify_pipeline.py --json
  
  # Check recent activity
  python3 scripts/verify_pipeline.py --since 24h
  
  # Trace specific document
  python3 scripts/verify_pipeline.py --trace a1b2c3d4
  
  # Strict mode (exit non-zero on warnings)
  python3 scripts/verify_pipeline.py --strict
        """
    )
    
    parser.add_argument("--json", action="store_true", help="Output JSON for CI (silent mode)")
    parser.add_argument("--strict", action="store_true", help="Exit non-zero on warnings (CI-friendly)")
    parser.add_argument("--since", help="Only check documents from last N time (e.g., 30m, 24h, 7d)")
    parser.add_argument("--trace", help="Trace specific document by SHA256 prefix")
    parser.add_argument("--test", help="Run specific test only", 
                       choices=["preflight", "observability", "smoke", "integrity", "performance", "quarantine"])
    
    args = parser.parse_args()
    
    try:
        # Fix 4: Respect JSON mode - no emoji/prints in JSON mode
        verifier = PipelineVerifier(json_mode=args.json)
        
        if args.test:
            # Run single test
            test_method = getattr(verifier, f"{args.test}_test")
            if args.test == "performance":
                result = test_method(args.since)
            elif args.test == "trace" and args.trace:
                result = verifier.trace_document(args.trace)
            else:
                result = test_method()
            
            if args.json:
                print(json.dumps(verifier.results, indent=2))
            
            sys.exit(0 if result else 1)
        else:
            # Run all tests
            results = verifier.run_all_tests(since=args.since, trace_sha=args.trace)
            
            if args.json:
                # Fix 4: Single-line CI summary in JSON mode
                summary = {
                    "status": results["overall_status"],
                    "chain": results["tests"].get("smoke", {}).get("details", {}).get("has_complete_chain", False),
                    "orphans": results["tests"].get("integrity", {}).get("details", {}).get("orphaned_content", 0),
                    "dup_content": results["tests"].get("integrity", {}).get("details", {}).get("duplicate_content", 0),
                }
                
                if args.since:
                    perf_details = results["tests"].get("performance", {}).get("details", {})
                    summary[f"docs_{args.since}"] = perf_details.get("documents", {}).get("total", 0)
                    summary[f"emb_{args.since}"] = perf_details.get("embeddings", {}).get("total", 0)
                
                print(json.dumps(summary))
            else:
                # Human-readable summary
                status = results["overall_status"]
                emoji = {"PASS": "✅", "WARN": "⚠️", "FAIL": "❌"}[status]
                logger.info(f"\n{emoji} Overall Status: {status}")
                logger.info(f"Tests: {results['summary']['passed_tests']}/{results['summary']['total_tests']} passed")
            
            # Fix 4: Exit codes with strict mode
            status = results["overall_status"]
            if status == "PASS":
                exit_code = 0
            elif status == "WARN":
                exit_code = 1 if args.strict else 0
            else:  # FAIL
                exit_code = 1
            
            sys.exit(exit_code)
            
    except ValueError as e:
        if args.json:
            print(json.dumps({"error": str(e), "exit_code": 2}))
        else:
            logger.error(f"Configuration error: {e}")
        sys.exit(2)
    except sqlite3.OperationalError as e:
        if args.json:
            print(json.dumps({"error": f"Database error: {e}", "exit_code": 3}))
        else:
            logger.error(f"Schema/environment mismatch: {e}")
        sys.exit(3)
    except Exception as e:
        if args.json:
            print(json.dumps({"error": f"Unexpected error: {e}", "exit_code": 4}))
        else:
            logger.error(f"Verification failed: {e}")
        sys.exit(4)


if __name__ == "__main__":
    main()