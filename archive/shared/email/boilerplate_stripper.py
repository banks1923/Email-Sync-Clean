"""Boilerplate text removal for legal documents and emails.

Simple, conservative approach to removing common boilerplate while
preserving substantive content for better embeddings and search.
"""

import hashlib
import re


class BoilerplateStripper:
    """
    Remove common boilerplate from legal documents and emails.
    """
    
    # Common email/legal boilerplate patterns (conservative list)
    PATTERNS = [
        # Email confidentiality notices
        r"This email is confidential.*?delete this email\.",
        r"CONFIDENTIALITY NOTICE:.*",
        r"If you are not the intended recipient.*",
        
        # Legal disclaimers
        r"WITHOUT PREJUDICE.*",
        r"ATTORNEY[- ]CLIENT PRIVILEGED.*",
        r"This communication is protected by.*privilege.*",
        
        # Email signatures  
        r"Sent from my (?:iPhone|iPad|Android|Samsung).*",
        r"Get Outlook for (?:iOS|Android).*",
        
        # Page numbers and headers/footers
        r"Page\s+\d+\s+of\s+\d+",
        r"^\d+\s*$",  # Standalone page numbers
        
        # Repeated section markers
        r"[-=]{3,}",  # Lines of dashes or equals
        r"\*{3,}",    # Lines of asterisks
    ]
    
    def __init__(self):
        """
        Initialize with compiled regex patterns.
        """
        self.compiled_patterns = [
            re.compile(pattern, re.IGNORECASE | re.DOTALL) 
            for pattern in self.PATTERNS
        ]
    
    def strip(self, text: str) -> str:
        """Remove boilerplate from text.

        Args:
            text: Input text

        Returns:
            Text with boilerplate removed
        """
        if not text:
            return text
            
        result = text
        
        # Apply each pattern
        for pattern in self.compiled_patterns:
            result = pattern.sub("", result)
        
        # Clean up excessive whitespace
        result = re.sub(r'\n{3,}', '\n\n', result)  # Max 2 newlines
        result = re.sub(r' {2,}', ' ', result)      # Collapse multiple spaces
        result = result.strip()
        
        # If we removed too much (less than 30% remains), return original
        if len(result) < len(text) * 0.3:
            return text
            
        return result
    
    def compute_hash(self, text: str) -> str:
        """Compute SHA256 hash of text for duplicate detection.

        Args:
            text: Text to hash (should be substantive_text)

        Returns:
            SHA256 hex digest
        """
        if not text:
            return ""
        
        # Normalize for consistent hashing
        normalized = text.lower().strip()
        normalized = re.sub(r'\s+', ' ', normalized)  # Normalize whitespace
        
        return hashlib.sha256(normalized.encode('utf-8')).hexdigest()
    
    def is_mostly_boilerplate(self, text: str, original: str) -> bool:
        """Check if text is mostly boilerplate.

        Args:
            text: Stripped text
            original: Original text

        Returns:
            True if more than 70% was removed
        """
        if not original:
            return False
            
        return len(text) < len(original) * 0.3


# Singleton instance for reuse
_stripper = None

def get_boilerplate_stripper() -> BoilerplateStripper:
    """
    Get or create the boilerplate stripper instance.
    """
    global _stripper
    if _stripper is None:
        _stripper = BoilerplateStripper()
    return _stripper


def strip_boilerplate(text: str) -> str:
    """Convenience function to strip boilerplate.

    Args:
        text: Input text

    Returns:
        Text with boilerplate removed
    """
    return get_boilerplate_stripper().strip(text)


def compute_content_hash(text: str) -> str:
    """Convenience function to compute content hash.

    Args:
        text: Text to hash (ideally substantive_text)

    Returns:
        SHA256 hex digest
    """
    return get_boilerplate_stripper().compute_hash(text)