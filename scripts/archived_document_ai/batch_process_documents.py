#!/usr/bin/env python3
"""Batch process documents in a directory with Google Document AI.

Usage:
    python3 scripts/batch_process_documents.py <directory> [output_directory]

Examples:
    python3 scripts/batch_process_documents.py data/Stoneman_dispute/user_data
    python3 scripts/batch_process_documents.py data/Stoneman_dispute/user_data ./extracted_text
"""

import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent))

from scripts.process_single_document import process_document


def batch_process(directory, output_dir=None, recursive=False):
    """Process all PDFs in a directory.

    Args:
        directory: Directory containing PDFs
        output_dir: Optional output directory for extracted text
        recursive: Whether to search subdirectories
    """
    
    directory = Path(directory)
    if not directory.exists():
        print(f"Directory not found: {directory}")
        return
    
    # Find all PDFs
    if recursive:
        pdf_files = list(directory.rglob("*.pdf"))
    else:
        pdf_files = list(directory.glob("*.pdf"))
        
    if not pdf_files:
        print(f"No PDF files found in {directory}")
        return
    
    print(f"Found {len(pdf_files)} PDF files")
    
    # Create output directory
    if output_dir:
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
    
    successful = 0
    failed = 0
    
    # Process each file
    for pdf_file in pdf_files:
        print(f"\n{'='*60}")
        print(f"Processing: {pdf_file.name}")
        print(f"{'='*60}")
        
        try:
            text = process_document(str(pdf_file))
            
            if text:
                successful += 1
                if output_dir:
                    # Save extracted text
                    output_file = output_dir / f"{pdf_file.stem}.txt"
                    with open(output_file, 'w', encoding='utf-8') as f:
                        f.write(text)
                    print(f"✅ Saved text to: {output_file}")
            else:
                failed += 1
                print(f"⚠️  No text extracted from {pdf_file.name}")
                
        except Exception as e:
            failed += 1
            print(f"❌ Error processing {pdf_file.name}: {e}")
    
    # Summary
    print(f"\n{'='*60}")
    print(f"Processing Complete:")
    print(f"  ✅ Successful: {successful}")
    print(f"  ❌ Failed: {failed}")
    print(f"  📊 Total: {len(pdf_files)}")
    print(f"{'='*60}")

def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return
    
    directory = sys.argv[1]
    output_dir = sys.argv[2] if len(sys.argv) > 2 else None
    recursive = '--recursive' in sys.argv or '-r' in sys.argv
    
    batch_process(directory, output_dir, recursive)

if __name__ == "__main__":
    main()