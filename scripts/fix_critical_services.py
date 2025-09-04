#!/usr/bin/env python3
"""
Fix critical services that reference legacy tables.
This script identifies and reports what needs to be fixed in each file.
"""

import re
from pathlib import Path
from typing import List, Tuple

# Critical files that need immediate fixing
CRITICAL_FILES = [
    "gmail/storage.py",
    "legal_evidence/evidence_tracker.py", 
    "legal_evidence/thread_analyzer.py",
    "search_intelligence/duplicate_detector.py",
    "search_intelligence/similarity.py",
    "entity/database.py",
    "utilities/timeline/main.py",
]

# Patterns to find and their replacements
REPLACEMENTS = [
    # Table references
    (r'\bFROM\s+emails\b', 'FROM individual_messages im JOIN content_unified cu ON cu.source_id = im.message_hash'),
    (r'\bJOIN\s+emails\b', 'JOIN individual_messages im JOIN content_unified cu ON cu.source_id = im.message_hash'),
    (r'INSERT\s+INTO\s+emails\b', 'INSERT INTO individual_messages /* FIXME: needs full rewrite */'),
    (r'UPDATE\s+emails\b', 'UPDATE individual_messages /* FIXME: needs JOIN rewrite */'),
    
    # Entity table
    (r'\bemail_entities\b', 'entity_content_mapping /* FIXME: different schema */'),
    
    # Plural form
    (r'\bemail_messages\b', 'email_message'),
    (r"source_type\s*=\s*'email_messages'", "source_type = 'email_message'"),
    
    # Common field mappings
    (r'emails\.message_id', 'im.message_id'),
    (r'emails\.subject', 'im.subject'),
    (r'emails\.content', 'cu.body'),
    (r'emails\.sender', 'im.sender_email'),
]


def analyze_file(filepath: Path) -> List[Tuple[int, str, str]]:
    """Analyze a file for legacy patterns."""
    issues = []
    
    try:
        with open(filepath, 'r') as f:
            lines = f.readlines()
        
        for line_num, line in enumerate(lines, 1):
            for pattern, replacement in REPLACEMENTS:
                if re.search(pattern, line, re.IGNORECASE):
                    issues.append((line_num, line.strip(), pattern))
    
    except Exception as e:
        print(f"Error reading {filepath}: {e}")
    
    return issues


def generate_fix_report():
    """Generate a report of what needs fixing."""
    print("=" * 80)
    print("CRITICAL SERVICE FIX REPORT")
    print("=" * 80)
    
    total_issues = 0
    
    for file_path in CRITICAL_FILES:
        full_path = Path(file_path)
        if not full_path.exists():
            print(f"\n❌ NOT FOUND: {file_path}")
            continue
        
        issues = analyze_file(full_path)
        if issues:
            print(f"\n📄 {file_path} ({len(issues)} issues)")
            print("-" * 60)
            
            for line_num, line_text, pattern in issues[:5]:  # Show first 5
                print(f"  Line {line_num}: {pattern}")
                print(f"    {line_text[:80]}...")
            
            if len(issues) > 5:
                print(f"  ... and {len(issues) - 5} more issues")
            
            total_issues += len(issues)
    
    print("\n" + "=" * 80)
    print(f"TOTAL ISSUES: {total_issues}")
    print("=" * 80)
    
    print("\n📋 NEXT STEPS:")
    print("1. Each file needs manual SQL JOIN fixes")
    print("2. Use patterns from docs/README_SQL.md")
    print("3. Test each fix with: python3 tests/test_no_legacy_tables.py")
    print("4. Commit fixes with: 'fix: migrate [service] to v2 schema'")


def generate_fix_stub(file_path: str):
    """Generate a fix stub for a specific file."""
    print(f"\n🔧 FIX STUB for {file_path}:")
    print("=" * 60)
    
    if "storage.py" in file_path:
        print("""
# Replace store_email method:
def store_email(self, email_data):
    # Step 1: Generate message_hash
    message_hash = self._compute_message_hash(email_data)
    
    # Step 2: Store in individual_messages
    self.db.execute('''
        INSERT OR IGNORE INTO individual_messages (
            message_hash, content, subject, sender_email,
            recipients, date_sent, message_id, thread_id
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    ''', (...))
    
    # Step 3: Store in content_unified
    self.db.execute('''
        INSERT OR IGNORE INTO content_unified (
            source_type, source_id, title, body, 
            substantive_text, sha256, created_at
        ) VALUES ('email_message', ?, ?, ?, ?, ?, ?)
    ''', (message_hash, ...))
""")
    
    elif "evidence_tracker" in file_path:
        print("""
# Replace get_emails_by_eid:
def get_emails_by_eid(self, eid):
    return self.db.fetch('''
        SELECT im.*, cu.body
        FROM individual_messages im
        JOIN content_unified cu ON cu.source_id = im.message_hash
        WHERE cu.source_type = 'email_message'
          AND im.eid = ?
        ORDER BY im.date_sent DESC
    ''', (eid,))
""")
    
    elif "entity/database" in file_path:
        print("""
# Replace store_entities:
def store_entities(self, message_hash, entities):
    for entity in entities:
        self.db.execute('''
            INSERT INTO entity_content_mapping (
                content_id, entity_type, entity_text,
                start_char, end_char, confidence
            ) VALUES (?, ?, ?, ?, ?, ?)
        ''', (message_hash, entity['type'], entity['text'], ...))
""")


if __name__ == "__main__":
    generate_fix_report()
    
    # Show example fix for most critical service
    print("\n" + "=" * 80)
    print("EXAMPLE FIX PATTERN")
    print("=" * 80)
    generate_fix_stub("gmail/storage.py")