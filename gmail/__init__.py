"""Gmail service package for email synchronization with batch processing
support.

This package provides Gmail API integration with features including:
- OAuth2 authentication with secure keyring storage
- Streaming batch sync for large email volumes (500+ emails)
- Incremental sync using Gmail History API
- Content-based deduplication with SHA-256 hashing
- Automatic document summarization on ingestion
- Configurable sender filters for legal/property contacts
"""

from .config import GmailConfig
from .gmail_api import GmailAPI
from .main import GmailService
from .oauth import GmailAuth
# EmailStorage removed - use SimpleDB directly


def get_gmail_service():
    """
    Factory function for GmailService.
    """
    return GmailService()


__all__ = [
    "GmailService",
    "GmailAuth",
    "GmailAPI",
    "GmailConfig",
    "get_gmail_service",
]
