#!/usr/bin/env python3
"""
PDF Consolidation Script using Local OCR
Uses existing PDF processing capabilities in the project
"""

import json
from pathlib import Path
from typing import List, Dict
import sys
import sqlite3

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

# Import existing PDF processor
from pdf.pdf_processor_enhanced import EnhancedPDFProcessor

def find_all_pdfs(directory: Path = Path(".")) -> list[Path]:
    """Find all PDF files in directory and subdirectories"""
    pdf_files = []
    
    # Common directories to search
    search_dirs = [
        directory,
        directory / "data",
        directory / "data" / "Stoneman_dispute",
        directory / "data" / "Stoneman_dispute" / "user_data"
    ]
    
    for search_dir in search_dirs:
        if search_dir.exists():
            pdfs = list(search_dir.glob("**/*.pdf"))
            pdf_files.extend(pdfs)
    
    # Remove duplicates
    pdf_files = list(set(pdf_files))
    
    # Sort by name
    pdf_files.sort(key=lambda x: x.name)
    
    return pdf_files

def process_pdf_with_local_ocr(pdf_path: Path) -> dict:
    """Process a PDF using the existing PDF processor"""
    try:
        processor = EnhancedPDFProcessor()
        
        print(f"   📄 Processing {pdf_path.name}...")
        
        # Extract and chunk the PDF (with OCR if needed)
        result = processor.extract_and_chunk_pdf(str(pdf_path))
        
        if result['success']:
            # Join chunks back into full text
            chunks = result.get('chunks', [])
            text = '\n'.join(chunks)
            print(f"   ✅ Extracted {len(text)} characters from {len(chunks)} chunks")
            return {
                'success': True,
                'text': text,
                'chunks': chunks,
                'metadata': result.get('metadata', {}),
                'ocr_performed': result.get('extraction_method') == 'ocr'
            }
        else:
            print(f"   ⚠️ Failed: {result.get('error', 'Unknown error')}")
            return {'success': False, 'text': '', 'error': result.get('error')}
            
    except Exception as e:
        print(f"   ❌ Error: {e}")
        return {'success': False, 'text': '', 'error': str(e)}

def check_existing_content(db_path: Path) -> dict[str, str]:
    """Check what PDFs are already in the database"""
    existing = {}
    
    if not db_path.exists():
        return existing
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Check content_unified table for PDFs
        cursor.execute("""
            SELECT source_id, title, body 
            FROM content_unified 
            WHERE source_type = 'pdf'
        """)
        
        for row in cursor.fetchall():
            source_id, title, body = row
            if title:
                existing[title] = body[:500] if body else ''
        
        conn.close()
        print(f"📊 Found {len(existing)} PDFs already in database")
        
    except Exception as e:
        print(f"⚠️ Could not check database: {e}")
    
    return existing

def main():
    print("🔍 PDF Consolidation (Local OCR)")
    print("=" * 50)
    
    # Check database for existing content
    db_path = Path("data/system_data/emails.db")
    existing_pdfs = check_existing_content(db_path)
    
    # Find all PDFs
    pdf_files = find_all_pdfs()
    
    if not pdf_files:
        print("❌ No PDF files found")
        sys.exit(1)
    
    print(f"📂 Found {len(pdf_files)} PDF files")
    for pdf in pdf_files[:10]:  # Show first 10
        name = pdf.name
        status = "✓" if name in existing_pdfs else "○"
        print(f"   {status} {pdf}")
    if len(pdf_files) > 10:
        print(f"   ... and {len(pdf_files) - 10} more")
    
    # Create output directory
    output_dir = Path("pdf_texts")
    output_dir.mkdir(exist_ok=True)
    
    # Process each PDF
    all_texts = []
    metadata = []
    processed_count = 0
    error_count = 0
    
    print(f"\n⚙️ Processing {len(pdf_files)} PDFs...")
    
    for i, pdf_path in enumerate(pdf_files, 1):
        print(f"\n[{i}/{len(pdf_files)}] {pdf_path.name}")
        
        # Skip if already in database with content
        if pdf_path.name in existing_pdfs and existing_pdfs[pdf_path.name]:
            print(f"   ⏭️ Already in database, skipping")
            # Still add to consolidated from DB
            text = existing_pdfs[pdf_path.name]
            all_texts.append(f"\n{'='*80}\n")
            all_texts.append(f"FILE: {pdf_path} [FROM DATABASE]\n")
            all_texts.append(f"{'='*80}\n")
            all_texts.append(text + "\n[truncated in preview]")
            continue
        
        # Process with OCR
        result = process_pdf_with_local_ocr(pdf_path)
        
        if result['success'] and result['text']:
            text = result['text']
            processed_count += 1
            
            # Save individual text file
            text_filename = output_dir / f"{pdf_path.stem}.txt"
            with open(text_filename, 'w', encoding='utf-8') as f:
                f.write(text)
            print(f"   💾 Saved to {text_filename}")
            
            # Add to consolidated list
            all_texts.append(f"\n{'='*80}\n")
            all_texts.append(f"FILE: {pdf_path}\n")
            if result.get('ocr_performed'):
                all_texts.append(f"OCR: Yes\n")
            all_texts.append(f"{'='*80}\n")
            all_texts.append(text)
            
            # Add metadata
            metadata.append({
                'file': str(pdf_path),
                'name': pdf_path.name,
                'size': pdf_path.stat().st_size,
                'text_length': len(text),
                'text_file': str(text_filename),
                'ocr_performed': result.get('ocr_performed', False)
            })
        else:
            error_count += 1
            print(f"   ❌ Failed to extract text")
    
    # Write consolidated text file
    consolidated_file = Path("consolidated_pdfs.txt")
    with open(consolidated_file, 'w', encoding='utf-8') as f:
        f.write("PDF CONSOLIDATED TEXT\n")
        f.write("=" * 80 + "\n")
        f.write(f"Total PDFs: {len(pdf_files)}\n")
        f.write(f"Processed: {processed_count}\n")
        f.write(f"From Database: {len(existing_pdfs)}\n")
        f.write(f"Errors: {error_count}\n")
        f.write("=" * 80 + "\n")
        f.writelines(all_texts)
    
    print(f"\n✅ Wrote consolidated text to {consolidated_file}")
    print(f"   File size: {consolidated_file.stat().st_size:,} bytes")
    
    # Write metadata JSON
    metadata_file = Path("pdf_metadata.json")
    with open(metadata_file, 'w', encoding='utf-8') as f:
        json.dump(metadata, f, indent=2)
    
    print(f"✅ Wrote metadata to {metadata_file}")
    
    # Summary
    print("\n📊 Summary:")
    print(f"   Total PDFs found: {len(pdf_files)}")
    print(f"   Newly processed: {processed_count}")
    print(f"   From database: {len(existing_pdfs)}")
    print(f"   Errors: {error_count}")
    if metadata:
        print(f"   Total text extracted: {sum(m['text_length'] for m in metadata):,} characters")
    print(f"   Output directory: {output_dir}")
    print("\n✅ PDF consolidation complete!")

if __name__ == "__main__":
    main()