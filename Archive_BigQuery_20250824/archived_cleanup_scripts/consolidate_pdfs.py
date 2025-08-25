#!/usr/bin/env python3
"""
PDF OCR Batch Processing Script
Uses Google Document AI to OCR all PDFs and consolidate text
"""

import json
from pathlib import Path
from typing import List
import sys

# Google Cloud imports
try:
    from google.cloud import documentai_v1 as documentai
    from google.api_core.client_options import ClientOptions
    from google.oauth2 import service_account
except ImportError:
    print("❌ Google Cloud libraries not installed.")
    print("   Run: pip install google-cloud-documentai")
    sys.exit(1)

# Configuration - Update these values
PROJECT_ID = "your-project-id"  # Your GCP project ID
LOCATION = "us"  # or "eu" 
PROCESSOR_ID = "your-processor-id"  # Document AI processor ID
PROCESSOR_VERSION = "stable"  # or specific version

# If using service account key file
SERVICE_ACCOUNT_FILE = None  # Path to service account JSON, or None to use default credentials

def get_document_ai_client():
    """Initialize Document AI client"""
    opts = ClientOptions(api_endpoint=f"{LOCATION}-documentai.googleapis.com")
    
    if SERVICE_ACCOUNT_FILE:
        credentials = service_account.Credentials.from_service_account_file(SERVICE_ACCOUNT_FILE)
        client = documentai.DocumentProcessorServiceClient(
            client_options=opts,
            credentials=credentials
        )
    else:
        # Use default credentials (gcloud auth)
        client = documentai.DocumentProcessorServiceClient(client_options=opts)
    
    return client

def process_pdf_with_ocr(client, pdf_path: Path) -> str:
    """Process a single PDF with Google Document AI OCR"""
    
    # The full resource name of the processor
    name = client.processor_path(PROJECT_ID, LOCATION, PROCESSOR_ID)
    
    # Read the PDF file
    with open(pdf_path, "rb") as pdf_file:
        pdf_content = pdf_file.read()
    
    # Configure the process request
    document = documentai.RawDocument(
        content=pdf_content,
        mime_type="application/pdf"
    )
    
    request = documentai.ProcessRequest(
        name=name,
        raw_document=document
    )
    
    print(f"   📤 Sending {pdf_path.name} to Document AI...")
    
    try:
        # Process the document
        result = client.process_document(request=request)
        document = result.document
        
        # Extract text
        text = document.text
        print(f"   ✅ Extracted {len(text)} characters")
        return text
        
    except Exception as e:
        print(f"   ❌ Error processing {pdf_path.name}: {e}")
        return ""

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

def main():
    print("🔍 PDF OCR Batch Processing")
    print("=" * 50)
    
    # Find all PDFs
    pdf_files = find_all_pdfs()
    
    if not pdf_files:
        print("❌ No PDF files found")
        sys.exit(1)
    
    print(f"📂 Found {len(pdf_files)} PDF files")
    for pdf in pdf_files[:10]:  # Show first 10
        print(f"   • {pdf}")
    if len(pdf_files) > 10:
        print(f"   ... and {len(pdf_files) - 10} more")
    
    # Ask for confirmation
    response = input("\n🤔 Process all PDFs with Google Document AI? (y/n): ")
    if response.lower() != 'y':
        print("❌ Cancelled")
        sys.exit(0)
    
    # Initialize Document AI client
    print("\n🔌 Connecting to Google Document AI...")
    try:
        client = get_document_ai_client()
    except Exception as e:
        print(f"❌ Failed to connect: {e}")
        print("\n📝 To set up Google Cloud:")
        print("   1. Install gcloud CLI")
        print("   2. Run: gcloud auth application-default login")
        print("   3. Update PROJECT_ID, PROCESSOR_ID in this script")
        sys.exit(1)
    
    # Create output directory
    output_dir = Path("pdf_texts")
    output_dir.mkdir(exist_ok=True)
    
    # Process each PDF
    all_texts = []
    metadata = []
    
    print(f"\n⚙️ Processing {len(pdf_files)} PDFs...")
    
    for i, pdf_path in enumerate(pdf_files, 1):
        print(f"\n[{i}/{len(pdf_files)}] Processing {pdf_path.name}")
        
        # Process with OCR
        text = process_pdf_with_ocr(client, pdf_path)
        
        if text:
            # Save individual text file
            text_filename = output_dir / f"{pdf_path.stem}.txt"
            with open(text_filename, 'w', encoding='utf-8') as f:
                f.write(text)
            print(f"   💾 Saved to {text_filename}")
            
            # Add to consolidated list
            all_texts.append(f"\n{'='*80}\n")
            all_texts.append(f"FILE: {pdf_path}\n")
            all_texts.append(f"{'='*80}\n")
            all_texts.append(text)
            
            # Add metadata
            metadata.append({
                'file': str(pdf_path),
                'name': pdf_path.name,
                'size': pdf_path.stat().st_size,
                'text_length': len(text),
                'text_file': str(text_filename)
            })
    
    # Write consolidated text file
    consolidated_file = Path("consolidated_pdfs.txt")
    with open(consolidated_file, 'w', encoding='utf-8') as f:
        f.write("PDF OCR CONSOLIDATED TEXT\n")
        f.write("=" * 80 + "\n")
        f.write(f"Total PDFs: {len(pdf_files)}\n")
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
    print(f"   Total PDFs processed: {len(metadata)}")
    print(f"   Total text extracted: {sum(m['text_length'] for m in metadata):,} characters")
    print(f"   Output directory: {output_dir}")
    print("\n✅ PDF OCR processing complete!")

if __name__ == "__main__":
    main()