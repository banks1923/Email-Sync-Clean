#!/usr/bin/env python3
"""Test BigQuery connection and setup."""

import os
from google.cloud import bigquery
from datetime import datetime
import uuid

# Set credentials
os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = '/Users/jim/Secrets/modular-command-466820-p2-bc0974cd5852.json'

def test_bigquery():
    """Test BigQuery connection and tables."""
    
    # Initialize client
    client = bigquery.Client(project='modular-command-466820-p2')
    
    print("✅ Connected to BigQuery")
    
    # List datasets
    datasets = list(client.list_datasets())
    print(f"\n📊 Found {len(datasets)} datasets:")
    for dataset in datasets:
        print(f"  - {dataset.dataset_id}")
    
    # Check our tables
    dataset_ref = client.dataset('legal_documents')
    tables = list(client.list_tables(dataset_ref))
    
    print(f"\n📋 Tables in legal_documents:")
    for table in tables:
        print(f"  - {table.table_id}")
    
    # Insert test record
    table_ref = dataset_ref.table('documents')
    table = client.get_table(table_ref)
    
    test_row = {
        'document_id': str(uuid.uuid4()),
        'file_name': 'test_document.pdf',
        'file_path': '/test/path/test_document.pdf',
        'category': 'test',
        'extracted_text': 'This is a test document',
        'confidence_score': 0.95,
        'page_count': 1,
        'process_date': datetime.now().isoformat(),
        'status': 'completed'
    }
    
    errors = client.insert_rows_json(table, [test_row])
    
    if errors:
        print(f"\n❌ Error inserting test row: {errors}")
    else:
        print(f"\n✅ Test row inserted successfully")
    
    # Query test
    query = """
        SELECT COUNT(*) as count 
        FROM `modular-command-466820-p2.legal_documents.documents`
    """
    
    query_job = client.query(query)
    results = query_job.result()
    
    for row in results:
        print(f"\n📊 Documents in BigQuery: {row.count}")
    
    print("\n🎉 BigQuery is ready for document storage!")

if __name__ == "__main__":
    test_bigquery()