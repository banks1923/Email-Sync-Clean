import json
import os

import keyring
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow

SCOPES = [
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/gmail.addons.current.message.metadata",
]


class GmailAuth:
    """Handle OAuth2 authentication for Gmail API using secure keyring storage."""

    def __init__(self, credentials_file="credentials.json", token_file="token.json"):
        """Initialize Gmail authentication handler.

        Args:
            credentials_file: Path to OAuth2 client credentials JSON file.
            token_file: Legacy token file path (for migration compatibility).
        """
        self.credentials_file = credentials_file
        self.token_file = token_file
        self.keyring_service = "gmail_service"
        self.keyring_username = "oauth_token"
        self.creds = None

    def get_credentials(self):
        """Get or refresh Gmail API credentials using keyring storage.

        Returns:
            dict: Success status and credentials or error message.
        """
        # Try to load from secure keyring first
        token_json = keyring.get_password(self.keyring_service, self.keyring_username)
        if token_json:
            try:
                self.creds = Credentials.from_authorized_user_info(json.loads(token_json), SCOPES)
            except (json.JSONDecodeError, ValueError, KeyError):
                # If keyring token is corrupted, continue to file fallback
                pass

        # Fallback to file-based token (for migration)
        if not self.creds and os.path.exists(self.token_file):
            self.creds = Credentials.from_authorized_user_file(self.token_file, SCOPES)

        if not self.creds or not self.creds.valid:
            if self.creds and self.creds.expired and self.creds.refresh_token:
                self.creds.refresh(Request())
            else:
                if not os.path.exists(self.credentials_file):
                    return {"success": False, "error": "credentials.json not found"}

                flow = InstalledAppFlow.from_client_secrets_file(self.credentials_file, SCOPES)
                self.creds = flow.run_local_server(port=0)

            # Save to secure keyring instead of file
            keyring.set_password(self.keyring_service, self.keyring_username, self.creds.to_json())

            # Remove old file if it exists (migration)
            if os.path.exists(self.token_file):
                os.remove(self.token_file)

        return {"success": True, "credentials": self.creds}

    def is_authenticated(self):
        """Check if current credentials are valid.

        Returns:
            bool: True if credentials exist and are valid.
        """
        return self.creds and self.creds.valid
