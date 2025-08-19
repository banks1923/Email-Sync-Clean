#!/usr/bin/env python3
"""
OpenAI Whisper API Quick Transcription Script
Process specific files first with auto-proceed
"""

import csv
import json
import subprocess
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any

try:
    import openai
    from tqdm import tqdm
except ImportError as e:
    print(f"Missing dependency: {e}")
    print("Install with: pip install openai tqdm")
    exit(1)

class OpenAIBatchTranscriber:
    """High-speed batch transcription using OpenAI Whisper API."""
    
    def __init__(self):
        self.client = openai.OpenAI()
        self.total_cost = 0.0
        self.rate_per_minute = 0.006  # $0.006 per minute
        self.max_workers = 3  # Reduced for stability
        self.results = []
        
        # Legal domain prompts
        self.legal_prompts = {
            "landlord_tenant": "The following is a conversation about landlord-tenant matters, property management, lease agreements, rental disputes, and property inspections.",
            "property_inspection": "The following is a conversation about property inspection, maintenance, repairs, building conditions, and mold testing.",
            "legal_general": "The following is a legal conversation involving contracts, agreements, documentation, and legal procedures."
        }
    
    def get_audio_duration(self, file_path: Path) -> float:
        """Get audio duration using FFprobe."""
        try:
            cmd = [
                "ffprobe", "-v", "quiet", "-print_format", "json",
                "-show_format", str(file_path)
            ]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            if result.returncode == 0:
                data = json.loads(result.stdout)
                return float(data.get("format", {}).get("duration", 0))
        except Exception as e:
            print(f"Warning: Could not get duration for {file_path.name}: {e}")
        return 0.0
    
    def determine_context_type(self, file_path: Path) -> str:
        """Determine the best context type based on file path and name."""
        path_str = str(file_path).lower()
        name = file_path.name.lower()
        
        if "mold" in name or "sally" in name:
            return "property_inspection"
        elif "brad" in name:
            return "legal_general"
        elif any(term in path_str for term in ["property", "inspection", "test"]):
            return "property_inspection"
        else:
            return "landlord_tenant"
    
    def transcribe_file(self, file_path: Path) -> dict[str, Any]:
        """Transcribe a single file using OpenAI Whisper API."""
        context_type = self.determine_context_type(file_path)
        prompt = self.legal_prompts.get(context_type, self.legal_prompts["landlord_tenant"])
        
        try:
            with open(file_path, "rb") as audio_file:
                # Get duration for cost calculation
                duration = self.get_audio_duration(file_path)
                
                # Call OpenAI Whisper API with legal context
                response = self.client.audio.transcriptions.create(
                    model="whisper-1",
                    file=audio_file,
                    response_format="verbose_json",
                    timestamp_granularities=["segment"],
                    prompt=prompt
                )
                
                # Calculate cost
                cost = duration * self.rate_per_minute / 60
                self.total_cost += cost
                
                # Process segments
                segments = []
                for segment in response.segments:
                    segments.append({
                        "start": segment.start,
                        "end": segment.end,
                        "text": segment.text.strip(),
                        "avg_logprob": getattr(segment, 'avg_logprob', -1.0),
                        "no_speech_prob": getattr(segment, 'no_speech_prob', 0.0)
                    })
                
                result = {
                    "filename": file_path.name,
                    "file_path": str(file_path),
                    "text": response.text,
                    "language": response.language,
                    "duration": duration,
                    "cost": cost,
                    "context_type": context_type,
                    "segments": segments,
                    "engine": "openai_whisper_api",
                    "word_count": len(response.text.split()),
                    "speech_rate": len(response.text.split()) / (duration / 60) if duration > 0 else 0,
                    "success": True
                }
                
                return result
                
        except Exception as e:
            return {
                "filename": file_path.name,
                "file_path": str(file_path),
                "success": False,
                "error": str(e),
                "cost": 0.0
            }
    
    def process_files(self, file_paths: list[Path]) -> None:
        """Process multiple files with parallel execution."""
        print("\n🚀 Starting OpenAI Whisper API batch transcription")
        print(f"📁 Files to process: {len(file_paths)}")
        print(f"⚡ Max parallel workers: {self.max_workers}")
        print(f"💰 Rate: ${self.rate_per_minute:.3f}/minute")
        print("="*60)
        
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            # Submit all jobs
            future_to_path = {
                executor.submit(self.transcribe_file, path): path 
                for path in file_paths
            }
            
            # Process results with progress bar
            with tqdm(total=len(file_paths), desc="Transcribing", unit="files") as pbar:
                for future in as_completed(future_to_path):
                    file_path = future_to_path[future]
                    try:
                        result = future.result()
                        self.results.append(result)
                        
                        if result.get("success"):
                            pbar.set_postfix({
                                "current": file_path.name[:15],
                                "cost": f"${self.total_cost:.3f}"
                            })
                        else:
                            tqdm.write(f"❌ Failed: {file_path.name} - {result.get('error')}")
                        
                    except Exception as e:
                        tqdm.write(f"❌ Exception processing {file_path.name}: {e}")
                        self.results.append({
                            "filename": file_path.name,
                            "success": False,
                            "error": str(e),
                            "cost": 0.0
                        })
                    
                    pbar.update(1)
    
    def save_results(self, output_dir: Path) -> None:
        """Save results to JSON and CSV formats."""
        output_dir.mkdir(exist_ok=True)
        
        successful_results = [r for r in self.results if r.get("success")]
        
        # Save combined CSV
        csv_file = output_dir / "openai_transcriptions_quick.csv"
        with open(csv_file, 'w', newline='', encoding='utf-8') as f:
            fieldnames = [
                "filename", "context_type", "language", "duration", "cost",
                "word_count", "speech_rate", "text"
            ]
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            
            for result in successful_results:
                writer.writerow({
                    "filename": result["filename"],
                    "context_type": result.get("context_type", "unknown"),
                    "language": result.get("language", "unknown"),
                    "duration": f"{result.get('duration', 0):.1f}",
                    "cost": f"${result.get('cost', 0):.4f}",
                    "word_count": result.get("word_count", 0),
                    "speech_rate": f"{result.get('speech_rate', 0):.1f}",
                    "text": result.get("text", "")
                })
        
        # Save quick summary
        summary_file = output_dir / "quick_summary.json"
        successful_count = len(successful_results)
        failed_count = len(self.results) - successful_count
        total_duration = sum(r.get("duration", 0) for r in successful_results)
        total_words = sum(r.get("word_count", 0) for r in successful_results)
        
        summary = {
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "total_files": len(self.results),
            "successful": successful_count,
            "failed": failed_count,
            "total_duration_minutes": total_duration / 60,
            "total_cost": self.total_cost,
            "total_words": total_words,
            "average_speech_rate": total_words / (total_duration / 60) if total_duration > 0 else 0
        }
        
        with open(summary_file, 'w', encoding='utf-8') as f:
            json.dump(summary, f, indent=2)
        
        print("\n📊 RESULTS SAVED:")
        print(f"   📄 CSV: {csv_file}")
        print(f"   📈 Summary: {summary_file}")


