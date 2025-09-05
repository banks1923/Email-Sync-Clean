#!/usr/bin/env python3
"""
Stoneman Dispute Legal Search Tool
Quick search and analysis for the mold/habitability case
"""
import sqlite3
import re
from pathlib import Path
from datetime import datetime
import json

# Your case documents
STONEMAN_DIR = Path("/Users/jim/Projects/Litigator_solo/data/Stoneman_dispute")

def setup_database():
    """Index all Stoneman documents for quick searching"""
    conn = sqlite3.connect('data/stoneman.db')
    
    # Create FTS5 table with case-specific fields
    conn.execute('''
        CREATE VIRTUAL TABLE IF NOT EXISTS docs USING fts5(
            path, 
            content, 
            doc_type,
            date_mentioned,
            parties_mentioned,
            violations_mentioned,
            tokenize='porter unicode61'
        )
    ''')
    
    # Index all text files
    count = 0
    for subdir in ['Plain_txt_summaries', 'Cleaned docs and text']:
        dir_path = STONEMAN_DIR / subdir
        if dir_path.exists():
            for file in dir_path.glob("*.txt"):
                content = file.read_text(errors='ignore')
                
                # Extract dates
                dates = re.findall(r'\b(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2},\s+\d{4}\b', content)
                dates += re.findall(r'\b\d{1,2}/\d{1,2}/\d{4}\b', content)
                
                # Extract key parties
                parties = []
                if re.search(r'\bDean\b', content, re.I): parties.append('Dean')
                if re.search(r'\bBrad\b', content, re.I): parties.append('Brad')
                if re.search(r'\bJen\b|\bJennifer\b', content, re.I): parties.append('Jennifer')
                if re.search(r'\bJim\b|\bJames\b', content, re.I): parties.append('James')
                if re.search(r'\bBurbank\b', content, re.I): parties.append('Burbank')
                if re.search(r'\bStoneman\b', content, re.I): parties.append('Stoneman')
                
                # Detect violations/issues
                violations = []
                if re.search(r'mold', content, re.I): violations.append('mold')
                if re.search(r'Civil Code.{0,10}1954', content): violations.append('CC1954')
                if re.search(r'Civil Code.{0,10}1942', content): violations.append('CC1942')
                if re.search(r'IICRC', content): violations.append('IICRC-violation')
                if re.search(r'retaliat', content, re.I): violations.append('retaliation')
                if re.search(r'habitab', content, re.I): violations.append('habitability')
                
                conn.execute(
                    'INSERT INTO docs VALUES (?, ?, ?, ?, ?, ?)',
                    (
                        str(file),
                        content,
                        subdir,
                        '|'.join(dates[:5]),  # First 5 dates
                        '|'.join(parties),
                        '|'.join(violations)
                    )
                )
                count += 1
    
    conn.commit()
    print(f"✅ Indexed {count} documents")
    return conn

def search(query, show_context=True):
    """Search with legal context"""
    conn = sqlite3.connect('data/stoneman.db')
    
    # Search with snippet
    if show_context:
        results = conn.execute('''
            SELECT 
                path,
                snippet(docs, 1, ">>>", "<<<", "...", 30) as snippet,
                parties_mentioned,
                violations_mentioned
            FROM docs 
            WHERE content MATCH ? 
            ORDER BY rank
            LIMIT 20
        ''', (query,)).fetchall()
    else:
        results = conn.execute('''
            SELECT path, parties_mentioned, violations_mentioned
            FROM docs 
            WHERE content MATCH ? 
            ORDER BY rank
        ''', (query,)).fetchall()
    
    return results

def find_contradictions():
    """Find potential contradictions in Dean/Brad's statements"""
    conn = sqlite3.connect('data/stoneman.db')
    
    print("\n🔍 SEARCHING FOR CONTRADICTIONS...")
    
    # Search for Dean's claims about mold
    dean_mold = conn.execute('''
        SELECT path, snippet(docs, 1, ">>>", "<<<", "...", 40) 
        FROM docs 
        WHERE content MATCH 'Dean AND (mold OR certified OR inspector)'
        ORDER BY rank
    ''').fetchall()
    
    print("\n📋 Dean's Claims About Mold/Certification:")
    for path, snippet in dean_mold[:5]:
        print(f"  • {Path(path).name}: {snippet}")
    
    # Search for repair completion claims vs excuses
    repair_claims = conn.execute('''
        SELECT path, snippet(docs, 1, ">>>", "<<<", "...", 40)
        FROM docs 
        WHERE content MATCH 'repair AND (complete OR finished OR done)'
    ''').fetchall()
    
    repair_excuses = conn.execute('''
        SELECT path, snippet(docs, 1, ">>>", "<<<", "...", 40)
        FROM docs 
        WHERE content MATCH 'repair AND (delay OR cancel OR postpone OR unable)'
    ''').fetchall()
    
    print(f"\n⚠️  Repair Claims: {len(repair_claims)} vs Repair Excuses: {len(repair_excuses)}")
    
