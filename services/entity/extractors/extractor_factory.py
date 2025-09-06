"""Factory for creating entity extractors.

Follows the same pattern as vector_service/providers/embedder_factory.py
"""

from typing import Any

from .base_extractor import BaseExtractor
from .combined_extractor import CombinedExtractor
from .legal_extractor import LegalExtractor
from .spacy_extractor import SpacyExtractor


class ExtractorFactory:
    """
    Factory for creating entity extraction providers.
    """

    # Registry of available extractors
    EXTRACTORS = {
        "combined": CombinedExtractor,  # Best option: spaCy + legal patterns
        "spacy": SpacyExtractor,
        "legal": LegalExtractor,
        # Future extractors could be added here:
        # "transformers": TransformersExtractor,
        # "openai": OpenAIExtractor,
    }

    @classmethod
    def create_extractor(cls, extractor_type: str = "combined", **kwargs) -> BaseExtractor:
        """Create an entity extractor instance.

        Args:
            extractor_type: Type of extractor to create
            **kwargs: Additional arguments for extractor initialization

        Returns:
            BaseExtractor instance

        Raises:
            ValueError: If extractor type is not supported
        """
        if extractor_type not in cls.EXTRACTORS:
            available = ", ".join(cls.EXTRACTORS.keys())
            raise ValueError(
                f"Unsupported extractor type '{extractor_type}'. Available: {available}"
            )

        extractor_class = cls.EXTRACTORS[extractor_type]
        return extractor_class(**kwargs)

    @classmethod
    def get_available_extractors(cls) -> dict[str, dict[str, Any]]:
        """Get information about all available extractors.

        Returns:
            Dict mapping extractor names to their info
        """
        extractors_info = {}

        for name, extractor_class in cls.EXTRACTORS.items():
            try:
                # Create a temporary instance to check availability
                temp_extractor = extractor_class()

                extractors_info[name] = {
                    "available": temp_extractor.is_available(),
                    "class": extractor_class.__name__,
                    "supported_types": (
                        temp_extractor.get_supported_entity_types()
                        if temp_extractor.is_available()
                        else []
                    ),
                    "validation_result": temp_extractor.validation_result,
                }

                # Clean up if needed
                del temp_extractor

            except Exception as e:
                extractors_info[name] = {
                    "available": False,
                    "class": extractor_class.__name__,
                    "supported_types": [],
                    "validation_result": {"success": False, "error": str(e)},
                }

        return extractors_info

    @classmethod
    def get_best_available_extractor(cls, preferred: str | None = None) -> BaseExtractor:
        """Get the best available extractor.

        Args:
            preferred: Preferred extractor type, if available

        Returns:
            Best available BaseExtractor instance

        Raises:
            RuntimeError: If no extractors are available
        """
        available_extractors = cls.get_available_extractors()

        # Filter to only available extractors
        available = {name: info for name, info in available_extractors.items() if info["available"]}

        if not available:
            raise RuntimeError("No entity extractors are available")

        # Try preferred extractor first
        if preferred and preferred in available:
            return cls.create_extractor(preferred)

        # Fall back to priority order
        priority_order = [
            "combined",
            "spacy",
            "legal",
        ]  # Combined is best, then individual extractors

        for extractor_type in priority_order:
            if extractor_type in available:
                return cls.create_extractor(extractor_type)

        # If none in priority order, use first available
        first_available = next(iter(available.keys()))
        return cls.create_extractor(first_available)

    @classmethod
    def validate_extractor_config(
        cls, extractor_type: str, config: dict[str, Any]
    ) -> dict[str, Any]:
        """Validate configuration for a specific extractor type.

        Args:
            extractor_type: Type of extractor
            config: Configuration to validate

        Returns:
            Validation result dict
        """
        if extractor_type not in cls.EXTRACTORS:
            return {"success": False, "error": f"Unknown extractor type: {extractor_type}"}

        try:
            # Create temporary instance with config to validate
            extractor_class = cls.EXTRACTORS[extractor_type]
            temp_extractor = extractor_class(**config)
            result = temp_extractor.validation_result.copy()

            # Clean up
            del temp_extractor

            return result

        except Exception as e:
            return {"success": False, "error": f"Configuration validation failed: {str(e)}"}


# Convenience alias following the embedder pattern
EntityExtractor = ExtractorFactory  # For backward compatibility if needed
