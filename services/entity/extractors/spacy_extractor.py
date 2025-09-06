"""SpaCy-based entity extractor implementation.

Provides named entity recognition using spaCy's en_core_web_sm model.
"""

from typing import Any

from loguru import logger

from .base_extractor import BaseExtractor


class SpacyExtractor(BaseExtractor):
    """
    SpaCy-based named entity extractor.
    """

    def __init__(self, model_name: str = "en_core_web_sm") -> None:
        super().__init__("spacy")
        self.model_name = model_name
        self.nlp = None
        # Logger is now imported globally from loguru
        self._initialize_model()

    def _initialize_model(self) -> None:
        """
        Initialize spaCy model with lazy loading.
        """
        try:
            import spacy

            self.nlp = spacy.load(self.model_name)
            self.validation_result = {"success": True}
            logger.info(f"SpaCy model '{self.model_name}' loaded successfully")
        except ImportError:
            self.validation_result = {
                "success": False,
                "error": "spaCy not installed. Run: pip install spacy",
            }
        except OSError:
            self.validation_result = {
                "success": False,
                "error": f"SpaCy model '{self.model_name}' not found. Run: python -m spacy download {self.model_name}",
            }
        except Exception as e:
            self.validation_result = {
                "success": False,
                "error": f"Failed to load spaCy model: {str(e)}",
            }

    def extract_entities(self, text: str, message_id: str) -> dict[str, Any]:
        """Extract named entities using spaCy NLP model.

        Returns entities in the format expected by the database:
        - message_id, text, type, label, start, end, confidence, normalized_form
        """
        if not self.validation_result["success"]:
            return {
                "success": False,
                "error": f"SpaCy extractor not available: {self.validation_result['error']}",
            }

        # Validate input text
        validation = self.validate_text(text)
        if not validation["success"]:
            return validation

        try:
            # Process text with spaCy
            doc = self.nlp(text)

            # Extract entities
            entities = []
            for ent in doc.ents:
                entity_data = {
                    "message_id": message_id,
                    "text": ent.text,
                    "type": ent.label_,  # PERSON, ORG, GPE, etc.
                    "label": ent.label_,  # Same as type for spaCy
                    "start": ent.start_char,
                    "end": ent.end_char,
                    "confidence": self._get_entity_confidence(ent),
                    "normalized_form": self.normalize_entity(ent.text),
                }
                entities.append(entity_data)

            logger.debug(f"Extracted {len(entities)} entities from message {message_id}")

            return {
                "success": True,
                "entities": entities,
                "count": len(entities),
                "message_id": message_id,
            }

        except Exception as e:
            error_msg = f"Entity extraction failed for {message_id}: {str(e)}"
            logger.error(error_msg)
            return {"success": False, "error": error_msg}

    def _get_entity_confidence(self, ent) -> float:
        """Get confidence score for entity.

        SpaCy doesn't provide confidence directly, so we use a
        heuristic.
        """
        # Simple heuristic based on entity length and type
        base_confidence = 0.8

        # Longer entities tend to be more reliable
        if len(ent.text) > 10:
            base_confidence += 0.1
        elif len(ent.text) < 3:
            base_confidence -= 0.2

        # Some entity types are more reliable
        reliable_types = ["PERSON", "ORG", "GPE", "MONEY", "DATE"]
        if ent.label_ in reliable_types:
            base_confidence += 0.1

        return min(1.0, max(0.1, base_confidence))

    def is_available(self) -> bool:
        """
        Check if spaCy extractor is available.
        """
        return self.validation_result["success"] and self.nlp is not None

    def get_supported_entity_types(self) -> list[str]:
        """
        Get spaCy's supported entity types.
        """
        if not self.is_available():
            return []

        # Common spaCy entity types
        return [
            "PERSON",  # People, including fictional
            "NORP",  # Nationalities or religious/political groups
            "FAC",  # Buildings, airports, highways, bridges, etc.
            "ORG",  # Companies, agencies, institutions, etc.
            "GPE",  # Countries, cities, states
            "LOC",  # Non-GPE locations, mountain ranges, bodies of water
            "PRODUCT",  # Objects, vehicles, foods, etc.
            "EVENT",  # Named hurricanes, battles, wars, etc.
            "WORK_OF_ART",  # Titles of books, songs, etc.
            "LAW",  # Named documents made into laws
            "LANGUAGE",  # Any named language
            "DATE",  # Absolute or relative dates or periods
            "TIME",  # Times smaller than a day
            "PERCENT",  # Percentage, including "%"
            "MONEY",  # Monetary values, including unit
            "QUANTITY",  # Measurements, as of weight or distance
            "ORDINAL",  # "first", "second", etc.
            "CARDINAL",  # Numerals that do not fall under another type
        ]

    def extract_entities_batch(
        self,
        texts_with_ids: list[tuple],
        confidence_threshold: float = 0.5,
        allowed_types: list[str] = None,
    ) -> dict[str, Any]:
        """Process multiple texts in batch for efficiency.

        Args:
            texts_with_ids: List of (text, message_id) tuples
            confidence_threshold: Minimum confidence for entities
            allowed_types: Only extract these entity types

        Returns:
            Dict with batch results
        """
        if not self.is_available():
            return {
                "success": False,
                "error": f"SpaCy extractor not available: {self.validation_result['error']}",
            }

        try:
            all_entities = []
            processed_count = 0

            for text, message_id in texts_with_ids:
                result = self.extract_entities(text, message_id)
                if result["success"]:
                    # Apply filtering
                    entities = self.filter_entities(
                        result["entities"],
                        confidence_threshold=confidence_threshold,
                        allowed_types=allowed_types,
                    )
                    all_entities.extend(entities)
                    processed_count += 1
                else:
                    logger.warning(
                        f"Failed to extract entities for {message_id}: {result.get('error')}"
                    )

            return {
                "success": True,
                "entities": all_entities,
                "total_entities": len(all_entities),
                "processed_emails": processed_count,
                "requested_emails": len(texts_with_ids),
            }

        except Exception as e:
            error_msg = f"Batch entity extraction failed: {str(e)}"
            logger.error(error_msg)
            return {"success": False, "error": error_msg}

    def get_model_info(self) -> dict[str, Any]:
        """
        Get information about the loaded spaCy model.
        """
        if not self.is_available():
            return {"available": False, "error": self.validation_result["error"]}

        return {
            "available": True,
            "model_name": self.model_name,
            "model_meta": self.nlp.meta,
            "supported_entities": len(self.get_supported_entity_types()),
            "pipeline_components": list(self.nlp.pipe_names),
        }