def build_timeline():
    """Extract chronological events for the case"""
    conn = sqlite3.connect('data/stoneman.db')
    
    events = []
    
    # Get all documents with dates
    docs = conn.execute('''
        SELECT path, content, date_mentioned 
        FROM docs 
        WHERE date_mentioned != ''
    ''').fetchall()
    
    for path, content, dates_str in docs:
        if dates_str:
            dates = dates_str.split('|')
            for date in dates:
                # Find sentence containing this date
                pattern = re.escape(date)
                matches = re.finditer(f'[^.]*{pattern}[^.]*\.', content)
                for match in matches:
                    events.append({
                        'date': date,
                        'event': match.group().strip(),
                        'source': Path(path).name
                    })
    
    # Sort and save
    events = sorted(events, key=lambda x: x['date'])
    
    with open('stoneman_timeline.txt', 'w') as f:
        f.write("STONEMAN CASE TIMELINE\n")
        f.write("=" * 50 + "\n\n")
        
        for event in events:
            f.write(f"DATE: {event['date']}\n")
            f.write(f"EVENT: {event['event']}\n")
            f.write(f"SOURCE: {event['source']}\n")
            f.write("-" * 30 + "\n")
    
    print(f"✅ Timeline with {len(events)} events saved to stoneman_timeline.txt")

def analyze_recording_issues():
    """Analyze recording consent and admissibility issues"""
    conn = sqlite3.connect('data/stoneman.db')
    
    print("\n📹 RECORDING & CONSENT ANALYSIS")
    print("=" * 50)
    
    # Find all recording-related content
    recording = conn.execute('''
        SELECT path, snippet(docs, 1, ">>>", "<<<", "...", 50)
        FROM docs 
        WHERE content MATCH 'recording OR camera OR consent OR video OR audio'
        ORDER BY rank
    ''').fetchall()
    
    for path, snippet in recording[:10]:
        print(f"\n{Path(path).name}:")
        print(f"  {snippet}")

def find_health_impacts():
    """Extract all health-related impacts for damages"""
    conn = sqlite3.connect('data/stoneman.db')
    
    print("\n🏥 HEALTH IMPACT DOCUMENTATION")
    print("=" * 50)
    
    health = conn.execute('''
        SELECT path, snippet(docs, 1, ">>>", "<<<", "...", 50)
        FROM docs 
        WHERE content MATCH 'respiratory OR health OR medical OR child OR symptoms OR cough'
        ORDER BY rank
    ''').fetchall()
    
    for path, snippet in health[:10]:
        if 'respiratory' in snippet.lower() or 'symptom' in snippet.lower():
            print(f"\n{Path(path).name}:")
            print(f"  {snippet}")

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("""
Stoneman Legal Search Tool
==========================
Usage:
  python stoneman_search.py setup              # First time setup
  python stoneman_search.py search "term"      # Search documents
  python stoneman_search.py timeline           # Build timeline
  python stoneman_search.py contradictions     # Find contradictions
  python stoneman_search.py recording          # Recording issues
  python stoneman_search.py health             # Health impacts
        """)
    elif sys.argv[1] == "setup":
        setup_database()
    elif sys.argv[1] == "search" and len(sys.argv) > 2:
        query = ' '.join(sys.argv[2:])
        results = search(query)
        for path, snippet, parties, violations in results:
            print(f"\n📄 {Path(path).name}")
            if parties: print(f"   Parties: {parties}")
            if violations: print(f"   Issues: {violations}")
            print(f"   {snippet}")
    elif sys.argv[1] == "timeline":
        build_timeline()
    elif sys.argv[1] == "contradictions":
        find_contradictions()
    elif sys.argv[1] == "recording":
        analyze_recording_issues()
    elif sys.argv[1] == "health":
        find_health_impacts()
