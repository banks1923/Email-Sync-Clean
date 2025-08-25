#!/usr/bin/env python3
"""
Simple Document AI PDF processor - test one PDF at a time
"""
import json
from google.cloud import documentai_v1 as documentai

# CONFIGURATION
PROJECT_ID = 'modular-command-466820-p2'  # Your project ID
LOCATION = 'us'  
PROCESSOR_ID = '8fadbc185616d041'  # Stoneman OCR processor

def process_one_pdf(pdf_path):
    """Process a single PDF with Document AI"""
    print(f"Processing: {pdf_path}")
    
    client = documentai.DocumentProcessorServiceClient()
    processor = f'projects/{PROJECT_ID}/locations/{LOCATION}/processors/{PROCESSOR_ID}'
    
    # Read PDF
    with open(pdf_path, 'rb') as f:
        content = f.read()
    
    print(f"PDF size: {len(content):,} bytes")
    
    # Process with Document AI
    request = documentai.ProcessRequest(
        name=processor,
        raw_document=documentai.RawDocument(
            content=content,
            mime_type='application/pdf'
        )
    )
    
    result = client.process_document(request=request)
    
    # Extract info
    pages = len(result.document.pages)
    text = result.document.text
    text_length = len(text)
    
    # Save text output
    txt_path = pdf_path.replace('.pdf', '_docai.txt')
    with open(txt_path, 'w', encoding='utf-8') as f:
        f.write(text)
    
    # Save JSON metadata
    json_path = pdf_path.replace('.pdf', '_docai.json')
    metadata = {
        'pdf_path': pdf_path,
        'pages': pages,
        'text_length': text_length,
        'txt_path': txt_path,
        'processor_id': PROCESSOR_ID
    }
    
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(metadata, f, indent=2)
    
    # Results
    print(f"✅ SUCCESS")
    print(f"   Pages: {pages}")
    print(f"   Text length: {text_length:,} chars")
    print(f"   Text saved: {txt_path}")
    print(f"   Metadata: {json_path}")
    
    return result

if __name__ == "__main__":
    # TEST FILE - pick smallest PDF first
    test_files = [
        "./data/Stoneman_dispute/low_confidence/Civil - Family Move - Robert L.pdf",
        "./data/Stoneman_dispute/pdfs_raw/Owner Move In #2/60 day notice 06:19:2025.pdf",
        "./data/Stoneman_dispute/pdfs_raw/CRD Defendants Response .pdf"
    ]
    
    print("Available test files:")
    for i, file in enumerate(test_files):
        print(f"{i+1}. {file}")
    
    print(f"\n🚀 Testing with: {test_files[0]}")
    
    # Test with first (smallest) PDF
    process_one_pdf(test_files[0])