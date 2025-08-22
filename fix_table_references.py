#!/usr/bin/env python3
"""
Fix table references from 'content' to 'content_unified'.
Aware of concurrent pipeline removal - only fixes files that will survive.

IMPORTANT: This runs AFTER or DURING pipeline removal.
Files in infrastructure/pipelines/ will be deleted, so we skip them.
"""

import os
import sys
import shutil
from pathlib import Path
from datetime import datetime
import re

# Files that will SURVIVE pipeline removal and need fixing
FILES_TO_FIX = [
    # Core embedding processing (CRITICAL - will remain)
    "tools/scripts/process_embeddings.py",
    
    # Knowledge graph modules (all will remain)
    "knowledge_graph/similarity_analyzer.py",
    "knowledge_graph/similarity_integration.py", 
    "knowledge_graph/timeline_relationships.py",
    "knowledge_graph/topic_clustering.py",
    
    # Search intelligence (will remain)
    "search_intelligence/duplicate_detector.py",
    "search_intelligence/similarity.py",
    
    # Verification scripts (may be updated but will remain)
    "scripts/verify_pipeline.py",  # Will be renamed to verify_system.py
    
    # CLI handlers (will remain)
    "shared/archive/cli/dedup_handler.py",
    
    # Make helpers (will remain but simplified)
    "tools/scripts/make_helpers.py"
]

# Files to SKIP (being deleted in pipeline removal)
SKIP_FILES = [
    "utilities/semantic_pipeline.py",  # Being removed with pipeline
    "infrastructure/pipelines/*",      # Entire directory being deleted
    "scripts/verify_semantic_wiring.py"  # Part of pipeline, being removed
]

# Table and column mappings
TABLE_REPLACEMENTS = [
    # Table name replacements
    (r'\bFROM content\b(?! unified)', 'FROM content_unified'),
    (r'\bINTO content\b(?! unified)', 'INTO content_unified'),
    (r'\bUPDATE content\b(?! unified)', 'UPDATE content_unified'),
    (r'\bJOIN content\b(?! unified)', 'JOIN content_unified'),
    (r'"content"(?!_unified)', '"content_unified"'),
    (r"'content'(?!_unified)", "'content_unified'"),
]

COLUMN_REPLACEMENTS = [
    # Column name replacements (only in SQL context)
    (r'\bcontent\.content_type\b', 'content_unified.source_type'),
    (r'\bcontent\.content\b(?!_)', 'content_unified.body'),
    (r'\bcontent\.title\b', 'content_unified.title'),
    (r'\bcontent\.created_at\b', 'content_unified.created_time'),
    (r'\bcontent\.id\b', 'content_unified.id'),
    (r'\bvector_processed\b', 'ready_for_embedding'),
    
    # In SELECT/WHERE clauses
    (r'\bcontent_type\s*=', 'source_type ='),
    (r'SELECT.*?\bcontent_type\b', lambda m: m.group(0).replace('content_type', 'source_type')),
    (r"get\('content_type'", "get('source_type'"),
    (r'result\["content_type"\]', 'result["source_type"]'),
    (r"result\['content_type'\]", "result['source_type']"),
]

def backup_file(filepath):
    """Create timestamped backup of file."""
    backup_path = filepath + f".backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    shutil.copy2(filepath, backup_path)
    return backup_path

def apply_replacements(content, filepath):
    """Apply all replacements to file content."""
    original = content
    changes = []
    
    # Apply table replacements
    for pattern, replacement in TABLE_REPLACEMENTS:
        new_content = re.sub(pattern, replacement, content, flags=re.IGNORECASE)
        if new_content != content:
            matches = len(re.findall(pattern, content, flags=re.IGNORECASE))
            changes.append(f"  - Replaced {matches} instances of '{pattern}' → '{replacement}'")
            content = new_content
    
    # Apply column replacements (more careful)
    for pattern, replacement in COLUMN_REPLACEMENTS:
        if callable(replacement):
            new_content = re.sub(pattern, replacement, content)
        else:
            new_content = re.sub(pattern, replacement, content)
        
        if new_content != content:
            matches = len(re.findall(pattern, content))
            changes.append(f"  - Updated column reference: '{pattern}'")
            content = new_content
    
    return content, changes

