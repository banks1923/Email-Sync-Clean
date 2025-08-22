"""Legal Report Generator - Creates evidence reports with EID references.

Generates both lookup mode (structured references) and report mode (narrative).
"""

import os
import re
from collections import defaultdict
from datetime import datetime
from typing import Any

from loguru import logger

from .evidence_tracker import get_evidence_tracker
from .thread_analyzer import get_thread_analyzer


class LegalReportGenerator:
    """Generate legal evidence reports with traceable EID references."""
    
    def __init__(self, db_path: str = "data/emails.db"):
        """Initialize with evidence tracker and thread analyzer."""
        self.evidence = get_evidence_tracker(db_path)
        self.threads = get_thread_analyzer(db_path)
        
    def generate_lookup_report(self, 
                              thread_ids: list[str] | None = None,
                              keywords: list[str] | None = None) -> str:
        """Generate structured lookup report with EID references.
        
        This is for quick evidence retrieval during legal proceedings.
        """
        report = []
        report.append("# Legal Evidence Lookup Report")
        report.append(f"Generated: {datetime.now().isoformat()}")
        report.append("")
        
        # Get evidence summary
        summary = self.evidence.get_evidence_summary()
        report.append("## Evidence Summary")
        report.append(f"- Total Emails with EID: {summary['emails_with_eid']}")
        report.append(f"- Total Threads: {summary['total_threads']}")
        report.append(f"- Date Range: {summary['date_range']['earliest']} to {summary['date_range']['latest']}")
        report.append("")
        
        # Process specified threads or find disputed ones
        if thread_ids:
            threads_to_process = thread_ids
        elif keywords:
            disputed = self.threads.find_disputed_topics(keywords)
            threads_to_process = list(disputed.keys())
        else:
            # Get all threads
            cursor = self.evidence.db.execute("""
                SELECT DISTINCT thread_id FROM emails 
                WHERE thread_id IS NOT NULL 
                ORDER BY thread_id
            """)
            threads_to_process = [row[0] for row in cursor.fetchall()]
            
        report.append("## Thread Evidence")
        report.append("")
        
        for thread_id in threads_to_process[:20]:  # Limit to 20 threads for report size
            thread_summary = self.threads.get_thread_summary(thread_id)
            
            if 'error' in thread_summary:
                continue
                
            report.append(f"### {thread_id}: {thread_summary['base_subject']}")
            report.append(f"**Participants**: {', '.join(thread_summary['participants'])}")
            report.append(f"**Period**: {thread_summary['date_range']['start']} to {thread_summary['date_range']['end']}")
            report.append("")
            
            # List each email with EID and key excerpt
            for email in thread_summary['emails']:
                report.append(f"[{email['eid']}]")
                report.append(f"**Subject**: {email['subject']}")
                report.append(f"**Date**: {email['datetime_utc']}")
                report.append(f"**From**: {email['sender']}")
                report.append(f"**Message-ID**: <{email['message_id']}>")
                
                # Extract key excerpt
                content = email['content'] or ""
                sentences = re.split(r'[.!?]+', content)
                
                # Find most relevant sentence based on keywords if provided
                excerpt = ""
                if keywords:
                    for sentence in sentences:
                        if any(kw.lower() in sentence.lower() for kw in keywords):
                            excerpt = sentence.strip()
                            break
                            
                if not excerpt and sentences:
                    excerpt = sentences[0].strip()
                    
                if excerpt:
                    # Clean up the excerpt
                    excerpt = re.sub(r'\s+', ' ', excerpt)
                    if len(excerpt) > 200:
                        excerpt = excerpt[:197] + "..."
                    report.append(f"> \"{excerpt}\"")
                    
                report.append("")
                
            report.append("---")
            report.append("")
            
        return "\n".join(report)
    
    def generate_narrative_report(self,
                                 disputed_topics: list[str],
                                 focus_senders: list[str] | None = None) -> str:
        """Generate narrative report with pattern analysis for court filing."""
        report = []
        report.append("# Legal Evidence Analysis Report")
        report.append(f"Generated: {datetime.now().isoformat()}")
        report.append("")
        
        # Executive Summary
        report.append("## Executive Summary")
        
        # Find disputed threads
        disputed_threads = self.threads.find_disputed_topics(disputed_topics)
        
        report.append(f"This report analyzes {len(disputed_threads)} email threads ")
        report.append(f"containing discussions about: {', '.join(disputed_topics)}")
        report.append("")
        
        # Communication Patterns
        report.append("## Communication Patterns")
        
        if focus_senders:
            for sender in focus_senders:
                patterns = self.threads.analyze_communication_patterns(sender)
                report.append(f"### {sender}")
                report.append(f"- Total Emails: {patterns['total_emails']}")
                report.append(f"- Threads Participated: {patterns['total_threads']}")
                
                if patterns['subject_patterns']:
                    report.append("- Subject Patterns:")
                    for pattern, count in patterns['subject_patterns'].items():
                        report.append(f"  - {pattern}: {count} occurrences")
                report.append("")
        else:
            patterns = self.threads.analyze_communication_patterns()
            report.append(f"- Total Emails Analyzed: {patterns['total_emails']}")
            report.append(f"- Unique Participants: {patterns['unique_senders'] + patterns['unique_recipients']}")
            report.append(f"- Total Threads: {patterns['total_threads']}")
            report.append("")
            
        # Disputed Topics Analysis
        report.append("## Disputed Topics Analysis")
        report.append("")
        
        for topic in disputed_topics:
            report.append(f"### Topic: \"{topic}\"")
            
            # Find all mentions
            mentions = self.evidence.search_by_pattern(topic, limit=50)
            
            if mentions:
                report.append(f"Found {len(mentions)} emails mentioning this topic.")
                report.append("")
                
                # Group by sender position
                positions = defaultdict(list)
                for mention in mentions:
                    content = mention['content'] or ""
                    
                    # Determine position (simplified)
                    if any(word in content.lower() for word in ['yes', 'agree', 'allow', 'permitted', 'free']):
                        positions['affirmative'].append(mention)
                    elif any(word in content.lower() for word in ['no', 'deny', 'refuse', 'require', 'must']):
                        positions['negative'].append(mention)
                    else:
                        positions['neutral'].append(mention)
                        
                # Report positions
                for position, emails in positions.items():
                    if emails:
                        report.append(f"**{position.capitalize()} Statements** ({len(emails)} instances):")
                        
                        # Show first 3 examples
                        for email in emails[:3]:
                            report.append(f"- {email['eid']} ({email['datetime_utc'][:10]}, {email['sender']})")
                            
                            # Find relevant excerpt
                            content = email['content'] or ""
                            sentences = re.split(r'[.!?]+', content)
                            for sentence in sentences:
                                if topic.lower() in sentence.lower():
                                    excerpt = re.sub(r'\s+', ' ', sentence.strip())
                                    if len(excerpt) > 150:
                                        excerpt = excerpt[:147] + "..."
                                    report.append(f"  > \"{excerpt}\"")
                                    break
                                    
                        report.append("")
                        
            report.append("")
            
        # Contradictions Analysis
        report.append("## Potential Contradictions")
        report.append("")
        
        contradiction_count = 0
        for thread_id in list(disputed_threads.keys())[:10]:  # Check first 10 threads
            contradictions = self.threads.find_contradictions(thread_id, disputed_topics)
            
            if contradictions:
                contradiction_count += len(contradictions)
                
                for contradiction in contradictions:
                    report.append(f"### Contradiction Found: {contradiction['sender']} on \"{contradiction['topic']}\"")
                    
                    for stmt in contradiction['statements']:
                        report.append(f"- {stmt['eid']} ({stmt['date'][:10]}): \"{stmt['statement']}\"")
                        
                    report.append("")
                    
        if contradiction_count == 0:
            report.append("No clear contradictions identified in the analyzed threads.")
            
        report.append("")
        
        # Legal Significance
        report.append("## Legal Significance")
        report.append("")
        report.append("The documented email exchanges demonstrate:")
        report.append("")
        
        # Auto-generate significance points based on patterns
        if len(disputed_threads) > 0:
            report.append(f"1. **Pattern of Communication**: {len(disputed_threads)} separate threads")
            report.append("   discussing disputed topics over the period analyzed.")
            
        if contradiction_count > 0:
            report.append(f"2. **Inconsistent Positions**: {contradiction_count} instances where")
            report.append("   parties changed or contradicted their stated positions.")
            
        # Count total evidence items
        total_evidence = sum(len(emails) for emails in disputed_threads.values())
        report.append(f"3. **Documentary Evidence**: {total_evidence} email exchanges")
        report.append("   with traceable EID references for court submission.")
        
        report.append("")
        report.append("## Evidence References")
        report.append("")
        report.append("All email evidence is identified by unique Evidence IDs (EIDs) in the format")
        report.append("EID-YYYY-NNNN and includes original Message-ID headers for authentication.")
        report.append("Full email content and metadata are preserved in the evidence database.")
        report.append("")
        
        return "\n".join(report)
    
    def export_evidence_package(self, 
                               output_dir: str,
                               thread_ids: list[str] | None = None,
                               keywords: list[str] | None = None) -> dict[str, Any]:
        """Export complete evidence package with all reports and data."""
        os.makedirs(output_dir, exist_ok=True)
        
        # Generate timestamp for filenames
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        files_created = []
        
        # 1. Generate lookup report
        lookup_report = self.generate_lookup_report(thread_ids, keywords)
        lookup_file = os.path.join(output_dir, f"evidence_lookup_{timestamp}.md")
        with open(lookup_file, 'w') as f:
            f.write(lookup_report)
        files_created.append(lookup_file)
        logger.info(f"Created lookup report: {lookup_file}")
        
        # 2. Generate narrative report if keywords provided
        if keywords:
            narrative_report = self.generate_narrative_report(keywords)
            narrative_file = os.path.join(output_dir, f"evidence_narrative_{timestamp}.md")
            with open(narrative_file, 'w') as f:
                f.write(narrative_report)
            files_created.append(narrative_file)
            logger.info(f"Created narrative report: {narrative_file}")
            
        # 3. Export thread chronologies
        threads_dir = os.path.join(output_dir, f"threads_{timestamp}")
        os.makedirs(threads_dir, exist_ok=True)
        
        if thread_ids:
            threads_to_export = thread_ids
        else:
            # Export disputed threads if keywords provided
            if keywords:
                disputed = self.threads.find_disputed_topics(keywords)
                threads_to_export = list(disputed.keys())[:10]  # Limit to 10
            else:
                threads_to_export = []
                
        for thread_id in threads_to_export:
            narrative = self.threads.get_chronological_narrative(thread_id)
            thread_file = os.path.join(threads_dir, f"{thread_id}.md")
            with open(thread_file, 'w') as f:
                f.write(narrative)
            files_created.append(thread_file)
            
        logger.info(f"Exported {len(threads_to_export)} thread chronologies")
        
        # 4. Create index file
        index_content = []
        index_content.append("# Legal Evidence Package")
        index_content.append(f"Generated: {datetime.now().isoformat()}")
        index_content.append("")
        index_content.append("## Contents")
        index_content.append("")
        
        for file in files_created:
            rel_path = os.path.relpath(file, output_dir)
            index_content.append(f"- [{rel_path}]({rel_path})")
            
        index_file = os.path.join(output_dir, "index.md")
        with open(index_file, 'w') as f:
            f.write("\n".join(index_content))
            
        return {
            "success": True,
            "output_dir": output_dir,
            "files_created": len(files_created) + 1,  # +1 for index
            "timestamp": timestamp
        }


# Simple factory function  
def get_report_generator(db_path: str = "data/emails.db") -> LegalReportGenerator:
    """Get report generator instance."""
    return LegalReportGenerator(db_path)