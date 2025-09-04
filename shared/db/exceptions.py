"""Custom exceptions for database operations.

Following best practices for error handling in the SimpleDB layer.
"""


class DatabaseException(Exception):
    """Base exception for all database-related errors."""
    pass


class TestDataBlockedException(DatabaseException):
    """Raised when test data is blocked from entering production database."""
    
    def __init__(self, message: str, title: str = None, content_type: str = None):
        super().__init__(message)
        self.title = title
        self.content_type = content_type
        self.blocked_count = 0  # Can be set by the caller


class ContentValidationError(DatabaseException):
    """Raised when content fails validation rules."""
    
    def __init__(self, message: str, validation_errors: list = None):
        super().__init__(message)
        self.validation_errors = validation_errors or []


class DuplicateContentError(DatabaseException):
    """Raised when duplicate content is detected (if strict mode enabled)."""
    
    def __init__(self, message: str, existing_id: str = None, sha256: str = None):
        super().__init__(message)
        self.existing_id = existing_id
        self.sha256 = sha256