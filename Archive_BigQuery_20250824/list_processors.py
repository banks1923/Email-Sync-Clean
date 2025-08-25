#!/usr/bin/env python3
"""
List Document AI processors using Python client
"""
from google.cloud import documentai_v1 as documentai

PROJECT_ID = 'litigator-solo'  # Update with your project ID
LOCATION = 'us'

def list_processors():
    """List all Document AI processors"""
    try:
        client = documentai.DocumentProcessorServiceClient()
        parent = f'projects/{PROJECT_ID}/locations/{LOCATION}'
        
        print(f"Listing processors in {parent}...")
        
        response = client.list_processors(parent=parent)
        
        print("\nAvailable Document AI processors:")
        print("=" * 50)
        
        for processor in response:
            print(f"Name: {processor.display_name}")
            print(f"Type: {processor.type_}")
            print(f"ID: {processor.name.split('/')[-1]}")
            print(f"State: {processor.state.name}")
            print("-" * 30)
        
        if not list(response):
            print("No processors found!")
            print("\nTo create an OCR processor:")
            print("1. Go to https://console.cloud.google.com/ai/document-ai/processors")
            print("2. Click 'Create Processor'")
            print("3. Choose 'Document OCR'")
            print("4. Name it and create")
            
    except Exception as e:
        print(f"Error listing processors: {e}")
        print("\nMake sure:")
        print("1. PROJECT_ID is correct")
        print("2. You're authenticated: gcloud auth application-default login")
        print("3. Document AI API is enabled")

if __name__ == "__main__":
    list_processors()