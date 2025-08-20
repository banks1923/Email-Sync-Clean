-- Migration V002: Fix truncated SHA256 source_ids in content_unified table
-- Date: 2025-08-20
-- Status: APPLIED (retroactive documentation)
-- Issue: content_unified.source_id had 16-char truncated SHA256s instead of full 64-char hashes
-- Impact: Broke JOINs between documents and content_unified tables, caused orphaned records

-- Prerequisites:
-- - V001 must be applied (basic schema structure)
-- - Database backup recommended before applying

-- Problem Analysis:
-- The content_unified.source_id column was storing truncated SHA256 hashes (16 chars)
-- instead of full hashes (64 chars), breaking the relationship with documents.sha256.
-- This caused orphaned content_unified records and broke the semantic pipeline.

-- Solution:
-- Update content_unified.source_id values to use full SHA256 hashes from documents table
-- where truncated hashes match the beginning of full hashes.

-- Data Repair Query:
UPDATE content_unified 
SET source_id = (
    SELECT DISTINCT d.sha256 
    FROM documents d 
    WHERE d.sha256 LIKE content_unified.source_id || '%'
    LIMIT 1
)
WHERE EXISTS (
    SELECT 1 
    FROM documents d 
    WHERE d.sha256 LIKE content_unified.source_id || '%'
)
AND length(source_id) < 64;  -- Only update truncated hashes

-- Verification Queries:
-- After applying this migration, these queries should show:
-- 1. Zero orphaned content_unified records:
-- SELECT COUNT(*) FROM content_unified c
-- LEFT JOIN documents d ON c.source_id = d.sha256
-- WHERE d.sha256 IS NULL;
-- 
-- 2. All source_ids should be 64 characters:
-- SELECT COUNT(*) FROM content_unified WHERE length(source_id) != 64;
--
-- 3. Document->Content chains should work:
-- SELECT COUNT(*) FROM documents d 
-- JOIN content_unified c ON d.sha256 = c.source_id;

-- Migration Success Criteria:
-- ✓ All content_unified.source_id values are full 64-character SHA256 hashes
-- ✓ Zero orphaned content_unified records
-- ✓ All document->content->embedding chains restored
-- ✓ Pipeline verification passes all tests

-- Rollback Information:
-- See rollback/R002_revert_sha256_fix.sql for rollback procedure
-- Note: Rollback requires database backup from before this migration