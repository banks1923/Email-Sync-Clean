-- R004_revert_fk_fix.sql
-- Rollback script for V004_fix_foreign_key_constraints.sql
-- Reverts foreign key constraints back to reference content table
-- WARNING: This will restore broken foreign keys - only use if V004 causes issues

-- Enable foreign key checking
PRAGMA foreign_keys = ON;

-- 1. Revert kg_nodes table to old schema
-- Backup current data
CREATE TEMP TABLE kg_nodes_backup AS SELECT * FROM kg_nodes;

-- Drop and recreate with old foreign key (broken reference)
DROP TABLE IF EXISTS kg_nodes;
CREATE TABLE kg_nodes (
    node_id TEXT PRIMARY KEY,
    id TEXT NOT NULL,
    content_type TEXT NOT NULL,
    title TEXT,
    node_metadata TEXT,
    created_time TEXT DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (id) REFERENCES content(content_id) ON DELETE CASCADE
);

-- Restore data
INSERT INTO kg_nodes SELECT * FROM kg_nodes_backup;

-- 2. Revert document_summaries table
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
    FOREIGN KEY (document_id) REFERENCES content(content_id) ON DELETE CASCADE
);

-- 3. Revert relationship_cache table
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
    FOREIGN KEY (source_id) REFERENCES content(content_id) ON DELETE CASCADE,
    FOREIGN KEY (target_id) REFERENCES content(content_id) ON DELETE CASCADE,
    UNIQUE(source_id, target_id, relationship_type)
);

-- 4. Revert document_intelligence table
DROP TABLE IF EXISTS document_intelligence;
CREATE TABLE document_intelligence (
    intelligence_id TEXT PRIMARY KEY DEFAULT (lower(hex(randomblob(16)))),
    document_id TEXT NOT NULL,
    intelligence_type TEXT NOT NULL,
    intelligence_data TEXT NOT NULL,
    confidence_score REAL DEFAULT 0.0 CHECK(confidence_score >= 0.0 AND confidence_score <= 1.0),
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (document_id) REFERENCES content(content_id) ON DELETE CASCADE
);

-- Recreate indexes
CREATE INDEX IF NOT EXISTS idx_kg_nodes_id ON kg_nodes(id);
CREATE INDEX IF NOT EXISTS idx_kg_nodes_content_type ON kg_nodes(content_type);
CREATE INDEX IF NOT EXISTS idx_document_summaries_document_id ON document_summaries(document_id);
CREATE INDEX IF NOT EXISTS idx_relationship_cache_source_id ON relationship_cache(source_id);
CREATE INDEX IF NOT EXISTS idx_relationship_cache_target_id ON relationship_cache(target_id);
CREATE INDEX IF NOT EXISTS idx_document_intelligence_document_id ON document_intelligence(document_id);

-- Note: Foreign key check will fail because content table doesn't exist
-- This rollback script restores the broken state