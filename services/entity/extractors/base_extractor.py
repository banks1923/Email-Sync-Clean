"""Base abstract class for entity extractors.

Follows the same pattern as vector_service/providers/base_embedder.py
"""

from abc import ABC, abstractmethod
from typing import Any


class BaseExtractor(ABC):
    """
    Abstract base class for entity extraction providers.
    """

    def __init__(self, name: str) -> None:
        self.name = name
        self.validation_result = {"success": True}

    @abstractmethod
    def extract_entities(self, text: str, message_id: str) -> dict[str, Any]:
        """Extract named entities from text.

        Args:
            text: Input text to process
            message_id: Email message identifier

        Returns:
            Dict containing:
            - success: bool
            - entities: List of entity dicts with keys:
                - text: Entity text
                - label: Entity type (PERSON, ORG, etc.)
                - start: Start character position
                - end: End character position
                - confidence: Confidence score (0-1)
                - normalized_form: Normalized entity text
            - error: Error message if success=False
        """

    @abstractmethod
    def is_available(self) -> bool:
        """
        Check if extractor is available for use.
        """

    @abstractmethod
    def get_supported_entity_types(self) -> list[str]:
        """
        Get list of supported entity types.
        """

    def validate_text(self, text: str, max_length: int = 10000) -> dict[str, Any]:
        """
        Validate input text before processing.
        """
        if not text or not isinstance(text, str):
            return {"success": False, "error": "Text must be a non-empty string"}

        if len(text) > max_length:
            return {
                "success": False,
                "error": f"Text length ({len(text)}) exceeds maximum ({max_length})",
            }

        return {"success": True}

    def normalize_entity(self, entity_text: str) -> str:
        """
        Normalize entity text for consistent storage.
        """
        return entity_text.strip().lower()

    def filter_entities(
        self,
        entities: list[dict],
        confidence_threshold: float = 0.5,
        allowed_types: list[str] = None,
    ) -> list[dict]:
        """
        Filter entities by confidence and type.
        """
        filtered = []

        for entity in entities:
            # Filter by confidence
            if entity.get("confidence", 1.0) < confidence_threshold:
                continue

            # Filter by type
            if allowed_types and entity.get("label") not in allowed_types:
                continue

            filtered.append(entity)

        return filtered

    def __str__(self) -> str:
        return f"{self.__class__.__name__}({self.name})"
