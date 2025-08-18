#!/usr/bin/env python3
"""
OpenAI Whisper API Batch Transcription Script
Fast, high-quality transcription using OpenAI's cloud infrastructure
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
        self.max_workers = 5  # Parallel API calls
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
    
    def transcribe_file(self, file_path: Path) -> Dict[str, Any]:
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
    
    def process_files(self, file_paths: List[Path]) -> None:
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
                                "current": file_path.name[:20],
                                "cost": f"${self.total_cost:.3f}"
                            })
                        else:
                            print(f"\n❌ Failed: {file_path.name} - {result.get('error')}")
                        
                    except Exception as e:
                        print(f"\n❌ Exception processing {file_path.name}: {e}")
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
        
        # Save individual JSON files
        json_dir = output_dir / "json"
        json_dir.mkdir(exist_ok=True)
        
        successful_results = [r for r in self.results if r.get("success")]
        
        for result in successful_results:
            json_file = json_dir / f"{result['filename']}.json"
            with open(json_file, 'w', encoding='utf-8') as f:
                json.dump(result, f, indent=2, ensure_ascii=False)
        
        # Save combined CSV
        csv_file = output_dir / "openai_transcriptions_combined.csv"
        with open(csv_file, 'w', newline='', encoding='utf-8') as f:
            fieldnames = [
                "filename", "context_type", "language", "duration", "cost",
                "word_count", "speech_rate", "text", "segment_count"
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
                    "text": result.get("text", ""),
                    "segment_count": len(result.get("segments", []))
                })
        
        # Save detailed CSV with segments
        segments_csv = output_dir / "openai_transcriptions_segments.csv"
        with open(segments_csv, 'w', newline='', encoding='utf-8') as f:
            fieldnames = [
                "filename", "segment_start", "segment_end", "segment_text",
                "avg_logprob", "no_speech_prob", "context_type"
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
                        "no_speech_prob": f"{segment.get('no_speech_prob', 0.0):.4f}",
                        "context_type": result.get("context_type", "unknown")
                    })
        
        # Save summary report
        summary_file = output_dir / "transcription_summary.json"
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
            "average_speech_rate": total_words / (total_duration / 60) if total_duration > 0 else 0,
            "files_by_context": {}
        }
        
        # Group by context type
        for result in successful_results:
            context = result.get("context_type", "unknown")
            if context not in summary["files_by_context"]:
                summary["files_by_context"][context] = 0
            summary["files_by_context"][context] += 1
        
        with open(summary_file, 'w', encoding='utf-8') as f:
            json.dump(summary, f, indent=2)
        
        print("\n📊 RESULTS SAVED:")
        print(f"   📁 JSON files: {json_dir}")
        print(f"   📄 Combined CSV: {csv_file}")
        print(f"   📋 Segments CSV: {segments_csv}")
        print(f"   📈 Summary: {summary_file}")


def main():
    """Main execution function."""
    # Define target files and directories
    target_files = [
        "data/originals/Mold - Test - Sally.mov",
        "data/originals/05.22.24 Brad.MP4"
    ]
    
    target_dirs = [
        "data/originals/20250814",
        "data/originals/20250719"
    ]
    
    # Collect all files
    all_files = []
    base_dir = Path("/Users/jim/Projects/Email Sync")
    
    # Add specific files
    for file_path in target_files:
        full_path = base_dir / file_path
        if full_path.exists():
            all_files.append(full_path)
        else:
            print(f"⚠️  File not found: {full_path}")
    
    # Add files from directories
    for dir_path in target_dirs:
        full_dir = base_dir / dir_path
        if full_dir.exists():
            for ext in ["*.mp4", "*.MP4", "*.mov", "*.MOV"]:
                all_files.extend(full_dir.rglob(ext))
        else:
            print(f"⚠️  Directory not found: {full_dir}")
    
    # Remove duplicates
    all_files = list(set(all_files))
    all_files.sort()
    
    if not all_files:
        print("❌ No files found to process!")
        return
    
    print(f"🎯 Found {len(all_files)} files to transcribe")
    
    # Estimate cost
    total_size_mb = sum(f.stat().st_size for f in all_files if f.exists()) / (1024 * 1024)
    estimated_minutes = total_size_mb / 2  # Rough estimate: 2MB per minute
    estimated_cost = estimated_minutes * 0.006
    
    print("📊 Estimation:")
    print(f"   📁 Total size: {total_size_mb:.1f} MB")
    print(f"   ⏱️  Estimated duration: {estimated_minutes:.1f} minutes")
    print(f"   💰 Estimated cost: ${estimated_cost:.2f}")
    
    # Confirm before proceeding
    response = input("\n🚀 Proceed with transcription? (y/N): ").strip().lower()
    if response != 'y':
        print("❌ Transcription cancelled.")
        return
    
    # Initialize transcriber and process
    transcriber = OpenAIBatchTranscriber()
    transcriber.process_files(all_files)
    
    # Save results
    output_dir = base_dir / "openai_transcriptions"
    transcriber.save_results(output_dir)
    
    # Final summary
    successful = len([r for r in transcriber.results if r.get("success")])
    failed = len(transcriber.results) - successful
    
    print("\n🎉 TRANSCRIPTION COMPLETE!")
    print(f"   ✅ Successful: {successful}/{len(transcriber.results)}")
    print(f"   ❌ Failed: {failed}")
    print(f"   💰 Total cost: ${transcriber.total_cost:.2f}")
    print(f"   📁 Results: {output_dir}")


if __name__ == "__main__":
    main()