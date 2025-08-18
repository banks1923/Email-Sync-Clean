#!/usr/bin/env python3
"""
OpenAI Whisper API Transcription for Archive Files
Process smaller files that are under 25MB API limit
"""

import csv
import json
import time
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Dict, Any
import subprocess

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
        self.max_workers = 5  # OpenAI can handle more parallel requests
        self.results = []
        self.max_file_size = 25 * 1024 * 1024  # 25MB limit
        
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
    
    def check_file_size(self, file_path: Path) -> bool:
        """Check if file is under API size limit."""
        try:
            size = file_path.stat().st_size
            return size < self.max_file_size and size > 1000  # At least 1KB
        except:
            return False
    
    def transcribe_file(self, file_path: Path) -> Dict[str, Any]:
        """Transcribe a single file using OpenAI Whisper API."""
        # Check file size first
        if not self.check_file_size(file_path):
            size_mb = file_path.stat().st_size / (1024 * 1024) if file_path.exists() else 0
            return {
                "filename": file_path.name,
                "file_path": str(file_path),
                "success": False,
                "error": f"File too large: {size_mb:.1f}MB (limit: 25MB)",
                "cost": 0.0
            }
        
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
    
    def process_files(self, file_paths: List[Path]) -> None:
        """Process multiple files with parallel execution."""
        print("\n🚀 OpenAI Whisper API Batch Transcription")
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
            with tqdm(total=len(file_paths), desc="🎤 Transcribing", unit="files") as pbar:
                for future in as_completed(future_to_path):
                    file_path = future_to_path[future]
                    try:
                        result = future.result()
                        self.results.append(result)
                        
                        if result.get("success"):
                            pbar.set_postfix({
                                "file": file_path.name[:12],
                                "cost": f"${self.total_cost:.3f}"
                            })
                        else:
                            error = result.get('error', 'Unknown error')[:50]
                            tqdm.write(f"❌ {file_path.name}: {error}")
                        
                    except Exception as e:
                        tqdm.write(f"❌ Exception: {file_path.name}: {e}")
                        self.results.append({
                            "filename": file_path.name,
                            "success": False,
                            "error": str(e),
                            "cost": 0.0
                        })
                    
                    pbar.update(1)
    
    def save_results(self, output_dir: Path) -> None:
        """Save results to CSV and JSON formats."""
        output_dir.mkdir(exist_ok=True)
        
        successful_results = [r for r in self.results if r.get("success")]
        failed_results = [r for r in self.results if not r.get("success")]
        
        # Save text transcriptions
        txt_file = output_dir / "all_transcriptions.txt"
        with open(txt_file, 'w', encoding='utf-8') as f:
            f.write("OPENAI WHISPER API TRANSCRIPTIONS\\n")
            f.write("=" * 50 + "\\n\\n")
            
            for result in successful_results:
                f.write(f"=== {result['filename']} ===\\n")
                f.write(f"Context: {result.get('context_type', 'unknown')}\\n")
                f.write(f"Language: {result.get('language', 'unknown')}\\n")
                f.write(f"Duration: {result.get('duration', 0):.1f}s\\n")
                f.write(f"Cost: ${result.get('cost', 0):.4f}\\n")
                f.write(f"Text: {result.get('text', '')}\\n\\n")
        
        # Save CSV with segments
        csv_file = output_dir / "openai_transcriptions_segments.csv"
        with open(csv_file, 'w', newline='', encoding='utf-8') as f:
            fieldnames = [
                "filename", "segment_start", "segment_end", "segment_text",
                "avg_logprob", "context_type", "cost"
            ]
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            
            for result in successful_results:
                for segment in result.get("segments", []):
                    writer.writerow({
                        "filename": result["filename"],
                        "segment_start": f"{segment['start']:.3f}",
                        "segment_end": f"{segment['end']:.3f}",
                        "segment_text": segment["text"],
                        "avg_logprob": f"{segment.get('avg_logprob', -1.0):.4f}",
                        "context_type": result.get("context_type", "unknown"),
                        "cost": f"${result.get('cost', 0):.4f}"
                    })
        
        # Save summary
        summary_file = output_dir / "transcription_summary.json"
        total_duration = sum(r.get("duration", 0) for r in successful_results)
        total_words = sum(r.get("word_count", 0) for r in successful_results)
        
        summary = {
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "engine": "openai_whisper_api",
            "total_files": len(self.results),
            "successful": len(successful_results),
            "failed": len(failed_results),
            "total_duration_minutes": total_duration / 60,
            "total_cost": self.total_cost,
            "total_words": total_words,
            "average_speech_rate": total_words / (total_duration / 60) if total_duration > 0 else 0,
            "failed_files": [{"filename": r["filename"], "error": r.get("error", "")} for r in failed_results]
        }
        
        with open(summary_file, 'w', encoding='utf-8') as f:
            json.dump(summary, f, indent=2)
        
        print("\\n📊 RESULTS SAVED:")
        print(f"   📄 Text: {txt_file}")
        print(f"   📋 CSV: {csv_file}")
        print(f"   📈 Summary: {summary_file}")


