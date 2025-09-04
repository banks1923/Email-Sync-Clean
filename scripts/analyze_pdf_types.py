#!/usr/bin/env python3
"""Analyze PDFs to identify searchable vs scanned documents."""

import os
import sys
from pathlib import Path

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pdf.ocr.validator import PDFValidator

def analyze_pdfs(directory: str):
    """Analyze all PDFs in directory to determine if searchable or scanned."""
    validator = PDFValidator()
    results = []
    
    pdf_dir = Path(directory)
    pdf_files = list(pdf_dir.glob("*.pdf"))
    
    print(f"\nAnalyzing {len(pdf_files)} PDFs in {directory}\n")
    print("-" * 80)
    
    for pdf_path in pdf_files:
        try:
            # Check if PDF is scanned
            is_scanned, confidence = validator.is_scanned_pdf(str(pdf_path))
            pdf_type = "SCANNED" if is_scanned else "SEARCHABLE"
            
            results.append({
                "file": pdf_path.name,
                "type": pdf_type,
                "confidence": confidence,
                "is_scanned": is_scanned
            })
            
            # Print progress
            status = "📷" if is_scanned else "📝"
            print(f"{status} {pdf_type:12} ({confidence:.0%} conf): {pdf_path.name}")
            
        except Exception as e:
            print(f"❌ ERROR: {pdf_path.name} - {str(e)}")
            results.append({
                "file": pdf_path.name,
                "type": "ERROR",
                "confidence": 0,
                "is_scanned": None
            })
    
    # Generate summary report
    print("\n" + "=" * 80)
    print("SUMMARY REPORT")
    print("=" * 80)
    
    searchable = [r for r in results if r["type"] == "SEARCHABLE"]
    scanned = [r for r in results if r["type"] == "SCANNED"]
    errors = [r for r in results if r["type"] == "ERROR"]
    
    print(f"\nTotal PDFs analyzed: {len(results)}")
    print(f"  📝 Searchable (native text): {len(searchable)} ({len(searchable)/len(results)*100:.1f}%)")
    print(f"  📷 Scanned (needs OCR):      {len(scanned)} ({len(scanned)/len(results)*100:.1f}%)")
    if errors:
        print(f"  ❌ Errors:                   {len(errors)} ({len(errors)/len(results)*100:.1f}%)")
    
    # List scanned PDFs that might need OCR
    if scanned:
        print("\n" + "-" * 80)
        print("SCANNED PDFs (may need OCR processing):")
        print("-" * 80)
        for pdf in sorted(scanned, key=lambda x: x["confidence"], reverse=True):
            print(f"  - {pdf['file']} (confidence: {pdf['confidence']:.0%})")
    
    # High confidence searchable PDFs
    high_conf_searchable = [r for r in searchable if r["confidence"] < 0.2]
    if high_conf_searchable:
        print("\n" + "-" * 80)
        print(f"HIGH CONFIDENCE SEARCHABLE PDFs ({len(high_conf_searchable)} files):")
        print("-" * 80)
        for pdf in sorted(high_conf_searchable, key=lambda x: x["confidence"])[:10]:
            print(f"  - {pdf['file']} (text density: {(1-pdf['confidence'])*100:.0f}%)")
    
    return results

if __name__ == "__main__":
    directory = "data/Stoneman_dispute/user_data"
    if len(sys.argv) > 1:
        directory = sys.argv[1]
    
    analyze_pdfs(directory)