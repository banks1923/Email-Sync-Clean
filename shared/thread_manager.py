"""
Thread Management and Timeline Reconstruction
Handles email threading, deduplication, and chronological ordering
"""

import hashlib
import re
from datetime import datetime
from typing import Any, Dict, List

from .email_parser import QuotedMessage


class ThreadService:
    """
    Manages email threading and conversation grouping.
    """

    def __init__(self):
        self.reference_map: Dict[str, str] = {}
        self.subject_threads: Dict[str, str] = {}
        self.next_thread_id = 1
        self._normalized_cache: Dict[str, str] = {}

    def get_thread_id(self, email: Dict[str, Any]) -> str:
        """
        Determine thread ID for an email based on headers and subject.
        """
        message_id = email.get("message_id", "")
        
        # Check References header first
        references = email.get("references", "")
        if references:
            ref_ids = references.split()
            if ref_ids:
                # Use the first reference as thread root
                root_ref = ref_ids[0].strip("<>")
                if root_ref in self.reference_map:
                    thread_id = self.reference_map[root_ref]
                else:
                    thread_id = f"ref-{self.next_thread_id}"
                    self.next_thread_id += 1
                    self.reference_map[root_ref] = thread_id
                
                self.reference_map[message_id] = thread_id
                return thread_id

        # Check In-Reply-To header
        in_reply_to = email.get("in_reply_to", "")
        if in_reply_to:
            reply_id = in_reply_to.strip("<>")
            if reply_id in self.reference_map:
                thread_id = self.reference_map[reply_id]
                self.reference_map[message_id] = thread_id
                return thread_id

        # Fallback to subject-based threading
        subject = email.get("subject", "")
        if subject:
            normalized_subject = self._normalize_subject(subject)
            if normalized_subject:
                if normalized_subject in self.subject_threads:
                    thread_id = self.subject_threads[normalized_subject]
                    self.reference_map[message_id] = thread_id
                    return thread_id
                else:
                    # Create a new subject-based thread
                    thread_id = f"subject-{self.next_thread_id}"
                    self.next_thread_id += 1
                    self.subject_threads[normalized_subject] = thread_id
                    self.reference_map[message_id] = thread_id
                    return thread_id

        # Create a singleton thread for this message
        thread_id = (
            f"singleton-{message_id[-8:]}"
            if len(message_id) > 8
            else f"singleton-{self.next_thread_id}"
        )
        self.next_thread_id += 1
        self.reference_map[message_id] = thread_id
        return thread_id

    def _normalize_subject(self, subject: str) -> str:
        """Normalize email subject by removing prefixes like Re:, Fwd:, etc."""
        if not subject:
            return ""
        if subject in self._normalized_cache:
            return self._normalized_cache[subject]

        # Remove common prefixes
        prefixes = [
            r"^re:\s*",
            r"^fwd:\s*", 
            r"^fw:\s*",
            r"^reply:\s*",
            r"^\[\w+\]\s*",  # [Tag] pattern
        ]

        normalized = subject.lower()

        for pattern in prefixes:
            normalized = re.sub(pattern, "", normalized, flags=re.IGNORECASE)

        normalized = normalized.strip()
        self._normalized_cache[subject] = normalized
        return normalized


