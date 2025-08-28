-- Nuclear Reset v2: Quarantine Legacy emails Table
-- This script prevents any code from using the old emails table

-- Step 1: Backup the legacy table by renaming it
ALTER TABLE emails RENAME TO emails_legacy_backup_20250828;

-- Step 2: Create a trap VIEW that breaks any attempt to use 'emails'
-- This will cause immediate errors in any code still trying to use the old table
CREATE VIEW emails AS 
SELECT 
    'FATAL: Legacy emails table is deprecated. Use content_unified + individual_messages' AS error_message,
    NULL AS id,
    NULL AS message_id,
    NULL AS subject,
    NULL AS sender,
    NULL AS content
WHERE 1=0;  -- Always empty, but preserves column names for error clarity

-- Step 3: Block any writes to the backup table
CREATE TRIGGER block_legacy_emails_ins 
BEFORE INSERT ON emails_legacy_backup_20250828 
BEGIN
    SELECT RAISE(ABORT, 'FATAL: Writes to emails_legacy are forbidden. Use content_unified + individual_messages');
END;

CREATE TRIGGER block_legacy_emails_upd 
BEFORE UPDATE ON emails_legacy_backup_20250828 
BEGIN
    SELECT RAISE(ABORT, 'FATAL: Updates to emails_legacy are forbidden. Use content_unified + individual_messages');
END;

CREATE TRIGGER block_legacy_emails_del 
BEFORE DELETE ON emails_legacy_backup_20250828 
BEGIN
    SELECT RAISE(ABORT, 'FATAL: Deletes from emails_legacy are forbidden. This is archived data');
END;

-- Step 4: Verify the quarantine
SELECT 
    'Table Status' as check_type,
    name,
    type,
    CASE 
        WHEN name = 'emails' AND type = 'view' THEN '✅ Quarantined as VIEW'
        WHEN name = 'emails_legacy_backup_20250828' AND type = 'table' THEN '✅ Backed up'
        ELSE '❌ Unexpected'
    END as status
FROM sqlite_master 
WHERE name IN ('emails', 'emails_legacy_backup_20250828')
ORDER BY name;