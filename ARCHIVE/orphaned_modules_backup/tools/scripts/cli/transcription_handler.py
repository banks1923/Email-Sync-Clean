#!/usr/bin/env python3
"""
Transcription Handler - Modular CLI component for transcription operations
Handles: transcribe command
"""

import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

# Import transcription service
from transcription import TranscriptionService


def transcribe_single_file(file_path):
    """Transcribe a single audio/video file"""
    print(f"🎙️ Transcribing: {file_path}")

    try:
        service = TranscriptionService()
        result = service.transcribe_file(file_path)

        if result["success"]:
            data = result["data"]
            metadata = result.get("metadata", {})

            print("✅ Transcription successful!")
            print(f"   🎬 File: {data.get('filename', 'Unknown')}")
            print(f"   ⏱️  Duration: {data.get('duration', 0):.2f}s")
            print(f"   📊 Confidence: {data.get('avg_confidence', 0):.2f}")
            print(f"   🔧 Provider: {metadata.get('provider', 'Unknown')}")
            print(f"   📝 Text length: {len(data.get('text', ''))}")

            # Show preview of transcription
            text = data.get("text", "")
            if text:
                print(f"   📄 Preview: {text[:100]}...")

            return True
        else:
            print(f"❌ Transcription failed: {result['error']}")
            return False

    except Exception as e:
        print(f"❌ Transcription error: {e}")
        return False
