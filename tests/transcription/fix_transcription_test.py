#!/usr/bin/env python3
"""
Fixed OpenAI Whisper API test with anti-hallucination settings.
"""

import os
import time
from pathlib import Path

try:
    import openai
except ImportError:
    print("❌ OpenAI package not installed. Run: pip install openai")
    exit(1)

def test_fixed_transcription():
    """Test OpenAI API with anti-hallucination settings."""
    
    # Files to process
    files_to_process = [
        "/Users/jim/Projects/Email Sync/data/originals/Raw Videos/20250814/08/47 copy.mp4",
        "/Users/jim/Projects/Email Sync/data/originals/Raw Videos/20250814/08/48 copy.mp4"
    ]
    
    print("🎬 Fixed OpenAI Whisper API Test (Anti-Hallucination)")
    print("=" * 60)
    
    # Check API key
    if not os.getenv("OPENAI_API_KEY"):
        print("❌ OPENAI_API_KEY environment variable not set!")
        return
    
    client = openai.OpenAI()
    
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
        
        if size_mb > 25:
            print("   ❌ File too large for OpenAI API (25MB limit)")
            continue
        
        try:
            start_time = time.time()
            
            with open(file_path, "rb") as audio_file:
                print("   🚀 Calling OpenAI API with anti-hallucination settings...")
                
                # FIXED SETTINGS - No prompt, anti-hallucination parameters
                response = client.audio.transcriptions.create(
                    model="whisper-1",
                    file=audio_file,
                    response_format="verbose_json",
                    timestamp_granularities=["segment"],
                    # NO PROMPT - this was causing hallucinations
                    # Anti-hallucination settings:
                    temperature=0.0,  # Deterministic output
                )
            
            end_time = time.time()
            processing_time = end_time - start_time
            
            print("   ✅ Success!")
            print(f"   Processing Time: {processing_time:.1f} seconds")
            print(f"   Language: {response.language}")
            print(f"   Text Length: {len(response.text)}")
            print(f"   Segments: {len(response.segments)}")
            
            # Apply basic repetition filtering
            filtered_text = filter_repetitions(response.text)
            filtered_segments = filter_segment_repetitions(response.segments)
            
            print("   After Filtering:")
            print(f"   Text Length: {len(filtered_text)}")
            print(f"   Segments: {len(filtered_segments)}")
            
            # Show first 200 characters
            preview = filtered_text[:200]
            if len(filtered_text) > 200:
                preview += "..."
            print(f"   Preview: {preview}")
            
            # Save transcription
            output_file = Path(f"/Users/jim/Projects/Email Sync/{file_path_obj.stem}_fixed_transcription.txt")
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(f"=== {file_path_obj.name} (FIXED) ===\n")
                f.write("Engine: OpenAI Whisper API (Anti-Hallucination)\n")
                f.write(f"Language: {response.language}\n")
                f.write(f"Processing Time: {processing_time:.1f}s\n")
                f.write(f"Original Segments: {len(response.segments)}\n")
                f.write(f"Filtered Segments: {len(filtered_segments)}\n")
                f.write("\nFiltered Transcription:\n")
                f.write(filtered_text)
                f.write("\n\n=== ORIGINAL (for comparison) ===\n")
                f.write(response.text)
                f.write("\n\n=== FILTERED SEGMENTS ===\n")
                for segment in filtered_segments:
                    f.write(f"[{segment.start:.1f}s - {segment.end:.1f}s]: {segment.text}\n")
            
            print(f"   💾 Saved to: {output_file}")
            
            # Store result
            results.append({
                "filename": file_path_obj.name,
                "success": True,
                "processing_time": processing_time,
                "original_text_length": len(response.text),
                "filtered_text_length": len(filtered_text),
                "original_segments": len(response.segments),
                "filtered_segments": len(filtered_segments),
                "language": response.language,
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
    print("\n📊 RESULTS SUMMARY")
    print("=" * 60)
    
    successful = [r for r in results if r["success"]]
    failed = [r for r in results if not r["success"]]
    
    print(f"✅ Successful: {len(successful)}/{len(results)}")
    print(f"❌ Failed: {len(failed)}")
    
    if successful:
        print("\n📈 Quality Improvements:")
        for r in successful:
            reduction = (r["original_text_length"] - r["filtered_text_length"]) / r["original_text_length"] * 100
            print(f"   {r['filename']}:")
            print(f"     Original: {r['original_text_length']} chars, {r['original_segments']} segments")
            print(f"     Filtered: {r['filtered_text_length']} chars, {r['filtered_segments']} segments")
            print(f"     Improvement: {reduction:.1f}% reduction in noise")
        
        print("\n📝 Cleaned Transcriptions:")
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

def filter_segment_repetitions(segments):
    """Filter repetitive segments."""
    if not segments:
        return segments
    
    filtered = []
    for segment in segments:
        text = segment.text.strip()
        
        # Skip empty segments
        if not text:
            continue
            
        # Skip very repetitive segments
        words = text.split()
        if len(words) > 3:
            unique_words = {word.lower() for word in words}
            if len(unique_words) <= 2:  # Too repetitive
                continue
        
        # Skip if identical to previous segment
        if filtered and text.lower() == filtered[-1].text.strip().lower():
            continue
            
        filtered.append(segment)
    
    return filtered

if __name__ == "__main__":
    test_fixed_transcription()