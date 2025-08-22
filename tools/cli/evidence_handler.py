"""CLI handler for legal evidence commands.

Direct implementation for vsearch evidence commands.
"""

import json

from legal_evidence import get_evidence_tracker, get_report_generator, get_thread_analyzer


def assign_eids_command(limit: int | None = None):
    """Assign Evidence IDs (EIDs) to all emails."""
    print("📋 Assigning Evidence IDs to emails...")
    
    tracker = get_evidence_tracker()
    result = tracker.assign_eids(limit)
    
    if result['success']:
        print(f"✅ Assigned {result['assigned']} new EIDs")
        if result['total_without_eid'] > result['assigned']:
            remaining = result['total_without_eid'] - result['assigned']
            print(f"ℹ️  {remaining} emails still need EIDs (use higher limit)")
    else:
        print("❌ Failed to assign EIDs")
        
        
def assign_threads_command():
    """Group emails into threads for conversation tracking."""
    print("🔗 Grouping emails into conversation threads...")
    
    tracker = get_evidence_tracker()
    result = tracker.assign_thread_ids()
    
    if result['success']:
        print(f"✅ Created {result['threads_created']} threads")
        print(f"📧 Processed {result['emails_processed']} emails")
    else:
        print("❌ Failed to assign thread IDs")
        

def lookup_command(eid: str | None = None, thread: str | None = None):
    """Look up specific evidence by EID or thread."""
    tracker = get_evidence_tracker()
    
    if eid:
        print(f"🔍 Looking up evidence: {eid}")
        evidence = tracker.get_email_evidence(eid)
        
        if evidence:
            print(f"\n[{evidence['eid']}]")
            print(f"Subject: {evidence['subject']}")
            print(f"Date: {evidence['datetime_utc']}")
            print(f"From: {evidence['sender']}")
            print(f"To: {evidence['recipient_to']}")
            print(f"Thread: {evidence['thread_id']}")
            print(f"Message-ID: <{evidence['message_id']}>")
            
            # Show excerpt
            content = evidence['content'] or ""
            if content:
                excerpt = content[:300]
                if len(content) > 300:
                    excerpt += "..."
                print(f"\nContent Preview:\n{excerpt}")
        else:
            print(f"❌ No evidence found for EID: {eid}")
            
    elif thread:
        print(f"🔍 Looking up thread: {thread}")
        emails = tracker.get_thread_emails(thread)
        
        if emails:
            print(f"\nFound {len(emails)} emails in thread")
            print("-" * 50)
            
            for email in emails:
                print(f"[{email['eid']}] {email['datetime_utc'][:10]} - {email['sender']}")
                print(f"  Subject: {email['subject']}")
                
                # Show brief excerpt
                content = email['content'] or ""
                if content:
                    excerpt = content[:100].replace('\n', ' ')
                    if len(content) > 100:
                        excerpt += "..."
                    print(f"  > {excerpt}")
                print()
        else:
            print(f"❌ No emails found for thread: {thread}")
    else:
        print("❌ Please specify --eid or --thread")
        

def report_command(output_dir: str = "legal_evidence_export",
                  keywords: list[str] | None = None,
                  threads: list[str] | None = None,
                  mode: str = "both"):
    """Generate legal evidence reports."""
    print("📄 Generating legal evidence reports...")
    
    generator = get_report_generator()
    
    # Parse keywords if provided as comma-separated
    if keywords and len(keywords) == 1 and ',' in keywords[0]:
        keywords = [k.strip() for k in keywords[0].split(',')]
        
    # Parse threads if provided as comma-separated
    if threads and len(threads) == 1 and ',' in threads[0]:
        threads = [t.strip() for t in threads[0].split(',')]
    
    if mode == "export":
        # Full export package
        result = generator.export_evidence_package(output_dir, threads, keywords)
        
        if result['success']:
            print(f"✅ Evidence package created in: {result['output_dir']}")
            print(f"📁 {result['files_created']} files generated")
            print(f"⏰ Timestamp: {result['timestamp']}")
        else:
            print("❌ Failed to generate evidence package")
            
    else:
        # Generate and display reports
        if mode in ["lookup", "both"]:
            print("\n=== LOOKUP REPORT ===")
            lookup_report = generator.generate_lookup_report(threads, keywords)
            print(lookup_report)
            
        if mode in ["narrative", "both"]:
            if keywords:
                print("\n=== NARRATIVE REPORT ===")
                narrative_report = generator.generate_narrative_report(keywords)
                print(narrative_report)
            else:
                print("ℹ️  Narrative report requires keywords")
                

def search_pattern_command(pattern: str, limit: int = 100):
    """Search for specific patterns in emails (for discovery)."""
    print(f"🔍 Searching for pattern: '{pattern}'")
    
    tracker = get_evidence_tracker()
    results = tracker.search_by_pattern(pattern, limit)
    
    if results:
        print(f"✅ Found {len(results)} matches")
        print("-" * 50)
        
        for result in results[:10]:  # Show first 10
            print(f"[{result['eid']}] {result['datetime_utc'][:10]} - {result['sender']}")
            print(f"  Subject: {result['subject']}")
            print(f"  Thread: {result['thread_id']}")
            
            # Highlight pattern in content
            content = result['content'] or ""
            import re
            sentences = re.split(r'[.!?]+', content)
            for sentence in sentences:
                if pattern.lower() in sentence.lower():
                    excerpt = sentence.strip()[:150]
                    print(f"  > ...{excerpt}...")
                    break
            print()
            
        if len(results) > 10:
            print(f"... and {len(results) - 10} more results")
    else:
        print(f"❌ No matches found for pattern: '{pattern}'")
        

def analyze_thread_command(thread_id: str, output_format: str = "text"):
    """Analyze a specific thread for patterns and contradictions."""
    print(f"🔬 Analyzing thread: {thread_id}")
    
    analyzer = get_thread_analyzer()
    
    # Get thread summary
    summary = analyzer.get_thread_summary(thread_id)
    
    if 'error' in summary:
        print(f"❌ {summary['error']}")
        return
        
    if output_format == "json":
        print(json.dumps(summary, indent=2, default=str))
    else:
        # Get narrative
        narrative = analyzer.get_chronological_narrative(thread_id)
        print(narrative)
        
        
def status_command():
    """Show evidence tracking status."""
    tracker = get_evidence_tracker()
    stats = tracker.get_evidence_summary()
    
    print("📊 Legal Evidence Status")
    print("-" * 30)
    print(f"Emails with EID: {stats['emails_with_eid']}")
    print(f"Emails without EID: {stats['emails_without_eid']}")
    print(f"Total threads: {stats['total_threads']}")
    
    if stats['date_range']['earliest'] and stats['date_range']['latest']:
        print(f"Date range: {stats['date_range']['earliest'][:10]} to {stats['date_range']['latest'][:10]}")
    
    print("\n💡 Next steps:")
    if stats['emails_without_eid'] > 0:
        print(f"  - Run 'vsearch evidence assign-eids' to assign {stats['emails_without_eid']} missing EIDs")
    if stats['total_threads'] == 0:
        print("  - Run 'vsearch evidence assign-threads' to group emails into conversations")
    if stats['emails_with_eid'] > 0:
        print("  - Run 'vsearch evidence report --keywords \"entry,access\"' to generate evidence reports")