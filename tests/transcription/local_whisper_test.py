#!/usr/bin/env python3
"""
Test local Whisper with small model on the specified files.
"""

# Add project root to path
import sys
import time
from pathlib import Path

sys.path.append("/Users/jim/Projects/Email Sync")

def test_local_whisper():
    """Test local Whisper small model."""
    
    # Files to process
    files_to_process = [
        "/Users/jim/Projects/Email Sync/data/originals/Raw Videos/20250814/08/47 copy.mp4",
        "/Users/jim/Projects/Email Sync/data/originals/Raw Videos/20250814/08/48 copy.mp4"
    ]
    
    print("🎬 Local Whisper Small Model Test")
    print("=" * 50)
    
    try:
        import whisper
    except ImportError:
        print("❌ Whisper not installed. Run: pip install openai-whisper")
        return
    
    # Load small model (CPU only, no MPS issues)
    print("📥 Loading Whisper 'small' model...")
    start_load = time.time()
    model = whisper.load_model("small", device="cpu")  # Force CPU to avoid MPS issues
    load_time = time.time() - start_load
    print(f"✅ Model loaded in {load_time:.1f} seconds")
    
    results = []
    
    for i, file_path in enumerate(files_to_process, 1):
        file_path_obj = Path(file_path)
        
        if not file_path_obj.exists():
            print(f"❌ File not found: {file_path}")
            continue
            
        print(f"\n🎤 Processing File {i}/2: {file_path_obj.name}")
        
        # Check file size
        size_mb = file_path_obj.stat().st_size / (1024 * 1024)
        print(f"   File Size: {size_mb:.1f} MB")
        
        try:
            start_time = time.time()
            
            print("   🚀 Running local Whisper (small model, CPU)...")
            
            # Local Whisper with anti-hallucination settings
            result = model.transcribe(
                str(file_path),
                # Anti-hallucination settings:
                verbose=False,
                condition_on_previous_text=False,  # Prevent feedback loops
                compression_ratio_threshold=2.4,   # Quality control
                logprob_threshold=-1.0,           # Confidence threshold
                no_speech_threshold=0.6,          # Better silence detection
                temperature=0.0,                  # Deterministic
                # NO INITIAL PROMPT - avoid contamination
            )
            
            end_time = time.time()
            processing_time = end_time - start_time
            
            print("   ✅ Success!")
            print(f"   Processing Time: {processing_time:.1f} seconds")
            print(f"   Language: {result.get('language', 'unknown')}")
            print(f"   Text Length: {len(result['text'])}")
            print(f"   Segments: {len(result.get('segments', []))}")
            
            # Apply basic filtering
            filtered_text = filter_repetitions(result['text'])
            
            print("   After Filtering:")
            print(f"   Text Length: {len(filtered_text)}")
            
            # Show preview
            preview = filtered_text[:200]
            if len(filtered_text) > 200:
                preview += "..."
            print(f"   Preview: {preview}")
            
            # Save transcription
            output_file = Path(f"/Users/jim/Projects/Email Sync/{file_path_obj.stem}_local_small_transcription.txt")
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(f"=== {file_path_obj.name} (LOCAL WHISPER SMALL) ===\n")
                f.write("Engine: Whisper Small (CPU)\n")
                f.write(f"Language: {result.get('language', 'unknown')}\n")
                f.write(f"Processing Time: {processing_time:.1f}s\n")
                f.write(f"Original Segments: {len(result.get('segments', []))}\n")
                f.write("\nFiltered Transcription:\n")
                f.write(filtered_text)
                f.write("\n\n=== ORIGINAL (for comparison) ===\n")
                f.write(result['text'])
                f.write("\n\n=== SEGMENTS ===\n")
                for segment in result.get('segments', []):
                    f.write(f"[{segment['start']:.1f}s - {segment['end']:.1f}s]: {segment['text']}\n")
            
            print(f"   💾 Saved to: {output_file}")
            
            # Store result
            results.append({
                "filename": file_path_obj.name,
                "success": True,
                "processing_time": processing_time,
                "original_text_length": len(result['text']),
                "filtered_text_length": len(filtered_text),
                "segments": len(result.get('segments', [])),
                "language": result.get('language', 'unknown'),
                "filtered_text": filtered_text
            })
            
        except Exception as e:
            print(f"   ❌ Failed: {e}")
            results.append({
                "filename": file_path_obj.name,
                "success": False,
                "error": str(e)
            })
    
    # Summary
    print("\n📊 LOCAL WHISPER RESULTS")
    print("=" * 50)
    
    successful = [r for r in results if r["success"]]
    failed = [r for r in results if not r["success"]]
    
    print(f"✅ Successful: {len(successful)}/{len(results)}")
    print(f"❌ Failed: {len(failed)}")
    print(f"⏱️  Model Load Time: {load_time:.1f} seconds")
    
    if successful:
        total_time = sum(r["processing_time"] for r in successful)
        print("\n📈 Performance:")
        print(f"   Total Processing: {total_time:.1f} seconds")
        print(f"   Average Time: {total_time/len(successful):.1f} seconds/file")
        print("   Model: Whisper Small (CPU)")
        
        print("\n📝 Local Whisper Transcriptions:")
        for r in successful:
            preview = r["filtered_text"][:150].replace('\n', ' ')
            if len(r["filtered_text"]) > 150:
                preview += "..."
            print(f"   {r['filename']}: {preview}")
    
    if failed:
        print("\n❌ Failed Files:")
        for fail in failed:
            print(f"   {fail['filename']}: {fail['error']}")

def filter_repetitions(text):
    """Basic repetition filtering."""
    if not text:
        return text
    
    # Split into sentences
    sentences = [s.strip() for s in text.split('.') if s.strip()]
    
    # Remove exact duplicates and excessive repetition
    filtered_sentences = []
    for sentence in sentences:
        # Skip if this exact sentence was just added
        if filtered_sentences and sentence.lower() == filtered_sentences[-1].lower():
            continue
        
        # Skip sentences that are just repeated words
        words = sentence.split()
        if len(words) > 3 and len({word.lower() for word in words}) <= 2:
            continue  # Too repetitive
            
        filtered_sentences.append(sentence)
    
    return '. '.join(filtered_sentences).strip()

if __name__ == "__main__":
    test_local_whisper()