def process_file(filepath, dry_run=False):
    """Process a single file for table reference fixes."""
    if not os.path.exists(filepath):
        return False, f"File not found: {filepath}"
    
    # Check if file is in skip list
    for skip_pattern in SKIP_FILES:
        if skip_pattern.endswith('*'):
            if filepath.startswith(skip_pattern[:-1]):
                return False, f"Skipping (will be deleted): {filepath}"
        elif filepath == skip_pattern:
            return False, f"Skipping (will be deleted): {filepath}"
    
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Apply replacements
        new_content, changes = apply_replacements(content, filepath)
        
        if new_content == content:
            return True, f"No changes needed in {filepath}"
        
        if dry_run:
            return True, f"Would update {filepath}:\n" + "\n".join(changes)
        
        # Create backup
        backup_path = backup_file(filepath)
        
        # Write updated content
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(new_content)
        
        return True, f"Updated {filepath} (backup: {backup_path}):\n" + "\n".join(changes)
        
    except Exception as e:
        return False, f"Error processing {filepath}: {str(e)}"

def validate_changes():
    """Run basic validation after changes."""
    validations = []
    
    # Check if content_unified table exists
    import sqlite3
    try:
        conn = sqlite3.connect('data/emails.db')
        cursor = conn.cursor()
        
        # Check content_unified exists and has data
        cursor.execute("SELECT COUNT(*) FROM content_unified")
        count = cursor.fetchone()[0]
        validations.append(f"✅ content_unified table has {count} rows")
        
        # Check old content table (should still exist but deprecated)
        cursor.execute("SELECT COUNT(*) FROM content")
        old_count = cursor.fetchone()[0]
        validations.append(f"ℹ️  Old content table has {old_count} rows (deprecated)")
        
        conn.close()
    except Exception as e:
        validations.append(f"❌ Database validation failed: {e}")
    
    return validations

def main():
    """Main migration function."""
    import argparse
    parser = argparse.ArgumentParser(description="Fix table references from content to content_unified")
    parser.add_argument('--dry-run', action='store_true', help='Preview changes without applying')
    parser.add_argument('--validate-only', action='store_true', help='Only run validation')
    args = parser.parse_args()
    
    if args.validate_only:
        print("🔍 Running validation only...")
        validations = validate_changes()
        for v in validations:
            print(v)
        return
    
    print("🔧 Table Reference Migration Script")
    print("=" * 50)
    
    if args.dry_run:
        print("🔍 DRY RUN MODE - No changes will be made")
    else:
        print("⚠️  LIVE MODE - Files will be modified")
        print("✅ Auto-confirming (running in automated context)")
    
    print(f"\n📋 Processing {len(FILES_TO_FIX)} files...")
    print(f"⏭️  Skipping {len(SKIP_FILES)} patterns (pipeline removal)")
    print()
    
    success_count = 0
    error_count = 0
    
    for filepath in FILES_TO_FIX:
        success, message = process_file(filepath, dry_run=args.dry_run)
        
        if success:
            if "No changes needed" in message:
                print(f"✓ {message}")
            else:
                print(f"✅ {message}")
            success_count += 1
        else:
            if "Skipping" in message:
                print(f"⏭️  {message}")
            else:
                print(f"❌ {message}")
                error_count += 1
    
    print("\n" + "=" * 50)
    print(f"📊 Results: {success_count} successful, {error_count} errors")
    
    if not args.dry_run and success_count > 0:
        print("\n🔍 Running post-migration validation...")
        validations = validate_changes()
        for v in validations:
            print(v)
        
        print("\n📝 Next steps:")
        print("1. Test the changed files manually")
        print("2. Run: python3 tools/scripts/process_embeddings.py")
        print("3. Update CHANGELOG.md with changes")
        print("4. Commit with message: 'fix: migrate table references from content to content_unified'")

if __name__ == "__main__":
    main()