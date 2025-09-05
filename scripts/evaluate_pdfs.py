#!/usr/bin/env python3
"""
Evaluate PDF collection for duplicates, OCR status, and quality.
"""

import os
import hashlib
from pathlib import Path
from collections import defaultdict
import pypdf

def get_file_hash(filepath):
    """Get SHA256 hash of file."""
    hasher = hashlib.sha256()
    with open(filepath, 'rb') as f:
        buf = f.read(65536)
        while len(buf) > 0:
            hasher.update(buf)
            buf = f.read(65536)
    return hasher.hexdigest()

def check_pdf_text(filepath):
    """Check if PDF has extractable text."""
    try:
        with open(filepath, 'rb') as f:
            reader = pypdf.PdfReader(f)
            text_chars = 0
            for page in reader.pages[:3]:  # Check first 3 pages
                text = page.extract_text()
                text_chars += len(text.strip())
            return text_chars > 100  # Has meaningful text
    except:
        return False

def analyze_pdfs(directory):
    """Analyze all PDFs in directory."""
    pdf_dir = Path(directory)
    pdfs = list(pdf_dir.glob("*.pdf"))
    
    print(f"\n📊 PDF Collection Analysis")
    print(f"{'='*60}")
    print(f"Total PDFs: {len(pdfs)}")
    
    # Group by hash
    by_hash = defaultdict(list)
    for pdf in pdfs:
        file_hash = get_file_hash(pdf)
        by_hash[file_hash].append(pdf)
    
    # Find duplicates
    duplicates = {k: v for k, v in by_hash.items() if len(v) > 1}
    print(f"\n🔄 Duplicate Files: {len(duplicates)} sets")
    for hash_val, files in list(duplicates.items())[:5]:
        print(f"\n  Same content ({hash_val[:8]}...):")
        for f in files:
            size_mb = f.stat().st_size / (1024*1024)
            print(f"    - {f.name} ({size_mb:.1f}MB)")
    
    # Check OCR status
    print(f"\n📄 Text Extraction Status:")
    searchable = []
    scanned = []
    
    for pdf in pdfs[:30]:  # Sample first 30
        if check_pdf_text(pdf):
            searchable.append(pdf)
        else:
            scanned.append(pdf)
    
    print(f"  Searchable (has text): {len(searchable)}")
    print(f"  Scanned (needs OCR): {len(scanned)}")
    
    # Size analysis
    sizes = [(p, p.stat().st_size) for p in pdfs]
    sizes.sort(key=lambda x: x[1])
    
    print(f"\n📏 Size Distribution:")
    small = [s for s in sizes if s[1] < 500*1024]
    medium = [s for s in sizes if 500*1024 <= s[1] < 2*1024*1024]
    large = [s for s in sizes if s[1] >= 2*1024*1024]
    
    print(f"  Small (<500KB): {len(small)} - likely text PDFs")
    print(f"  Medium (500KB-2MB): {len(medium)} - mixed")
    print(f"  Large (>2MB): {len(large)} - likely scanned")
    
    # Document type patterns
    print(f"\n📁 Document Types:")
    patterns = {
        "Discovery": ["RFA", "RFP", "SROG", "FROG", "Response"],
        "Court": ["Court", "Demur", "Motion", "Order"],
        "Evidence": ["Lab", "Report", "Photo", "Inspection"],
        "Legal": ["Lease", "Notice", "Subpoena", "Proof"]
    }
    
    for doc_type, keywords in patterns.items():
        matching = [p for p in pdfs if any(kw in p.name for kw in keywords)]
        print(f"  {doc_type}: {len(matching)} documents")
        
    return {
        "total": len(pdfs),
        "duplicates": len(duplicates),
        "searchable": searchable,
        "scanned": scanned
    }

if __name__ == "__main__":
    results = analyze_pdfs("data/Stoneman_dispute/user_data")
    
    print(f"\n💡 Recommendations:")
    if results["duplicates"] > 0:
        print(f"  • Remove {results['duplicates']} duplicate sets")
    if results["scanned"]:
        print(f"  • OCR {len(results['scanned'])} scanned PDFs")
    print(f"  • Process {len(results['searchable'])} searchable PDFs first")