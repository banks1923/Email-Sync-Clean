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

# Import service modules
from pdf import PDFService
from transcription import TranscriptionService
from infrastructure.pipelines.data_pipeline import DataPipelineOrchestrator

# Import AnalogDBProcessor for new routing
try:
    from shared.analog_db_processor import AnalogDBProcessor
    ANALOG_DB_AVAILABLE = True
except ImportError:
    ANALOG_DB_AVAILABLE = False
    print("⚠️  AnalogDBProcessor not available - using legacy pipeline only")


def get_upload_mode():
    """Get upload routing mode from environment or default to 'analog'."""
    import os
    mode = os.environ.get("UPLOAD_MODE", "analog").lower()
    if mode not in ["analog", "pipeline", "hybrid"]:
        print(f"⚠️  Unknown UPLOAD_MODE '{mode}', defaulting to 'analog'")
        return "analog"
    return mode


def upload_pdf(pdf_path, source="upload", storage_mode=None):
    """Upload single PDF file with configurable routing to AnalogDB or pipeline."""
    print(f"📄 Uploading PDF: {os.path.basename(pdf_path)}")

    # Determine storage mode
    mode = storage_mode or get_upload_mode()
    
    try:
        success = False
        
        if mode == "analog" and ANALOG_DB_AVAILABLE:
            success = _upload_to_analog_db(pdf_path, "pdf", source)
        elif mode == "pipeline":
            success = _upload_to_pipeline(pdf_path, source)
        elif mode == "hybrid":
            # Try analog first, fallback to pipeline
            if ANALOG_DB_AVAILABLE:
                success = _upload_to_analog_db(pdf_path, "pdf", source)
                if not success:
                    print("⚠️  Analog DB upload failed, falling back to pipeline")
                    success = _upload_to_pipeline(pdf_path, source)
            else:
                success = _upload_to_pipeline(pdf_path, source)
        else:
            # Fallback to pipeline if analog not available
            if not ANALOG_DB_AVAILABLE:
                print("⚠️  AnalogDB not available, using pipeline")
            success = _upload_to_pipeline(pdf_path, source)
        
        return success

    except Exception as e:
        print(f"❌ Upload error: {e}")
        return False


def _upload_to_analog_db(file_path, doc_type, source):
    """Upload file to AnalogDB system."""
    try:
        processor = AnalogDBProcessor()
        
        result = processor.process_document(
            file_path=file_path,
            doc_type=doc_type,
            metadata={"source": source, "upload_method": "analog_db"}
        )
        
        if result["success"]:
            print(f"✅ Stored in AnalogDB: {os.path.basename(result['target_path'])}")
            print(f"📍 Location: {result['target_path']}")
            print(f"🆔 Document ID: {result['doc_id']}")
            return True
        else:
            print(f"❌ AnalogDB error: {result['error']}")
            return False
            
    except Exception as e:
        print(f"❌ AnalogDB upload error: {e}")
        return False


def _upload_to_pipeline(file_path, source):
    """Upload file to legacy pipeline system."""
    try:
        # Add to pipeline (copy mode to preserve original)
        pipeline = DataPipelineOrchestrator()
        pipeline_result = pipeline.add_to_raw(file_path, copy=True)
        
        if not pipeline_result["success"]:
            print(f"❌ Pipeline error: {pipeline_result['error']}")
            return False
            
        print(f"✅ Added to pipeline: {os.path.basename(pipeline_result['path'])}")
        print("📋 File queued for processing through pipeline")
        return True
        
    except Exception as e:
        print(f"❌ Pipeline upload error: {e}")
        return False


def upload_directory(dir_path, limit=None, storage_mode=None):
    """Upload all PDFs in directory with configurable routing."""
    print(f"📁 Scanning directory: {dir_path}")
    
    mode = storage_mode or get_upload_mode()
    print(f"📋 Using storage mode: {mode}")

    try:
        # Use AnalogDB for directory uploads if available and configured
        if mode in ["analog", "hybrid"] and ANALOG_DB_AVAILABLE:
            return _upload_directory_analog_db(dir_path, limit, mode)
        else:
            # Fallback to PDFService for legacy pipeline
            if not ANALOG_DB_AVAILABLE and mode == "analog":
                print("⚠️  AnalogDB not available, using pipeline")
            return _upload_directory_pipeline(dir_path, limit)

    except Exception as e:
        print(f"❌ Directory upload error: {e}")
        return False


