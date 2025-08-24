-- BigQuery schema for legal documents

-- Main documents table
CREATE TABLE IF NOT EXISTS `modular-command-466820-p2.legal_documents.documents` (
  document_id STRING NOT NULL,
  file_name STRING NOT NULL,
  file_path STRING,
  category STRING,
  document_type STRING,
  
  -- OCR results
  extracted_text STRING,
  confidence_score FLOAT64,
  page_count INT64,
  
  -- Metadata
  process_date TIMESTAMP,
  processor_type STRING,
  mime_type STRING,
  file_size_bytes INT64,
  
  -- Legal metadata
  case_number STRING,
  document_date DATE,
  filing_date DATE,
  parties ARRAY<STRING>,
  
  -- Processing status
  status STRING,
  error_message STRING,
  warnings ARRAY<STRING>,
  
  -- Timestamps
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP(),
  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP()
);

-- Entities extracted from documents
CREATE TABLE IF NOT EXISTS `modular-command-466820-p2.legal_documents.entities` (
  entity_id STRING NOT NULL,
  document_id STRING NOT NULL,
  entity_type STRING,  -- PERSON, ORG, DATE, MONEY, ADDRESS, etc.
  entity_value STRING,
  confidence FLOAT64,
  page_number INT64,
  context STRING,  -- Surrounding text
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP()
);

-- Form fields extracted
CREATE TABLE IF NOT EXISTS `modular-command-466820-p2.legal_documents.form_fields` (
  field_id STRING NOT NULL,
  document_id STRING NOT NULL,
  field_name STRING,
  field_value STRING,
  field_type STRING,  -- text, checkbox, signature, etc.
  confidence FLOAT64,
  page_number INT64,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP()
);

-- Document relationships (for tracking versions, amendments, etc.)
CREATE TABLE IF NOT EXISTS `modular-command-466820-p2.legal_documents.document_relationships` (
  relationship_id STRING NOT NULL,
  source_document_id STRING NOT NULL,
  target_document_id STRING NOT NULL,
  relationship_type STRING,  -- amendment, response, exhibit, etc.
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP()
);