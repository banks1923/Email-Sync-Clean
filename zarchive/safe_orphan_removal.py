#!/usr/bin/env python3
"""
Safe Orphaned Module Removal - Conservative Approach

This script identifies only genuinely safe-to-remove files that won't break the system.
After the incident where essential modules were incorrectly identified as orphaned,
this takes a much more conservative approach.
"""

import shutil
from pathlib import Path
from datetime import datetime
import json
import subprocess
import sys

PROJECT_ROOT = Path("/Users/jim/Projects/Email-Sync-Clean-Backup")

# CRITICAL MODULES - Never remove these
CRITICAL_MODULES = {
    "gmail", "pdf", "transcription", "entity", "legal_intelligence", 
    "search_intelligence", "knowledge_graph", "utilities", "shared",
    "infrastructure", "summarization", "monitoring"
}

# SAFE TO REMOVE - Only these patterns are safe for automated removal
SAFE_REMOVAL_PATTERNS = [
    # Archive directories that are clearly old backups
    "Archive0817/",
    
    # Test artifacts that may be orphaned
    "tests/deprecated/",
    "tests/old/",
    "tests/archive/",
    
    # Clearly temporary or debug files
    "*_backup.py",
    "*_old.py", 
    "*_temp.py",
    "temp_*.py",
    "debug_*.py",
    
    # Known deprecated scripts
    "migrate_analog_to_database.py",
    "vector_debug_fix.py",
    "id_mismatch_audit.py",
    "bowler_id_fixes.py",
    "bowler_codebase_alignment.py",
    "reverse_migration.py",
]

def identify_safe_removals():
    """Identify files that are genuinely safe to remove."""
    safe_files = []
    
    # 1. Find Archive0817 files (clearly archived)
    archive_dir = PROJECT_ROOT / "Archive0817"
    if archive_dir.exists():
        for item in archive_dir.rglob("*"):
            if item.is_file():
                safe_files.append(str(item.relative_to(PROJECT_ROOT)))
    
    # 2. Find root-level migration/debug scripts
    root_scripts = [
        "migrate_analog_to_database.py",
        "vector_debug_fix.py", 
        "id_mismatch_audit.py",
        "bowler_id_fixes.py",
        "bowler_codebase_alignment.py",
        "reverse_migration.py",
        "database_migration.py",
        "codebase_audit_automation.md"
    ]
    
    for script in root_scripts:
        script_path = PROJECT_ROOT / script
        if script_path.exists():
            safe_files.append(script)
    
    # 3. Find any clearly temporary files
    for pattern in ["*_backup.*", "*_old.*", "*_temp.*", "temp_*.*", "debug_*.*"]:
        for item in PROJECT_ROOT.rglob(pattern):
            if item.is_file() and not any(critical in str(item) for critical in CRITICAL_MODULES):
                safe_files.append(str(item.relative_to(PROJECT_ROOT)))
    
    return safe_files

