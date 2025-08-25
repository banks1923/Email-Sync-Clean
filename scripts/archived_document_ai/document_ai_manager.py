#!/usr/bin/env python3
"""Document AI Manager - Unified CLI for Google Document AI operations.

Usage:
    python3 scripts/document_ai_manager.py <command> [options]
    
Commands:
    process <file>           - Process a single document
    batch <directory>        - Process all PDFs in a directory
    test                     - Test Document AI connection
    list-processors          - List available processors
    
Examples:
    python3 scripts/document_ai_manager.py test
    python3 scripts/document_ai_manager.py process document.pdf
    python3 scripts/document_ai_manager.py batch data/Stoneman_dispute/user_data --output ./extracted
"""

import argparse
import os
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent))

from scripts.process_single_document import process_document
from scripts.batch_process_documents import batch_process
from scripts.test_document_ai_connection import test_document_ai_auth

def list_processors():
    """
    List available Document AI processors.
    """
    from google.cloud import documentai_v1 as documentai
    
    os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = '/Users/jim/Secrets/modular-command-466820-p2-bc0974cd5852.json'
    
    client = documentai.DocumentProcessorServiceClient()
    parent = f"projects/modular-command-466820-p2/locations/us"
    
    print("Available Document AI Processors:")
    print("-" * 50)
    
    processors = client.list_processors(parent=parent)
    for processor in processors:
        print(f"  • {processor.display_name}")
        print(f"    Type: {processor.type_}")
        print(f"    State: {processor.state}")
        print()
    
    if not processors:
        print("  No processors found. They will be created automatically when needed.")

def main():
    parser = argparse.ArgumentParser(
        description="Document AI Manager",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )
    
    parser.add_argument("command", 
                        choices=["process", "batch", "test", "list-processors"],
                        help="Command to run")
    parser.add_argument("path", nargs="?", help="File or directory path")
    parser.add_argument("--output", "-o", help="Output directory for batch processing")
    parser.add_argument("--type", default="OCR_PROCESSOR", 
                        help="Processor type (OCR_PROCESSOR, FORM_PARSER_PROCESSOR, etc.)")
    parser.add_argument("--recursive", "-r", action="store_true",
                        help="Process subdirectories recursively")
    
    args = parser.parse_args()
    
    if args.command == "test":
        print("🧪 Testing Document AI Connection...\n")
        test_document_ai_auth()
    
    elif args.command == "list-processors":
        list_processors()
    
    elif args.command == "process":
        if not args.path:
            print("❌ Error: Please provide a file path")
            print("Example: python3 scripts/document_ai_manager.py process document.pdf")
            return
        
        if not Path(args.path).exists():
            print(f"❌ File not found: {args.path}")
            return
        
        print(f"📄 Processing {args.path} with Document AI...")
        process_document(args.path, args.type)
    
    elif args.command == "batch":
        if not args.path:
            print("❌ Error: Please provide a directory path")
            print("Example: python3 scripts/document_ai_manager.py batch ./documents")
            return
        
        print(f"📁 Batch processing directory: {args.path}")
        batch_process(args.path, args.output, args.recursive)

if __name__ == "__main__":
    main()