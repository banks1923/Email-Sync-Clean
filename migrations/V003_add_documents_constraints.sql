-- Migration V003: Add unique constraints to documents table
-- Date: 2025-08-20  
-- Status: APPLIED (retroactive documentation)
-- Purpose: Prevent duplicate documents while allowing legitimate multi-chunk documents

-- Prerequisites:
-- - V002 must be applied (SHA256 truncation fix)
-- - No duplicate (sha256, chunk_index) pairs should exist
-- - Database backup recommended before applying

-- Problem Analysis:
-- The documents table lacked constraints to prevent duplicate entries.
-- This could lead to data inconsistency and processing inefficiencies.
-- Need to allow multiple chunks per document (different chunk_index values)
-- but prevent true duplicates (same sha256 AND chunk_index).

-- Schema Changes:

-- 1. Create unique constraint on (sha256, chunk_index) for non-null SHA256s
-- This prevents duplicate chunks while allowing legitimate multi-chunk documents
CREATE UNIQUE INDEX IF NOT EXISTS idx_documents_sha256_chunk_unique 
ON documents(sha256, chunk_index) 
WHERE sha256 IS NOT NULL;

-- 2. Ensure SHA256 index exists for query performance
CREATE INDEX IF NOT EXISTS idx_documents_sha256 
ON documents(sha256);

-- 3. Add additional performance indexes for common queries
CREATE INDEX IF NOT EXISTS idx_documents_file_name 
ON documents(file_name);

CREATE INDEX IF NOT EXISTS idx_documents_chunk_index 
ON documents(chunk_index);

-- Constraint Behavior:
-- ✓ Allows multiple NULL sha256 values (unprocessed documents)
-- ✓ Allows same sha256 with different chunk_index (multi-chunk docs)
-- ✗ Prevents same sha256 with same chunk_index (true duplicates)

-- Verification Queries:
-- After applying this migration, these should work:
-- 
-- 1. Test duplicate prevention (should fail with UNIQUE constraint error):
-- INSERT INTO documents (chunk_id, sha256, chunk_index, file_name) 
-- VALUES ('test', 'existing_sha256', 0, 'test.pdf');
--
-- 2. Test multi-chunk support (should succeed):
-- INSERT INTO documents (chunk_id, sha256, chunk_index, file_name) 
-- VALUES ('test2', 'existing_sha256', 1, 'test.pdf');
--
-- 3. Test NULL handling (should succeed multiple times):
-- INSERT INTO documents (chunk_id, sha256, chunk_index, file_name) 
-- VALUES ('test3', NULL, 0, 'unprocessed.pdf');

-- Migration Success Criteria:
-- ✓ Unique constraint idx_documents_sha256_chunk_unique exists
-- ✓ Performance indexes created for common query patterns  
-- ✓ Constraint prevents duplicate (sha256, chunk_index) pairs
-- ✓ Multi-chunk documents still work correctly
-- ✓ NULL sha256 handling preserved for unprocessed documents
-- ✓ Pipeline integrity maintained

-- Integration Impact:
-- This migration complements V002 by ensuring the fixed relationships
-- cannot be broken by future duplicate insertions. Together they provide:
-- ✓ Correct document->content relationships (V002)
-- ✓ Prevention of future duplicate documents (V003)
-- ✓ Complete pipeline data integrity protection

-- Rollback Information:
-- See rollback/R003_remove_constraints.sql for rollback procedure
-- Rollback is safe and only removes indexes - no data loss