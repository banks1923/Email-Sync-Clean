#!/usr/bin/env python3
"""
Set up BigQuery dataset and tables for legal document processing.
"""

import os
from google.cloud import bigquery

# Set up credentials
os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = '/Users/jim/Secrets/modular-command-466820-p2-bc0974cd5852.json'

def create_dataset_and_tables():
    """
    Create BigQuery dataset and tables for legal documents.
    """
    
    client = bigquery.Client()
    project_id = client.project
    
    print(f"🔧 Setting up BigQuery in project: {project_id}")
    print("=" * 60)
    
    # Create dataset
    dataset_id = f"{project_id}.stoneman_case"
    dataset = bigquery.Dataset(dataset_id)
    dataset.location = "US"
    dataset.description = "Stoneman legal case document analysis"
    
    try:
        dataset = client.create_dataset(dataset, exists_ok=True)
        print(f"✅ Dataset created/verified: {dataset_id}")
    except Exception as e:
        print(f"⚠️  Dataset exists or error: {e}")
    
    # Define table schemas
    tables = {
        "documents": [
            bigquery.SchemaField("document_id", "STRING", mode="REQUIRED", description="SHA256 hash of document"),
            bigquery.SchemaField("filename", "STRING", mode="REQUIRED"),
            bigquery.SchemaField("filepath", "STRING", mode="REQUIRED"),
            bigquery.SchemaField("document_type", "STRING", description="email|notice|complaint|report|discovery|motion"),
            bigquery.SchemaField("content", "STRING", description="Full extracted text"),
            bigquery.SchemaField("content_ocr", "STRING", description="OCR extracted text if different"),
            bigquery.SchemaField("confidence", "FLOAT64", description="Processing confidence score"),
            bigquery.SchemaField("processor_used", "STRING", description="FORM|OCR|BOTH"),
            bigquery.SchemaField("page_count", "INTEGER"),
            bigquery.SchemaField("extracted_entities", "JSON", description="Named entities extracted"),
            bigquery.SchemaField("structured_fields", "JSON", description="Form fields extracted"),
            bigquery.SchemaField("evidence_classification", "JSON", description="Legal relevance scoring"),
            bigquery.SchemaField("processing_timestamp", "TIMESTAMP", mode="REQUIRED"),
            bigquery.SchemaField("document_date", "DATE", description="Date mentioned in document"),
            bigquery.SchemaField("parties", "STRING", mode="REPEATED", description="Parties mentioned"),
            bigquery.SchemaField("violations", "STRING", mode="REPEATED", description="Violations detected"),
            bigquery.SchemaField("money_amounts", "FLOAT64", mode="REPEATED", description="Money amounts mentioned"),
        ],
        
        "evidence_patterns": [
            bigquery.SchemaField("pattern_id", "STRING", mode="REQUIRED"),
            bigquery.SchemaField("pattern_type", "STRING", description="identity_concealment|repair_avoidance|retaliation|harassment"),
            bigquery.SchemaField("documents", "STRING", mode="REPEATED", description="Document IDs showing pattern"),
            bigquery.SchemaField("strength_score", "FLOAT64", description="Pattern strength 0-1"),
            bigquery.SchemaField("legal_implications", "STRING", description="Legal significance"),
            bigquery.SchemaField("timeline_correlation", "JSON", description="Related timeline events"),
            bigquery.SchemaField("created_at", "TIMESTAMP", mode="REQUIRED"),
        ],
        
        "timeline": [
            bigquery.SchemaField("event_id", "STRING", mode="REQUIRED"),
            bigquery.SchemaField("event_date", "DATE", mode="REQUIRED"),
            bigquery.SchemaField("event_time", "TIME", description="Time if available"),
            bigquery.SchemaField("event_description", "STRING", mode="REQUIRED"),
            bigquery.SchemaField("event_category", "STRING", description="notice|repair|complaint|legal|communication"),
            bigquery.SchemaField("source_documents", "STRING", mode="REPEATED"),
            bigquery.SchemaField("parties_involved", "STRING", mode="REPEATED"),
            bigquery.SchemaField("violation_type", "STRING", description="Type of violation if applicable"),
            bigquery.SchemaField("legal_deadline", "DATE", description="Any deadline triggered by this event"),
            bigquery.SchemaField("created_at", "TIMESTAMP", mode="REQUIRED"),
        ],
        
        "processing_log": [
            bigquery.SchemaField("log_id", "STRING", mode="REQUIRED"),
            bigquery.SchemaField("document_id", "STRING", mode="REQUIRED"),
            bigquery.SchemaField("filename", "STRING", mode="REQUIRED"),
            bigquery.SchemaField("processor", "STRING", description="FORM_PARSER|OCR_PROCESSOR"),
            bigquery.SchemaField("status", "STRING", description="success|failed|low_confidence"),
            bigquery.SchemaField("confidence_score", "FLOAT64"),
            bigquery.SchemaField("error_message", "STRING"),
            bigquery.SchemaField("processing_time_ms", "INTEGER"),
            bigquery.SchemaField("timestamp", "TIMESTAMP", mode="REQUIRED"),
        ]
    }
    
    # Create tables
    for table_name, schema in tables.items():
        table_id = f"{dataset_id}.{table_name}"
        table = bigquery.Table(table_id, schema=schema)
        
        try:
            table = client.create_table(table, exists_ok=True)
            print(f"✅ Table created/verified: {table_name}")
            print(f"   Fields: {len(schema)}")
        except Exception as e:
            print(f"⚠️  Table {table_name} exists or error: {e}")
    
    print("\n" + "=" * 60)
    print("✅ BigQuery setup complete!")
    print(f"Dataset: {dataset_id}")
    print(f"Tables: {', '.join(tables.keys())}")
    
    # Test query
    print("\n🔍 Testing BigQuery connection...")
    query = f"""
    SELECT 
        table_name,
        ROUND(size_bytes / 1024, 2) as size_kb,
        row_count
    FROM `{project_id}.stoneman_case.__TABLES__`
    """
    
    try:
        results = client.query(query).result()
        print("✅ BigQuery connection verified")
        for row in results:
            print(f"   Table: {row.table_name}, Rows: {row.row_count}")
    except Exception as e:
        print(f"Query test result: {e}")
    
    return dataset_id

if __name__ == "__main__":
    dataset_id = create_dataset_and_tables()
    print(f"\n📊 Next step: Process documents with Document AI and load to BigQuery")
    print(f"Dataset ready: {dataset_id}")