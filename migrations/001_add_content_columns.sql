-- Migration 001: Add missing columns to content table
-- Date: 2025-08-20
-- Purpose: Add columns needed for semantic pipeline and vector processing

-- Add missing columns
ALTER TABLE content ADD COLUMN eid TEXT;
ALTER TABLE content ADD COLUMN message_id TEXT;
ALTER TABLE content ADD COLUMN word_count INTEGER DEFAULT 0;
ALTER TABLE content ADD COLUMN source_path TEXT;
ALTER TABLE content ADD COLUMN vector_processed INTEGER DEFAULT 0;

-- Create indexes for performance
CREATE INDEX IF NOT EXISTS ix_content_message_id ON content(message_id);
CREATE INDEX IF NOT EXISTS ix_content_vector_processed ON content(vector_processed);
CREATE INDEX IF NOT EXISTS ix_content_eid ON content(eid);

-- Update word_count for existing records that have content
UPDATE content SET word_count = (
    CASE 
        WHEN content IS NOT NULL AND length(trim(content)) > 0 
        THEN length(content) - length(replace(content, ' ', '')) + 1
        ELSE 0
    END
) WHERE word_count = 0 OR word_count IS NULL;