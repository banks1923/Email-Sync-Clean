"""
Simple, centralized error handling for Email Sync System.
No complex hierarchies - just practical error handling that works.
"""

from typing import Any


class ErrorHandler:
    """Simple error handler - no enterprise patterns, just what works."""

    # Error categories (keep it simple)
    NETWORK_ERROR = "network_error"
    DATABASE_ERROR = "database_error"
    VALIDATION_ERROR = "validation_error"
    SERVICE_ERROR = "service_error"

    @staticmethod
    def handle(
        error: Exception,
        context: str = "",
        category: str = "service_error",
        logger_instance: Any = None,
    ) -> dict[str, Any]:
        """
        Handle an error and return standard response format.

        Args:
            error: The exception that occurred
            context: What we were trying to do (e.g., "uploading PDF")
            category: Error category for better handling
            logger_instance: Optional logger for recording the error

        Returns:
            Standard error response: {"success": False, "error": str, "details": dict}
        """
        error_msg = str(error)

        # Build response
        response = {
            "success": False,
            "error": error_msg,
            "details": {"category": category, "context": context, "type": error.__class__.__name__},
        }

        # Log if logger provided
        if logger_instance:
            logger_instance.error(f"{context}: {error_msg}" if context else error_msg)

        return response

    @staticmethod
    def format_user_message(error_response: dict[str, Any]) -> str:
        """
        Convert error response to user-friendly message.

        Args:
            error_response: Standard error response dict

        Returns:
            User-friendly error message
        """
        category = error_response.get("details", {}).get("category", "")
        context = error_response.get("details", {}).get("context", "")
        error = error_response.get("error", "Unknown error")

        # User-friendly messages by category
        if category == ErrorHandler.NETWORK_ERROR:
            msg = "Network connection issue"
            if "timeout" in error.lower():
                msg += " (request timed out)"
            elif "connection refused" in error.lower():
                msg += " (service unavailable)"
        elif category == ErrorHandler.DATABASE_ERROR:
            msg = "Database operation failed"
            if "locked" in error.lower():
                msg += " (database is busy, will retry)"
            elif "no such table" in error.lower():
                msg += " (database not initialized)"
        elif category == ErrorHandler.VALIDATION_ERROR:
            msg = f"Invalid input: {error}"
        else:
            msg = f"Operation failed: {error}"

        if context:
            msg = f"{msg} while {context}"

        return msg

    @staticmethod
    def get_recovery_suggestion(error_response: dict[str, Any]) -> str | None:
        """
        Suggest how to fix the error.

        Args:
            error_response: Standard error response dict

        Returns:
            Helpful suggestion or None
        """
        error = error_response.get("error", "").lower()
        category = error_response.get("details", {}).get("category", "")

        # Common fixes
        if "qdrant" in error and "connection" in error:
            return "Qdrant not running? Start it first or use keyword search"
        elif "gmail" in error and "credentials" in error:
            return "Gmail not authenticated? Run: scripts/vsearch auth-gmail"
        elif "file not found" in error or "no such file" in error:
            return "Check that the file path exists and is accessible"
        elif "permission denied" in error:
            return "Check file permissions or run with appropriate access"
        elif category == ErrorHandler.DATABASE_ERROR and "locked" in error:
            return "Database is busy. Wait a moment and try again"
        elif "model" in error and "not found" in error:
            return "Model will be downloaded on first use (may take time)"

        return None
