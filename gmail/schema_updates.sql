-- Gmail Sync Enhancement Schema Updates
-- Task 5: Advanced Deduplication and Incremental Sync

-- 1. Add content_hash column to emails table for content-based deduplication
ALTER TABLE emails ADD COLUMN content_hash TEXT;
CREATE UNIQUE INDEX idx_emails_content_hash ON emails(content_hash);

-- 2. Create sync_state table for tracking Gmail sync progress
CREATE TABLE IF NOT EXISTS sync_state (
    account_email TEXT PRIMARY KEY,
    last_history_id TEXT,
    last_sync_time DATETIME,
    last_message_id TEXT,
    sync_status TEXT DEFAULT 'idle',
    sync_in_progress BOOLEAN DEFAULT 0,
    messages_processed INTEGER DEFAULT 0,
    duplicates_found INTEGER DEFAULT 0,
    error_count INTEGER DEFAULT 0,
    last_error TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- 3. Add attachment metadata table
CREATE TABLE IF NOT EXISTS email_attachments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    message_id TEXT NOT NULL,
    filename TEXT,
    mime_type TEXT,
    size_bytes INTEGER,
    attachment_id TEXT,
    stored_path TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (message_id) REFERENCES emails(message_id)
);

-- 4. Add index for faster sync queries
CREATE INDEX idx_emails_datetime ON emails(datetime_utc);
CREATE INDEX idx_sync_state_status ON sync_state(sync_status);
CREATE INDEX idx_attachments_message ON email_attachments(message_id);
