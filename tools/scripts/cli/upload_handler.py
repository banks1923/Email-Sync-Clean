#!/usr/bin/env python3
"""
Upload Handler - Modular CLI component for upload operations
Handles: upload, process-uploads, process-pdf-uploads commands
Updated to use direct processing instead of pipeline.
"""

import os
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from shared.simple_upload_processor import get_upload_processor


def upload_pdf(pdf_path, source="upload"):
    """
    Upload single PDF file using direct processing.
    """
    print(f"📄 Uploading PDF: {os.path.basename(pdf_path)}")

    try:
        # Process directly without pipeline
        processor = get_upload_processor()
        result = processor.process_file(Path(pdf_path), source=source)

        if not result["success"]:
            print(f"❌ Processing error: {result['error']}")
            if "quarantine_path" in result:
                print(f"📋 File quarantined: {result['quarantine_path']}")
            return False

        print(f"✅ Processed successfully: {os.path.basename(pdf_path)}")
        print(f"📄 Content ID: {result['content_id']}")
        return True

    except Exception as e:
        print(f"❌ Upload processing error: {e}")
        return False


def upload_directory(dir_path, limit=None):
    """
    Upload all files in directory using direct processing.
    """
    print(f"📁 Scanning directory: {dir_path}")
    print("📋 Using direct processing")

    try:
        processor = get_upload_processor()
        result = processor.process_directory(Path(dir_path), limit=limit)

        if result["success"]:
            print(f"✅ Processed {result['success_count']}/{result['total_files']} files")
            if result["failed_files"]:
                print(f"❌ Failed files: {len(result['failed_files'])}")
                for failed in result["failed_files"][:5]:  # Show first 5 failures
                    print(f"   • {failed['file']}: {failed['error']}")
            return True
        else:
            print(f"❌ Directory processing failed: {result.get('error', 'Unknown error')}")
            return False

    except Exception as e:
        print(f"❌ Directory processing error: {e}")
        return False


def transcribe_file(file_path, source="transcribe"):
    """
    Transcribe audio/video file using direct processing.
    """
    print(f"🎤 Transcribing: {os.path.basename(file_path)}")
    print("⚠️  Transcription service not yet implemented in simple processing")

    # TODO: Implement direct transcription when needed
    # For now, treat as unsupported file type
    return False


def process_uploads():
    """Process all files in upload queue (deprecated - use direct upload)."""
    print("⚠️  Queue-based processing deprecated")
    print("📋 Use 'upload <file>' or 'upload-dir <directory>' for direct processing")
    print("💡 This system now uses direct processing without queues")
    return True


def process_pdf_uploads():
    """Process PDF files specifically (deprecated - use direct upload)."""
    print("⚠️  PDF queue processing deprecated")
    print("📋 Use 'upload <file.pdf>' for direct PDF processing")
    print("💡 PDFs are now processed directly without staging")
    return True