def main():
    """Main execution function."""
    # Process only the two specific files first
    base_dir = Path("/Users/jim/Projects/Email Sync")
    
    specific_files = [
        base_dir / "data/originals/Raw Videos/Mold - Test - Sally.mov",
        base_dir / "data/originals/Raw Videos/05.22.24 Brad.MP4"
    ]
    
    # Add a few sample files from each directory to test
    sample_files = []
    
    # Add 3 files from 20250814/08
    dir_08 = base_dir / "data/originals/20250814/08"
    if dir_08.exists():
        mp4_files = list(dir_08.glob("*.mp4"))[:3]
        sample_files.extend(mp4_files)
    
    # Add 3 files from 20250814/09  
    dir_09 = base_dir / "data/originals/20250814/09"
    if dir_09.exists():
        mp4_files = list(dir_09.glob("*.mp4"))[:3]
        sample_files.extend(mp4_files)
    
    # Add 2 files from 20250719
    dir_719 = base_dir / "data/originals/20250719"
    if dir_719.exists():
        mp4_files = list(dir_719.rglob("*.mp4"))[:2]
        sample_files.extend(mp4_files)
    
    # Combine all files
    all_files = []
    for file_path in specific_files:
        if file_path.exists():
            all_files.append(file_path)
        else:
            print(f"⚠️  File not found: {file_path}")
    
    all_files.extend(sample_files)
    all_files = list(set(all_files))  # Remove duplicates
    all_files.sort()
    
    if not all_files:
        print("❌ No files found to process!")
        return
    
    print(f"🎯 Quick test: {len(all_files)} files")
    for f in all_files:
        print(f"   📁 {f.name}")
    
    # Estimate cost
    total_size_mb = sum(f.stat().st_size for f in all_files if f.exists()) / (1024 * 1024)
    estimated_minutes = total_size_mb / 2  # Rough estimate: 2MB per minute
    estimated_cost = estimated_minutes * 0.006
    
    print("\n📊 Estimation:")
    print(f"   📁 Total size: {total_size_mb:.1f} MB")
    print(f"   ⏱️  Estimated duration: {estimated_minutes:.1f} minutes")
    print(f"   💰 Estimated cost: ${estimated_cost:.2f}")
    
    print("\n🚀 Starting transcription in 3 seconds...")
    time.sleep(3)
    
    # Initialize transcriber and process
    transcriber = OpenAIBatchTranscriber()
    transcriber.process_files(all_files)
    
    # Save results
    output_dir = base_dir / "openai_transcriptions"
    transcriber.save_results(output_dir)
    
    # Final summary
    successful = len([r for r in transcriber.results if r.get("success")])
    failed = len(transcriber.results) - successful
    
    print("\n🎉 QUICK TRANSCRIPTION COMPLETE!")
    print(f"   ✅ Successful: {successful}/{len(transcriber.results)}")
    print(f"   ❌ Failed: {failed}")
    print(f"   💰 Total cost: ${transcriber.total_cost:.2f}")
    print(f"   📁 Results: {output_dir}")


if __name__ == "__main__":
    main()