def reconstruct_thread_timeline(emails: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Reconstruct chronological timeline of email thread with individual messages.
    """
    timeline = []
    
    for email in emails:
        # Add the main email
        timeline.append({
            "message_id": email.get("message_id"),
            "thread_id": email.get("thread_id"),
            "sender": email.get("sender"),
            "subject": email.get("subject"),
            "date": email.get("datetime_utc", email.get("date")),
            "content": email.get("content", ""),
            "type": "email"
        })
        
        # If email has conversation messages, add them
        if "conversation_messages" in email:
            for i, msg in enumerate(email["conversation_messages"]):
                timeline.append({
                    "message_id": f"{email.get('message_id')}-msg-{i}",
                    "thread_id": email.get("thread_id"),
                    "sender": msg.get("sender", email.get("sender")),
                    "subject": email.get("subject"),
                    "date": msg.get("date", email.get("datetime_utc")),
                    "content": msg.get("content", ""),
                    "type": "extracted_message",
                    "depth": msg.get("depth", 0),
                    "parent_email": email.get("message_id")
                })
    
    # Sort by date
    def sort_key(msg):
        date_str = msg.get("date", "")
        if not date_str:
            return datetime.min
        
        try:
            # Handle different date formats
            if isinstance(date_str, str):
                # Try common formats
                formats = [
                    "%Y-%m-%d %H:%M:%S+00:00",
                    "%Y-%m-%d %H:%M:%S", 
                    "%a, %d %b %Y %H:%M:%S %z",
                    "%d %b %Y %H:%M:%S"
                ]
                for fmt in formats:
                    try:
                        return datetime.strptime(date_str, fmt)
                    except ValueError:
                        continue
                return datetime.min
            return date_str
        except:
            return datetime.min
    
    timeline.sort(key=sort_key)
    return timeline


def deduplicate_messages(
    messages: List[Dict[str, Any]], 
    similarity_threshold: float = 0.85,
    preserve_metadata: bool = True
) -> List[Dict[str, Any]]:
    """
    Remove duplicate messages while preserving the most complete version.
    
    Args:
        messages: List of message dictionaries
        similarity_threshold: Minimum similarity to consider duplicates (0.0-1.0)
        preserve_metadata: Keep message with most metadata when deduplicating
    
    Returns:
        Deduplicated list of messages
    """
    if not messages:
        return []
    
    unique_messages = []
    processed_hashes = set()
    
    for message in messages:
        content = message.get("content", "")
        if not content.strip():
            continue
        
        # Create content hash for exact duplicates
        content_hash = hashlib.sha256(content.encode('utf-8')).hexdigest()
        
        # Skip exact duplicates
        if content_hash in processed_hashes:
            continue
        
        # Check for similar messages
        is_duplicate = False
        for i, existing in enumerate(unique_messages):
            similarity = _calculate_similarity(content, existing.get("content", ""))
            
            if similarity >= similarity_threshold:
                is_duplicate = True
                
                # Replace with message that has more metadata
                if preserve_metadata:
                    existing_metadata_count = sum(1 for v in existing.values() if v)
                    new_metadata_count = sum(1 for v in message.values() if v)
                    
                    if new_metadata_count > existing_metadata_count:
                        unique_messages[i] = message
                
                break
        
        if not is_duplicate:
            unique_messages.append(message)
            processed_hashes.add(content_hash)
    
    return unique_messages


def _calculate_similarity(text1: str, text2: str) -> float:
    """
    Calculate similarity between two texts using simple word overlap.
    Returns value between 0.0 and 1.0.
    """
    if not text1 or not text2:
        return 0.0
    
    # Simple word-based similarity
    words1 = set(text1.lower().split())
    words2 = set(text2.lower().split())
    
    if not words1 or not words2:
        return 0.0
    
    intersection = words1 & words2
    union = words1 | words2
    
    return len(intersection) / len(union) if union else 0.0


def quoted_message_to_dict(message: 'QuotedMessage') -> Dict[str, Any]:
    """Convert QuotedMessage object to dictionary for processing."""
    return {
        "content": message.content,
        "sender": message.sender,
        "date": message.date,
        "subject": message.subject,
        "message_type": message.message_type,
        "depth": message.depth,
        "raw_header": message.raw_header,
        "email_id": message.email_id,
        "thread_id": message.thread_id
    }

def extract_thread_messages(thread_emails: List[Dict[str, Any]]) -> List[QuotedMessage]:
    """
    Extract all individual messages from a thread of emails.
    
    Args:
        thread_emails: List of email dictionaries from same thread
        
    Returns:
        List of individual QuotedMessage objects
    """
    from .email_parser import parse_conversation_chain
    
    all_messages = []
    
    for email in thread_emails:
        content = email.get('body', email.get('content', ''))
        if not content:
            continue
            
        # Parse individual messages from this email
        messages = parse_conversation_chain(content)
        
        # Add context from parent email
        for msg in messages:
            msg.email_id = email.get('message_id')
            msg.thread_id = email.get('thread_id')
            
            # Use email subject if message doesn't have one
            if not msg.subject:
                msg.subject = email.get('subject', '')
                
            # Use email sender if message doesn't have one  
            if not msg.sender:
                msg.sender = email.get('sender', '')
                
            # Use email date if message doesn't have one
            if not msg.date:
                msg.date = email.get('datetime_utc', '')
        
        all_messages.extend(messages)
    
    return all_messages


def find_ignored_messages(thread_messages: List[QuotedMessage]) -> List[Dict[str, Any]]:
    """
    Find messages in a thread that were never replied to.
    This helps identify selective reply patterns in harassment cases.
    """
    ignored = []
    
    # Sort messages chronologically
    sorted_messages = sorted(
        thread_messages,
        key=lambda x: x.date or "",
        reverse=False
    )
    
    for i, message in enumerate(sorted_messages):
        # Check if this message was replied to
        has_reply = False
        
        # Look for later messages that might be replies
        for later_msg in sorted_messages[i+1:]:
            # Simple heuristic: if later message quotes this one or mentions sender
            if (message.content[:50] in later_msg.content or 
                (message.sender and message.sender in later_msg.content)):
                has_reply = True
                break
        
        if not has_reply and message.content.strip():
            ignored.append({
                "message": message,
                "sender": message.sender,
                "date": message.date,
                "content_preview": message.content[:100] + "..." if len(message.content) > 100 else message.content
            })
    
    return ignored