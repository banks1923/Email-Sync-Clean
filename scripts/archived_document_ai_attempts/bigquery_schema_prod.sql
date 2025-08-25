-- BigQuery Schema for Stoneman Legal Document Processing
-- Project: modular-command-466820-p2
-- Dataset: stoneman_case

-- Create dataset (run in BigQuery console)
CREATE SCHEMA IF NOT EXISTS `modular-command-466820-p2.stoneman_case`
OPTIONS(
  description="Stoneman legal case document analysis",
  location="US"
);

-- Main documents table (target)
CREATE OR REPLACE TABLE `modular-command-466820-p2.stoneman_case.documents` (
  document_id STRING NOT NULL,  -- SHA256 hash of document content
  filename STRING NOT NULL,      -- Original filename
  filepath STRING,               -- Full path to original file
  document_type STRING,          -- notice, complaint, discovery, motion, report, email, text_message, other
  processor_used STRING,         -- FORM_PARSER or OCR
  processing_timestamp TIMESTAMP NOT NULL,  -- When processed
  page_count INT64,              -- Number of pages
  confidence FLOAT64,            -- Processing confidence score (0-1)
  coverage FLOAT64,              -- Text coverage metric (chars per page)
  excerpt STRING,                -- First 20k characters for quick access
  entities STRING,               -- JSON: people, organizations, dates, money_amounts, legal_terms, case_numbers
  evidence STRING,               -- JSON: habitability, quiet_enjoyment, retaliation scores
  parties ARRAY<STRING>,         -- Extracted party names
  money_amounts ARRAY<FLOAT64>,  -- Extracted monetary values
  full_text_uri STRING,          -- Path to full text file (local or GCS)
  chunk_info STRING,             -- JSON: chunk metadata if document was split
  processing_metrics STRING      -- JSON: latency_ms, text_length, coverage, success, error
)
PARTITION BY DATE(processing_timestamp)
CLUSTER BY document_type, processor_used;

-- Staging table for atomic upserts
CREATE OR REPLACE TABLE `modular-command-466820-p2.stoneman_case.documents_stage` (
  document_id STRING NOT NULL,
  filename STRING NOT NULL,
  filepath STRING,
  document_type STRING,
  processor_used STRING,
  processing_timestamp TIMESTAMP NOT NULL,
  page_count INT64,
  confidence FLOAT64,
  coverage FLOAT64,
  excerpt STRING,
  entities STRING,
  evidence STRING,
  parties ARRAY<STRING>,
  money_amounts ARRAY<FLOAT64>,
  full_text_uri STRING,
  chunk_info STRING,
  processing_metrics STRING
);

-- Create views for easier querying

-- High confidence documents only
CREATE OR REPLACE VIEW `modular-command-466820-p2.stoneman_case.high_confidence_docs` AS
SELECT *
FROM `modular-command-466820-p2.stoneman_case.documents`
WHERE confidence >= 0.7
ORDER BY confidence DESC;

-- Evidence summary view
CREATE OR REPLACE VIEW `modular-command-466820-p2.stoneman_case.evidence_summary` AS
SELECT 
  document_id,
  filename,
  document_type,
  confidence,
  JSON_VALUE(evidence, '$.habitability') as habitability_score,
  JSON_VALUE(evidence, '$.quiet_enjoyment') as quiet_enjoyment_score,
  JSON_VALUE(evidence, '$.retaliation') as retaliation_score,
  JSON_VALUE(evidence, '$.evidence_strength') as evidence_strength,
  processing_timestamp
FROM `modular-command-466820-p2.stoneman_case.documents`
WHERE evidence IS NOT NULL
ORDER BY processing_timestamp DESC;

-- Financial summary view
CREATE OR REPLACE VIEW `modular-command-466820-p2.stoneman_case.financial_summary` AS
SELECT 
  document_id,
  filename,
  document_type,
  money_amounts,
  ARRAY_LENGTH(money_amounts) as money_mention_count,
  (SELECT SUM(amount) FROM UNNEST(money_amounts) as amount) as total_amount_mentioned,
  processing_timestamp
FROM `modular-command-466820-p2.stoneman_case.documents`
WHERE ARRAY_LENGTH(money_amounts) > 0
ORDER BY total_amount_mentioned DESC;

-- Entity extraction view
CREATE OR REPLACE VIEW `modular-command-466820-p2.stoneman_case.entity_view` AS
SELECT 
  document_id,
  filename,
  parties,
  JSON_EXTRACT_ARRAY(entities, '$.dates') as dates,
  JSON_EXTRACT_ARRAY(entities, '$.case_numbers') as case_numbers,
  JSON_EXTRACT_ARRAY(entities, '$.legal_terms') as legal_terms,
  processing_timestamp
FROM `modular-command-466820-p2.stoneman_case.documents`
WHERE entities IS NOT NULL;

-- Processing metrics view
CREATE OR REPLACE VIEW `modular-command-466820-p2.stoneman_case.processing_metrics` AS
SELECT 
  DATE(processing_timestamp) as processing_date,
  COUNT(*) as documents_processed,
  AVG(confidence) as avg_confidence,
  AVG(coverage) as avg_coverage,
  AVG(page_count) as avg_pages,
  SUM(CAST(JSON_VALUE(processing_metrics, '$.success') AS BOOL)) as successful,
  COUNT(*) - SUM(CAST(JSON_VALUE(processing_metrics, '$.success') AS BOOL)) as failed,
  AVG(CAST(JSON_VALUE(processing_metrics, '$.latency_ms') AS FLOAT64)) as avg_latency_ms
FROM `modular-command-466820-p2.stoneman_case.documents`
GROUP BY processing_date
ORDER BY processing_date DESC;

-- Sample queries for analysis

-- Find all eviction-related documents with high confidence
/*
SELECT 
  filename,
  document_type,
  confidence,
  excerpt
FROM `modular-command-466820-p2.stoneman_case.documents`
WHERE 
  confidence >= 0.8
  AND (
    LOWER(excerpt) LIKE '%eviction%'
    OR LOWER(excerpt) LIKE '%unlawful detainer%'
    OR document_type = 'notice'
  )
ORDER BY processing_timestamp DESC;
*/

-- Get timeline of events from dates extracted
/*
WITH extracted_dates AS (
  SELECT 
    document_id,
    filename,
    date_val
  FROM `modular-command-466820-p2.stoneman_case.documents`,
    UNNEST(JSON_EXTRACT_ARRAY(entities, '$.dates')) as date_val
)
SELECT 
  date_val as event_date,
  filename,
  document_id
FROM extracted_dates
ORDER BY date_val;
*/

-- Find documents mentioning specific parties
/*
SELECT 
  filename,
  document_type,
  parties,
  confidence
FROM `modular-command-466820-p2.stoneman_case.documents`
WHERE EXISTS (
  SELECT 1 
  FROM UNNEST(parties) as party 
  WHERE LOWER(party) LIKE '%stoneman%'
)
ORDER BY confidence DESC;
*/

-- Aggregate financial information
/*
SELECT 
  SUM(amount) as total_amount,
  COUNT(DISTINCT document_id) as document_count,
  ARRAY_AGG(DISTINCT filename LIMIT 10) as sample_documents
FROM `modular-command-466820-p2.stoneman_case.documents`,
  UNNEST(money_amounts) as amount
WHERE amount > 0;
*/