def _upload_directory_analog_db(dir_path, limit, mode):
    """Upload directory contents using AnalogDB routing."""
    from pathlib import Path
    
    dir_path = Path(dir_path)
    if not dir_path.exists():
        print(f"❌ Directory not found: {dir_path}")
        return False
    
    # Find PDF files
    pdf_files = list(dir_path.glob("*.pdf"))
    if limit:
        pdf_files = pdf_files[:limit]
    
    stats = {
        "total_files": len(pdf_files),
        "success_count": 0,
        "failed_count": 0,
        "failed_files": []
    }
    
    print(f"📄 Found {len(pdf_files)} PDF files")
    
    for pdf_file in pdf_files:
        print(f"\n📄 Processing: {pdf_file.name}")
        success = upload_pdf(str(pdf_file), source="directory", storage_mode=mode)
        
        if success:
            stats["success_count"] += 1
        else:
            stats["failed_count"] += 1
            stats["failed_files"].append({
                "file": pdf_file.name, 
                "error": "Upload failed"
            })
    
    # Print summary
    print("\n📊 Upload Results:")
    print(f"   📄 Total files: {stats['total_files']}")
    print(f"   ✅ Successful: {stats['success_count']}")
    print(f"   ❌ Failed: {stats['failed_count']}")
    
    if stats["failed_files"]:
        print("\n❌ Failed files:")
        for failure in stats["failed_files"]:
            print(f"   • {failure['file']}: {failure['error']}")
    
    return stats["failed_count"] == 0


def _upload_directory_pipeline(dir_path, limit):
    """Upload directory using legacy pipeline."""
    service = PDFService()
    result = service.upload_directory(dir_path, limit)

    if result["success"]:
        stats = result["results"]
        print("\n📊 Upload Results:")
        print(f"   📄 Total files: {stats['total_files']}")
        print(f"   ✅ Successful: {stats['success_count']}")
        print(f"   ⏭️  Skipped: {stats['skipped_count']}")
        print(f"   ❌ Failed: {stats['failed_count']}")

        if stats["failed_files"]:
            print("\n❌ Failed files:")
            for failure in stats["failed_files"]:
                print(f"   • {failure['file']}: {failure['error']}")

        return stats["failed_count"] == 0
    else:
        print(f"❌ Directory upload failed: {result['error']}")
        return False


def process_uploads():
    """Process videos from uploads directory"""
    print("🎙️ Processing videos from uploads directory...")

    try:
        service = TranscriptionService()
        result = service.process_uploads_directory()

        if result["success"]:
            metadata = result.get("metadata", {})
            print("\n📊 Processing Results:")
            print(f"   🎬 Total files: {metadata.get('total_files', 0)}")
            print(f"   ✅ Successful: {metadata.get('successful', 0)}")
            print(f"   ❌ Failed: {metadata.get('failed', 0)}")
            print(f"   📁 Input: {metadata.get('input_directory', 'Unknown')}")
            print(f"   📁 Output: {metadata.get('output_directory', 'Unknown')}")

            if metadata.get("processed_files"):
                print("\n✅ Processed files moved to:")
                for file_path in metadata["processed_files"]:
                    print(f"   • {file_path}")

            if metadata.get("failed_files"):
                print("\n❌ Failed files:")
                for failure in metadata["failed_files"]:
                    print(f"   • {failure['file']}: {failure['error']}")

            return metadata.get("failed", 0) == 0
        else:
            print(f"❌ Processing failed: {result['error']}")
            return False

    except Exception as e:
        print(f"❌ Processing error: {e}")
        return False


def process_pdf_uploads():
    """Process PDFs from uploads directory and move to processed"""
    print("📄 Processing PDFs from uploads directory...")

    try:
        service = PDFService()
        result = service.process_uploads_directory()

        if result["success"]:
            data = result.get("data", {})
            metadata = result.get("metadata", {})

            print("\n📊 Processing Results:")
            print(f"   📄 Total files: {data.get('total_files', 0)}")
            print(f"   ✅ Successful: {data.get('success_count', 0)}")
            print(f"   ⏭️  Skipped: {data.get('skipped_count', 0)}")
            print(f"   ❌ Failed: {data.get('failed_count', 0)}")
            print(f"   📁 Input: {metadata.get('input_directory', 'Unknown')}")
            print(f"   📁 Output: {metadata.get('output_directory', 'Unknown')}")

            if data.get("processed_files"):
                print("\n✅ Processed files moved to:")
                for file_path in data["processed_files"]:
                    print(f"   • {os.path.basename(file_path)}")

            if data.get("failed_files"):
                print("\n❌ Failed files:")
                for failure in data["failed_files"]:
                    print(f"   • {failure['file']}: {failure['error']}")

            return data.get("failed_count", 0) == 0
        else:
            print(f"❌ Processing failed: {result['error']}")
            return False

    except Exception as e:
        print(f"❌ Processing error: {e}")
        return False
