#!/usr/bin/env python3
"""
Clean existing exported documents that contain raw HTML.

This script processes files in data/export/ and cleans HTML content
while preserving the YAML frontmatter and document structure.
"""

import re
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from shared.html_cleaner import extract_email_content


def process_exported_file(filepath: str) -> dict:
    """
    Process a single exported markdown file to clean HTML content.
    
    Returns:
        Dict with success status and details
    """
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Split YAML frontmatter and content
        if content.startswith('---\n'):
            parts = content.split('---\n', 2)
            if len(parts) >= 3:
                yaml_front = f"---\n{parts[1]}---\n\n"
                document_content = parts[2]
            else:
                yaml_front = ""
                document_content = content
        else:
            yaml_front = ""
            document_content = content
        
        # Check if content has HTML (contains < and > tags)
        if '<' in document_content and '>' in document_content:
            # Extract the main content section
            content_match = re.search(r'## Content\s*\n\n(.+)', document_content, re.DOTALL)
            if content_match:
                html_content = content_match.group(1)
                
                # Clean the HTML content
                cleaned_content, email_metadata = extract_email_content(html_content)
                
                # Rebuild the document
                header_section = document_content[:content_match.start(1)]
                new_content = yaml_front + header_section + cleaned_content
                
                # Write the cleaned version
                with open(filepath, 'w', encoding='utf-8') as f:
                    f.write(new_content)
                
                return {
                    "success": True,
                    "cleaned": True,
                    "original_size": len(content),
                    "new_size": len(new_content),
                    "reduction": len(content) - len(new_content)
                }
            else:
                return {
                    "success": True, 
                    "cleaned": False, 
                    "reason": "No content section found"
                }
        else:
            return {
                "success": True,
                "cleaned": False, 
                "reason": "No HTML content detected"
            }
            
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }


def main():
    """Clean all exported documents in data/export/"""
    export_dir = project_root / "data" / "export"
    
    if not export_dir.exists():
        print(f"Export directory not found: {export_dir}")
        return
    
    print(f"Processing files in: {export_dir}")
    
    # Find all .md files
    md_files = list(export_dir.glob("*.md"))
    print(f"Found {len(md_files)} markdown files")
    
    if not md_files:
        print("No markdown files to process")
        return
    
    # Process each file
    stats = {
        "total": len(md_files),
        "cleaned": 0,
        "skipped": 0,
        "errors": 0,
        "total_reduction": 0
    }
    
    for md_file in md_files:
        print(f"Processing: {md_file.name}", end="...")
        
        result = process_exported_file(str(md_file))
        
        if result["success"]:
            if result["cleaned"]:
                stats["cleaned"] += 1
                stats["total_reduction"] += result.get("reduction", 0)
                reduction_kb = result.get("reduction", 0) / 1024
                print(f" CLEANED (-{reduction_kb:.1f}KB)")
            else:
                stats["skipped"] += 1
                print(f" SKIPPED ({result.get('reason', 'unknown')})")
        else:
            stats["errors"] += 1
            print(f" ERROR: {result['error']}")
    
    # Print summary
    print("\n📊 Cleaning Summary:")
    print(f"   Total files: {stats['total']}")
    print(f"   Cleaned: {stats['cleaned']}")
    print(f"   Skipped: {stats['skipped']}")
    print(f"   Errors: {stats['errors']}")
    print(f"   Total size reduction: {stats['total_reduction']/1024/1024:.1f}MB")
    
    if stats["cleaned"] > 0:
        avg_reduction = stats["total_reduction"] / stats["cleaned"] / 1024
        print(f"   Average reduction per file: {avg_reduction:.1f}KB")


if __name__ == "__main__":
    main()