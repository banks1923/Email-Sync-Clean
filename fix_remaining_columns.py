#!/usr/bin/env python3
"""
Fix remaining column reference issues after automated updates.
Handles edge cases and dictionary access patterns.
"""

import os
import sys
from pathlib import Path

def fix_topic_clustering():
    """Fix topic_clustering.py issues."""
    filepath = "knowledge_graph/topic_clustering.py"
    
    if not os.path.exists(filepath):
        print(f"❌ {filepath} not found")
        return False
    
    with open(filepath, 'r') as f:
        content = f.read()
    
    # Line 86: Remove redundant *, body
    content = content.replace(
        '"SELECT *, body FROM content_unified WHERE id = ?",',
        '"SELECT * FROM content_unified WHERE id = ?",',
    )
    
    # Line 90: Fix dictionary access
    content = content.replace(
        "text = f\"{content['title'] or ''} {content['content_unified'] or ''}\"",
        "text = f\"{content['title'] or ''} {content['body'] or ''}\"",
    )
    
    # Line 179: Remove redundant *, body
    content = content.replace(
        'query = "SELECT *, body FROM content_unified"',
        'query = "SELECT * FROM content_unified"',
    )
    
    with open(filepath, 'w') as f:
        f.write(content)
    
    print(f"✅ Fixed {filepath}")
    return True

def verify_simple_db():
    """Verify SimpleDB get_content is correct."""
    filepath = "shared/simple_db.py"
    
    if not os.path.exists(filepath):
        print(f"❌ {filepath} not found")
        return False
    
    with open(filepath, 'r') as f:
        content = f.read()
    
    # Already fixed in line 440
    if 'FROM content_unified WHERE id = ?' in content:
        print(f"✅ {filepath} already correct")
        return True
    
    print(f"⚠️  {filepath} may need manual review")
    return False

def test_imports():
    """Test that all modules still import correctly."""
    print("\n🧪 Testing imports...")
    
    modules = [
        "tools.scripts.process_embeddings",
        "knowledge_graph.similarity_analyzer",
        "knowledge_graph.topic_clustering",
        "search_intelligence.duplicate_detector",
        "shared.simple_db",
    ]
    
    all_good = True
    for module in modules:
        try:
            exec(f"from {module} import *")
            print(f"  ✅ {module}")
        except ImportError as e:
            print(f"  ❌ {module}: {e}")
            all_good = False
    
    return all_good

def main():
    """Main function."""
    print("🔧 Final Column Reference Cleanup")
    print("=" * 50)
    
    # Fix specific files
    success = True
    
    print("\n📝 Fixing remaining issues...")
    success &= fix_topic_clustering()
    success &= verify_simple_db()
    
    # Test imports
    success &= test_imports()
    
    print("\n" + "=" * 50)
    if success:
        print("✅ All fixes applied successfully!")
        print("\nNext steps:")
        print("1. Run: python3 tools/scripts/process_embeddings.py")
        print("2. Test vector search functionality")
        print("3. Update CHANGELOG.md")
    else:
        print("⚠️  Some issues remain - please review manually")

if __name__ == "__main__":
    main()