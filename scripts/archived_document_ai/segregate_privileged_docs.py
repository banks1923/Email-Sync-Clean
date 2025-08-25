#!/usr/bin/env python3
"""
Segregate potentially privileged documents before cloud processing.
CRITICAL: Review attorney communications and strategy docs before uploading.
"""

import os
import shutil
from pathlib import Path
from datetime import datetime
import json

# Define paths
BASE_DIR = Path("data/Stoneman_dispute/pdfs_raw")
READY_FOR_CLOUD = Path("data/Stoneman_dispute/ready_for_cloud")
HOLD_PRIVILEGED = Path("data/Stoneman_dispute/hold_privileged")
SEGREGATION_LOG = Path("data/Stoneman_dispute/segregation_log.json")

# Patterns that may indicate privilege
PRIVILEGED_KEYWORDS = [
    "strategy", "strategies",
    "attorney", "lawyer", "counsel",
    "privileged", "confidential",
    "medical", "health",
    "analysis", "plan",
    "work product"
]

# Patterns that are safe to process
SAFE_PATTERNS = [
    "notice", "3 day", "unlawful detainer",
    "docket", "civil", "complaint",
    "response", "discovery",
    "report", "inspection",
    "email", "correspondence"
]

def categorize_documents():
    """Categorize documents based on filename patterns."""
    
    # Create directories
    READY_FOR_CLOUD.mkdir(parents=True, exist_ok=True)
    HOLD_PRIVILEGED.mkdir(parents=True, exist_ok=True)
    
    categorization = {
        "ready_for_processing": [],
        "hold_for_review": [],
        "summary": {}
    }
    
    # Find all PDFs
    pdf_files = list(BASE_DIR.rglob("*.pdf"))
    
    print(f"\n📁 Found {len(pdf_files)} PDF files to categorize")
    print("=" * 60)
    
    for pdf_path in pdf_files:
        relative_path = pdf_path.relative_to(BASE_DIR)
        parent_dir = pdf_path.parent.name.lower()
        filename = pdf_path.name.lower()
        
        # Check for privileged patterns
        is_privileged = False
        reason = ""
        
        # Check directory name
        if any(keyword in parent_dir for keyword in PRIVILEGED_KEYWORDS):
            is_privileged = True
            reason = f"Directory contains: {parent_dir}"
        
        # Check filename
        elif any(keyword in filename for keyword in PRIVILEGED_KEYWORDS):
            is_privileged = True
            reason = f"Filename contains privileged keyword"
        
        # Special case: "Analysis & Strategies" folder
        elif "analysis" in parent_dir or "strategies" in parent_dir:
            is_privileged = True
            reason = "Strategy/Analysis folder - review required"
        
        # Check for safe patterns
        elif any(pattern in parent_dir.lower() or pattern in filename for pattern in SAFE_PATTERNS):
            is_privileged = False
            reason = "Public court document or notice"
        
        # Default to caution
        else:
            is_privileged = True
            reason = "Unknown category - hold for review"
        
        # Log the decision
        if is_privileged:
            categorization["hold_for_review"].append({
                "file": str(relative_path),
                "reason": reason,
                "size_kb": pdf_path.stat().st_size / 1024
            })
            print(f"⚠️  HOLD: {relative_path}")
            print(f"   Reason: {reason}")
        else:
            categorization["ready_for_processing"].append({
                "file": str(relative_path),
                "reason": reason,
                "size_kb": pdf_path.stat().st_size / 1024
            })
            print(f"✅ READY: {relative_path}")
    
    # Summary
    categorization["summary"] = {
        "total_files": len(pdf_files),
        "ready_for_processing": len(categorization["ready_for_processing"]),
        "hold_for_review": len(categorization["hold_for_review"]),
        "timestamp": datetime.now().isoformat()
    }
    
    # Save categorization log
    with open(SEGREGATION_LOG, 'w') as f:
        json.dump(categorization, f, indent=2)
    
    print("\n" + "=" * 60)
    print("📊 CATEGORIZATION SUMMARY:")
    print(f"✅ Ready for processing: {categorization['summary']['ready_for_processing']} files")
    print(f"⚠️  Hold for review: {categorization['summary']['hold_for_review']} files")
    print(f"\n📝 Log saved to: {SEGREGATION_LOG}")
    
    return categorization

def copy_ready_files(categorization):
    """Copy files that are ready for processing to the cloud staging area."""
    
    print("\n" + "=" * 60)
    print("📦 PREPARING FILES FOR CLOUD PROCESSING...")
    
    copied_count = 0
    for item in categorization["ready_for_processing"]:
        src = BASE_DIR / item["file"]
        dst = READY_FOR_CLOUD / item["file"]
        
        # Create parent directories
        dst.parent.mkdir(parents=True, exist_ok=True)
        
        # Copy file
        if src.exists():
            shutil.copy2(src, dst)
            copied_count += 1
            print(f"✅ Copied: {item['file']}")
    
    print(f"\n✅ Copied {copied_count} files to: {READY_FOR_CLOUD}")
    
    # Copy privileged files to hold directory
    print("\n📦 SEGREGATING PRIVILEGED FILES...")
    held_count = 0
    for item in categorization["hold_for_review"]:
        src = BASE_DIR / item["file"]
        dst = HOLD_PRIVILEGED / item["file"]
        
        # Create parent directories
        dst.parent.mkdir(parents=True, exist_ok=True)
        
        # Copy file
        if src.exists():
            shutil.copy2(src, dst)
            held_count += 1
            print(f"⚠️  Held: {item['file']}")
    
    print(f"\n⚠️  Held {held_count} files for review in: {HOLD_PRIVILEGED}")

if __name__ == "__main__":
    print("🔒 LEGAL DOCUMENT PRIVILEGE SEGREGATION")
    print("=" * 60)
    print("This script will separate documents for processing:")
    print("• Public court documents → ready_for_cloud/")
    print("• Potentially privileged → hold_privileged/")
    print()
    
    response = input("Proceed with segregation? (yes/no): ")
    if response.lower() != 'yes':
        print("Cancelled.")
        exit(0)
    
    categorization = categorize_documents()
    
    print("\n" + "=" * 60)
    print("⚠️  IMPORTANT: Review the categorization above.")
    print("Files marked as HOLD may contain:")
    print("• Attorney-client communications")
    print("• Work product / strategy documents")
    print("• Medical records")
    print()
    
    response = input("Copy files to staging directories? (yes/no): ")
    if response.lower() == 'yes':
        copy_ready_files(categorization)
        print("\n✅ SEGREGATION COMPLETE")
        print("Next steps:")
        print("1. Review files in hold_privileged/ with attorney")
        print("2. Process files in ready_for_cloud/ with Document AI")
    else:
        print("File copying cancelled. Review the log file for categorization.")