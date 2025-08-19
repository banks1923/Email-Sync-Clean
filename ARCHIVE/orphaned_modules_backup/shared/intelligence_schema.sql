-- Document Intelligence Schema Extensions
-- For Email Sync System Unified Intelligence Modules
-- Created: 2025-01-15

-- Table 1: Document Summaries
-- Stores TF-IDF keywords and TextRank sentences for documents
CREATE TABLE IF NOT EXISTS document_summaries (
    summary_id TEXT PRIMARY KEY DEFAULT (lower(hex(randomblob(16)))),
    document_id TEXT NOT NULL,
    summary_type TEXT NOT NULL CHECK(summary_type IN ('tfidf', 'textrank', 'combined')),
    summary_text TEXT,
    tf_idf_keywords TEXT, -- JSON array of {keyword: score} pairs
    textrank_sentences TEXT, -- JSON array of key sentences
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT DEFAULT CURRENT_TIMESTAMP,

    -- Foreign key to content table
    FOREIGN KEY (document_id) REFERENCES content(content_id) ON DELETE CASCADE
);

-- Indexes for document_summaries
CREATE INDEX IF NOT EXISTS idx_summaries_document ON document_summaries(document_id);
CREATE INDEX IF NOT EXISTS idx_summaries_type ON document_summaries(summary_type);
CREATE INDEX IF NOT EXISTS idx_summaries_created ON document_summaries(created_at);

-- Table 2: Document Intelligence
-- Stores various intelligence analysis results
CREATE TABLE IF NOT EXISTS document_intelligence (
    intelligence_id TEXT PRIMARY KEY DEFAULT (lower(hex(randomblob(16)))),
    document_id TEXT NOT NULL,
    intelligence_type TEXT NOT NULL, -- e.g., 'entity_extraction', 'sentiment', 'classification'
    intelligence_data TEXT NOT NULL, -- JSON data storing the intelligence results
    confidence_score REAL DEFAULT 0.0 CHECK(confidence_score >= 0.0 AND confidence_score <= 1.0),
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT DEFAULT CURRENT_TIMESTAMP,

    -- Foreign key to content table
    FOREIGN KEY (document_id) REFERENCES content(content_id) ON DELETE CASCADE
);

-- Indexes for document_intelligence
CREATE INDEX IF NOT EXISTS idx_intelligence_document ON document_intelligence(document_id);
CREATE INDEX IF NOT EXISTS idx_intelligence_type ON document_intelligence(intelligence_type);
CREATE INDEX IF NOT EXISTS idx_intelligence_confidence ON document_intelligence(confidence_score);
CREATE INDEX IF NOT EXISTS idx_intelligence_created ON document_intelligence(created_at);

-- Table 3: Relationship Cache
-- Caches expensive relationship computations between documents
CREATE TABLE IF NOT EXISTS relationship_cache (
    cache_id TEXT PRIMARY KEY DEFAULT (lower(hex(randomblob(16)))),
    source_id TEXT NOT NULL,
    target_id TEXT NOT NULL,
    relationship_type TEXT NOT NULL, -- e.g., 'similar', 'references', 'follows', 'contradicts'
    strength REAL DEFAULT 0.0 CHECK(strength >= 0.0 AND strength <= 1.0),
    cached_data TEXT, -- JSON data with additional relationship details
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    expires_at TEXT, -- Optional TTL for cache expiration

    -- Foreign keys to content table
    FOREIGN KEY (source_id) REFERENCES content(content_id) ON DELETE CASCADE,
    FOREIGN KEY (target_id) REFERENCES content(content_id) ON DELETE CASCADE,

    -- Ensure unique relationships per type
    UNIQUE(source_id, target_id, relationship_type)
);

-- Indexes for relationship_cache
CREATE INDEX IF NOT EXISTS idx_cache_source ON relationship_cache(source_id);
CREATE INDEX IF NOT EXISTS idx_cache_target ON relationship_cache(target_id);
CREATE INDEX IF NOT EXISTS idx_cache_type ON relationship_cache(relationship_type);
CREATE INDEX IF NOT EXISTS idx_cache_strength ON relationship_cache(strength);
CREATE INDEX IF NOT EXISTS idx_cache_expires ON relationship_cache(expires_at);

-- Composite indexes for common queries
CREATE INDEX IF NOT EXISTS idx_cache_source_type ON relationship_cache(source_id, relationship_type);
CREATE INDEX IF NOT EXISTS idx_cache_target_type ON relationship_cache(target_id, relationship_type);

-- View for expired cache entries (for cleanup)
CREATE VIEW IF NOT EXISTS expired_cache AS
SELECT * FROM relationship_cache
WHERE expires_at IS NOT NULL AND expires_at < datetime('now');

-- View for document summary overview
CREATE VIEW IF NOT EXISTS document_summary_overview AS
SELECT
    c.content_id,
    c.content_type,
    c.title,
    ds.summary_type,
    ds.summary_text,
    ds.created_at as summary_created
FROM content c
LEFT JOIN document_summaries ds ON c.content_id = ds.document_id
ORDER BY ds.created_at DESC;

-- View for document intelligence overview
CREATE VIEW IF NOT EXISTS document_intelligence_overview AS
SELECT
    c.content_id,
    c.content_type,
    c.title,
    di.intelligence_type,
    di.confidence_score,
    di.created_at as intelligence_created
FROM content c
LEFT JOIN document_intelligence di ON c.content_id = di.document_id
ORDER BY di.created_at DESC;
