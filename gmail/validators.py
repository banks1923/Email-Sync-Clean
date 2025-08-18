"""
Common input validators for the Email Sync System
"""

import re
from datetime import datetime


class EmailValidator:
    """Validate email addresses and email-related inputs with intelligent parsing"""

    # More permissive email regex - accepts real Gmail emails with apostrophes, international chars, etc.
    # Prioritizes accepting valid emails over rejecting edge cases
    EMAIL_REGEX = re.compile(r"^[a-zA-Z0-9._%+'=/-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$")

    # Max email size in bytes (25MB is common limit)
    MAX_EMAIL_SIZE = 25 * 1024 * 1024  # 25MB

    @staticmethod
    def extract_email_from_header(header_value: str) -> str:
        """Extract email from RFC 5322 format: 'Name <email>' -> 'email'

        Handles various formats:
        - 'Name <email@domain.com>' -> 'email@domain.com'
        - '<email@domain.com>' -> 'email@domain.com'
        - 'email@domain.com' -> 'email@domain.com'
        - '"Name with spaces" <email@domain.com>' -> 'email@domain.com'
        """
        if not header_value:
            return ""

        header_value = header_value.strip()

        # Handle angle bracket format: "Name <email@domain.com>" or "<email@domain.com>"
        angle_match = re.search(r"<([^>]+)>", header_value)
        if angle_match:
            return angle_match.group(1).strip()

        # Handle quoted format: '"Name" email@domain.com'
        if '"' in header_value:
            # Remove quoted parts and extract remaining email
            clean = re.sub(r'"[^"]*"', "", header_value).strip()
            if "@" in clean:
                return clean

        # Return as-is if it already looks like plain email
        return header_value

    @staticmethod
    def validate_email_address(email: str, auto_extract: bool = True) -> dict:
        """Validate email address format with intelligent parsing

        Args:
            email: Email address or header to validate
            auto_extract: If True, automatically extract email from RFC 5322 headers
        """
        if not email:
            return {"success": False, "error": "Email address cannot be empty"}

        if not isinstance(email, str):
            return {"success": False, "error": "Email address must be a string"}

        # Auto-extract email from header if requested
        if auto_extract:
            extracted_email = EmailValidator.extract_email_from_header(email)
            if extracted_email != email:
                # Store both original and extracted for reference
                validation_result = EmailValidator.validate_email_address(
                    extracted_email, auto_extract=False
                )
                if validation_result["success"]:
                    validation_result["original_header"] = email
                    validation_result["extracted_email"] = extracted_email
                return validation_result

        # Basic length check
        if len(email) > 320:  # RFC 5321 max email length
            return {"success": False, "error": "Email address too long (max 320 characters)"}

        # Format validation with better error messages
        if not EmailValidator.EMAIL_REGEX.match(email):
            # Provide more specific error messages
            if "@" not in email:
                return {"success": False, "error": "Email address missing @ symbol"}
            elif email.startswith("@") or email.endswith("@"):
                return {"success": False, "error": "Email address has invalid @ placement"}
            elif ".." in email:
                return {"success": False, "error": "Email address contains consecutive dots"}
            else:
                return {"success": False, "error": "Invalid email address format"}

        return {"success": True}

    @staticmethod
    def validate_email_header(header_value: str) -> dict:
        """Validate email header with full RFC 5322 support

        Returns both validation result and parsed components
        """
        if not header_value:
            return {"success": False, "error": "Email header cannot be empty"}

        extracted = EmailValidator.extract_email_from_header(header_value)
        validation = EmailValidator.validate_email_address(extracted, auto_extract=False)

        if validation["success"]:
            return {
                "success": True,
                "original_header": header_value,
                "extracted_email": extracted,
                "is_rfc5322_format": "<" in header_value and ">" in header_value,
            }
        else:
            validation["original_header"] = header_value
            validation["extracted_email"] = extracted
            return validation

    @staticmethod
    def validate_email_size(size: int | str) -> dict:
        """Validate email size"""
        try:
            size_int = int(size) if isinstance(size, str) else size

            if size_int < 0:
                return {"success": False, "error": "Email size cannot be negative"}

            if size_int > EmailValidator.MAX_EMAIL_SIZE:
                return {
                    "success": False,
                    "error": f"Email size exceeds maximum ({EmailValidator.MAX_EMAIL_SIZE} bytes)",
                }

            return {"success": True, "size": size_int}
        except (ValueError, TypeError):
            return {"success": False, "error": "Invalid email size format"}


