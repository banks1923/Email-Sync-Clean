#!/usr/bin/env python3
"""
Direct OpenAI Whisper API test for the specified files.
"""

import os
import time
import json
from pathlib import Path

try:
    import openai
except ImportError:
    print("❌ OpenAI package not installed. Run: pip install openai")
    exit(1)

def test_direct_openai():
    """Test direct OpenAI API transcription."""
    
    # Files to process
    files_to_process = [
        "/Users/jim/Projects/Email Sync/data/originals/Raw Videos/20250814/08/47 copy.mp4",
        "/Users/jim/Projects/Email Sync/data/originals/Raw Videos/20250814/08/48 copy.mp4"
    ]
    
    print("🎬 Direct OpenAI Whisper API Test")
    print("=" * 50)
    
    # Check API key
    if not os.getenv("OPENAI_API_KEY"):
        print("❌ OPENAI_API_KEY environment variable not set!")
        return
    
    client = openai.OpenAI()
    
    # Legal domain prompt for landlord-tenant matters
    legal_prompt = "The following is a conversation about landlord-tenant matters, property management, lease agreements, rental disputes, and property inspections."
    
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
        
        # Estimate cost (rough calculation based on file size)
        estimated_minutes = size_mb / 2  # Very rough estimate
        estimated_cost = estimated_minutes * 0.006  # $0.006 per minute
        print(f"   Estimated Cost: ${estimated_cost:.4f}")
        
        try:
            start_time = time.time()
            
            with open(file_path, "rb") as audio_file:
                print("   🚀 Calling OpenAI Whisper API...")
                
                response = client.audio.transcriptions.create(
                    model="whisper-1",
                    file=audio_file,
                    response_format="verbose_json",
                    timestamp_granularities=["segment"],
                    prompt=legal_prompt
                )
            
            end_time = time.time()
            processing_time = end_time - start_time
            
            print("   ✅ Success!")
            print(f"   Processing Time: {processing_time:.1f} seconds")
            print(f"   Language: {response.language}")
            print(f"   Text Length: {len(response.text)}")
            print(f"   Segments: {len(response.segments)}")
            
            # Show first 200 characters
            preview = response.text[:200]
            if len(response.text) > 200:
                preview += "..."
            print(f"   Preview: {preview}")
            
            # Save transcription
            output_file = Path(f"/Users/jim/Projects/Email Sync/{file_path_obj.stem}_openai_transcription.txt")
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(f"=== {file_path_obj.name} ===\n")
                f.write("Engine: OpenAI Whisper API\n")
                f.write(f"Language: {response.language}\n")
                f.write(f"Processing Time: {processing_time:.1f}s\n")
                f.write(f"Estimated Cost: ${estimated_cost:.4f}\n")
                f.write(f"Segments: {len(response.segments)}\n")
                f.write("\nFull Transcription:\n")
                f.write(response.text)
                f.write("\n\n=== SEGMENTS ===\n")
                for segment in response.segments:
                    f.write(f"[{segment.start:.1f}s - {segment.end:.1f}s]: {segment.text}\n")
            
            print(f"   💾 Saved to: {output_file}")
            
            # Store result
            results.append({
                "filename": file_path_obj.name,
                "success": True,
                "processing_time": processing_time,
                "text_length": len(response.text),
                "language": response.language,
                "segments": len(response.segments),
                "estimated_cost": estimated_cost,
                "text": response.text
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
    print("=" * 50)
    
    successful = [r for r in results if r["success"]]
    failed = [r for r in results if not r["success"]]
    
    print(f"✅ Successful: {len(successful)}/{len(results)}")
    print(f"❌ Failed: {len(failed)}")
    
    if successful:
        total_time = sum(r["processing_time"] for r in successful)
        total_cost = sum(r["estimated_cost"] for r in successful)
        total_text = sum(r["text_length"] for r in successful)
        
        print("\n📈 Performance:")
        print(f"   Total Processing: {total_time:.1f} seconds")
        print(f"   Average Time: {total_time/len(successful):.1f} seconds/file")
        print(f"   Total Cost: ${total_cost:.4f}")
        print(f"   Total Text: {total_text:,} characters")
        
        print("\n📝 Transcription Previews:")
        for r in successful:
            preview = r["text"][:100].replace('\n', ' ')
            if len(r["text"]) > 100:
                preview += "..."
            print(f"   {r['filename']}: {preview}")
    
    if failed:
        print("\n❌ Failed Files:")
        for fail in failed:
            print(f"   {fail['filename']}: {fail['error']}")
    
    # Save results
    results_file = Path("/Users/jim/Projects/Email Sync/direct_openai_results.json")
    with open(results_file, 'w') as f:
        json.dump({
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "method": "Direct OpenAI API",
            "files_processed": len(results),
            "results": results,
            "summary": {
                "successful": len(successful),
                "failed": len(failed),
                "total_cost": sum(r.get("estimated_cost", 0) for r in successful),
                "total_processing_time": sum(r.get("processing_time", 0) for r in successful)
            }
        }, f, indent=2)
    
    print(f"\n💾 Results saved to: {results_file}")

if __name__ == "__main__":
    test_direct_openai()