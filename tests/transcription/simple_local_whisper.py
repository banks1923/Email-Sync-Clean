#!/usr/bin/env python3
"""
Simple local Whisper test - minimal settings.
"""

import time
from pathlib import Path


def test_simple_local_whisper():
    """Test local Whisper with minimal settings."""
    
    # Files to process
    files_to_process = [
        "/Users/jim/Projects/Email Sync/data/originals/Raw Videos/20250814/08/47 copy.mp4",
        "/Users/jim/Projects/Email Sync/data/originals/Raw Videos/20250814/08/48 copy.mp4"
    ]
    
    print("🎬 Simple Local Whisper Test")
    print("=" * 40)
    
    try:
        import whisper
    except ImportError:
        print("❌ Whisper not installed. Run: pip install openai-whisper")
        return
    
    # Load small model
    print("📥 Loading Whisper 'small' model...")
    model = whisper.load_model("small")
    print("✅ Model loaded")
    
    for i, file_path in enumerate(files_to_process, 1):
        file_path_obj = Path(file_path)
        
        print(f"\n🎤 File {i}/2: {file_path_obj.name}")
        
        try:
            start_time = time.time()
            
            # Simple transcribe - no extra settings
            result = model.transcribe(str(file_path))
            
            processing_time = time.time() - start_time
            
            print(f"   Time: {processing_time:.1f}s")
            print(f"   Language: {result.get('language', 'unknown')}")
            print(f"   Text: {result['text']}")
            
            # Save to file
            output_file = Path(f"/Users/jim/Projects/Email Sync/{file_path_obj.stem}_simple_local.txt")
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(f"=== {file_path_obj.name} (SIMPLE LOCAL) ===\n")
                f.write(f"Language: {result.get('language', 'unknown')}\n")
                f.write(f"Time: {processing_time:.1f}s\n\n")
                f.write(result['text'])
            
            print(f"   💾 Saved: {output_file}")
            
        except Exception as e:
            print(f"   ❌ Failed: {e}")

if __name__ == "__main__":
    test_simple_local_whisper()