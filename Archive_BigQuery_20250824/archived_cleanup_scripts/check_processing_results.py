#!/usr/bin/env python3
"""
Check the results of Document AI processing.
"""

import os
from google.cloud import bigquery
from pathlib import Path
import json

os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = '/Users/jim/Secrets/modular-command-466820-p2-bc0974cd5852.json'

# Paths
OUTPUT_DIR = Path("data/Stoneman_dispute/processed")
LOW_CONFIDENCE_DIR = Path("data/Stoneman_dispute/low_confidence")
FULL_TEXT_DIR = Path("data/Stoneman_dispute/full_text")

def check_results():
    """Check processing results."""
    
    print("📊 DOCUMENT AI PROCESSING RESULTS")
    print("=" * 60)
    
    # Check local files
    json_files = list(OUTPUT_DIR.glob("*.json"))
    text_files = list(FULL_TEXT_DIR.glob("*.txt")) if FULL_TEXT_DIR.exists() else []
    low_conf_files = list(LOW_CONFIDENCE_DIR.glob("*.pdf")) if LOW_CONFIDENCE_DIR.exists() else []
    
    print(f"\n📁 Local Files:")
    print(f"  Processed JSONs: {len(json_files)}")
    print(f"  Full text files: {len(text_files)}")
    print(f"  Low confidence PDFs: {len(low_conf_files)}")
    
    # Check BigQuery
    client = bigquery.Client()
    
    # Overall stats
    query = """
    SELECT 
        COUNT(*) as total_docs,
        COUNT(DISTINCT document_type) as doc_types,
        AVG(confidence) as avg_confidence,
        MIN(confidence) as min_confidence,
        MAX(confidence) as max_confidence,
        SUM(page_count) as total_pages,
        COUNT(DISTINCT processor_used) as processors_used,
        SUM(content_length) as total_chars
    FROM `modular-command-466820-p2.stoneman_case.documents`
    """
    
    print(f"\n📊 BigQuery Statistics:")
    for row in client.query(query).result():
        print(f"  Total documents: {row.total_docs}")
        print(f"  Document types: {row.doc_types}")
        print(f"  Average confidence: {row.avg_confidence:.3f}")
        print(f"  Confidence range: {row.min_confidence:.3f} - {row.max_confidence:.3f}")
        print(f"  Total pages: {row.total_pages}")
        print(f"  Total characters: {row.total_chars:,}")
        print(f"  Processors used: {row.processors_used}")
    
    # By document type
    query = """
    SELECT 
        document_type,
        COUNT(*) as count,
        AVG(confidence) as avg_conf,
        AVG(page_count) as avg_pages
    FROM `modular-command-466820-p2.stoneman_case.documents`
    GROUP BY document_type
    ORDER BY count DESC
    """
    
    print(f"\n📑 By Document Type:")
    for row in client.query(query).result():
        print(f"  {row.document_type}: {row.count} docs, "
              f"avg conf: {row.avg_conf:.3f}, "
              f"avg pages: {row.avg_pages:.1f}")
    
    # By processor
    query = """
    SELECT 
        processor_used,
        COUNT(*) as count,
        AVG(confidence) as avg_conf,
        SUM(dual_processed) as dual_processed_count
    FROM `modular-command-466820-p2.stoneman_case.documents`
    GROUP BY processor_used
    """
    
    print(f"\n🔧 By Processor:")
    for row in client.query(query).result():
        print(f"  {row.processor_used}: {row.count} docs, "
              f"avg conf: {row.avg_conf:.3f}, "
              f"dual processed: {row.dual_processed_count or 0}")
    
    # Evidence classification
    query = """
    SELECT 
        JSON_EXTRACT_SCALAR(evidence_classification, '$.evidence_strength') as strength,
        COUNT(*) as count
    FROM `modular-command-466820-p2.stoneman_case.documents`
    WHERE evidence_classification IS NOT NULL
    GROUP BY strength
    ORDER BY count DESC
    """
    
    print(f"\n⚖️ Evidence Strength:")
    for row in client.query(query).result():
        if row.strength:
            print(f"  {row.strength}: {row.count} documents")
    
    # Top entities
    query = """
    SELECT 
        party,
        COUNT(*) as mentions
    FROM `modular-command-466820-p2.stoneman_case.documents`,
    UNNEST(parties) as party
    GROUP BY party
    ORDER BY mentions DESC
    LIMIT 10
    """
    
    print(f"\n👥 Top Parties Mentioned:")
    for row in client.query(query).result():
        print(f"  {row.party}: {row.mentions} mentions")
    
    # Money amounts
    query = """
    SELECT 
        DISTINCT amount
    FROM `modular-command-466820-p2.stoneman_case.documents`,
    UNNEST(money_amounts) as amount
    WHERE amount > 0
    ORDER BY amount DESC
    LIMIT 10
    """
    
    print(f"\n💰 Money Amounts Found:")
    for row in client.query(query).result():
        print(f"  ${row.amount:,.2f}")
    
    # Failed processing (from log if exists)
    log_path = OUTPUT_DIR / "processing_log.json"
    if log_path.exists():
        with open(log_path) as f:
            log = json.load(f)
        
        print(f"\n📝 Processing Log Summary:")
        print(f"  Timestamp: {log.get('timestamp', 'N/A')}")
        if 'summary' in log:
            print(f"  Total files: {log['summary'].get('total_files', 0)}")
            print(f"  Failed: {log['summary'].get('failed', 0)}")
            print(f"  Low confidence: {log['summary'].get('low_confidence', 0)}")
        
        if log.get('failed_files'):
            print(f"\n❌ Failed Files:")
            for file in log['failed_files'][:5]:
                print(f"  - {Path(file).name}")

if __name__ == "__main__":
    check_results()