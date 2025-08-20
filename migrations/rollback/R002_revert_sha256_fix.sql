-- Rollback R002: Revert SHA256 truncation fix
-- Reverts: Migration V002_fix_sha256_truncation.sql  
-- Date: 2025-08-20
-- WARNING: This rollback requires a database backup from BEFORE V002 was applied

-- CRITICAL WARNING:
-- This rollback cannot be executed using just SQL commands because we need
-- to restore the truncated SHA256 values that were overwritten in V002.
-- The only safe way to rollback is to restore from backup.

-- Rollback Procedure:
-- 1. Stop all applications using the database
-- 2. Identify the backup file created before V002 was applied
-- 3. Replace current database with backup:
--    cp data/emails.db.backup.TIMESTAMP data/emails.db  
-- 4. Update schema_version table to reflect rollback:
--    DELETE FROM schema_version WHERE version = 2;
-- 5. Restart applications

-- To identify the correct backup:
-- Look for backup files with timestamps from before the V002 fix was applied.
-- Example backup naming: emails.db.backup.20250820_111037

-- Verification after rollback:
-- These queries should show the original problem state:
-- 
-- 1. Should show orphaned content_unified records again:
-- SELECT COUNT(*) FROM content_unified c
-- LEFT JOIN documents d ON d.sha256 LIKE c.source_id || '%'  
-- WHERE d.sha256 IS NULL;
-- 
-- 2. Should show truncated source_id values (16 chars):
-- SELECT DISTINCT length(source_id) FROM content_unified;
--
-- 3. Direct joins should fail (0 results):
-- SELECT COUNT(*) FROM documents d 
-- JOIN content_unified c ON d.sha256 = c.source_id;

-- Manual Rollback Query (DANGEROUS - DATA LOSS):
-- If no backup is available, this query attempts to recreate truncated values.
-- WARNING: This is approximate and may not restore exact original state.
/*
UPDATE content_unified 
SET source_id = substr(source_id, 1, 16)
WHERE length(source_id) = 64 
AND source_type = 'document';
*/

-- Expected State After Rollback:
-- ❌ content_unified.source_id values truncated to 16 characters
-- ❌ Orphaned content_unified records (cannot join with documents)
-- ❌ Broken semantic pipeline (no document->content->embedding chain)
-- ❌ Pipeline verification will fail on integrity tests

-- Recovery Process:
-- After rollback, if you need to restore functionality:
-- 1. Re-apply V002 migration: python3 migrations/migrate.py
-- 2. Run pipeline verification: python3 scripts/verify_pipeline.py
-- 3. Confirm all 6 tests pass

-- Backup Recommendations:
-- Always create database backups before applying migrations:
-- timestamp=$(date +%Y%m%d_%H%M%S)
-- cp data/emails.db data/emails.db.backup.$timestamp