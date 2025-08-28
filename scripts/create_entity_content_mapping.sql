-- Nuclear Reset v2: Create Entity Content Mapping Table
-- This bridges entities to content_unified with proper foreign keys

-- Step 1: Create the new entity_content_mapping table
CREATE TABLE IF NOT EXISTS entity_content_mapping (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    entity_id INTEGER NOT NULL,
    content_id TEXT NOT NULL,  -- References content_unified.source_id (message_hash for emails)
    entity_type TEXT NOT NULL,
    entity_text TEXT NOT NULL,
    start_char INTEGER,
    end_char INTEGER,
    confidence REAL DEFAULT 1.0,
    extractor_type TEXT DEFAULT 'spacy',
    created_at TEXT DEFAULT (datetime('now')),
    FOREIGN KEY (content_id) REFERENCES content_unified(source_id) ON DELETE CASCADE,
    UNIQUE(content_id, entity_text, entity_type, start_char)  -- Prevent duplicate entities
);

-- Step 2: Create indexes for performance
CREATE INDEX IF NOT EXISTS idx_ecm_content ON entity_content_mapping(content_id);
CREATE INDEX IF NOT EXISTS idx_ecm_entity ON entity_content_mapping(entity_id);
CREATE INDEX IF NOT EXISTS idx_ecm_type ON entity_content_mapping(entity_type);

-- Step 3: Backup the old email_entities table
CREATE TABLE IF NOT EXISTS email_entities_backup_20250828 AS 
SELECT * FROM email_entities;

-- Step 4: Create deprecation VIEW to catch any legacy usage
DROP TABLE IF EXISTS email_entities;
CREATE VIEW email_entities AS 
SELECT 
    'DEPRECATED: Use entity_content_mapping instead' AS error_message,
    NULL AS id,
    NULL AS message_id,
    NULL AS entity_text
WHERE 1=0;

-- Step 5: Verify the new structure
SELECT 
    'Table Status' as check_type,
    name,
    type,
    CASE 
        WHEN name = 'entity_content_mapping' AND type = 'table' THEN '✅ Created'
        WHEN name = 'email_entities' AND type = 'view' THEN '✅ Deprecated as VIEW'
        WHEN name = 'email_entities_backup_20250828' AND type = 'table' THEN '✅ Backed up'
        ELSE '❓ Unknown'
    END as status
FROM sqlite_master 
WHERE name IN ('entity_content_mapping', 'email_entities', 'email_entities_backup_20250828')
ORDER BY name;