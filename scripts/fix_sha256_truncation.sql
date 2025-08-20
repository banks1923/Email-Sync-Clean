-- SQL Migration: Fix truncated SHA256 source_ids in content_unified table
-- Date: 2025-08-20
-- Issue: content_unified.source_id had 16-char truncated SHA256s instead of full 64-char hashes
-- Impact: Broke JOINs between documents and content_unified tables, caused orphaned records

-- Step 1: Backup database first (done via shell)
-- cp data/emails.db data/emails.db.backup.$(date +%Y%m%d_%H%M%S)

-- Step 2: Verify the problem
SELECT 
    'Before fix - Orphaned content_unified' as check_name,
    COUNT(*) as count
FROM content_unified c
LEFT JOIN documents d ON d.sha256 LIKE c.source_id || '%'
WHERE d.sha256 IS NULL;

-- Step 3: Show the mapping
SELECT 
    c.id as content_id,
    c.source_id as truncated_hash,
    d.sha256 as full_hash
FROM content_unified c 
JOIN documents d ON d.sha256 LIKE c.source_id || '%'
ORDER BY c.id;

-- Step 4: Apply the fix
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
);

-- Step 5: Verify the fix
SELECT 
    'After fix - Orphaned content_unified' as check_name,
    COUNT(*) as count
FROM content_unified c
LEFT JOIN documents d ON c.source_id = d.sha256
WHERE d.sha256 IS NULL;

SELECT 
    'After fix - Document->Content chains' as check_name,
    COUNT(*) as count
FROM documents d 
JOIN content_unified c ON d.sha256 = c.source_id;

-- Expected results after fix:
-- - Orphaned content_unified: 0 (was 2)
-- - Document->Content chains: 4 (was 0)
-- - content_unified.source_id length: 64 characters (was 16)