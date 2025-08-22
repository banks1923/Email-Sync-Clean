-- V004_fix_foreign_key_constraints.sql
-- Fix foreign key constraints to reference content_unified instead of content
-- This migration fixes the issue where MCP legal intelligence tools fail with "no such table: content"

-- Disable foreign key checking temporarily for this migration
PRAGMA foreign_keys = OFF;

-- 1. Fix kg_nodes table (has 10 records to preserve)
-- First backup existing data, but only records that have valid content_unified references
-- Note: Current kg_nodes table has 'content_id' column, not 'id'
CREATE TEMP TABLE kg_nodes_backup AS 
SELECT 
    node_id,
    content_id as id,  -- Rename content_id to id for new schema
    content_type,
    title,
    node_metadata,
    created_time
FROM kg_nodes kg 
WHERE kg.content_id IN (SELECT id FROM content_unified);

-- Drop old table and recreate with correct foreign key
DROP TABLE IF EXISTS kg_nodes;
CREATE TABLE kg_nodes (
    node_id TEXT PRIMARY KEY,
    id TEXT NOT NULL,
    content_type TEXT NOT NULL,
    title TEXT,
    node_metadata TEXT,
    created_time TEXT DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (id) REFERENCES content_unified(id) ON DELETE CASCADE
);

-- Restore only valid data from backup
INSERT INTO kg_nodes SELECT * FROM kg_nodes_backup;

-- 2. Fix document_summaries table (0 records, safe to recreate)
DROP TABLE IF EXISTS document_summaries;
CREATE TABLE document_summaries (
    summary_id TEXT PRIMARY KEY DEFAULT (lower(hex(randomblob(16)))),
    document_id TEXT NOT NULL,
    summary_type TEXT NOT NULL CHECK(summary_type IN ('tfidf', 'textrank', 'combined')),
    summary_text TEXT,
    tf_idf_keywords TEXT,
    textrank_sentences TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (document_id) REFERENCES content_unified(id) ON DELETE CASCADE
);

-- 3. Fix relationship_cache table (0 records, safe to recreate)
DROP TABLE IF EXISTS relationship_cache;
CREATE TABLE relationship_cache (
    cache_id TEXT PRIMARY KEY DEFAULT (lower(hex(randomblob(16)))),
    source_id TEXT NOT NULL,
    target_id TEXT NOT NULL,
    relationship_type TEXT NOT NULL,
    strength REAL DEFAULT 0.0 CHECK(strength >= 0.0 AND strength <= 1.0),
    cached_data TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    expires_at TEXT,
    FOREIGN KEY (source_id) REFERENCES content_unified(id) ON DELETE CASCADE,
    FOREIGN KEY (target_id) REFERENCES content_unified(id) ON DELETE CASCADE,
    UNIQUE(source_id, target_id, relationship_type)
);

-- 4. Fix document_intelligence table (0 records, safe to recreate)
DROP TABLE IF EXISTS document_intelligence;
CREATE TABLE document_intelligence (
    intelligence_id TEXT PRIMARY KEY DEFAULT (lower(hex(randomblob(16)))),
    document_id TEXT NOT NULL,
    intelligence_type TEXT NOT NULL,
    intelligence_data TEXT NOT NULL,
    confidence_score REAL DEFAULT 0.0 CHECK(confidence_score >= 0.0 AND confidence_score <= 1.0),
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (document_id) REFERENCES content_unified(id) ON DELETE CASCADE
);

-- 5. Clean up test/temporary tables from debugging attempts
DROP TABLE IF EXISTS kg_nodes_new;
DROP TABLE IF EXISTS kg_nodes_test;
DROP TABLE IF EXISTS test_fk;
DROP TABLE IF EXISTS test_fk2;

-- Create indexes for performance
CREATE INDEX IF NOT EXISTS idx_kg_nodes_id ON kg_nodes(id);
CREATE INDEX IF NOT EXISTS idx_kg_nodes_content_type ON kg_nodes(content_type);
CREATE INDEX IF NOT EXISTS idx_document_summaries_document_id ON document_summaries(document_id);
CREATE INDEX IF NOT EXISTS idx_relationship_cache_source_id ON relationship_cache(source_id);
CREATE INDEX IF NOT EXISTS idx_relationship_cache_target_id ON relationship_cache(target_id);
CREATE INDEX IF NOT EXISTS idx_document_intelligence_document_id ON document_intelligence(document_id);

-- Re-enable foreign key checking
PRAGMA foreign_keys = ON;

-- Verify foreign key integrity
PRAGMA foreign_key_check;