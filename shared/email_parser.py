"""
Email Parsing Core - Extract individual messages from conversation chains
Clean implementation following CLAUDE.md principles: Simple > Complex
"""

import re
from dataclasses import dataclass
from functools import lru_cache
from typing import Any

# Compile regex patterns once for performance
COMPILED_PATTERNS = {
    'zero_width': re.compile(r"[\u200b\u200c\u200d\ufeff]"),
    'html_tags': re.compile(r"<[^<]+?>"),
    'whitespace': re.compile(r"\s+"),
    'excessive_newlines': re.compile(r"\n{3,}"),
    'reply_prefixes': re.compile(r"^(RE:|FW:|FWD:|Re:|Fw:|Fwd:)\s*", re.IGNORECASE),
    'gmail_quote': re.compile(r"^On .+ wrote:$", re.MULTILINE),
    'outlook_quote': re.compile(r"^From:.*?\nSent:.*?\nTo:.*?\nSubject:", re.MULTILINE | re.DOTALL),
    'original_message': re.compile(r"^-{3,}\s*Original Message\s*-{3,}", re.MULTILINE),
    'underscore_sep': re.compile(r"^_{10,}", re.MULTILINE),
    'quote_markers': re.compile(r"^>{1,}", re.MULTILINE),
    'message_id': re.compile(r"<[^<>@\s]+@[^<>\s]+>"),
    'email_address': re.compile(r"<([^>]+)>"),
}

@dataclass
class QuotedMessage:
    """
    Represents an individual message extracted from quoted content.
    """
    content: str
    sender: str | None = None
    date: str | None = None
    subject: str | None = None
    message_type: str = "reply"  # reply, forward, original
    depth: int = 0  # nesting level
    raw_header: str | None = None
    email_id: str | None = None  # Original email ID this came from
    thread_id: str | None = None  # Thread this belongs to


def clean_text(text: str, max_length: int | None = None) -> str:
    """
    Clean text by removing extra whitespace and optionally truncating.
    """
    if not text:
        return ""
        
    # Remove extra whitespace using compiled pattern
    text = COMPILED_PATTERNS['whitespace'].sub(" ", text)

    # Remove zero-width characters using compiled pattern
    text = COMPILED_PATTERNS['zero_width'].sub("", text)

    # Truncate if needed
    if max_length and len(text) > max_length:
        text = text[: max_length - 3] + "..."

    return text.strip()


def extract_domain(email: str) -> str:
    """
    Extract domain from email address.
    """
    if "@" in email:
        return email.split("@")[1].lower()
    return ""


@lru_cache(maxsize=1000)
def normalize_email(email: str) -> str:
    """
    Normalize email address for comparison with caching.
    """
    if not email:
        return ""
    
    # Remove name part and angle brackets
    match = COMPILED_PATTERNS['email_address'].search(email)
    if match:
        email = match.group(1)
    
    return email.lower().strip()


def extract_reply_content(email_body: str) -> str:
    """Extract the new content from a reply, removing quoted text.

    Simple implementation focusing on common patterns.
    """
    if not email_body:
        return ""

    # Split on common reply boundaries
    boundaries = [
        COMPILED_PATTERNS['gmail_quote'],
        COMPILED_PATTERNS['outlook_quote'], 
        COMPILED_PATTERNS['original_message'],
        COMPILED_PATTERNS['underscore_sep']
    ]
    
    lines = email_body.split('\n')
    reply_lines = []
    
    for line in lines:
        # Stop at quote markers
        if COMPILED_PATTERNS['quote_markers'].match(line):
            break
            
        # Check boundary patterns
        skip_line = False
        for boundary in boundaries:
            if boundary.search(line):
                skip_line = True
                break
        
        if skip_line:
            break
            
        reply_lines.append(line)
    
    return clean_text('\n'.join(reply_lines))


