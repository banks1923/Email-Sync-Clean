-- Migration: Add query_logs table for search analytics
-- Date: 2025-09-06
-- Purpose: Track search queries for analytics and performance monitoring

CREATE TABLE IF NOT EXISTS query_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    query TEXT NOT NULL,
    search_mode TEXT NOT NULL CHECK(search_mode IN ('semantic_only', 'keyword_only', 'rrf')),
    result_count INTEGER NOT NULL,
    execution_time_ms REAL NOT NULL,
    filters TEXT,  -- JSON string of applied filters
    user_session TEXT,  -- Optional session identifier
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes for common queries
CREATE INDEX IF NOT EXISTS idx_query_logs_created_at ON query_logs(created_at);
CREATE INDEX IF NOT EXISTS idx_query_logs_mode ON query_logs(search_mode);
CREATE INDEX IF NOT EXISTS idx_query_logs_session ON query_logs(user_session);

-- Add comment explaining the table
-- This table logs all search queries for analytics purposes including:
-- - Query text and mode
-- - Performance metrics (execution time, result count)
-- - Applied filters
-- - Optional session tracking