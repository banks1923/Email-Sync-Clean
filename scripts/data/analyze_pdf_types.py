#!/usr/bin/env python3
"""
Analyze PDFs to identify searchable vs scanned documents.
"""

import os
import sys
from pathlib import Path

try:
    import pypdf
except ImportError:
    print("Error: pypdf not installed. Run: pip install pypdf")
    sys.exit(1)

def analyze_pdfs(directory: str):
    """
    Analyze all PDFs in directory to determine if searchable or scanned.
    """
    results = []
    
    pdf_dir = Path(directory)
    pdf_files = list(pdf_dir.glob("*.pdf"))
    
    print(f"\nAnalyzing {len(pdf_files)} PDFs in {directory}\n")
    print("-" * 80)
    
    for pdf_path in pdf_files:
        try:
            with open(pdf_path, 'rb') as file:
                reader = pypdf.PdfReader(file)
                page_count = len(reader.pages)
                
                # Try to extract text from first few pages
                text_found = False
                for i in range(min(3, page_count)):  # Check first 3 pages
                    page_text = reader.pages[i].extract_text()
                    if page_text and len(page_text.strip()) > 50:
                        text_found = True
                        break
                
                doc_type = "searchable" if text_found else "scanned"
                results.append({
                    'name': pdf_path.name,
                    'pages': page_count,
                    'type': doc_type
                })
                
                print(f"{pdf_path.name:50} {page_count:4} pages  [{doc_type:10}]")
                
        except Exception as e:
            print(f"{pdf_path.name:50} ERROR: {e}")
            results.append({
                'name': pdf_path.name,
                'pages': 0,
                'type': 'error'
            })
    
    # Summary
    searchable = sum(1 for r in results if r['type'] == 'searchable')
    scanned = sum(1 for r in results if r['type'] == 'scanned')
    errors = sum(1 for r in results if r['type'] == 'error')
    
    print("-" * 80)
    print("\nSummary:")
    print(f"  Searchable (text-based): {searchable}")
    print(f"  Scanned (needs OCR):     {scanned}")
    print(f"  Errors:                  {errors}")
    print(f"  Total:                   {len(pdf_files)}")
    
    if scanned > 0:
        print(f"\n⚠️  {scanned} PDFs need external OCR processing")
    
    return results

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python analyze_pdf_types.py <pdf_directory>")
        sys.exit(1)
    
    directory = sys.argv[1]
    if not os.path.isdir(directory):
        print(f"Error: {directory} is not a valid directory")
        sys.exit(1)
    
    analyze_pdfs(directory)