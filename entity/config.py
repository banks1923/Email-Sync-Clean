"""Configuration and validation for entity service.

Follows existing patterns from vector_service/config.py
"""

import os
from typing import Any


class EntityConfig:
    """
    Configuration manager for entity service.
    """

    def __init__(self) -> None:
        # Logger is now imported globally from loguru
        self.config = self._load_config()
        self.validation_result = self._validate_config()

    def _load_config(self) -> dict[str, Any]:
        """
        Load configuration with defaults.
        """
        return {
            # SpaCy model configuration
            "spacy_model": os.getenv("ENTITY_SPACY_MODEL", "en_core_web_sm"),
            "batch_size": int(os.getenv("ENTITY_BATCH_SIZE", "100")),
            # Entity filtering
            "confidence_threshold": float(os.getenv("ENTITY_CONFIDENCE_THRESHOLD", "0.5")),
            "entity_types": os.getenv("ENTITY_TYPES", "PERSON,ORG,GPE,MONEY,DATE").split(","),
            # Database configuration
            "db_path": os.getenv("ENTITY_DB_PATH", "data/emails.db"),
            "max_connections": int(os.getenv("ENTITY_DB_CONNECTIONS", "5")),
            # Processing configuration
            "max_text_length": int(os.getenv("ENTITY_MAX_TEXT_LENGTH", "10000")),
            "enable_normalization": os.getenv("ENTITY_NORMALIZE", "true").lower() == "true",
        }

    def _validate_config(self) -> dict[str, Any]:
        """
        Validate configuration settings.
        """
        try:
            # Validate spaCy model availability
            import spacy

            try:
                spacy.load(self.config["spacy_model"])
            except OSError:
                return {
                    "success": False,
                    "error": f"SpaCy model '{self.config['spacy_model']}' not found. Run: python -m spacy download {self.config['spacy_model']}",
                }

            # Validate numeric ranges
            if self.config["batch_size"] <= 0:
                return {"success": False, "error": "Batch size must be positive"}

            if not 0 <= self.config["confidence_threshold"] <= 1:
                return {"success": False, "error": "Confidence threshold must be between 0 and 1"}

            if self.config["max_connections"] <= 0:
                return {"success": False, "error": "Max connections must be positive"}

            return {"success": True}

        except ImportError as e:
            return {"success": False, "error": f"Missing required dependency: {e}"}
        except Exception as e:
            return {"success": False, "error": f"Configuration validation error: {e}"}

    def get(self, key: str, default=None):
        """
        Get configuration value.
        """
        return self.config.get(key, default)

    def is_valid(self) -> bool:
        """
        Check if configuration is valid.
        """
        return self.validation_result["success"]
