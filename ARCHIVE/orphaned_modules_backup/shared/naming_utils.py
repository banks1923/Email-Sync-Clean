"""
Markdown File Naming Utilities

Provides cross-platform filename generation, slugification, and validation
for analog database markdown files. Follows CLAUDE.md principles.
"""

import hashlib
import re
import unicodedata
from datetime import datetime
from pathlib import Path

from loguru import logger


class MarkdownNamingUtils:
    """Core utilities for markdown file naming with cross-platform compatibility."""

    # Reserved names that cannot be used on Windows
    RESERVED_NAMES = {
        "con",
        "prn",
        "aux",
        "nul",
        "com1",
        "com2",
        "com3",
        "com4",
        "com5",
        "com6",
        "com7",
        "com8",
        "com9",
        "lpt1",
        "lpt2",
        "lpt3",
        "lpt4",
        "lpt5",
        "lpt6",
        "lpt7",
        "lpt8",
        "lpt9",
    }

    # Characters illegal on various platforms
    ILLEGAL_CHARS = r'[<>:"/\\|?*\x00-\x1f]'

    # Maximum filename length (conservative for all platforms)
    MAX_FILENAME_LENGTH = 200  # Leave room for extensions and collision resolution

    def __init__(self):
        """Initialize naming utilities."""
        self.logger = logger.bind(service="naming_utils")

    def slugify(self, text: str, max_length: int | None = None) -> str:
        """
        Convert text to URL-safe slug format for filenames.

        Args:
            text: Input text to slugify
            max_length: Optional maximum length limit

        Returns:
            Slugified text safe for filenames
        """
        if not text:
            return "untitled"

        # Normalize unicode characters
        text = unicodedata.normalize("NFKD", text)

        # Convert to ASCII, ignoring non-ASCII characters
        text = text.encode("ascii", "ignore").decode("ascii")

        # Convert to lowercase
        text = text.lower().strip()

        # Replace spaces and multiple whitespace with hyphens
        text = re.sub(r"\s+", "-", text)

        # Remove special characters, keep alphanumeric and hyphens
        text = re.sub(r"[^a-z0-9\-]", "", text)

        # Remove multiple consecutive hyphens
        text = re.sub(r"-+", "-", text)

        # Strip leading/trailing hyphens
        text = text.strip("-")

        # Fallback for empty result
        if not text:
            text = "untitled"

        # Apply length limit if specified
        if max_length and len(text) > max_length:
            text = text[:max_length].rstrip("-")

        return text

    def sanitize_filename(self, filename: str) -> str:
        """
        Sanitize filename for cross-platform compatibility.

        Args:
            filename: Raw filename to sanitize

        Returns:
            Sanitized filename safe for all platforms
        """
        # Handle empty or None input
        if not filename:
            return "untitled"

        # Normalize unicode
        filename = unicodedata.normalize("NFKD", filename)

        # Remove illegal characters
        filename = re.sub(self.ILLEGAL_CHARS, "", filename)

        # Handle reserved names (case-insensitive)
        stem = Path(filename).stem.lower()
        if stem in self.RESERVED_NAMES:
            filename = f"file_{filename}"

        # Replace problematic characters
        filename = filename.replace("..", ".")  # No double dots
        filename = filename.strip(". ")  # No leading/trailing dots or spaces

        # Ensure it's not empty after sanitization
        if not filename:
            filename = "untitled"

        return filename

    def truncate_filename(self, filename: str, max_length: int | None = None) -> str:
        """
        Truncate filename while preserving extension.

        Args:
            filename: Filename to truncate
            max_length: Maximum length (defaults to MAX_FILENAME_LENGTH)

        Returns:
            Truncated filename with preserved extension
        """
        if not filename:
            return "untitled.md"

        max_len = max_length or self.MAX_FILENAME_LENGTH

        if len(filename) <= max_len:
            return filename

        # Split into stem and extension
        path_obj = Path(filename)
        stem = path_obj.stem
        suffix = path_obj.suffix

        # Calculate available space for stem
        available_space = max_len - len(suffix)

        if available_space <= 0:
            # Edge case: extension is too long
            return f"untitled{suffix[:max_len-8]}"

        # Truncate stem
        truncated_stem = stem[:available_space]

        # Remove trailing hyphens or underscores from truncation
        truncated_stem = truncated_stem.rstrip("-_")

        return f"{truncated_stem}{suffix}"

    def generate_document_filename(
        self, title: str, doc_type: str = "document", date: datetime | None = None
    ) -> str:
        """
        Generate filename for documents: YYYY-MM-DD_descriptive-name.md

        Args:
            title: Document title
            doc_type: Type of document (for fallback naming)
            date: Optional date (defaults to now)

        Returns:
            Generated filename following naming convention
        """
        if date is None:
            date = datetime.now()

        # Create date prefix
        date_prefix = date.strftime("%Y-%m-%d")

        # Slugify title for filename
        slug = self.slugify(title, max_length=120)  # Leave room for date and extension

        if not slug or slug == "untitled":
            # Fallback to doc_type
            slug = self.slugify(doc_type, max_length=120)
            if not slug:
                slug = "document"

        # Combine parts
        filename = f"{date_prefix}_{slug}.md"

        # Final sanitization and truncation
        filename = self.sanitize_filename(filename)
        filename = self.truncate_filename(filename)

        self.logger.debug(f"Generated document filename: {filename}")
        return filename

    def generate_email_thread_filename(self, subject: str, thread_id: str = "") -> str:
        """
        Generate filename for email threads: subject-based-thread-name.md

        Args:
            subject: Email subject line
            thread_id: Optional thread ID for uniqueness

        Returns:
            Generated filename for email thread
        """
        # Handle empty subject
        if not subject or subject.strip() == "":
            subject = "email-thread"

        # Clean up common email subject prefixes
        subject = re.sub(r"^(re:\s*|fwd?:\s*|fw:\s*)+", "", subject, flags=re.IGNORECASE)
        subject = subject.strip()

        # Slugify subject
        slug = self.slugify(subject, max_length=150)  # Leave room for thread_id and extension

        if not slug:
            slug = "email-thread"

        # Add thread ID if provided for uniqueness
        if thread_id:
            thread_slug = self.slugify(thread_id)[:20]  # Limit thread ID part
            if thread_slug:
                filename = f"{slug}_{thread_slug}.md"
            else:
                filename = f"{slug}.md"
        else:
            filename = f"{slug}.md"

        # Final sanitization and truncation
        filename = self.sanitize_filename(filename)
        filename = self.truncate_filename(filename)

        self.logger.debug(f"Generated email thread filename: {filename}")
        return filename

    def extract_date_from_filename(self, filename: str) -> datetime | None:
        """
        Extract date from filename if it follows date-prefixed convention.

        Args:
            filename: Filename to parse

        Returns:
            Extracted datetime or None if no date found
        """
        # Match YYYY-MM-DD pattern at start of filename
        match = re.match(r"^(\d{4})-(\d{2})-(\d{2})_", filename)
        if match:
            try:
                year, month, day = map(int, match.groups())
                return datetime(year, month, day)
            except ValueError:
                # Invalid date values
                pass

        return None

    def is_valid_markdown_filename(self, filename: str) -> bool:
        """
        Check if filename is valid for markdown files.

        Args:
            filename: Filename to validate

        Returns:
            True if valid, False otherwise
        """
        if not filename:
            return False

        # Must end with .md
        if not filename.lower().endswith(".md"):
            return False

        # Check length
        if len(filename) > self.MAX_FILENAME_LENGTH + 50:  # Allow some extra room
            return False

        # Check for illegal characters
        if re.search(self.ILLEGAL_CHARS, filename):
            return False

        # Check for reserved names
        stem = Path(filename).stem.lower()
        if stem in self.RESERVED_NAMES:
            return False

        # Check for problematic patterns
        if ".." in filename or filename.startswith(".") or filename.endswith("."):
            return False

        return True

    def check_collision(self, filepath: Path) -> bool:
        """
        Check if a file already exists at the given path.

        Args:
            filepath: Path to check for collision

        Returns:
            True if collision exists, False otherwise
        """
        return filepath.exists()

    def generate_unique_filename(
        self, base_path: Path, filename: str, strategy: str = "counter"
    ) -> str:
        """
        Generate unique filename by resolving collisions.

        Args:
            base_path: Directory where file will be placed
            filename: Desired filename
            strategy: Resolution strategy ('counter', 'timestamp', 'hash')

        Returns:
            Unique filename that doesn't collide
        """
        original_path = base_path / filename

        if not self.check_collision(original_path):
            return filename

        # Split filename into stem and suffix
        path_obj = Path(filename)
        stem = path_obj.stem
        suffix = path_obj.suffix

        if strategy == "counter":
            return self._resolve_with_counter(base_path, stem, suffix)
        elif strategy == "timestamp":
            return self._resolve_with_timestamp(base_path, stem, suffix)
        elif strategy == "hash":
            return self._resolve_with_hash(base_path, stem, suffix)
        else:
            # Default to counter
            return self._resolve_with_counter(base_path, stem, suffix)

    def _resolve_with_counter(self, base_path: Path, stem: str, suffix: str) -> str:
        """Resolve collision by appending counter (_1, _2, etc.)."""
        counter = 1
        max_attempts = 1000  # Prevent infinite loops

        while counter <= max_attempts:
            new_filename = f"{stem}_{counter}{suffix}"
            if not (base_path / new_filename).exists():
                self.logger.debug(f"Resolved collision with counter: {new_filename}")
                return new_filename
            counter += 1

        # Fallback to timestamp if we hit max attempts
        return self._resolve_with_timestamp(base_path, stem, suffix)

    def _resolve_with_timestamp(self, base_path: Path, stem: str, suffix: str) -> str:
        """Resolve collision by appending timestamp."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        new_filename = f"{stem}_{timestamp}{suffix}"

        # If timestamp collision still exists (unlikely), add microseconds
        if (base_path / new_filename).exists():
            microseconds = datetime.now().strftime("%f")
            new_filename = f"{stem}_{timestamp}_{microseconds}{suffix}"

        self.logger.debug(f"Resolved collision with timestamp: {new_filename}")
        return new_filename

    def _resolve_with_hash(self, base_path: Path, stem: str, suffix: str) -> str:
        """Resolve collision by appending content hash (if available)."""
        # Generate a short hash from stem + current time for uniqueness
        content = f"{stem}_{datetime.now().isoformat()}"
        hash_digest = hashlib.md5(content.encode()).hexdigest()[:8]
        new_filename = f"{stem}_{hash_digest}{suffix}"

        self.logger.debug(f"Resolved collision with hash: {new_filename}")
        return new_filename

    def resolve_thread_collision(
        self, base_path: Path, subject: str, thread_id: str = "", participants: list[str] = None
    ) -> str:
        """
        Special collision resolution for email threads with same subject.

        Args:
            base_path: Directory where file will be placed
            subject: Email subject
            thread_id: Thread ID if available
            participants: List of participants for disambiguation

        Returns:
            Unique filename for email thread
        """
        # Generate base filename
        base_filename = self.generate_email_thread_filename(subject, thread_id)

        # Check for collision
        if not self.check_collision(base_path / base_filename):
            return base_filename

        # Try adding participant info for disambiguation
        if participants:
            # Use first few participants for uniqueness
            participant_slug = self.slugify("_".join(participants[:3]), max_length=30)
            path_obj = Path(base_filename)
            stem = path_obj.stem
            suffix = path_obj.suffix

            candidate_filename = f"{stem}_{participant_slug}{suffix}"
            candidate_filename = self.truncate_filename(candidate_filename)

            if not self.check_collision(base_path / candidate_filename):
                self.logger.debug(
                    f"Resolved thread collision with participants: {candidate_filename}"
                )
                return candidate_filename

        # Fall back to standard collision resolution
        return self.generate_unique_filename(base_path, base_filename, strategy="timestamp")

    def find_similar_filenames(
        self, base_path: Path, filename: str, threshold: float = 0.8
    ) -> list[str]:
        """
        Find existing files with similar names (potential duplicates).

        Args:
            base_path: Directory to search in
            filename: Filename to find similarities for
            threshold: Similarity threshold (0.0-1.0)

        Returns:
            List of similar filenames
        """
        if not base_path.exists():
            return []

        # Get filename without extension for comparison
        target_stem = Path(filename).stem.lower()
        similar_files = []

        try:
            for file_path in base_path.rglob("*.md"):
                existing_stem = file_path.stem.lower()
                similarity = self._calculate_similarity(target_stem, existing_stem)

                if similarity >= threshold:
                    similar_files.append(file_path.name)

        except Exception as e:
            self.logger.warning(f"Error finding similar files: {e}")

        return similar_files

    def _calculate_similarity(self, str1: str, str2: str) -> float:
        """
        Calculate simple similarity between two strings using Levenshtein-like approach.

        Args:
            str1: First string
            str2: Second string

        Returns:
            Similarity score (0.0-1.0)
        """
        if str1 == str2:
            return 1.0

        if not str1 or not str2:
            return 0.0

        # Simple approach: count common characters
        set1 = set(str1.lower())
        set2 = set(str2.lower())

        intersection = set1.intersection(set2)
        union = set1.union(set2)

        if not union:
            return 0.0

        return len(intersection) / len(union)


class CollisionResolver:
    """Dedicated class for handling filename collisions and duplicates."""

    def __init__(self, naming_utils: MarkdownNamingUtils | None = None):
        """Initialize collision resolver."""
        self.naming_utils = naming_utils or MarkdownNamingUtils()
        self.logger = logger.bind(service="collision_resolver")

    def resolve_collision(self, target_path: Path, strategy: str = "counter") -> Path:
        """
        Resolve filename collision and return unique path.

        Args:
            target_path: Desired file path
            strategy: Resolution strategy

        Returns:
            Unique file path
        """
        if not target_path.exists():
            return target_path

        base_path = target_path.parent
        filename = target_path.name

        unique_filename = self.naming_utils.generate_unique_filename(base_path, filename, strategy)

        return base_path / unique_filename

    def check_potential_duplicates(
        self, target_path: Path, similarity_threshold: float = 0.8
    ) -> list[Path]:
        """
        Check for potential duplicate files based on name similarity.

        Args:
            target_path: Path to check for duplicates
            similarity_threshold: Similarity threshold

        Returns:
            List of potentially duplicate file paths
        """
        similar_names = self.naming_utils.find_similar_filenames(
            target_path.parent, target_path.name, similarity_threshold
        )

        return [target_path.parent / name for name in similar_names]

    def suggest_resolution_strategies(self, collision_path: Path) -> list[str]:
        """
        Suggest resolution strategies for a collision.

        Args:
            collision_path: Path that has collision

        Returns:
            List of suggested resolution strategies
        """
        strategies = []

        # Always suggest counter as safest option
        strategies.append("counter")

        # Suggest timestamp for time-sensitive documents
        if "email" in collision_path.name.lower() or "thread" in collision_path.name.lower():
            strategies.append("timestamp")

        # Suggest hash for maximum uniqueness
        strategies.append("hash")

        return strategies


class FilenameValidator:
    """Cross-platform filename validation utilities."""

    # Platform-specific illegal characters
    WINDOWS_ILLEGAL = r'[<>:"/\\|?*\x00-\x1f]'
    MACOS_ILLEGAL = r"[:]"
    LINUX_ILLEGAL = r"[\x00/]"

    # Windows reserved names (case-insensitive)
    WINDOWS_RESERVED = {
        "con",
        "prn",
        "aux",
        "nul",
        "com1",
        "com2",
        "com3",
        "com4",
        "com5",
        "com6",
        "com7",
        "com8",
        "com9",
        "lpt1",
        "lpt2",
        "lpt3",
        "lpt4",
        "lpt5",
        "lpt6",
        "lpt7",
        "lpt8",
        "lpt9",
    }

    # Maximum path lengths by platform
    WINDOWS_MAX_PATH = 260
    WINDOWS_MAX_FILENAME = 255
    UNIX_MAX_FILENAME = 255
    MACOS_MAX_FILENAME = 255

    def __init__(self):
        """Initialize filename validator."""
        self.logger = logger.bind(service="filename_validator")

    def validate_filename(self, filename: str, target_platform: str = "all") -> dict:
        """
        Validate filename against platform-specific restrictions.

        Args:
            filename: Filename to validate
            target_platform: Target platform ('windows', 'macos', 'linux', 'all')

        Returns:
            Dictionary with validation results and errors
        """
        result = {"valid": True, "errors": [], "warnings": [], "platform": target_platform}

        if not filename:
            result["valid"] = False
            result["errors"].append("Filename cannot be empty")
            return result

        # Check for all platforms or specific platform
        if target_platform in ["all", "windows"]:
            self._validate_windows(filename, result)

        if target_platform in ["all", "macos"]:
            self._validate_macos(filename, result)

        if target_platform in ["all", "linux"]:
            self._validate_linux(filename, result)

        return result

    def _validate_windows(self, filename: str, result: dict):
        """Validate filename for Windows compatibility."""
        # Check illegal characters
        if re.search(self.WINDOWS_ILLEGAL, filename):
            result["valid"] = False
            result["errors"].append('Contains characters illegal on Windows: < > : " / \\ | ? *')

        # Check reserved names
        stem = Path(filename).stem.lower()
        if stem in self.WINDOWS_RESERVED:
            result["valid"] = False
            result["errors"].append(f"'{stem}' is a reserved name on Windows")

        # Check filename length
        if len(filename) > self.WINDOWS_MAX_FILENAME:
            result["valid"] = False
            result["errors"].append(
                f"Filename too long for Windows (max {self.WINDOWS_MAX_FILENAME} chars)"
            )

        # Check for trailing periods or spaces
        if filename.endswith(".") or filename.endswith(" "):
            result["valid"] = False
            result["errors"].append("Filename cannot end with period or space on Windows")

        # Warn about Unicode characters
        try:
            filename.encode("ascii")
        except UnicodeEncodeError:
            result["warnings"].append(
                "Contains non-ASCII characters (may cause issues on older Windows)"
            )

    def _validate_macos(self, filename: str, result: dict):
        """Validate filename for macOS compatibility."""
        # Check illegal characters (mainly colon)
        if re.search(self.MACOS_ILLEGAL, filename):
            result["valid"] = False
            result["errors"].append("Contains characters illegal on macOS: :")

        # Check filename length
        if len(filename) > self.MACOS_MAX_FILENAME:
            result["valid"] = False
            result["errors"].append(
                f"Filename too long for macOS (max {self.MACOS_MAX_FILENAME} chars)"
            )

        # Check for files starting with dot (hidden files warning)
        if filename.startswith("."):
            result["warnings"].append("Files starting with '.' are hidden on macOS/Linux")

    def _validate_linux(self, filename: str, result: dict):
        """Validate filename for Linux compatibility."""
        # Check illegal characters (mainly null and forward slash)
        if re.search(self.LINUX_ILLEGAL, filename):
            result["valid"] = False
            result["errors"].append("Contains characters illegal on Linux: null byte or /")

        # Check filename length
        if len(filename) > self.UNIX_MAX_FILENAME:
            result["valid"] = False
            result["errors"].append(
                f"Filename too long for Linux (max {self.UNIX_MAX_FILENAME} chars)"
            )

    def validate_path_length(self, filepath: str, target_platform: str = "all") -> dict:
        """
        Validate full path length restrictions.

        Args:
            filepath: Full file path to validate
            target_platform: Target platform

        Returns:
            Dictionary with validation results
        """
        result = {"valid": True, "errors": [], "warnings": []}

        path_length = len(filepath)

        if target_platform in ["all", "windows"]:
            if path_length > self.WINDOWS_MAX_PATH:
                result["valid"] = False
                result["errors"].append(
                    f"Path too long for Windows (max {self.WINDOWS_MAX_PATH} chars)"
                )

        # Unix systems typically have much higher path limits (4096+)
        # so we only warn if it's extremely long
        if path_length > 4096:
            result["warnings"].append("Extremely long path may cause issues on some systems")

        return result

    def validate_characters(self, filename: str) -> dict:
        """
        Validate specific character usage in filename.

        Args:
            filename: Filename to check

        Returns:
            Character validation results
        """
        result = {
            "has_unicode": False,
            "has_spaces": False,
            "has_special_chars": False,
            "problematic_chars": [],
        }

        # Check for Unicode characters
        try:
            filename.encode("ascii")
        except UnicodeEncodeError:
            result["has_unicode"] = True

        # Check for spaces
        if " " in filename:
            result["has_spaces"] = True

        # Check for problematic characters
        problematic = r'[<>:"/\\|?*\x00-\x1f!@#$%^&()+={}[\];\'`,~]'
        matches = re.findall(problematic, filename)
        if matches:
            result["has_special_chars"] = True
            result["problematic_chars"] = list(set(matches))

        return result

    def suggest_fixes(self, filename: str, validation_result: dict) -> str:
        """
        Suggest fixes for filename validation errors.

        Args:
            filename: Original filename
            validation_result: Result from validate_filename

        Returns:
            Suggested fixed filename
        """
        if validation_result["valid"]:
            return filename

        # Use MarkdownNamingUtils to fix the filename
        naming_utils = MarkdownNamingUtils()

        # First sanitize to remove illegal characters
        fixed = naming_utils.sanitize_filename(filename)

        # Then truncate if needed
        fixed = naming_utils.truncate_filename(fixed)

        self.logger.debug(f"Suggested fix: '{filename}' -> '{fixed}'")
        return fixed


# Convenience functions for common operations
def slugify_text(text: str, max_length: int | None = None) -> str:
    """Convenience function to slugify text."""
    return MarkdownNamingUtils().slugify(text, max_length)


def sanitize_filename(filename: str) -> str:
    """Convenience function to sanitize filename."""
    return MarkdownNamingUtils().sanitize_filename(filename)


def generate_document_name(title: str, doc_type: str = "document") -> str:
    """Convenience function to generate document filename."""
    return MarkdownNamingUtils().generate_document_filename(title, doc_type)


def generate_email_name(subject: str, thread_id: str = "") -> str:
    """Convenience function to generate email thread filename."""
    return MarkdownNamingUtils().generate_email_thread_filename(subject, thread_id)


def resolve_collision(target_path: Path, strategy: str = "counter") -> Path:
    """Convenience function to resolve filename collision."""
    return CollisionResolver().resolve_collision(target_path, strategy)


def check_for_duplicates(target_path: Path, similarity_threshold: float = 0.8) -> list[Path]:
    """Convenience function to check for potential duplicates."""
    return CollisionResolver().check_potential_duplicates(target_path, similarity_threshold)


def validate_filename(filename: str, target_platform: str = "all") -> dict:
    """Convenience function to validate filename for cross-platform compatibility."""
    return FilenameValidator().validate_filename(filename, target_platform)


def suggest_filename_fixes(filename: str) -> str:
    """Convenience function to get suggested fixes for problematic filename."""
    validator = FilenameValidator()
    validation = validator.validate_filename(filename)
    return validator.suggest_fixes(filename, validation)
