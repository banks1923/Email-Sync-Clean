"""Entity normalizer for advanced deduplication and alias management.

Handles fuzzy matching, name parsing, and entity consolidation.
"""

import re
from difflib import SequenceMatcher
from typing import Any

from loguru import logger


class EntityNormalizer:
    """
    Advanced entity deduplication and normalization.
    """

    def __init__(self):
        # Logger is now imported globally from loguru
        self._initialize_patterns()

    def _initialize_patterns(self):
        """
        Initialize normalization patterns.
        """

        # Name parsing patterns
        self.name_patterns = {
            "full_name": r"^([A-Z][a-z]+)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)$",
            "initial_last": r"^([A-Z]\.?\s*)+([A-Z][a-z]+)$",
            "last_first": r"^([A-Z][a-z]+),\s*([A-Z][a-z]+)$",
            "title_name": r"^(?:Mr\.?|Ms\.?|Mrs\.?|Dr\.?|Prof\.?)\s+(.+)$",
            "suffix_name": r"^(.+)\s+(?:Jr\.?|Sr\.?|III?|IV|Esq\.?)$",
        }

        # Organization name variations
        self.org_patterns = {
            "legal_suffixes": [
                "LLC",
                "Inc",
                "Corp",
                "Corporation",
                "Company",
                "Co",
                "LLP",
                "LP",
                "PC",
                "PA",
                "PLLC",
            ],
            "remove_chars": r'[.,\'"()]',
            "normalize_spaces": r"\s+",
        }

        # Legal role synonyms
        self.role_synonyms = {
            "attorney": ["lawyer", "counsel", "advocate", "solicitor"],
            "judge": ["justice", "magistrate", "honorable"],
            "client": ["customer", "party"],
        }

    def deduplicate_entities(self, entities: list[dict]) -> dict[str, Any]:
        """Deduplicate entities using fuzzy matching and normalization.

        Args:
            entities: List of raw entity extractions

        Returns:
            Dict with consolidated entities and mapping information
        """
        try:
            # Group entities by type for more accurate matching
            entities_by_type = {}
            for entity in entities:
                entity_type = entity.get("type", "UNKNOWN")
                if entity_type not in entities_by_type:
                    entities_by_type[entity_type] = []
                entities_by_type[entity_type].append(entity)

            consolidated_entities = {}
            entity_mappings = {}

            # Process each entity type separately
            for entity_type, type_entities in entities_by_type.items():
                if entity_type in ["PERSON", "ORG"]:
                    # Use advanced matching for people and organizations
                    type_consolidated, type_mappings = self._deduplicate_by_type(
                        type_entities, entity_type
                    )
                else:
                    # Use simple normalization for other types
                    type_consolidated, type_mappings = self._simple_deduplicate(
                        type_entities, entity_type
                    )

                consolidated_entities.update(type_consolidated)
                entity_mappings.update(type_mappings)

            logger.info(
                f"Deduplicated {len(entities)} entities into {len(consolidated_entities)} "
                f"consolidated entities"
            )

            return {
                "success": True,
                "consolidated_entities": consolidated_entities,
                "entity_mappings": entity_mappings,
                "original_count": len(entities),
                "consolidated_count": len(consolidated_entities),
            }

        except Exception as e:
            error_msg = f"Entity deduplication failed: {str(e)}"
            logger.error(error_msg)
            return {"success": False, "error": error_msg}

    def _deduplicate_by_type(self, entities: list[dict], entity_type: str) -> tuple[dict, dict]:
        """
        Deduplicate entities of a specific type using advanced matching.
        """
        consolidated = {}
        mappings = {}

        for entity in entities:
            best_match = self._find_best_match(entity, list(consolidated.values()), entity_type)

            if best_match:
                # Merge with existing entity
                consolidated_id = best_match["entity_id"]
                self._merge_entities(consolidated[consolidated_id], entity)
                mappings[self._get_entity_key(entity)] = consolidated_id
            else:
                # Create new consolidated entity
                consolidated_id = self._generate_consolidated_id(entity)
                consolidated[consolidated_id] = self._create_consolidated_entity(
                    entity, consolidated_id
                )
                mappings[self._get_entity_key(entity)] = consolidated_id

        return consolidated, mappings

    def _simple_deduplicate(self, entities: list[dict], entity_type: str) -> tuple[dict, dict]:
        """
        Simple deduplication based on normalized form.
        """
        consolidated = {}
        mappings = {}

        for entity in entities:
            normalized = entity.get("normalized_form", entity.get("text", "")).lower()

            # Find exact match
            existing_id = None
            for cons_id, cons_entity in consolidated.items():
                if cons_entity["primary_name"].lower() == normalized:
                    existing_id = cons_id
                    break

            if existing_id:
                # Merge with existing
                self._merge_entities(consolidated[existing_id], entity)
                mappings[self._get_entity_key(entity)] = existing_id
            else:
                # Create new
                consolidated_id = self._generate_consolidated_id(entity)
                consolidated[consolidated_id] = self._create_consolidated_entity(
                    entity, consolidated_id
                )
                mappings[self._get_entity_key(entity)] = consolidated_id

        return consolidated, mappings

    def _find_best_match(
        self, entity: dict, consolidated_entities: list[dict], entity_type: str
    ) -> dict:
        """
        Find the best matching consolidated entity.
        """
        entity_text = entity.get("text", "")
        entity.get("normalized_form", entity_text).lower()

        best_match = None
        best_score = 0.0
        similarity_threshold = 0.8  # Minimum similarity for match

        for cons_entity in consolidated_entities:
            # Calculate similarity score
            score = self._calculate_similarity(entity, cons_entity, entity_type)

            if score > similarity_threshold and score > best_score:
                best_match = cons_entity
                best_score = score

        return best_match

    def _calculate_similarity(self, entity1: dict, entity2: dict, entity_type: str) -> float:
        """
        Calculate similarity score between two entities.
        """
        text1 = entity1.get("text", "").lower()
        text2 = entity2.get("primary_name", "").lower()

        # Base string similarity
        base_similarity = SequenceMatcher(None, text1, text2).ratio()

        if entity_type == "PERSON":
            return self._person_similarity(entity1, entity2, base_similarity)
        elif entity_type == "ORG":
            return self._organization_similarity(entity1, entity2, base_similarity)
        else:
            return base_similarity

    def _person_similarity(self, entity1: dict, entity2: dict, base_similarity: float) -> float:
        """
        Calculate similarity for person entities.
        """
        text1 = entity1.get("text", "")
        text2 = entity2.get("primary_name", "")

        # Parse names into components
        name1_parts = self._parse_person_name(text1)
        name2_parts = self._parse_person_name(text2)

        # Check for name component matches
        component_matches = 0
        total_components = 0

        for key in ["first", "last", "middle"]:
            if name1_parts.get(key) and name2_parts.get(key):
                total_components += 1
                if name1_parts[key].lower() == name2_parts[key].lower():
                    component_matches += 1
                elif self._is_initial_match(name1_parts[key], name2_parts[key]):
                    component_matches += 0.8  # Partial credit for initial match

        if total_components > 0:
            name_similarity = component_matches / total_components
            # Combine with base similarity, giving more weight to name components
            return (name_similarity * 0.7) + (base_similarity * 0.3)

        return base_similarity

    def _organization_similarity(
        self, entity1: dict, entity2: dict, base_similarity: float
    ) -> float:
        """
        Calculate similarity for organization entities.
        """
        text1 = self._normalize_organization_name(entity1.get("text", ""))
        text2 = self._normalize_organization_name(entity2.get("primary_name", ""))

        # Calculate similarity on normalized names
        normalized_similarity = SequenceMatcher(None, text1, text2).ratio()

        # Give higher weight to normalized similarity for organizations
        return (normalized_similarity * 0.8) + (base_similarity * 0.2)

    def _parse_person_name(self, name: str) -> dict[str, str]:
        """
        Parse person name into components.
        """
        name = name.strip()
        components = {}

        # Try different name patterns
        for pattern_name, pattern in self.name_patterns.items():
            match = re.match(pattern, name)
            if match:
                if pattern_name == "full_name":
                    components["first"] = match.group(1)
                    rest = match.group(2).split()
                    components["last"] = rest[-1]
                    if len(rest) > 1:
                        components["middle"] = " ".join(rest[:-1])
                elif pattern_name == "initial_last":
                    components["first"] = match.group(1).replace(".", "").strip()
                    components["last"] = match.group(2)
                elif pattern_name == "last_first":
                    components["last"] = match.group(1)
                    components["first"] = match.group(2)
                break

        # Fallback: split on spaces
        if not components:
            parts = name.split()
            if len(parts) >= 2:
                components["first"] = parts[0]
                components["last"] = parts[-1]
                if len(parts) > 2:
                    components["middle"] = " ".join(parts[1:-1])

        return components

    def _normalize_organization_name(self, name: str) -> str:
        """
        Normalize organization name for comparison.
        """
        normalized = name.lower()

        # Remove legal suffixes for comparison
        for suffix in self.org_patterns["legal_suffixes"]:
            suffix_pattern = r"\b" + re.escape(suffix.lower()) + r"\.?\b"
            normalized = re.sub(suffix_pattern, "", normalized)

        # Remove punctuation and normalize spaces
        normalized = re.sub(self.org_patterns["remove_chars"], "", normalized)
        normalized = re.sub(self.org_patterns["normalize_spaces"], " ", normalized)

        return normalized.strip()

    def _is_initial_match(self, name1: str, name2: str) -> bool:
        """
        Check if one name is an initial of another.
        """
        # Check if either is a single character (initial)
        if len(name1) == 1 and len(name2) > 1:
            return name1.upper() == name2[0].upper()
        elif len(name2) == 1 and len(name1) > 1:
            return name2.upper() == name1[0].upper()
        return False

    def _create_consolidated_entity(self, entity: dict, entity_id: str) -> dict:
        """
        Create a new consolidated entity from a raw entity.
        """
        return {
            "entity_id": entity_id,
            "primary_name": entity.get("text", ""),
            "entity_type": entity.get("type", ""),
            "aliases": [entity.get("text")],
            "total_mentions": 1,
            "confidence_score": entity.get("confidence", 0.8),
            "additional_info": {
                "first_message_id": entity.get("message_id"),
                "extractor_type": entity.get("extractor_type", "unknown"),
                "role_type": entity.get("role_type"),
            },
        }

    def _merge_entities(self, consolidated: dict, new_entity: dict):
        """
        Merge a new entity into an existing consolidated entity.
        """
        # Add to aliases if not already present
        new_text = new_entity.get("text", "")
        if new_text not in consolidated["aliases"]:
            consolidated["aliases"].append(new_text)

        # Update counts
        consolidated["total_mentions"] += 1

        # Update confidence (weighted average)
        old_confidence = consolidated["confidence_score"]
        new_confidence = new_entity.get("confidence", 0.8)
        total_mentions = consolidated["total_mentions"]

        consolidated["confidence_score"] = (
            old_confidence * (total_mentions - 1) + new_confidence
        ) / total_mentions

        # Update additional info
        additional_info = consolidated.get("additional_info", {})
        if new_entity.get("role_type") and not additional_info.get("role_type"):
            additional_info["role_type"] = new_entity.get("role_type")

        consolidated["additional_info"] = additional_info

    def _generate_consolidated_id(self, entity: dict) -> str:
        """
        Generate a unique ID for a consolidated entity.
        """
        import hashlib

        text = entity.get("text", "")
        entity_type = entity.get("type", "")
        # Use a more stable hash for consolidated entities
        hash_input = f"{text.lower()}|{entity_type}"
        return f"entity_{hashlib.md5(hash_input.encode()).hexdigest()[:12]}"

    def _get_entity_key(self, entity: dict) -> str:
        """
        Get unique key for raw entity.
        """
        return f"{entity.get('message_id')}|{entity.get('start')}|{entity.get('end')}"
