"""
Email Cleaning and Sanitization Utilities Handles HTML stripping, signature
removal, and content normalization.
"""

import html as html_lib
import re
from functools import lru_cache
from typing import Any

# Compiled patterns for HTML and text cleaning
CLEANING_PATTERNS = {
    'style_script': re.compile(r"<(style|script)[^>]*>.*?</\1>", re.DOTALL | re.IGNORECASE),
    'block_elements': re.compile(r"<(p|div|br|li)[^>]*>", re.IGNORECASE),
    'block_end': re.compile(r"</?(p|div|br|li)[^>]*>", re.IGNORECASE),
    'html_tags': re.compile(r"<[^<]+?>"),
    'excessive_newlines': re.compile(r"\n{3,}"),
    'whitespace': re.compile(r"\s+"),
    'filename_invalid': re.compile(r'[\\/*?:"<>|]'),
}


class EmailCleaner:
    """
    Cleans and normalizes email content for storage and analysis.
    """

    def __init__(self):
        self.signature_patterns = [
            r"--\s*\n",  # Standard email signature separator
            r"Best regards,?\s*\n",
            r"Sincerely,?\s*\n", 
            r"Thanks,?\s*\n",
            r"Sent from my \w+",
            r"Get Outlook for \w+",
            r"\n\n.*@.*\.\w+$",  # Email at end
        ]
        self._compiled_signature_patterns = [re.compile(p, re.IGNORECASE | re.MULTILINE) for p in self.signature_patterns]

    def clean(self, email_data: dict[str, Any]) -> dict[str, Any]:
        """Clean an email dictionary, normalizing all text fields.

        Args:
            email_data: Raw email data dictionary

        Returns:
            Cleaned email data dictionary
        """
        cleaned = email_data.copy()
        
        # Clean subject
        if "subject" in cleaned:
            cleaned["subject"] = self._clean_subject(cleaned["subject"])
        
        # Clean body/content
        if "body" in cleaned:
            cleaned["body"] = self._clean_body(cleaned["body"])
        elif "content" in cleaned:
            cleaned["content"] = self._clean_body(cleaned["content"])
        
        # Clean sender/recipient fields
        for field in ["sender", "recipient_to", "recipient_cc", "recipient_bcc"]:
            if field in cleaned and cleaned[field]:
                cleaned[field] = self._clean_text_content(cleaned[field])
        
        return cleaned

    def _clean_subject(self, subject: str) -> str:
        """
        Clean email subject line.
        """
        if not subject:
            return ""
        
        # Remove HTML if present
        subject = self._strip_html(subject)
        
        # Normalize whitespace
        subject = CLEANING_PATTERNS['whitespace'].sub(" ", subject)
        
        return subject.strip()

    def _clean_body(self, body: str) -> str:
        """Clean email body content.

        Args:
            body: Raw email body text (may contain HTML)

        Returns:
            Cleaned plain text
        """
        if not body:
            return ""
        
        # Strip HTML first
        cleaned = self._strip_html(body)
        
        # Clean text content
        cleaned = self._clean_text_content(cleaned)
        
        # Remove signatures (optional - may want to preserve for legal evidence)
        # cleaned = self._remove_signatures(cleaned)
        
        return cleaned

    def _clean_text_content(self, text: str) -> str:
        """Clean text content - whitespace, newlines, etc."""
        if not text:
            return ""
        
        # Normalize excessive newlines  
        text = CLEANING_PATTERNS['excessive_newlines'].sub("\n\n", text)
        
        # Normalize whitespace within lines
        lines = text.split('\n')
        cleaned_lines = []
        for line in lines:
            cleaned_line = CLEANING_PATTERNS['whitespace'].sub(" ", line).strip()
            cleaned_lines.append(cleaned_line)
        
        return '\n'.join(cleaned_lines).strip()

    def _strip_html(self, html: str) -> str:
        """Convert HTML to plain text preserving structure.

        Args:
            html: HTML content string

        Returns:
            Plain text with preserved line breaks
        """
        if not html:
            return ""
        
        # Remove style and script tags completely
        html = CLEANING_PATTERNS['style_script'].sub("", html)
        
        # Convert block elements to line breaks
        html = CLEANING_PATTERNS['block_elements'].sub("\n", html)
        html = CLEANING_PATTERNS['block_end'].sub("", html)
        
        # Remove all remaining HTML tags
        html = CLEANING_PATTERNS['html_tags'].sub("", html)
        
        # Decode HTML entities
        html = html_lib.unescape(html)
        
        return html

    def _remove_signatures(self, text: str) -> str:
        """Remove email signatures from text.

        NOTE: For legal cases, may want to preserve signatures as evidence.
        """
        if not text:
            return ""
        
        for pattern in self._compiled_signature_patterns:
            # Find signature and remove everything after it
            match = pattern.search(text)
            if match:
                text = text[:match.start()].rstrip()
                break
        
        return text

    def _is_reply(self, email_data: dict[str, Any]) -> bool:
        """
        Determine if email is a reply based on subject and headers.
        """
        subject = email_data.get("subject", "").lower()
        
        # Check for reply prefixes
        reply_prefixes = ["re:", "reply:", "response:"]
        for prefix in reply_prefixes:
            if subject.startswith(prefix):
                return True
        
        # Check for In-Reply-To header
        if email_data.get("in_reply_to"):
            return True
        
        return False

    def batch_clean(self, emails: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Clean a batch of emails efficiently.

        Args:
            emails: List of email dictionaries

        Returns:
            List of cleaned email dictionaries
        """
        return [self.clean(email) for email in emails]


def sanitize_filename(filename: str) -> str:
    """Sanitize filename by removing invalid characters.

    Args:
        filename: Original filename

    Returns:
        Sanitized filename safe for filesystem use
    """
    if not filename:
        return "untitled"
    
    # Remove invalid characters
    sanitized = CLEANING_PATTERNS['filename_invalid'].sub("_", filename)
    
    # Remove excessive underscores
    sanitized = re.sub(r"_{2,}", "_", sanitized)
    
    # Trim and ensure not empty
    sanitized = sanitized.strip("_").strip()
    
    if not sanitized:
        return "untitled"
    
    # Limit length
    if len(sanitized) > 100:
        sanitized = sanitized[:97] + "..."
    
    return sanitized


@lru_cache(maxsize=500)
def compute_message_hash(message_content: str) -> str:
    """Compute hash for message content with caching.

    Args:
        message_content: Message content to hash

    Returns:
        SHA256 hash of message content
    """
    import hashlib
    
    if not message_content:
        return ""
    
    # Normalize content before hashing
    normalized = CLEANING_PATTERNS['whitespace'].sub(" ", message_content.strip().lower())
    
    return hashlib.sha256(normalized.encode('utf-8')).hexdigest()


def extract_email_addresses(text: str) -> list[str]:
    """Extract email addresses from text.

    Args:
        text: Text to search for email addresses

    Returns:
        List of email addresses found
    """
    if not text:
        return []
    
    # Simple email pattern
    email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
    matches = re.findall(email_pattern, text)
    
    # Remove duplicates and normalize
    emails = []
    seen = set()
    for email in matches:
        normalized = email.lower().strip()
        if normalized not in seen:
            emails.append(email)
            seen.add(normalized)
    
    return emails


def is_automated_email(email_data: dict[str, Any]) -> bool:
    """Detect if email appears to be automated/template-based.

    Useful for identifying systematic harassment patterns.
    """
    if not email_data:
        return False
    
    content = email_data.get("content", "") + " " + email_data.get("subject", "")
    content_lower = content.lower()
    
    # Template indicators
    automated_indicators = [
        "do not reply",
        "automated message", 
        "this is an automated",
        "no-reply@",
        "noreply@",
        "auto-generated",
        "system notification"
    ]
    
    # Check for template-like structure
    template_patterns = [
        r"thank you for .+ we will .+ when .+ available",  # Standard response template
        r"regarding your .+ we .+ address .+ when possible",  # Another template pattern
    ]
    
    # Check indicators
    for indicator in automated_indicators:
        if indicator in content_lower:
            return True
    
    # Check patterns  
    for pattern in template_patterns:
        if re.search(pattern, content_lower):
            return True
    
    return False