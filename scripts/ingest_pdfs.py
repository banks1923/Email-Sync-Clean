#!/usr/bin/env python3
"""
Ingest searchable PDFs into the system.
For MVP - processes text-extractable PDFs only.
"""

import sys
from pathlib import Path

# Add project root
sys.path.insert(0, str(Path(__file__).parent.parent))

from pdf.wiring import get_pdf_service
from lib.db import SimpleDB
import pypdf

def quick_check_pdf(filepath):
    """Quick check if PDF has extractable text."""
    try:
        with open(filepath, 'rb') as f:
            reader = pypdf.PdfReader(f)
            # Check first page
            if reader.pages:
                text = reader.pages[0].extract_text()
                return len(text.strip()) > 100
    except:
        pass
    return False

def ingest_searchable_pdfs(directory="data/Stoneman_dispute/user_data", limit=5):
    """
    Ingest searchable PDFs into content_unified table.
    
    Args:
        directory: Path to PDF directory
        limit: Max PDFs to process (for testing)
    """
    pdf_dir = Path(directory)
    pdfs = list(pdf_dir.glob("*.pdf"))
    
    print(f"\n🚀 PDF Ingestion (MVP)")
    print(f"{'='*60}")
    
    # Get services
    db = SimpleDB("data/system_data/emails.db")
    pdf_service = get_pdf_service("data/system_data/emails.db")
    
    processed = 0
    skipped = 0
    failed = 0
    
    for pdf_path in pdfs[:limit]:
        print(f"\n📄 {pdf_path.name}")
        
        # Quick check for text
        if not quick_check_pdf(pdf_path):
            print("  ⏭️  Skipped - no extractable text (needs OCR)")
            skipped += 1
            continue
        
        try:
            # Process PDF
            result = pdf_service.upload_single_pdf(str(pdf_path))
            
            if result.get("success"):
                chunks = result.get("chunks_processed", 0)
                print(f"  ✅ Processed - {chunks} chunks created")
                processed += 1
            else:
                print(f"  ❌ Failed - {result.get('error', 'Unknown error')}")
                failed += 1
                
        except Exception as e:
            print(f"  ❌ Error - {str(e)}")
            failed += 1
    
    print(f"\n📊 Summary:")
    print(f"  Processed: {processed}")
    print(f"  Skipped (need OCR): {skipped}")
    print(f"  Failed: {failed}")
    
    # Check what's in the database
    with db._get_connection() as conn:
        cursor = conn.cursor()
        
        # Check documents table
        cursor.execute("SELECT COUNT(*) FROM documents")
        doc_count = cursor.fetchone()[0]
        
        # Check if any made it to content_unified
        cursor.execute("""
            SELECT COUNT(*) FROM content_unified 
            WHERE source_type = 'document'
        """)
        unified_count = cursor.fetchone()[0]
        
    print(f"\n💾 Database Status:")
    print(f"  Documents table: {doc_count} chunks")
    print(f"  Content unified: {unified_count} documents")

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=5, help="Max PDFs to process")
    parser.add_argument("--dir", default="data/Stoneman_dispute/user_data", help="PDF directory")
    args = parser.parse_args()
    
    ingest_searchable_pdfs(args.dir, args.limit)