def main():
    """Main execution function."""
    base_dir = Path("/Users/jim/Projects/Email Sync")
    
    # Process files from Raw Videos directory
    video_dirs = [
        "data/originals/Raw Videos/20250814",
        "data/originals/Raw Videos/20250719"
    ]
    
    all_files = []
    
    # Add specific large files (these will be checked for size)
    specific_files = [
        "data/originals/Raw Videos/Mold - Test - Sally.mov",
        "data/originals/Raw Videos/05.22.24 Brad.MP4"
    ]
    
    for file_path in specific_files:
        full_path = base_dir / file_path
        if full_path.exists():
            all_files.append(full_path)
            print(f"📁 Added specific file: {full_path.name}")
    
    # Add files from directories
    for dir_path in video_dirs:
        full_dir = base_dir / dir_path
        if full_dir.exists():
            # Look for all video formats
            for pattern in ["*.mp4", "*.MP4", "*.mov", "*.MOV"]:
                video_files = list(full_dir.rglob(pattern))
                all_files.extend(video_files)
            print(f"📁 Found {len(list(full_dir.rglob('*.*')))} files in {dir_path}")
        else:
            print(f"⚠️  Directory not found: {dir_path}")
    
    if not all_files:
        print("❌ No files found in archive directories!")
        return
    
    # Filter files by size (under 25MB)
    valid_files = []
    for f in all_files:
        if f.exists():
            size_mb = f.stat().st_size / (1024 * 1024)
            if size_mb < 25 and size_mb > 0.001:  # Between 1KB and 25MB
                valid_files.append(f)
            else:
                print(f"⚠️  Skipping {f.name}: {size_mb:.1f}MB")
    
    if not valid_files:
        print("❌ No valid files under 25MB found!")
        return
    
    print(f"\\n🎯 Processing {len(valid_files)} valid files")
    
    # Estimate cost
    total_size_mb = sum(f.stat().st_size for f in valid_files) / (1024 * 1024)
    estimated_minutes = total_size_mb / 2  # Rough estimate
    estimated_cost = estimated_minutes * 0.006
    
    print("📊 Estimation:")
    print(f"   📁 Total size: {total_size_mb:.1f} MB")
    print(f"   ⏱️  Estimated duration: {estimated_minutes:.1f} minutes")
    print(f"   💰 Estimated cost: ${estimated_cost:.2f}")
    
    print("\\n🚀 Starting in 3 seconds...")
    time.sleep(3)
    
    # Process files
    transcriber = OpenAIBatchTranscriber()
    transcriber.process_files(valid_files)
    
    # Save results
    output_dir = base_dir / "openai_transcriptions"
    transcriber.save_results(output_dir)
    
    # Final summary
    successful = len([r for r in transcriber.results if r.get("success")])
    failed = len(transcriber.results) - successful
    
    print("\\n🎉 TRANSCRIPTION COMPLETE!")
    print(f"   ✅ Successful: {successful}/{len(transcriber.results)}")
    print(f"   ❌ Failed: {failed}")
    print(f"   💰 Total cost: ${transcriber.total_cost:.2f}")
    print(f"   📁 Results saved to: {output_dir}")


if __name__ == "__main__":
    main()