def create_backup_snapshot():
    """Create a complete backup snapshot."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_dir = PROJECT_ROOT / "BACKUPS"
    backup_dir.mkdir(exist_ok=True)
    
    snapshot_path = backup_dir / f"safe_removal_snapshot_{timestamp}.tar.gz"
    
    print(f"Creating backup snapshot: {snapshot_path}")
    
    # Create tar backup of key directories
    subprocess.run([
        "tar", "-czf", str(snapshot_path),
        "--exclude=.git", "--exclude=__pycache__", "--exclude=*.pyc",
        "--exclude=node_modules", "--exclude=.env",
        "."
    ], cwd=PROJECT_ROOT, check=True)
    
    return snapshot_path

def safe_remove_files(file_list, backup_snapshot):
    """Safely remove files with logging."""
    removal_log = {
        "timestamp": datetime.now().isoformat(),
        "backup_snapshot": str(backup_snapshot),
        "files_removed": [],
        "total_files": len(file_list),
        "space_saved_bytes": 0
    }
    
    archive_dir = PROJECT_ROOT / "ARCHIVE" / "safe_removal_backup"
    archive_dir.mkdir(parents=True, exist_ok=True)
    
    for file_path_str in file_list:
        try:
            file_path = PROJECT_ROOT / file_path_str
            if not file_path.exists():
                continue
                
            # Get file size
            if file_path.is_file():
                size = file_path.stat().st_size
            else:
                size = sum(f.stat().st_size for f in file_path.rglob('*') if f.is_file())
            
            # Archive to backup first
            backup_path = archive_dir / file_path_str
            backup_path.parent.mkdir(parents=True, exist_ok=True)
            
            if file_path.is_dir():
                shutil.copytree(file_path, backup_path, dirs_exist_ok=True)
                shutil.rmtree(file_path)
            else:
                shutil.copy2(file_path, backup_path)
                file_path.unlink()
            
            removal_log["files_removed"].append({
                "path": file_path_str,
                "size_bytes": size,
                "backup_path": str(backup_path)
            })
            removal_log["space_saved_bytes"] += size
            
            print(f"✅ Removed: {file_path_str} ({size:,} bytes)")
            
        except Exception as e:
            print(f"❌ Error removing {file_path_str}: {e}")
    
    # Save log
    log_path = PROJECT_ROOT / "safe_removal_log.json"
    with open(log_path, 'w') as f:
        json.dump(removal_log, f, indent=2)
    
    return removal_log

def verify_system_health():
    """Verify system is still healthy after removal."""
    print("\n🔍 Verifying system health...")
    
    # Test core imports
    test_imports = [
        "gmail.main",
        "pdf.main", 
        "search_intelligence.main",
        "shared.simple_db",
        "utilities.embeddings"
    ]
    
    all_passed = True
    for module in test_imports:
        try:
            result = subprocess.run([
                sys.executable, "-c", f"import {module}; print('✅ {module}')"
            ], cwd=PROJECT_ROOT, capture_output=True, text=True, timeout=10)
            
            if result.returncode == 0:
                print(f"✅ {module} import successful")
            else:
                print(f"❌ {module} import failed: {result.stderr}")
                all_passed = False
                
        except Exception as e:
            print(f"❌ {module} import error: {e}")
            all_passed = False
    
    # Check CLI script
    cli_script = PROJECT_ROOT / "tools" / "scripts" / "vsearch"
    if cli_script.exists():
        print("✅ CLI script exists")
    else:
        print("❌ CLI script missing")
        all_passed = False
    
    return all_passed

def main():
    """Main execution."""
    print("🛡️  SAFE ORPHANED MODULE REMOVAL")
    print("=" * 50)
    print("Conservative approach after emergency restoration")
    
    # 1. Identify safe files to remove
    print("\n📋 Identifying safe files to remove...")
    safe_files = identify_safe_removals()
    
    if not safe_files:
        print("No safe files identified for removal.")
        return 0
    
    print(f"Found {len(safe_files)} safe files to remove:")
    for file_path in safe_files:
        print(f"  - {file_path}")
    
    # 2. Create backup snapshot
    print("\n💾 Creating backup snapshot...")
    snapshot_path = create_backup_snapshot()
    print(f"Backup created: {snapshot_path}")
    
    # 3. Auto-proceed for safe files (all are non-critical)
    print(f"\n✅ Auto-proceeding with removal of {len(safe_files)} safe files")
    
    # 4. Perform safe removal
    print("\n🗑️  Removing files...")
    removal_log = safe_remove_files(safe_files, snapshot_path)
    
    # 5. Verify system health
    health_ok = verify_system_health()
    
    # 6. Summary
    space_mb = removal_log["space_saved_bytes"] / (1024 * 1024)
    print("\n📊 Summary:")
    print(f"   Files removed: {len(removal_log['files_removed'])}")
    print(f"   Space saved: {space_mb:.1f} MB")
    print(f"   Backup: {snapshot_path}")
    print(f"   System health: {'✅ PASS' if health_ok else '❌ FAIL'}")
    
    if health_ok:
        print("\n🎉 Safe removal completed successfully!")
    else:
        print("\n⚠️  System health check failed - check imports")
    
    return 0 if health_ok else 1

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)