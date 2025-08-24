#!/usr/bin/env python3
"""Process documents with Google Document AI."""

import os
import sys
from google.cloud import documentai_v1 as documentai
from pathlib import Path

# Set credentials
os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = '/Users/jim/Secrets/modular-command-466820-p2-bc0974cd5852.json'

PROJECT_ID = "modular-command-466820-p2"
LOCATION = "us"

def process_document(file_path, processor_type="OCR_PROCESSOR"):
    """Process a document with Document AI."""
    
    # Initialize client
    client = documentai.DocumentProcessorServiceClient()
    
    # You need a processor - let's create one if it doesn't exist
    parent = f"projects/{PROJECT_ID}/locations/{LOCATION}"
    
    try:
        # List existing processors
        processors = client.list_processors(parent=parent)
        processor = None
        
        for p in processors:
            if processor_type in p.type_:
                processor = p
                break
        
        if not processor:
            print(f"Creating {processor_type} processor...")
            processor = client.create_processor(
                parent=parent,
                processor=documentai.Processor(
                    display_name=f"Legal {processor_type}",
                    type_=processor_type
                )
            )
            print(f"Created processor: {processor.name}")
        
        # Read the file
        with open(file_path, 'rb') as f:
            file_content = f.read()
        
        # Configure the process request
        request = documentai.ProcessRequest(
            name=processor.name,
            raw_document=documentai.RawDocument(
                content=file_content,
                mime_type="application/pdf"  # Adjust based on file type
            )
        )
        
        # Process the document
        print(f"Processing {file_path}...")
        result = client.process_document(request=request)
        document = result.document
        
        # Extract text
        print(f"\nExtracted Text ({len(document.text)} characters):")
        print("-" * 50)
        print(document.text)
        print("-" * 50)
        
        # Extract entities if available
        if document.entities:
            print(f"\nFound {len(document.entities)} entities:")
            for entity in document.entities:
                print(f"  - {entity.type_}: {entity.mention_text}")
        
        return document.text
        
    except Exception as e:
        print(f"Error processing document: {e}")
        return None

def main():
    if len(sys.argv) < 2:
        print("Usage: python3 process_document.py <file_path>")
        print("Example: python3 process_document.py document.pdf")
        return
    
    file_path = sys.argv[1]
    
    if not Path(file_path).exists():
        print(f"File not found: {file_path}")
        return
    
    process_document(file_path)

if __name__ == "__main__":
    main()