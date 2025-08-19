#!/usr/bin/env python3
"""
Test the new hybrid transcription system on specified files.
"""

import json

# Add project root to path
import sys
import time
from pathlib import Path

from loguru import logger

sys.path.append("/Users/jim/Projects/Email Sync")

def test_hybrid_transcription():
    """Test the hybrid transcription system on the specified files."""
    
    # Files to process
    files_to_process = [
        "/Users/jim/Projects/Email Sync/data/originals/Raw Videos/20250814/08/47 copy.mp4",
        "/Users/jim/Projects/Email Sync/data/originals/Raw Videos/20250814/08/48 copy.mp4"
    ]
    
    print("🎬 Testing Hybrid Transcription System")
    print("=" * 50)
    
    try:
        from transcription.main import TranscriptionService

        # Initialize service
        service = TranscriptionService()
        
        # Get service status
        status = service.get_service_stats()
        print("📊 Service Status:")
        print(f"   Available Providers: {', '.join(status.get('available_providers', []))}")
        print(f"   Current Mode: {status.get('current_mode', 'Unknown')}")
        print(f"   GPU Available: {status.get('gpu_available', False)}")
        
        # Auto-configure to best mode
        print("\n🔧 Auto-configuring transcription mode...")
        config_result = service.auto_configure()
        print(f"   Recommended Mode: {config_result.get('recommended_mode', 'Unknown')}")
        print(f"   Reason: {config_result.get('reason', 'Unknown')}")
        
        # Process each file
        results = []
        
        for i, file_path in enumerate(files_to_process, 1):
            file_path_obj = Path(file_path)
            
            print(f"\n🎤 Processing File {i}/2: {file_path_obj.name}")
            print(f"   File Size: {file_path_obj.stat().st_size / (1024*1024):.1f} MB")
            
            # Estimate cost first
            cost_estimate = service.estimate_cost(file_path)
            if cost_estimate["success"]:
                print(f"   Estimated Cost: ${cost_estimate['estimated_cost']:.4f}")
                print(f"   Estimated Duration: {cost_estimate['estimated_duration']:.1f} seconds")
            
            # Start transcription
            start_time = time.time()
            print("   Starting transcription...")
            
            # Use landlord_tenant context for legal content
            result = service.transcribe_file(file_path, context_type="landlord_tenant")
            
            end_time = time.time()
            processing_time = end_time - start_time
            
            print(f"   Processing Time: {processing_time:.1f} seconds")
            
            if result["success"]:
                data = result["data"]
                print("   ✅ Success!")
                print(f"   Text Length: {len(data.get('text', ''))}")
                print(f"   Segments: {len(data.get('segments', []))}")
                print(f"   Language: {data.get('language', 'unknown')}")
                print(f"   Engine: {data.get('engine', 'unknown')}")
                
                # Show quality stats if available
                if 'stats' in data:
                    stats = data['stats']
                    print(f"   Quality Score: {stats.get('quality_score', 'N/A')}")
                    print(f"   Avg Confidence: {stats.get('avg_confidence', 'N/A')}")
                    
                # Show first 200 characters of transcription
                text_preview = data.get('text', '')[:200]
                if len(data.get('text', '')) > 200:
                    text_preview += "..."
                print(f"   Preview: {text_preview}")
                
                # Store result for summary
                results.append({
                    "filename": file_path_obj.name,
                    "success": True,
                    "processing_time": processing_time,
                    "text_length": len(data.get('text', '')),
                    "segments": len(data.get('segments', [])),
                    "quality_score": data.get('stats', {}).get('quality_score'),
                    "engine": data.get('engine', 'unknown')
                })
                
            else:
                print(f"   ❌ Failed: {result.get('error', 'Unknown error')}")
                results.append({
                    "filename": file_path_obj.name,
                    "success": False,
                    "error": result.get('error', 'Unknown error'),
                    "processing_time": processing_time
                })
        
        # Summary
        print("\n📊 TRANSCRIPTION SUMMARY")
        print("=" * 50)
        
        successful = [r for r in results if r["success"]]
        failed = [r for r in results if not r["success"]]
        
        print(f"✅ Successful: {len(successful)}/{len(results)}")
        print(f"❌ Failed: {len(failed)}")
        
        if successful:
            total_time = sum(r["processing_time"] for r in successful)
            total_text = sum(r["text_length"] for r in successful)
            avg_quality = sum(r.get("quality_score", 0) or 0 for r in successful) / len(successful)
            
            print("📈 Performance Metrics:")
            print(f"   Total Processing Time: {total_time:.1f} seconds")
            print(f"   Average Processing Time: {total_time/len(successful):.1f} seconds/file")
            print(f"   Total Text Generated: {total_text:,} characters")
            print(f"   Average Quality Score: {avg_quality:.3f}")
            
            # Show engines used
            engines = {r["engine"] for r in successful}
            print(f"   Engines Used: {', '.join(engines)}")
        
        if failed:
            print("❌ Failed Files:")
            for fail in failed:
                print(f"   {fail['filename']}: {fail['error']}")
        
        # Save detailed results
        output_file = Path("/Users/jim/Projects/Email Sync/hybrid_test_results.json")
        with open(output_file, 'w'):
            json.dump({
                "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
                "service_config": config_result,
                "files_processed": len(results),
                "results": results,
                "summary": {
                    "successful": len(successful),
                    "failed": len(failed),
                    "total_processing_time": sum(r["processing_time"] for r in results),
                    "average_quality_score": avg_quality if successful else 0
                }
            }, indent=2)
        
        print(f"\n💾 Detailed results saved to: {output_file}")
        
    except Exception as e:
        logger.error(f"Test failed with error: {e}")
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_hybrid_transcription()