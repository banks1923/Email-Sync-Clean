#!/usr/bin/env python3
"""Process documents with Google Document AI.

Usage:
    python3 scripts/process_single_document.py <file_path> [processor_type]
    
Examples:
    python3 scripts/process_single_document.py document.pdf
    python3 scripts/process_single_document.py document.pdf FORM_PARSER_PROCESSOR
"""

import os
import sys
from pathlib import Path
from google.cloud import documentai_v1 as documentai

# Set credentials
os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = '/Users/jim/Secrets/modular-command-466820-p2-bc0974cd5852.json'

PROJECT_ID = "modular-command-466820-p2"
LOCATION = "us"

def process_document(file_path, processor_type="OCR_PROCESSOR"):
    """Process a document with Document AI.
    
    Args:
        file_path: Path to the document file
        processor_type: Type of Document AI processor to use
        
    Returns:
        str: Extracted text or None if processing fails
    """
    
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
        
        # Determine MIME type based on file extension
        file_ext = Path(file_path).suffix.lower()
        mime_type_map = {
            '.pdf': 'application/pdf',
            '.png': 'image/png',
            '.jpg': 'image/jpeg',
            '.jpeg': 'image/jpeg',
            '.tiff': 'image/tiff',
            '.tif': 'image/tiff',
            '.gif': 'image/gif'
        }
        mime_type = mime_type_map.get(file_ext, 'application/pdf')
        
        # Configure the process request
        request = documentai.ProcessRequest(
            name=processor.name,
            raw_document=documentai.RawDocument(
                content=file_content,
                mime_type=mime_type
            )
        )
        
        # Process the document
        print(f"Processing {file_path}...")
        result = client.process_document(request=request)
        document = result.document
        
        # Extract text
        if document.text:
            print(f"\nExtracted Text ({len(document.text)} characters):")
            print("-" * 50)
            # Print first 500 chars as preview
            preview = document.text[:500] + "..." if len(document.text) > 500 else document.text
            print(preview)
            print("-" * 50)
        
        # Extract entities if available
        if document.entities:
            print(f"\nFound {len(document.entities)} entities:")
            for entity in document.entities[:10]:  # Show first 10
                print(f"  - {entity.type_}: {entity.mention_text}")
        
        # Extract form fields if it's a form parser
        if processor_type == "FORM_PARSER_PROCESSOR" and document.pages:
            print(f"\nForm Fields:")
            for page in document.pages:
                for form_field in page.form_fields:
                    field_name = get_text(form_field.field_name, document)
                    field_value = get_text(form_field.field_value, document)
                    print(f"  {field_name}: {field_value}")
        
        return document.text
        
    except Exception as e:
        print(f"Error processing document: {e}")
        return None

def get_text(doc_element, document):
    """Extract text from a document element."""
    response = ""
    if doc_element.text_anchor:
        for segment in doc_element.text_anchor.text_segments:
            start_index = segment.start_index if segment.start_index else 0
            end_index = segment.end_index
            response += document.text[start_index:end_index]
    return response.strip()

def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return
    
    file_path = sys.argv[1]
    processor_type = sys.argv[2] if len(sys.argv) > 2 else "OCR_PROCESSOR"
    
    if not Path(file_path).exists():
        print(f"File not found: {file_path}")
        return
    
    process_document(file_path, processor_type)

if __name__ == "__main__":
    main()