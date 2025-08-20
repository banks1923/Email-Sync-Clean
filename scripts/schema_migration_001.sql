-- Schema Migration 001: Fix PDF Pipeline
-- Date: 2025-08-20
-- Purpose: Add missing columns for PDF processing pipeline

-- Add missing columns to documents table
ALTER TABLE documents ADD COLUMN IF NOT EXISTS char_count INTEGER DEFAULT 0;
ALTER TABLE documents ADD COLUMN IF NOT EXISTS word_count INTEGER DEFAULT 0;
ALTER TABLE documents ADD COLUMN IF NOT EXISTS pages INTEGER DEFAULT 0;
ALTER TABLE documents ADD COLUMN IF NOT EXISTS sha256 TEXT;
ALTER TABLE documents ADD COLUMN IF NOT EXISTS ocr_applied INTEGER DEFAULT 0;
ALTER TABLE documents ADD COLUMN IF NOT EXISTS text_path TEXT;
ALTER TABLE documents ADD COLUMN IF NOT EXISTS meta_json_path TEXT;
ALTER TABLE documents ADD COLUMN IF NOT EXISTS status TEXT DEFAULT 'processed';
ALTER TABLE documents ADD COLUMN IF NOT EXISTS error_message TEXT;
ALTER TABLE documents ADD COLUMN IF NOT EXISTS processed_at TEXT;
ALTER TABLE documents ADD COLUMN IF NOT EXISTS attempt_count INTEGER DEFAULT 0;
ALTER TABLE documents ADD COLUMN IF NOT EXISTS next_retry_at TEXT;

-- Add unique index for deduplication
CREATE UNIQUE INDEX IF NOT EXISTS idx_documents_sha256 ON documents(sha256);

-- Create schema_version table for migration tracking
CREATE TABLE IF NOT EXISTS schema_version (
    version INTEGER PRIMARY KEY,
    applied_at TEXT DEFAULT CURRENT_TIMESTAMP,
    description TEXT
);

-- Record this migration
INSERT OR IGNORE INTO schema_version (version, description) 
VALUES (1, 'Add missing PDF pipeline columns');

-- Verify content table exists with proper structure
CREATE TABLE IF NOT EXISTS content_unified (
    id INTEGER PRIMARY KEY,
    source_type TEXT NOT NULL,
    source_id INTEGER NOT NULL,
    title TEXT,
    body TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    ready_for_embedding INTEGER DEFAULT 0,
    UNIQUE(source_type, source_id)
);

-- Verify embeddings table exists
CREATE TABLE IF NOT EXISTS embeddings (
    id INTEGER PRIMARY KEY,
    content_id INTEGER NOT NULL,
    vector BLOB,
    dim INTEGER NOT NULL DEFAULT 1024,
    model TEXT NOT NULL DEFAULT 'legal-bert',
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(content_id, model)
);