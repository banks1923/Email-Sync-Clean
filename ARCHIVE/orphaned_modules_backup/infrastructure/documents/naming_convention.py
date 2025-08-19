"""
File Naming Convention System

Handles standardized naming across document lifecycle stages.
"""

import re
from datetime import datetime
from pathlib import Path


class NamingConvention:
    """Manages naming conventions for different lifecycle stages."""

    def __init__(self):
        """Initialize naming convention system."""
        self.doc_counter = 0
        self._load_counter()

    def _load_counter(self):
        """Load document counter from persistent storage."""
        counter_file = Path("data/.doc_counter")
        if counter_file.exists():
            try:
                self.doc_counter = int(counter_file.read_text())
            except Exception:
                self.doc_counter = 0

    def _save_counter(self):
        """Save document counter to persistent storage."""
        counter_file = Path("data/.doc_counter")
        counter_file.parent.mkdir(exist_ok=True)
        counter_file.write_text(str(self.doc_counter))

    def raw_name(self, original_path: Path) -> str:
        """Raw stage: Keep original name as-is."""
        return original_path.name

    def staged_name(
        self, original_path: Path, case_name: str | None = None, doc_type: str | None = None
    ) -> str:
        """
        Staged naming: {Case}_{Type}_{Date}_{OriginalName}

        Args:
            original_path: Original file path
            case_name: Case identifier (optional)
            doc_type: Document type (optional)

        Returns:
            Formatted staged name
        """
        date_str = datetime.now().strftime("%Y%m%d")

        # Clean case name and doc type
        case = self._clean_string(case_name) if case_name else "GENERAL"
        dtype = self._clean_string(doc_type) if doc_type else "DOC"

        # Get base name without extension
        base_name = original_path.stem
        extension = original_path.suffix

        # Clean base name
        clean_base = self._clean_string(base_name)[:50]  # Limit length

        return f"{case}_{dtype}_{date_str}_{clean_base}{extension}"

    def processed_name(self, original_path: Path, format: str = "md") -> str:
        """
        Processed naming: DOC_{Year}_{Sequence:04d}.{format}

        Args:
            original_path: Original file path
            format: Output format (md, json, etc.)

        Returns:
            Formatted processed name with sequence number
        """
        self.doc_counter += 1
        self._save_counter()

        year = datetime.now().year
        return f"DOC_{year}_{self.doc_counter:04d}.{format}"

    def export_name(
        self, doc_id: str, case_name: str | None = None, doc_type: str | None = None
    ) -> str:
        """
        Export naming: {DocID}_{Case}_{Type}_processed.md

        Args:
            doc_id: Document ID from processed stage
            case_name: Case identifier
            doc_type: Document type

        Returns:
            Formatted export name
        """
        case = self._clean_string(case_name) if case_name else "GENERAL"
        dtype = self._clean_string(doc_type) if doc_type else "DOC"

        # Extract base doc_id without extension
        base_id = Path(doc_id).stem

        return f"{base_id}_{case}_{dtype}_processed.md"

    def quarantine_name(self, original_path: Path, error_type: str = "ERROR") -> str:
        """
        Quarantine naming: {Timestamp}_{ErrorType}_{OriginalName}

        Args:
            original_path: Original file path
            error_type: Type of error that occurred

        Returns:
            Formatted quarantine name
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        error = self._clean_string(error_type)[:20]

        return f"{timestamp}_{error}_{original_path.name}"

    def _clean_string(self, text: str) -> str:
        """
        Clean string for use in filenames.

        Args:
            text: Input text to clean

        Returns:
            Cleaned string safe for filenames
        """
        # Remove special characters, keep alphanumeric and basic punctuation
        cleaned = re.sub(r"[^\w\s\-_]", "", text)
        # Replace spaces with underscores
        cleaned = re.sub(r"\s+", "_", cleaned)
        # Remove multiple underscores
        cleaned = re.sub(r"_+", "_", cleaned)
        # Strip leading/trailing underscores
        cleaned = cleaned.strip("_")

        return cleaned.upper()

    def extract_metadata_from_name(self, filename: str, stage: str) -> dict:
        """
        Extract metadata from filename based on stage.

        Args:
            filename: File name to parse
            stage: Lifecycle stage (raw, staged, processed, export)

        Returns:
            Dictionary of extracted metadata
        """
        metadata = {"original_name": filename, "stage": stage}

        if stage == "staged":
            # Parse: {Case}_{Type}_{Date}_{OriginalName}
            parts = filename.split("_")
            if len(parts) >= 4:
                metadata["case"] = parts[0]
                metadata["type"] = parts[1]
                metadata["date"] = parts[2]
                metadata["base_name"] = "_".join(parts[3:])

        elif stage == "processed":
            # Parse: DOC_{Year}_{Sequence}.{format}
            match = re.match(r"DOC_(\d{4})_(\d{4})\.(\w+)", filename)
            if match:
                metadata["year"] = match.group(1)
                metadata["sequence"] = int(match.group(2))
                metadata["format"] = match.group(3)

        elif stage == "export":
            # Parse: {DocID}_{Case}_{Type}_processed.md
            parts = filename.replace("_processed.md", "").split("_")
            if len(parts) >= 4:
                metadata["doc_id"] = f"{parts[0]}_{parts[1]}_{parts[2]}"
                metadata["case"] = parts[3] if len(parts) > 3 else None
                metadata["type"] = parts[4] if len(parts) > 4 else None

        return metadata

    def validate_name(self, filename: str, stage: str) -> bool:
        """
        Validate if filename follows convention for given stage.

        Args:
            filename: Filename to validate
            stage: Lifecycle stage

        Returns:
            True if valid, False otherwise
        """
        if stage == "raw":
            # Any name is valid for raw
            return True

        elif stage == "staged":
            # Should have at least 4 parts separated by underscore
            parts = filename.split("_")
            return len(parts) >= 4

        elif stage == "processed":
            # Should match DOC_YYYY_NNNN.format
            pattern = r"^DOC_\d{4}_\d{4}\.\w+$"
            return bool(re.match(pattern, filename))

        elif stage == "export":
            # Should end with _processed.md
            return filename.endswith("_processed.md")

        elif stage == "quarantine":
            # Should start with timestamp
            pattern = r"^\d{8}_\d{6}_"
            return bool(re.match(pattern, filename))

        return False
