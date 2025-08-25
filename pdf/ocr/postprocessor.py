"""OCR postprocessor module - cleans and improves OCR output."""

import re
from typing import Any

# Logger is now imported globally from loguru


class OCRPostprocessor:
    """
    Cleans and improves OCR output quality.
    """

    def __init__(self) -> None:
        self.common_ocr_errors = {
            # Common OCR substitutions
            " l ": " I ",  # Lowercase L often read as uppercase I
            " 0 ": " O ",  # Zero read as O in text context
            " rn ": " m ",  # rn often read as m
            "  ": " ",  # Multiple spaces to single
        }

    def clean_ocr_text(self, text: str) -> str:
        """Clean OCR text output.

        Args:
            text: Raw OCR text

        Returns:
            Cleaned text
        """
        if not text:
            return ""

        # Remove excessive whitespace
        text = " ".join(text.split())

        # Fix common OCR errors
        for error, correction in self.common_ocr_errors.items():
            text = text.replace(error, correction)

        # Remove orphaned single characters (often noise)
        text = re.sub(r"\b\w\b\s*", "", text)

        # Fix spacing around punctuation
        text = re.sub(r"\s+([.,!?;:])", r"\1", text)
        text = re.sub(r"([.,!?;:])\s*", r"\1 ", text)

        # Remove repeated punctuation
        text = re.sub(r"([.,!?;:])\1+", r"\1", text)

        # Trim and return
        return text.strip()

    def merge_page_texts(self, page_texts: list[str]) -> str:
        """Merge texts from multiple pages intelligently.

        Args:
            page_texts: List of text from each page

        Returns:
            Merged text
        """
        merged_parts: list[str] = []

        for i, text in enumerate(page_texts):
            if not text.strip():
                continue

            # Clean the text
            cleaned = self.clean_ocr_text(text)

            if i > 0 and merged_parts:
                # Check if previous page ended mid-sentence
                last_text = merged_parts[-1]
                if last_text and not last_text.rstrip().endswith((".", "!", "?")):
                    # Likely continued sentence, join without break
                    merged_parts[-1] = last_text.rstrip() + " " + cleaned
                else:
                    merged_parts.append(cleaned)
            else:
                merged_parts.append(cleaned)

        return "\n\n".join(merged_parts)

    def validate_ocr_quality(self, text: str, confidence: float) -> dict[str, Any]:
        """Validate OCR output quality.

        Args:
            text: OCR extracted text
            confidence: OCR confidence score (0-1)

        Returns:
            Quality assessment
        """
        if not text:
            return {"quality": "empty", "valid": False, "warnings": ["No text extracted"]}

        warnings = []
        word_count = len(text.split())

        # Check confidence
        if confidence < 0.5:
            warnings.append(f"Low confidence: {confidence:.0%}")

        # Check text length
        if word_count < 10:
            warnings.append(f"Very short text: {word_count} words")

        # Check for excessive noise (too many special chars)
        special_char_ratio = len(re.findall(r"[^a-zA-Z0-9\s.,!?]", text)) / len(text)
        if special_char_ratio > 0.3:
            warnings.append(f"High noise: {special_char_ratio:.0%} special characters")

        # Determine quality level
        if confidence >= 0.8 and not warnings:
            quality = "high"
        elif confidence >= 0.6 and len(warnings) <= 1:
            quality = "medium"
        else:
            quality = "low"

        return {
            "quality": quality,
            "valid": quality != "empty",
            "confidence": confidence,
            "word_count": word_count,
            "warnings": warnings,
        }

    def extract_metadata_hints(self, text: str) -> dict[str, Any]:
        """Extract metadata hints from OCR text.

        Args:
            text: OCR text to analyze

        Returns:
            Metadata hints
        """
        metadata = {}

        # Look for dates
        date_patterns = [
            r"\b\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b",
            r"\b\d{4}[/-]\d{1,2}[/-]\d{1,2}\b",
            r"\b(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]* \d{1,2},? \d{4}\b",
        ]

        dates = []
        for pattern in date_patterns:
            dates.extend(re.findall(pattern, text, re.IGNORECASE))

        if dates:
            metadata["extracted_dates"] = dates[:5]  # First 5 dates

        # Look for document type hints
        doc_types = [
            "contract",
            "agreement",
            "invoice",
            "receipt",
            "letter",
            "memorandum",
            "report",
            "statement",
        ]

        found_types = []
        text_lower = text.lower()
        for doc_type in doc_types:
            if doc_type in text_lower:
                found_types.append(doc_type)

        if found_types:
            metadata["document_types"] = found_types

        return metadata