def parse_conversation_chain(email_body: str) -> list[QuotedMessage]:
    """Advanced parsing to extract individual messages from conversation
    chains.

    This handles nested replies, forwards, and complex quote structures.
    """
    if not email_body:
        return []

    messages = []
    lines = email_body.split("\n")
    current_message: dict[str, Any] = {"content": [], "depth": 0}
    
    # Enhanced patterns for different email clients
    header_patterns = [
        # Gmail style: "On Mon, Jan 15, 2024 at 2:30 PM John Doe <john@example.com> wrote:"
        re.compile(r"^On .+, .+ at .+ (.+) wrote:$", re.IGNORECASE),
        # Outlook style: "From: ... Sent: ... To: ... Subject:"
        re.compile(r"^From:\s*(.+)\s*$", re.MULTILINE),
        # Original message separator
        re.compile(r"^-{3,}\s*Original Message\s*-{3,}$", re.IGNORECASE),
        # Forwarded message
        re.compile(r"^-{3,}\s*Forwarded message\s*-{3,}$", re.IGNORECASE)
    ]
    
    in_header = False
    header_lines = []
    quote_depth = 0
    
    for i, line in enumerate(lines):
        # Count quote depth (> markers)
        stripped_line = line.lstrip()
        len(line) - len(stripped_line.lstrip('>'))
        
        if stripped_line.startswith('>'):
            quote_depth = stripped_line.count('>')
        else:
            quote_depth = 0
        
        # Check for message headers
        is_header = False
        sender = None
        
        for pattern in header_patterns:
            match = pattern.search(line)
            if match:
                is_header = True
                if match.groups():
                    sender = match.group(1).strip()
                
                # Save current message before starting new one
                if current_message["content"]:
                    content_text = "\n".join(current_message["content"]).strip()
                    if content_text:
                        messages.append(QuotedMessage(
                            content=clean_text(content_text),
                            sender=current_message.get("sender"),
                            date=current_message.get("date"), 
                            depth=current_message["depth"],
                            raw_header=current_message.get("raw_header")
                        ))
                
                # Start new message
                current_message = {
                    "content": [],
                    "depth": quote_depth,
                    "sender": sender,
                    "raw_header": line
                }
                in_header = True
                header_lines = [line]
                break
        
        if is_header:
            continue
            
        # Collect header lines
        if in_header:
            header_lines.append(line)
            # Try to extract more info from header
            if line.strip().startswith("Sent:") or line.strip().startswith("Date:"):
                date_match = re.search(r"Sent:\s*(.+)|Date:\s*(.+)", line)
                if date_match:
                    current_message["date"] = (date_match.group(1) or date_match.group(2)).strip()
            
            # End header when we hit empty line or content
            if line.strip() == "" or (_count_header_lines(header_lines) >= 3):
                in_header = False
                current_message["raw_header"] = "\n".join(header_lines)
                continue
        
        # Regular content line
        if not in_header and line.strip():
            current_message["content"].append(line)
    
    # Save final message
    if current_message["content"]:
        content_text = "\n".join(current_message["content"]).strip()
        if content_text:
            messages.append(QuotedMessage(
                content=clean_text(content_text),
                sender=current_message.get("sender"),
                date=current_message.get("date"),
                depth=current_message["depth"],
                raw_header=current_message.get("raw_header")
            ))
    
    # If no messages found, treat entire body as single message
    if not messages and email_body.strip():
        messages.append(QuotedMessage(
            content=clean_text(email_body),
            message_type="original",
            depth=0
        ))
    
    return messages


def _parse_message_header(header_lines: list[str]) -> tuple[str | None, str | None, str | None]:
    """
    Parse message header to extract sender, date, subject.
    """
    sender = None
    date = None
    subject = None
    
    for line in header_lines:
        if line.startswith("From:"):
            sender = line[5:].strip()
        elif line.startswith("Sent:") or line.startswith("Date:"):
            date = line.split(":", 1)[1].strip()
        elif line.startswith("Subject:"):
            subject = line[8:].strip()
    
    return sender, date, subject


def _count_header_lines(lines: list[str]) -> int:
    """
    Count header-like lines to determine when header ends.
    """
    header_count = 0
    for line in lines:
        if any(line.startswith(prefix) for prefix in ["From:", "To:", "Sent:", "Date:", "Subject:", "Cc:", "Bcc:"]):
            header_count += 1
    return header_count


def _is_signature_line(line: str) -> bool:
    """
    Determine if a line looks like part of an email signature.
    """
    line = line.strip()
    if len(line) < 3:
        return False
    
    # Common signature patterns
    signature_indicators = ["--", "Best regards", "Sincerely", "Thanks", "Phone:", "Email:", "www."]
    return any(indicator in line for indicator in signature_indicators)