#!/usr/bin/env python3
"""
Auto-categorize documents to show what would be segregated.
Run this first to review before actual segregation.
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
    "email", "correspondence",
    "crd", "defendants"
]

def categorize_documents():
    """Categorize documents based on filename patterns."""
    
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
        
        # Special case: "Analysis & Strategies" folder - definitely privileged
        if "analysis" in parent_dir and "strategies" in parent_dir:
            is_privileged = True
            reason = "Strategy/Analysis folder - attorney work product"
        
        # Special case: "Our Reports" - likely privileged
        elif "our reports" in parent_dir.lower():
            is_privileged = True
            reason = "Internal reports - review required"
        
        # Check directory name for privileged keywords
        elif any(keyword in parent_dir for keyword in PRIVILEGED_KEYWORDS):
            is_privileged = True
            reason = f"Directory contains privileged keyword: {parent_dir}"
        
        # Check filename for privileged keywords
        elif any(keyword in filename for keyword in PRIVILEGED_KEYWORDS):
            is_privileged = True
            reason = f"Filename contains privileged keyword"
        
        # Check for safe patterns - these are public documents
        elif any(pattern in parent_dir.lower() or pattern in filename for pattern in SAFE_PATTERNS):
            is_privileged = False
            reason = "Public court document or notice"
        
        # Default to caution for unknown
        else:
            is_privileged = True
            reason = "Unknown category - hold for review"
        
        # Log the decision
        if is_privileged:
            categorization["hold_for_review"].append({
                "file": str(relative_path),
                "reason": reason,
                "size_kb": round(pdf_path.stat().st_size / 1024, 2)
            })
            print(f"⚠️  HOLD: {relative_path}")
            print(f"   Reason: {reason}")
        else:
            categorization["ready_for_processing"].append({
                "file": str(relative_path),
                "reason": reason,
                "size_kb": round(pdf_path.stat().st_size / 1024, 2)
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

if __name__ == "__main__":
    print("🔒 LEGAL DOCUMENT PRIVILEGE ANALYSIS")
    print("=" * 60)
    print("Analyzing documents for privilege categorization...")
    print()
    
    categorization = categorize_documents()
    
    print("\n" + "=" * 60)
    print("⚠️  IMPORTANT NEXT STEPS:")
    print("1. Review the categorization in segregation_log.json")
    print("2. Files marked HOLD should be reviewed with attorney before cloud processing")
    print("3. Only files marked READY should be uploaded to Document AI")
    print("\n📂 To actually segregate files, update the script to copy them.")