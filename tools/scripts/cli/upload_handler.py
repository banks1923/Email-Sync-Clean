#!/usr/bin/env python3
"""
Upload Handler - Modular CLI component for upload operations
Handles: upload, process-uploads, process-pdf-uploads commands
"""

import os
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from infrastructure.pipelines.data_pipeline import DataPipelineOrchestrator

# Import service modules
from pdf.wiring import build_pdf_service


def upload_pdf(pdf_path, source="upload"):
    """Upload single PDF file using data pipeline."""
    print(f"📄 Uploading PDF: {os.path.basename(pdf_path)}")
    
    try:
        # Add to pipeline (copy mode to preserve original)
        pipeline = DataPipelineOrchestrator()
        pipeline_result = pipeline.add_to_raw(pdf_path, copy=True)
        
        if not pipeline_result["success"]:
            print(f"❌ Pipeline error: {pipeline_result['error']}")
            return False
            
        print(f"✅ Added to pipeline: {os.path.basename(pipeline_result['path'])}")
        print("📋 File queued for processing through pipeline")
        return True
        
    except Exception as e:
        print(f"❌ Pipeline upload error: {e}")
        return False


def upload_directory(dir_path, limit=None):
    """Upload all PDFs in directory using pipeline."""
    print(f"📁 Scanning directory: {dir_path}")
    print("📋 Using pipeline storage")

    try:
        service = build_pdf_service()
        result = service.upload_directory(dir_path, limit)

        if result["success"]:
            stats = result["results"]
            print(f"✅ Uploaded {stats['success_count']}/{stats['total_files']} files")
            if stats["failed_files"]:
                print(f"❌ Failed files: {stats['failed_files']}")
            return True
        else:
            print(f"❌ Upload failed: {result['error']}")
            return False

    except Exception as e:
        print(f"❌ Directory upload error: {e}")
        return False


def transcribe_file(file_path, source="transcribe"):
    """Transcribe audio/video file."""
    print(f"🎤 Transcribing: {os.path.basename(file_path)}")

    try:
        service = TranscriptionService()
        result = service.transcribe_file(str(file_path), metadata={"source": source})

        if result["success"]:
            print("✅ Transcription complete")
            print(f"📄 Content ID: {result['content_id']}")
            print("📝 Transcript saved to database")
            return True
        else:
            print(f"❌ Transcription failed: {result['error']}")
            return False

    except Exception as e:
        print(f"❌ Transcription error: {e}")
        return False


def process_uploads():
    """Process all files in upload queue."""
    print("⚙️  Processing upload queue...")

    try:
        service = build_pdf_service()
        # Process all pending uploads
        result = service.process_upload_queue()

        if result["success"]:
            stats = result["stats"]
            print(f"✅ Processed {stats['processed']}/{stats['total']} files")
            if stats["errors"]:
                print(f"❌ {stats['errors']} errors occurred")
            return True
        else:
            print(f"❌ Processing failed: {result['error']}")
            return False

    except Exception as e:
        print(f"❌ Queue processing error: {e}")
        return False


def process_pdf_uploads():
    """Process PDF files specifically."""
    print("📄 Processing PDF uploads...")

    try:
        pipeline = DataPipelineOrchestrator()
        # Process staged PDFs
        result = pipeline.process_staged()

        if result["success"]:
            print(f"✅ Processed {result['processed']} PDFs")
            if result.get("errors"):
                print(f"❌ {len(result['errors'])} errors occurred")
            return True
        else:
            print(f"❌ PDF processing failed: {result['error']}")
            return False

    except Exception as e:
        print(f"❌ PDF processing error: {e}")
        return False