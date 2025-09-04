-- Nuclear Reset v2: Final Cleanup - Permanent Deletion
-- This script permanently removes all legacy artifacts

PRAGMA foreign_keys=ON;

BEGIN TRANSACTION;

-- Drop all legacy tables and views
DROP TABLE IF EXISTS emails_legacy_backup_20250828;
DROP TABLE IF EXISTS email_entities_backup_20250828;
DROP VIEW IF EXISTS emails;  -- Remove the trap VIEW
DROP VIEW IF EXISTS email_entities;  -- Remove the entity trap VIEW

-- Verify cleanup
SELECT 
    'Cleanup Status' as check_type,
    CASE 
        WHEN COUNT(*) = 0 THEN '✅ All legacy artifacts removed'
        ELSE '❌ Legacy artifacts still present: ' || GROUP_CONCAT(name)
    END as status
FROM sqlite_master 
WHERE (name LIKE '%legacy%' OR name LIKE '%backup%' OR name IN ('emails', 'email_entities'))
  AND type IN ('table', 'view');

COMMIT;

-- Note: VACUUM must be run outside transaction
-- It will be executed separately