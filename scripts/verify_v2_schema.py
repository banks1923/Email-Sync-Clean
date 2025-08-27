#!/usr/bin/env python3
"""
Verification script for Semantic Search v2 schema.
Checks that all schema changes and data integrity are correct.

Usage:
    python scripts/verify_v2_schema.py
"""

import sys
from pathlib import Path
from datetime import datetime

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from shared.simple_db import SimpleDB
from loguru import logger


class SchemaV2Verifier:
    """Verifies v2 schema is correctly applied."""
    
    def __init__(self):
        """Initialize verifier."""
        self.db = SimpleDB()
        self.errors = []
        self.warnings = []
        self.info = []
    
    def verify_columns_exist(self) -> bool:
        """Verify required columns exist in content_unified."""
        logger.info("Checking column existence...")
        
        required_columns = [
            "quality_score",
            "metadata",
            "source_type",
            "source_id",
            "ready_for_embedding",
            "embedding_generated",
            "embedding_generated_at"
        ]
        
        # Get table schema
        result = self.db.fetch("PRAGMA table_info(content_unified)", [])
        column_names = [row['name'] for row in result]
        
        all_exist = True
        for col in required_columns:
            if col in column_names:
                self.info.append(f"✅ Column '{col}' exists")
            else:
                self.errors.append(f"❌ Column '{col}' is missing")
                all_exist = False
        
        return all_exist
    
    def verify_indices_exist(self) -> bool:
        """Verify required indices exist."""
        logger.info("Checking index existence...")
        
        required_indices = [
            "idx_content_quality",
            "idx_content_chunks",
            "idx_content_ready_quality"
        ]
        
        # Get all indices
        result = self.db.fetch(
            "SELECT name FROM sqlite_master WHERE type='index'",
            []
        )
        index_names = [row['name'] for row in result]
        
        all_exist = True
        for idx in required_indices:
            if idx in index_names:
                self.info.append(f"✅ Index '{idx}' exists")
            else:
                self.warnings.append(f"⚠️ Index '{idx}' is missing (performance impact)")
                all_exist = False
        
        return all_exist
    
    def verify_foreign_keys_enabled(self) -> bool:
        """Verify foreign keys are enabled."""
        logger.info("Checking foreign key status...")
        
        result = self.db.fetch("PRAGMA foreign_keys", [])
        if result and result[0]['foreign_keys'] == 1:
            self.info.append("✅ Foreign keys are ENABLED")
            return True
        else:
            self.errors.append("❌ Foreign keys are DISABLED")
            return False
    
    def verify_data_integrity(self) -> bool:
        """Verify data integrity and counts."""
        logger.info("Checking data integrity...")
        
        # Check total counts
        result = self.db.fetch("SELECT COUNT(*) as count FROM content_unified", [])
        total = result[0]['count']
        self.info.append(f"📊 Total content items: {total}")
        
        # Check quality scores
        result = self.db.fetch(
            """
            SELECT 
                COUNT(*) as count,
                MIN(quality_score) as min_score,
                MAX(quality_score) as max_score,
                AVG(quality_score) as avg_score
            FROM content_unified
            WHERE quality_score IS NOT NULL
            """,
            []
        )
        
        if result[0]['count'] > 0:
            self.info.append(f"📊 Quality scores: count={result[0]['count']}, "
                           f"min={result[0]['min_score']:.2f}, "
                           f"max={result[0]['max_score']:.2f}, "
                           f"avg={result[0]['avg_score']:.2f}")
        
        # Check for chunks
        result = self.db.fetch(
            "SELECT COUNT(*) as count FROM content_unified WHERE source_type = 'document_chunk'",
            []
        )
        chunk_count = result[0]['count']
        self.info.append(f"📊 Document chunks: {chunk_count}")
        
        # Check ready for embedding
        result = self.db.fetch(
            "SELECT COUNT(*) as count FROM content_unified WHERE ready_for_embedding = 1",
            []
        )
        ready_count = result[0]['count']
        self.info.append(f"📊 Ready for embedding: {ready_count}")
        
        # Check already embedded
        result = self.db.fetch(
            "SELECT COUNT(*) as count FROM content_unified WHERE embedding_generated = 1",
            []
        )
        embedded_count = result[0]['count']
        self.info.append(f"📊 Already embedded: {embedded_count}")
        
        # Verify no orphaned chunks (chunks without parent documents)
        if chunk_count > 0:
            result = self.db.fetch(
                """
                SELECT COUNT(*) as count 
                FROM content_unified c1
                WHERE c1.source_type = 'document_chunk'
                AND NOT EXISTS (
                    SELECT 1 FROM content_unified c2
                    WHERE c2.source_type = 'document'
                    AND c1.source_id LIKE c2.source_id || ':%'
                )
                """,
                []
            )
            orphaned = result[0]['count']
            if orphaned > 0:
                self.warnings.append(f"⚠️ Found {orphaned} orphaned chunks")
            else:
                self.info.append("✅ No orphaned chunks found")
        
        return True
    
    def verify_migration_tracking(self) -> bool:
        """Verify migration tracking table exists."""
        logger.info("Checking migration tracking...")
        
        result = self.db.fetch(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='v2_migration_progress'",
            []
        )
        
        if result:
            self.info.append("✅ Migration tracking table exists")
            
            # Check for any failed migrations
            result = self.db.fetch(
                "SELECT COUNT(*) as count FROM v2_migration_progress WHERE processing_status = 'failed'",
                []
            )
            if result[0]['count'] > 0:
                self.warnings.append(f"⚠️ {result[0]['count']} failed migration entries found")
            
            return True
        else:
            self.warnings.append("⚠️ Migration tracking table missing")
            return False
    
    def verify_chunk_quality_distribution(self) -> bool:
        """Verify quality score distribution for chunks."""
        logger.info("Checking chunk quality distribution...")
        
        result = self.db.fetch(
            """
            SELECT 
                source_type,
                COUNT(*) as count,
                SUM(CASE WHEN quality_score >= 0.35 THEN 1 ELSE 0 END) as acceptable,
                SUM(CASE WHEN quality_score < 0.35 THEN 1 ELSE 0 END) as filtered
            FROM content_unified
            WHERE source_type = 'document_chunk'
            GROUP BY source_type
            """,
            []
        )
        
        if result:
            for row in result:
                self.info.append(
                    f"📊 Chunk quality: {row['acceptable']} acceptable, "
                    f"{row['filtered']} filtered (< 0.35)"
                )
        
        return True
    
    def run_verification(self) -> bool:
        """Run all verification checks."""
        logger.info("=" * 60)
        logger.info("Starting Semantic Search v2 Schema Verification")
        logger.info("=" * 60)
        
        all_passed = True
        
        # Run all checks
        checks = [
            ("Column Existence", self.verify_columns_exist),
            ("Index Existence", self.verify_indices_exist),
            ("Foreign Keys", self.verify_foreign_keys_enabled),
            ("Data Integrity", self.verify_data_integrity),
            ("Migration Tracking", self.verify_migration_tracking),
            ("Chunk Quality", self.verify_chunk_quality_distribution),
        ]
        
        for check_name, check_func in checks:
            logger.info(f"\n🔍 Checking: {check_name}")
            try:
                if not check_func():
                    all_passed = False
            except Exception as e:
                self.errors.append(f"❌ {check_name} check failed: {e}")
                all_passed = False
        
        # Print summary
        logger.info("\n" + "=" * 60)
        logger.info("VERIFICATION SUMMARY")
        logger.info("=" * 60)
        
        if self.info:
            logger.info("\n📋 Information:")
            for msg in self.info:
                logger.info(f"  {msg}")
        
        if self.warnings:
            logger.warning("\n⚠️ Warnings:")
            for msg in self.warnings:
                logger.warning(f"  {msg}")
        
        if self.errors:
            logger.error("\n❌ Errors:")
            for msg in self.errors:
                logger.error(f"  {msg}")
        
        # Final result
        logger.info("\n" + "=" * 60)
        if all_passed and not self.errors:
            logger.success("✅ VERIFICATION PASSED - Schema v2 is correctly configured!")
            return True
        else:
            logger.error("❌ VERIFICATION FAILED - Please review errors above")
            return False


def main():
    """Main entry point."""
    verifier = SchemaV2Verifier()
    
    success = verifier.run_verification()
    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())