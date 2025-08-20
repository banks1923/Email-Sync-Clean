-- Rollback R003: Remove unique constraints from documents table
-- Reverts: Migration V003_add_documents_constraints.sql
-- Date: 2025-08-20
-- This rollback is SAFE - no data loss, only removes constraints

-- WARNING: After this rollback, the database will be vulnerable to:
-- - Duplicate document entries
-- - Data consistency issues
-- - Processing inefficiencies

-- Rollback Commands:

-- 1. Drop unique constraint on (sha256, chunk_index)
DROP INDEX IF EXISTS idx_documents_sha256_chunk_unique;

-- 2. Drop performance indexes added in V003 (optional, can keep for performance)
-- Uncomment these lines if you want to remove all indexes added in V003:
-- DROP INDEX IF EXISTS idx_documents_file_name;
-- DROP INDEX IF EXISTS idx_documents_chunk_index;

-- Note: idx_documents_sha256 may have existed before V003, so we don't drop it
-- to avoid breaking existing queries

-- 3. Update schema version to reflect rollback
DELETE FROM schema_version WHERE version = 3;

-- Verification after rollback:
-- These tests should demonstrate that constraints are removed:

-- 1. This should now succeed (would fail with constraints):
-- INSERT INTO documents (chunk_id, sha256, chunk_index, file_name) 
-- VALUES ('rollback_test_1', '1234567890123456789012345678901234567890123456789012345678901234', 0, 'test1.pdf');
-- INSERT INTO documents (chunk_id, sha256, chunk_index, file_name) 
-- VALUES ('rollback_test_2', '1234567890123456789012345678901234567890123456789012345678901234', 0, 'test2.pdf');

-- 2. Check that duplicate prevention is disabled:
-- SELECT sha256, chunk_index, COUNT(*) as count 
-- FROM documents 
-- GROUP BY sha256, chunk_index 
-- HAVING COUNT(*) > 1;

-- Cleanup test data:
-- DELETE FROM documents WHERE chunk_id LIKE 'rollback_test_%';

-- Expected State After Rollback:
-- ❌ No unique constraint on documents(sha256, chunk_index)
-- ❌ Database vulnerable to duplicate document entries  
-- ❌ No prevention of data consistency issues
-- ❌ Pipeline can process the same document multiple times
-- ✓ All existing data preserved
-- ✓ Basic SHA256 index preserved (if it existed before)

-- Recovery Process:
-- To restore constraints after rollback:
-- 1. Ensure no duplicate (sha256, chunk_index) pairs exist:
--    SELECT sha256, chunk_index, COUNT(*) 
--    FROM documents 
--    GROUP BY sha256, chunk_index 
--    HAVING COUNT(*) > 1;
-- 2. Remove any duplicates found
-- 3. Re-apply V003 migration: python3 migrations/migrate.py
-- 4. Run constraint validation tests

-- Performance Impact:
-- Removing performance indexes may slow down:
-- - Document lookups by SHA256
-- - File name searches  
-- - Chunk-based queries
-- Consider keeping performance indexes even after constraint removal

-- Safety Notes:
-- ✅ This rollback is safe - no data loss
-- ✅ Can be re-applied at any time
-- ⚠️  Database becomes vulnerable to duplicates
-- ⚠️  May impact query performance if indexes removed