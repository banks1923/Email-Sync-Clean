-- BigQuery Schema for Legal Document Processing
-- Implements proper deduplication and JSON fields as per requirements

-- Create dataset if not exists
CREATE SCHEMA IF NOT EXISTS `modular-command-466820-p2.stoneman_case`;

-- Drop existing tables to recreate with proper schema
DROP TABLE IF EXISTS `modular-command-466820-p2.stoneman_case.documents_stage`;
DROP TABLE IF EXISTS `modular-command-466820-p2.stoneman_case._stage_dedup`;
DROP TABLE IF EXISTS `modular-command-466820-p2.stoneman_case.documents`;

-- Main documents table with proper JSON and ARRAY types
CREATE TABLE `modular-command-466820-p2.stoneman_case.documents`
(
  document_key        STRING NOT NULL,   -- Unique key (chunk-aware)
  original_id         STRING,            -- Original document hash
  filename            STRING NOT NULL,
  filepath            STRING NOT NULL,
  document_type       STRING,            -- notice|complaint|discovery|motion|report|email|other
  processor_used      STRING,            -- FORM_PARSER|OCR|CONTRACT_PARSER|DUAL|TRIPLE
  page_count          INT64,
  confidence          FLOAT64,
  coverage            FLOAT64,           -- Characters per page metric
  processing_timestamp TIMESTAMP NOT NULL,
  excerpt             STRING,            -- First 20k chars
  entities            JSON,              -- Extracted entities as JSON
  evidence            JSON,              -- Evidence classification as JSON
  parties             ARRAY<STRING>,     -- People mentioned
  money_amounts       ARRAY<FLOAT64>,    -- Dollar amounts found
  violations          ARRAY<STRING>,     -- Violations detected
  legal_citations     ARRAY<STRING>,     -- Legal references
  full_text_uri       STRING,            -- Path to full text file
  chunk_info          JSON,              -- Chunk metadata if applicable
  processing_metrics  JSON               -- Performance metrics
)
PARTITION BY DATE(processing_timestamp)
CLUSTER BY original_id, document_type;

-- Staging table for batch inserts
CREATE TABLE `modular-command-466820-p2.stoneman_case.documents_stage`
(
  document_key        STRING NOT NULL,
  original_id         STRING,
  filename            STRING NOT NULL,
  filepath            STRING NOT NULL,
  document_type       STRING,
  processor_used      STRING,
  page_count          INT64,
  confidence          FLOAT64,
  coverage            FLOAT64,
  processing_timestamp TIMESTAMP NOT NULL,
  excerpt             STRING,
  entities            JSON,
  evidence            JSON,
  parties             ARRAY<STRING>,
  money_amounts       ARRAY<FLOAT64>,
  violations          ARRAY<STRING>,
  legal_citations     ARRAY<STRING>,
  full_text_uri       STRING,
  chunk_info          JSON,
  processing_metrics  JSON
)
PARTITION BY DATE(processing_timestamp)
CLUSTER BY document_key;

-- Processing log table for audit trail
CREATE TABLE IF NOT EXISTS `modular-command-466820-p2.stoneman_case.processing_log`
(
  log_id              STRING NOT NULL,
  document_key        STRING NOT NULL,
  filename            STRING NOT NULL,
  processor           STRING,
  status              STRING,           -- success|failed|low_confidence
  confidence_score    FLOAT64,
  error_message       STRING,
  processing_time_ms  INT64,
  timestamp           TIMESTAMP NOT NULL
);

-- Evidence patterns table
CREATE TABLE IF NOT EXISTS `modular-command-466820-p2.stoneman_case.evidence_patterns`
(
  pattern_id          STRING NOT NULL,
  pattern_type        STRING,           -- identity_concealment|repair_avoidance|retaliation|harassment
  documents           ARRAY<STRING>,    -- Document keys showing pattern
  strength_score      FLOAT64,          -- Pattern strength 0-1
  legal_implications  STRING,           -- Legal significance
  timeline_correlation JSON,            -- Related timeline events
  created_at          TIMESTAMP NOT NULL
);

-- Timeline table
CREATE TABLE IF NOT EXISTS `modular-command-466820-p2.stoneman_case.timeline`
(
  event_id            STRING NOT NULL,
  event_date          DATE NOT NULL,
  event_time          TIME,             -- Time if available
  event_description   STRING NOT NULL,
  event_category      STRING,           -- notice|repair|complaint|legal|communication
  source_documents    ARRAY<STRING>,    -- Document keys
  parties_involved    ARRAY<STRING>,
  violation_type      STRING,
  legal_deadline      DATE,             -- Any deadline triggered
  created_at          TIMESTAMP NOT NULL
);

