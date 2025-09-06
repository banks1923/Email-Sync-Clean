#!/usr/bin/env python3
"""
Process Handler - Modular CLI component for processing operations
Handles: process, embed commands
"""

import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

# Import service locator
from tools.scripts.cli.service_locator import get_locator


def process_emails(limit=None):
    """
    Process emails to generate AI embeddings for semantic search.
    """
    print("🤖 Processing emails for AI-powered semantic search...")
    locator = get_locator()

    try:
        service = locator.get_vector_service()

        if hasattr(service, "validation_result") and not service.validation_result.get("success"):
            print(f"❌ Vector service error: {service.validation_result['error']}")
            return False

        print("🔄 Generating Legal BERT embeddings...")
        result = service.process_emails(limit=limit)

        if result["success"]:
            processed = result.get("processed", 0)
            skipped = result.get("skipped", 0)
            print("✅ AI Processing Complete!")
            print(f"   📧 Processed: {processed} emails")
            print(f"   ⏭️  Skipped: {skipped} emails (already processed)")
            print("   🧠 Model: Legal BERT (1024-dimensional embeddings)")
            return True
        else:
            print(f"❌ Processing failed: {result['error']}")
            return False

    except Exception as e:
        print(f"❌ Processing error: {e}")
        return False


def embed_content(content_type="transcript", limit=None):
    """
    Generate embeddings for specific content types.
    """
    content_icons = {"transcript": "🎙️", "transcription": "🎙️", "pdf": "📄", "document": "📄"}
    icon = content_icons.get(content_type, "📄")
    locator = get_locator()

    print(f"{icon} Processing {content_type}s for AI-powered semantic search...")

    try:
        service = locator.get_vector_service()

        if hasattr(service, "validation_result") and not service.validation_result.get("success"):
            print(f"❌ Vector service error: {service.validation_result['error']}")
            return False

        print("🔄 Generating Legal BERT embeddings...")
        result = service.process_content(content_type=content_type, limit=limit)

        if result["success"]:
            processed = result.get("processed", 0)
            failed = result.get("failed", 0)
            total = result.get(f"total_{content_type}s", processed + failed)

            print("✅ AI Processing Complete!")
            print(f"   {icon} Total: {total} {content_type}s")
            print(f"   ✅ Processed: {processed} {content_type}s")
            print(f"   ❌ Failed: {failed} {content_type}s")
            print("   🧠 Model: Legal BERT (1024-dimensional embeddings)")
            print(f"   🧠 Provider: {result.get('provider', 'legal_bert')}")
            return True
        else:
            print(f"❌ Processing failed: {result['error']}")
            return False

    except Exception as e:
        print(f"❌ Processing error: {e}")
        return False