class DateValidator:
    """Validate date inputs"""

    # ISO 8601 date format
    ISO_FORMAT = "%Y-%m-%dT%H:%M:%S"

    @staticmethod
    def validate_iso_datetime(date_str: str) -> dict:
        """Validate ISO format datetime string"""
        if not date_str:
            return {"success": False, "error": "Date string cannot be empty"}

        if not isinstance(date_str, str):
            return {"success": False, "error": "Date must be a string"}

        try:
            # Try parsing with timezone
            if date_str.endswith("Z"):
                dt = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
            else:
                dt = datetime.fromisoformat(date_str)

            return {"success": True, "datetime": dt}
        except ValueError:
            # Try without timezone
            try:
                dt = datetime.strptime(date_str[:19], DateValidator.ISO_FORMAT)
                return {"success": True, "datetime": dt}
            except ValueError:
                return {"success": False, "error": "Invalid datetime format (expected ISO 8601)"}

    @staticmethod
    def validate_date_range(start: str, end: str) -> dict:
        """Validate a date range"""
        start_result = DateValidator.validate_iso_datetime(start)
        if not start_result["success"]:
            return {"success": False, "error": f"Invalid start date: {start_result['error']}"}

        end_result = DateValidator.validate_iso_datetime(end)
        if not end_result["success"]:
            return {"success": False, "error": f"Invalid end date: {end_result['error']}"}

        if start_result["datetime"] > end_result["datetime"]:
            return {"success": False, "error": "Start date must be before end date"}

        return {"success": True, "start": start_result["datetime"], "end": end_result["datetime"]}


class InputSanitizer:
    """Sanitize various inputs to prevent injection attacks"""

    @staticmethod
    def sanitize_search_query(query: str, max_length: int = 1000) -> dict:
        """Sanitize search query input"""
        if not query:
            return {"success": False, "error": "Search query cannot be empty"}

        if not isinstance(query, str):
            return {"success": False, "error": "Search query must be a string"}

        # Length check
        if len(query) > max_length:
            return {
                "success": False,
                "error": f"Search query too long (max {max_length} characters)",
            }

        # Remove control characters
        sanitized = "".join(char for char in query if ord(char) >= 32 or char in "\t\n\r")

        # Trim whitespace
        sanitized = sanitized.strip()

        if not sanitized:
            return {"success": False, "error": "Search query cannot be empty after sanitization"}

        return {"success": True, "query": sanitized}

    @staticmethod
    def sanitize_filename(filename: str) -> dict:
        """Sanitize filename to prevent path traversal"""
        if not filename:
            return {"success": False, "error": "Filename cannot be empty"}

        if not isinstance(filename, str):
            return {"success": False, "error": "Filename must be a string"}

        # Remove path separators and null bytes
        sanitized = filename.replace("/", "").replace("\\", "").replace("\0", "")

        # Remove leading dots to prevent hidden files
        sanitized = sanitized.lstrip(".")

        # Limit length
        if len(sanitized) > 255:
            sanitized = sanitized[:255]

        if not sanitized:
            return {"success": False, "error": "Invalid filename after sanitization"}

        return {"success": True, "filename": sanitized}


class LimitValidator:
    """Validate limit parameters for queries"""

    MAX_QUERY_LIMIT = 10000
    DEFAULT_LIMIT = 100

    @staticmethod
    def validate_query_limit(limit: int | str | None) -> dict:
        """Validate query limit parameter"""
        if limit is None:
            return {"success": True, "limit": LimitValidator.DEFAULT_LIMIT}

        try:
            limit_int = int(limit)

            if limit_int <= 0:
                return {"success": False, "error": "Limit must be a positive integer"}

            if limit_int > LimitValidator.MAX_QUERY_LIMIT:
                return {
                    "success": False,
                    "error": f"Limit exceeds maximum ({LimitValidator.MAX_QUERY_LIMIT})",
                }

            return {"success": True, "limit": limit_int}
        except (ValueError, TypeError):
            return {"success": False, "error": "Invalid limit format"}