-- Create stored procedure for deduplication and merge
CREATE OR REPLACE PROCEDURE `modular-command-466820-p2.stoneman_case.dedupe_and_merge`()
BEGIN
  -- Step 1: Deduplicate staging table
  CREATE OR REPLACE TABLE `modular-command-466820-p2.stoneman_case._stage_dedup` AS
  SELECT AS VALUE t
  FROM (
    SELECT t,
           ROW_NUMBER() OVER (
             PARTITION BY t.document_key
             ORDER BY t.processing_timestamp DESC
           ) AS rn
    FROM `modular-command-466820-p2.stoneman_case.documents_stage` t
  )
  WHERE rn = 1;

  -- Step 2: Merge deduplicated data into main table
  MERGE `modular-command-466820-p2.stoneman_case.documents` T
  USING `modular-command-466820-p2.stoneman_case._stage_dedup` S
  ON T.document_key = S.document_key
  WHEN MATCHED THEN UPDATE SET
    T.original_id = S.original_id,
    T.filename = S.filename,
    T.filepath = S.filepath,
    T.document_type = S.document_type,
    T.processor_used = S.processor_used,
    T.page_count = S.page_count,
    T.confidence = S.confidence,
    T.coverage = S.coverage,
    T.processing_timestamp = S.processing_timestamp,
    T.excerpt = S.excerpt,
    T.entities = S.entities,
    T.evidence = S.evidence,
    T.parties = S.parties,
    T.money_amounts = S.money_amounts,
    T.violations = S.violations,
    T.legal_citations = S.legal_citations,
    T.full_text_uri = S.full_text_uri,
    T.chunk_info = S.chunk_info,
    T.processing_metrics = S.processing_metrics
  WHEN NOT MATCHED THEN INSERT ROW;

  -- Step 3: Clean up
  TRUNCATE TABLE `modular-command-466820-p2.stoneman_case.documents_stage`;
  DROP TABLE IF EXISTS `modular-command-466820-p2.stoneman_case._stage_dedup`;
END;

-- Create views for analysis
CREATE OR REPLACE VIEW `modular-command-466820-p2.stoneman_case.high_confidence_docs` AS
SELECT * FROM `modular-command-466820-p2.stoneman_case.documents`
WHERE confidence >= 0.9
ORDER BY processing_timestamp DESC;

CREATE OR REPLACE VIEW `modular-command-466820-p2.stoneman_case.low_confidence_docs` AS
SELECT document_key, filename, confidence, processor_used
FROM `modular-command-466820-p2.stoneman_case.documents`
WHERE confidence < 0.7
ORDER BY confidence ASC;

CREATE OR REPLACE VIEW `modular-command-466820-p2.stoneman_case.processing_health` AS
SELECT
  COUNT(*) AS total_documents,
  COUNT(DISTINCT original_id) AS unique_originals,
  AVG(confidence) AS avg_confidence,
  MIN(confidence) AS min_confidence,
  MAX(confidence) AS max_confidence,
  COUNTIF(confidence < 0.7) AS low_confidence_count,
  COUNTIF(confidence >= 0.9) AS high_confidence_count,
  AVG(coverage) AS avg_coverage,
  COUNTIF(processor_used = 'DUAL') AS dual_processed,
  COUNTIF(processor_used = 'TRIPLE') AS triple_processed
FROM `modular-command-466820-p2.stoneman_case.documents`;

CREATE OR REPLACE VIEW `modular-command-466820-p2.stoneman_case.evidence_summary` AS
SELECT
  document_key,
  filename,
  document_type,
  JSON_VALUE(evidence, '$.habitability_score') AS habitability_score,
  JSON_VALUE(evidence, '$.retaliation_score') AS retaliation_score,
  JSON_VALUE(evidence, '$.quiet_enjoyment_score') AS quiet_enjoyment_score,
  ARRAY_LENGTH(violations) AS violation_count,
  ARRAY_LENGTH(money_amounts) AS money_mention_count,
  confidence
FROM `modular-command-466820-p2.stoneman_case.documents`
WHERE evidence IS NOT NULL
ORDER BY confidence DESC;