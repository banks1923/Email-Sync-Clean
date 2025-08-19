import base64
import datetime
import socket

from googleapiclient.discovery import build
from loguru import logger

from shared.error_handler import ErrorHandler
from shared.retry_helper import retry_network

from .oauth import GmailAuth

# Logger is now imported globally from loguru


class GmailAPI:
    """Gmail API wrapper with timeout handling and message parsing."""

    def __init__(self, timeout: int = 30) -> None:
        """Initialize Gmail API client with authentication.

        Args:
            timeout: Socket timeout in seconds for API requests.
        """
        self.auth = GmailAuth()
        self.service = None
        self.timeout = timeout

    def connect(self):
        """Connect to Gmail API using OAuth2 credentials.

        Returns:
            dict: Success status and connection message.
        """
        auth_result = self.auth.get_credentials()
        if not auth_result["success"]:
            return auth_result

        # Set default socket timeout for Gmail API requests
        socket.setdefaulttimeout(self.timeout)

        self.service = build("gmail", "v1", credentials=auth_result["credentials"])
        return {"success": True, "message": "Connected to Gmail API"}

    def _execute_with_timeout(self, request):
        """Execute a Gmail API request with timeout handling"""
        old_timeout = socket.getdefaulttimeout()
        try:
            socket.setdefaulttimeout(self.timeout)
            return request.execute()
        finally:
            socket.setdefaulttimeout(old_timeout)

    def get_messages(self, query="", max_results=100):
        """Get list of message IDs from Gmail matching query.

        Args:
            query: Gmail search query string.
            max_results: Maximum number of messages to return.

        Returns:
            dict: Success status with list of message objects.
        """
        if not self.service:
            connect_result = self.connect()
            if not connect_result["success"]:
                return connect_result

        try:
            # Execute with timeout
            request = (
                self.service.users().messages().list(userId="me", q=query, maxResults=max_results)
            )
            results = self._execute_with_timeout(request)
            messages = results.get("messages", [])
            return {"success": True, "data": messages}
        except TimeoutError:
            return {
                "success": False,
                "error": f"Gmail API request timed out after {self.timeout} seconds",
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    def get_message_detail(self, message_id):
        """Get full message details from Gmail.

        Args:
            message_id: Gmail message ID.

        Returns:
            dict: Success status with message data.
        """
        if not self.service:
            connect_result = self.connect()
            if not connect_result["success"]:
                return connect_result

        try:
            # Execute with timeout
            request = self.service.users().messages().get(userId="me", id=message_id)
            message = self._execute_with_timeout(request)
            return {"success": True, "data": message}
        except TimeoutError:
            return {
                "success": False,
                "error": f"Gmail API request timed out after {self.timeout} seconds",
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    def parse_message(self, message_data):
        """Parse Gmail message data into structured format.

        Args:
            message_data: Raw message data from Gmail API.

        Returns:
            dict: Parsed message with subject, sender, content, etc.
        """
        headers = message_data["payload"]["headers"]

        subject = next((h["value"] for h in headers if h["name"] == "Subject"), "")
        sender = next((h["value"] for h in headers if h["name"] == "From"), "")
        recipient_to = next((h["value"] for h in headers if h["name"] == "To"), "")
        date_header = next((h["value"] for h in headers if h["name"] == "Date"), "")

        content = self._extract_content(message_data["payload"])

        return {
            "message_id": message_data["id"],
            "thread_id": message_data.get("threadId"),
            "subject": subject,
            "sender": sender,
            "recipient_to": recipient_to,
            "content": content,
            "datetime_utc": self._parse_date(date_header),
        }

    def _decode_body_data(self, data):
        """Decode base64 body data to UTF-8 string"""
        return base64.urlsafe_b64decode(data).decode("utf-8")

    def _extract_content_from_part(self, part, text_content, html_content):
        """Extract content from a single email part"""
        mime_type = part.get("mimeType", "")

        # Extract text/plain content (preferred)
        if mime_type == "text/plain" and part["body"].get("data") and not text_content:
            data = part["body"]["data"]
            text_content = self._decode_body_data(data)

        # Extract text/html content (fallback)
        elif mime_type == "text/html" and part["body"].get("data") and not html_content:
            data = part["body"]["data"]
            html_content = self._decode_body_data(data)

        return text_content, html_content

    def _extract_from_parts(self, parts):
        """Recursively extract content from email parts"""
        text_content = ""
        html_content = ""

        for part in parts:
            # Handle nested parts recursively
            if "parts" in part:
                nested_text, nested_html = self._extract_from_parts(part["parts"])
                if not text_content and nested_text:
                    text_content = nested_text
                if not html_content and nested_html:
                    html_content = nested_html
            else:
                # Extract content from this part
                text_content, html_content = self._extract_content_from_part(
                    part, text_content, html_content
                )

        return text_content, html_content

    def _extract_content(self, payload):
        """Extract email content from payload"""
        content = ""

        if "parts" in payload:
            text_content, html_content = self._extract_from_parts(payload["parts"])
            # Prefer plain text, fallback to HTML
            content = text_content if text_content else html_content
        elif payload["body"].get("data"):
            # Direct body content
            data = payload["body"]["data"]
            content = self._decode_body_data(data)

        return content

    def _parse_date(self, date_str):
        """Parse email date header and return ISO string format for validation compatibility"""
        try:
            from email.utils import parsedate_to_datetime

            # Parse to datetime object first
            dt = parsedate_to_datetime(date_str)
            # Convert to ISO string format that DateValidator expects
            return dt.isoformat()
        except (ValueError, TypeError, ImportError):
            # Return current time as ISO string
            return datetime.datetime.now().isoformat()

    # History API Methods for Incremental Sync
    @retry_network
    def get_profile(self) -> dict:
        """Get user's email profile including current history ID"""
        if not self.service:
            connect_result = self.connect()
            if not connect_result["success"]:
                return connect_result

        try:
            request = self.service.users().getProfile(userId="me")
            profile = self._execute_with_timeout(request)
            return {
                "success": True,
                "email": profile.get("emailAddress"),
                "history_id": profile.get("historyId"),
                "messages_total": profile.get("messagesTotal"),
                "threads_total": profile.get("threadsTotal"),
            }
        except Exception as e:
            logger.error(f"Failed to get profile: {e}")
            return ErrorHandler.handle(
                e, "getting Gmail profile", ErrorHandler.NETWORK_ERROR, logger
            )

    @retry_network
    def get_history(self, start_history_id: str, max_results: int = 100) -> dict:
        """
        Get changes since a given history ID using Gmail History API.

        Args:
            start_history_id: The history ID to start from
            max_results: Maximum number of history records to return

        Returns:
            Dict with success status and history changes
        """
        if not self.service:
            connect_result = self.connect()
            if not connect_result["success"]:
                return connect_result

        try:
            history_list = []
            page_token = None
            total_fetched = 0

            while total_fetched < max_results:
                # Build request with pagination
                request_params = {
                    "userId": "me",
                    "startHistoryId": start_history_id,
                    "maxResults": min(100, max_results - total_fetched),
                }

                if page_token:
                    request_params["pageToken"] = page_token

                request = self.service.users().history().list(**request_params)
                response = self._execute_with_timeout(request)

                # Extract history records
                if "history" in response:
                    history_list.extend(response["history"])
                    total_fetched += len(response["history"])

                # Check for more pages
                page_token = response.get("nextPageToken")
                if not page_token or total_fetched >= max_results:
                    break

            # Extract new history ID
            new_history_id = response.get("historyId", start_history_id)

            logger.info(f"Fetched {len(history_list)} history records since {start_history_id}")

            return {
                "success": True,
                "history": history_list,
                "history_id": new_history_id,
                "next_page_token": page_token,
            }

        except Exception as e:
            error_msg = str(e)

            # Handle specific error cases
            if "404" in error_msg or "historyId" in error_msg:
                logger.warning(f"History ID {start_history_id} too old or invalid, need full sync")
                return {"success": False, "error": "History ID expired", "need_full_sync": True}

            logger.error(f"Failed to get history: {e}")
            return ErrorHandler.handle(
                e, "fetching Gmail history", ErrorHandler.NETWORK_ERROR, logger
            )

    def extract_message_ids_from_history(self, history_records: list[dict]) -> list[str]:
        """
        Extract message IDs from history records that need to be fetched.

        Args:
            history_records: List of history records from get_history()

        Returns:
            List of message IDs that were added or modified
        """
        message_ids = set()

        for record in history_records:
            # Check for added messages
            if "messagesAdded" in record:
                for msg_record in record["messagesAdded"]:
                    message_ids.add(msg_record["message"]["id"])

            # Check for messages with label changes (might be important)
            if "labelsAdded" in record:
                for label_record in record["labelsAdded"]:
                    message_ids.add(label_record["message"]["id"])

        return list(message_ids)

    def get_attachments(self, message_id: str, message_data: dict = None) -> dict:
        """
        Get attachment metadata for a message.

        Args:
            message_id: The message ID
            message_data: Optional pre-fetched message data

        Returns:
            Dict with attachment information
        """
        if not message_data:
            result = self.get_message_detail(message_id)
            if not result["success"]:
                return result
            message_data = result["data"]

        attachments = []

        def extract_attachments_from_parts(parts) -> None:
            """Recursively extract attachment info from message parts"""
            for part in parts:
                if "parts" in part:
                    # Recurse into nested parts
                    extract_attachments_from_parts(part["parts"])
                elif part.get("filename"):
                    # This part is an attachment
                    attachment = {
                        "filename": part["filename"],
                        "mime_type": part.get("mimeType", ""),
                        "size_bytes": part["body"].get("size", 0),
                        "attachment_id": part["body"].get("attachmentId", ""),
                    }
                    attachments.append(attachment)

        # Extract attachments from payload
        payload = message_data.get("payload", {})
        if "parts" in payload:
            extract_attachments_from_parts(payload["parts"])

        return {"success": True, "attachments": attachments, "count": len(attachments)}
