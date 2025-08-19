"""Combined entity extractor that uses both spaCy NLP and legal pattern
matching.

Provides comprehensive entity extraction for legal documents and
correspondence.
"""

from typing import Any

from loguru import logger

from .base_extractor import BaseExtractor
from .legal_extractor import LegalExtractor
from .spacy_extractor import SpacyExtractor


class CombinedExtractor(BaseExtractor):
    """
    Combined extractor using both spaCy NLP and legal patterns.
    """

    def __init__(self) -> None:
        super().__init__("combined")
        # Logger is now imported globally from loguru

        # Initialize component extractors
        try:
            self.spacy_extractor = SpacyExtractor()
        except Exception as e:
            logger.warning(f"SpaCy extractor unavailable: {e}")
            self.spacy_extractor = None

        try:
            self.legal_extractor = LegalExtractor()
        except Exception as e:
            logger.warning(f"Legal extractor unavailable: {e}")
            self.legal_extractor = None

        # Validate at least one extractor is available
        self._validate_extractors()

    def _validate_extractors(self) -> None:
        """
        Validate that at least one extractor is available.
        """
        available_extractors = []

        if self.spacy_extractor and self.spacy_extractor.is_available():
            available_extractors.append("spacy")

        if self.legal_extractor and self.legal_extractor.is_available():
            available_extractors.append("legal")

        if not available_extractors:
            self.validation_result = {
                "success": False,
                "error": "No extractors available (spaCy or legal patterns)",
            }
        else:
            self.validation_result = {"success": True, "available_extractors": available_extractors}

    def extract_entities(self, text: str, message_id: str) -> dict[str, Any]:
        """
        Extract entities using both spaCy and legal pattern extractors.
        """
        if not self.validation_result["success"]:
            return {
                "success": False,
                "error": f"Combined extractor not available: {self.validation_result['error']}",
            }

        validation = self.validate_text(text)
        if not validation["success"]:
            return validation

        try:
            all_entities = []
            extraction_results = {}

            # Extract using spaCy if available
            if self.spacy_extractor and self.spacy_extractor.is_available():
                spacy_result = self.spacy_extractor.extract_entities(text, message_id)
                if spacy_result["success"]:
                    all_entities.extend(spacy_result["entities"])
                    extraction_results["spacy"] = {
                        "success": True,
                        "count": len(spacy_result["entities"]),
                    }
                else:
                    extraction_results["spacy"] = {
                        "success": False,
                        "error": spacy_result.get("error"),
                    }

            # Extract using legal patterns if available
            if self.legal_extractor and self.legal_extractor.is_available():
                legal_result = self.legal_extractor.extract_entities(text, message_id)
                if legal_result["success"]:
                    all_entities.extend(legal_result["entities"])
                    extraction_results["legal"] = {
                        "success": True,
                        "count": len(legal_result["entities"]),
                    }
                else:
                    extraction_results["legal"] = {
                        "success": False,
                        "error": legal_result.get("error"),
                    }

            # Deduplicate entities (remove overlapping extractions)
            deduplicated_entities = self._deduplicate_entities(all_entities)

            logger.debug(
                f"Combined extraction for {message_id}: "
                f"{len(all_entities)} total, {len(deduplicated_entities)} after deduplication"
            )

            return {
                "success": True,
                "entities": deduplicated_entities,
                "count": len(deduplicated_entities),
                "message_id": message_id,
                "extraction_results": extraction_results,
            }

        except Exception as e:
            error_msg = f"Combined entity extraction failed for {message_id}: {str(e)}"
            logger.error(error_msg)
            return {"success": False, "error": error_msg}

    def _deduplicate_entities(self, entities: list[dict]) -> list[dict]:
        """Remove duplicate entities based on text overlap and similarity.

        Prefers higher confidence entities when duplicates found.
        """
        if not entities:
            return entities

        # Sort by confidence (highest first) for preference in deduplication
        sorted_entities = sorted(entities, key=lambda x: x.get("confidence", 0), reverse=True)

        deduplicated = []

        for entity in sorted_entities:
            # Check if this entity overlaps significantly with any existing entity
            is_duplicate = False

            for existing in deduplicated:
                if self._entities_overlap(entity, existing):
                    is_duplicate = True
                    break

            if not is_duplicate:
                deduplicated.append(entity)

        return deduplicated

    def _entities_overlap(self, entity1: dict, entity2: dict, min_overlap: float = 0.5) -> bool:
        """Check if two entities overlap significantly in text position.

        Args:
            entity1, entity2: Entity dictionaries with start/end positions
            min_overlap: Minimum overlap ratio to consider as duplicate

        Returns:
            True if entities overlap significantly
        """
        start1, end1 = entity1.get("start", 0), entity1.get("end", 0)
        start2, end2 = entity2.get("start", 0), entity2.get("end", 0)

        # Calculate overlap
        overlap_start = max(start1, start2)
        overlap_end = min(end1, end2)

        if overlap_start >= overlap_end:
            return False  # No overlap

        overlap_length = overlap_end - overlap_start

        # Calculate overlap ratio relative to shorter entity
        len1 = end1 - start1
        len2 = end2 - start2
        min_length = min(len1, len2)

        if min_length == 0:
            return False

        overlap_ratio = overlap_length / min_length

        return overlap_ratio >= min_overlap

    def is_available(self) -> bool:
        """
        Check if combined extractor is available.
        """
        return self.validation_result["success"]

    def get_supported_entity_types(self) -> list[str]:
        """
        Get all supported entity types from both extractors.
        """
        all_types = set()

        if self.spacy_extractor and self.spacy_extractor.is_available():
            all_types.update(self.spacy_extractor.get_supported_entity_types())

        if self.legal_extractor and self.legal_extractor.is_available():
            all_types.update(self.legal_extractor.get_supported_entity_types())

        return sorted(list(all_types))

    def get_extractor_info(self) -> dict[str, Any]:
        """
        Get information about component extractors.
        """
        info = {"available": self.is_available(), "component_extractors": {}}

        if self.spacy_extractor:
            info["component_extractors"]["spacy"] = {
                "available": self.spacy_extractor.is_available(),
                "supported_types": (
                    self.spacy_extractor.get_supported_entity_types()
                    if self.spacy_extractor.is_available()
                    else []
                ),
            }

        if self.legal_extractor:
            info["component_extractors"]["legal"] = {
                "available": self.legal_extractor.is_available(),
                "supported_types": (
                    self.legal_extractor.get_supported_entity_types()
                    if self.legal_extractor.is_available()
                    else []
                ),
            }

        return info
