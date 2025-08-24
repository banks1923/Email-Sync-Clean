#!/usr/bin/env python3
"""Simple CLI for Document AI operations."""

import argparse
import os
from pathlib import Path
from process_document import process_document

def main():
    parser = argparse.ArgumentParser(description="Document AI CLI")
    parser.add_argument("command", choices=["process", "batch"], help="Command to run")
    parser.add_argument("path", help="File or directory path")
    parser.add_argument("--output", "-o", help="Output directory for batch processing")
    parser.add_argument("--type", default="OCR_PROCESSOR", help="Processor type")
    
    args = parser.parse_args()
    
    if args.command == "process":
        if not Path(args.path).exists():
            print(f"File not found: {args.path}")
            return
        
        print(f"Processing {args.path} with Document AI...")
        process_document(args.path, args.type)
    
    elif args.command == "batch":
        from batch_process import batch_process
        batch_process(args.path, args.output)

if __name__ == "__main__":
    main()