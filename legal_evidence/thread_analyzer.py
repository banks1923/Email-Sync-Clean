"""Thread Analyzer - Groups and analyzes email conversations for legal evidence.

Simple implementation for identifying patterns in email threads.
"""

import re
from typing import Dict, List, Any, Optional
from collections import defaultdict
from datetime import datetime
from loguru import logger

from shared.simple_db import SimpleDB


class ThreadAnalyzer:
    """Analyze email threads for patterns and legal significance."""
    
    def __init__(self, db_path: str = "data/emails.db"):
        """Initialize with database connection."""
        self.db = SimpleDB(db_path)
        
    def get_thread_summary(self, thread_id: str) -> Dict[str, Any]:
        """Get comprehensive summary of a thread."""
        # Get all emails in thread
        cursor = self.db.execute("""
            SELECT eid, message_id, subject, sender, recipient_to,
                   datetime_utc, content
            FROM emails
            WHERE thread_id = ?
            ORDER BY datetime_utc
        """, (thread_id,))
        
        emails = [dict(row) for row in cursor.fetchall()]
        
        if not emails:
            return {"error": f"No emails found for thread {thread_id}"}
            
        # Analyze thread
        participants = set()
        subjects = []
        date_range = {
            'start': emails[0]['datetime_utc'],
            'end': emails[-1]['datetime_utc']
        }
        
        for email in emails:
            participants.add(email['sender'])
            if email['recipient_to']:
                participants.add(email['recipient_to'])
            subjects.append(email['subject'])
            
        # Find common subject (remove Re:, Fwd:)
        base_subject = subjects[0] if subjects else ""
        base_subject = re.sub(r'^(Re:|Fwd:|Fw:)\s*', '', base_subject, flags=re.IGNORECASE).strip()
        
        return {
            'thread_id': thread_id,
            'email_count': len(emails),
            'participants': list(participants),
            'base_subject': base_subject,
            'date_range': date_range,
            'emails': emails
        }
    
    def find_disputed_topics(self, keywords: List[str]) -> Dict[str, List[Dict]]:
        """Find threads containing disputed topics based on keywords."""
        disputed_threads = defaultdict(list)
        
        for keyword in keywords:
            cursor = self.db.execute("""
                SELECT DISTINCT thread_id, eid, subject, sender, datetime_utc,
                       content
                FROM emails
                WHERE (content LIKE ? OR subject LIKE ?)
                AND thread_id IS NOT NULL
                ORDER BY thread_id, datetime_utc
            """, (f"%{keyword}%", f"%{keyword}%"))
            
            for row in cursor:
                thread_data = dict(row)
                # Extract relevant excerpt
                content = thread_data['content'] or ""
                
                # Find sentence containing keyword
                sentences = re.split(r'[.!?]+', content)
                excerpt = ""
                for sentence in sentences:
                    if keyword.lower() in sentence.lower():
                        excerpt = sentence.strip()
                        break
                        
                thread_data['excerpt'] = excerpt[:200] if excerpt else ""
                thread_data['keyword'] = keyword
                
                disputed_threads[thread_data['thread_id']].append(thread_data)
                
        return dict(disputed_threads)
    
    def analyze_communication_patterns(self, sender: Optional[str] = None) -> Dict[str, Any]:
        """Analyze communication patterns for specific sender or all."""
        query = """
            SELECT sender, recipient_to, datetime_utc, thread_id, subject
            FROM emails
        """
        params = ()
        
        if sender:
            query += " WHERE sender = ?"
            params = (sender,)
            
        query += " ORDER BY datetime_utc"
        
        cursor = self.db.execute(query, params)
        emails = [dict(row) for row in cursor.fetchall()]
        
        # Analyze patterns
        patterns = {
            'total_emails': len(emails),
            'senders': defaultdict(int),
            'recipients': defaultdict(int),
            'threads': defaultdict(int),
            'time_distribution': defaultdict(int),
            'subject_patterns': defaultdict(int)
        }
        
        for email in emails:
            patterns['senders'][email['sender']] += 1
            if email['recipient_to']:
                patterns['recipients'][email['recipient_to']] += 1
            if email['thread_id']:
                patterns['threads'][email['thread_id']] += 1
                
            # Time analysis (hour of day)
            if email['datetime_utc']:
                try:
                    dt = datetime.fromisoformat(email['datetime_utc'].replace('Z', '+00:00'))
                    hour = dt.hour
                    patterns['time_distribution'][f"{hour:02d}:00"] += 1
                except:
                    pass
                    
            # Subject pattern analysis
            subject = email['subject'] or ""
            if 'entry' in subject.lower() or 'access' in subject.lower():
                patterns['subject_patterns']['access_related'] += 1
            if 'repair' in subject.lower() or 'maintenance' in subject.lower():
                patterns['subject_patterns']['maintenance_related'] += 1
            if 'notice' in subject.lower():
                patterns['subject_patterns']['notices'] += 1
            if 'complaint' in subject.lower():
                patterns['subject_patterns']['complaints'] += 1
                
        # Convert defaultdicts to regular dicts for clean output
        return {
            'total_emails': patterns['total_emails'],
            'unique_senders': len(patterns['senders']),
            'unique_recipients': len(patterns['recipients']),
            'total_threads': len(patterns['threads']),
            'top_senders': dict(sorted(patterns['senders'].items(), key=lambda x: x[1], reverse=True)[:5]),
            'time_distribution': dict(patterns['time_distribution']),
            'subject_patterns': dict(patterns['subject_patterns'])
        }
    
    def get_chronological_narrative(self, thread_id: str) -> str:
        """Generate chronological narrative of thread for legal documents."""
        summary = self.get_thread_summary(thread_id)
        
        if 'error' in summary:
            return summary['error']
            
        narrative = []
        narrative.append(f"## Thread: {summary['base_subject']}")
        narrative.append(f"**Period**: {summary['date_range']['start']} to {summary['date_range']['end']}")
        narrative.append(f"**Participants**: {', '.join(summary['participants'])}")
        narrative.append(f"**Total Exchanges**: {summary['email_count']}")
        narrative.append("")
        narrative.append("### Chronological Exchange:")
        narrative.append("")
        
        for email in summary['emails']:
            narrative.append(f"**[{email['eid']}]** - {email['datetime_utc']}")
            narrative.append(f"**From**: {email['sender']}")
            narrative.append(f"**Subject**: {email['subject']}")
            
            # Extract key quote (first 2 sentences)
            content = email['content'] or ""
            sentences = re.split(r'[.!?]+', content)[:2]
            quote = '. '.join(s.strip() for s in sentences if s.strip())
            
            if quote:
                narrative.append(f"> {quote}")
            narrative.append("")
            
        return "\n".join(narrative)
    
    def find_contradictions(self, thread_id: str, topics: List[str]) -> List[Dict[str, Any]]:
        """Find potential contradictions in a thread about specific topics."""
        cursor = self.db.execute("""
            SELECT eid, sender, datetime_utc, content
            FROM emails
            WHERE thread_id = ?
            ORDER BY datetime_utc
        """, (thread_id,))
        
        emails = [dict(row) for row in cursor.fetchall()]
        contradictions = []
        
        # Track statements by sender and topic
        statements = defaultdict(lambda: defaultdict(list))
        
        for email in emails:
            content = email['content'] or ""
            sender = email['sender']
            
            for topic in topics:
                if topic.lower() in content.lower():
                    # Extract sentences about topic
                    sentences = re.split(r'[.!?]+', content)
                    for sentence in sentences:
                        if topic.lower() in sentence.lower():
                            statements[sender][topic].append({
                                'eid': email['eid'],
                                'date': email['datetime_utc'],
                                'statement': sentence.strip()
                            })
                            
        # Look for contradictions (simplified - looks for different statements by same sender)
        for sender, topics_dict in statements.items():
            for topic, statement_list in topics_dict.items():
                if len(statement_list) > 1:
                    # Check for potentially contradictory keywords
                    has_positive = any('yes' in s['statement'].lower() or 
                                     'agree' in s['statement'].lower() or
                                     'allow' in s['statement'].lower() or
                                     'free' in s['statement'].lower()
                                     for s in statement_list)
                    has_negative = any('no' in s['statement'].lower() or 
                                     'disagree' in s['statement'].lower() or
                                     'deny' in s['statement'].lower() or
                                     'require' in s['statement'].lower()
                                     for s in statement_list)
                                     
                    if has_positive and has_negative:
                        contradictions.append({
                            'sender': sender,
                            'topic': topic,
                            'statements': statement_list
                        })
                        
        return contradictions


# Simple factory function
def get_thread_analyzer(db_path: str = "data/emails.db") -> ThreadAnalyzer:
    """Get thread analyzer instance."""
    return ThreadAnalyzer(db_path)