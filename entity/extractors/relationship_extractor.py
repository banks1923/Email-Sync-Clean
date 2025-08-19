"""Relationship extractor for building knowledge graphs from entity co-
occurrences.

Analyzes entity relationships based on proximity, context, and legal
patterns.
"""

import re
from typing import Any

from loguru import logger


class RelationshipExtractor:
    """
    Extract relationships between entities for knowledge graph construction.
    """

    def __init__(self) -> None:
        self.name = "relationship"
        # Logger is now imported globally from loguru
        self._initialize_patterns()
        self.validation_result = {"success": True}

    def _initialize_patterns(self) -> None:
        """
        Initialize relationship detection patterns.
        """

        # Relationship indicators with confidence scores
        self.relationship_patterns = {
            # Professional relationships
            "works_for": {
                "patterns": [
                    r"(?:works?\s+(?:for|at)|employed\s+(?:by|at)|attorney\s+(?:for|at)|counsel\s+(?:for|to))",
                    r"(?:represents?|representing)",
                    r"(?:partner\s+at|associate\s+at)",
                ],
                "confidence": 0.8,
            },
            "colleagues": {
                "patterns": [
                    r"(?:and|with|alongside)",
                    r"(?:team|group|department)",
                    r"(?:co-counsel|co-attorney)",
                ],
                "confidence": 0.6,
            },
            "legal_relationship": {
                "patterns": [
                    r"(?:v\.|vs\.|versus)",  # Adversarial relationship
                    r"(?:plaintiff|defendant)\s+(?:is|are)",
                    r"(?:client|customer)\s+(?:is|are)",
                ],
                "confidence": 0.9,
            },
            "communication": {
                "patterns": [
                    r"(?:spoke\s+(?:with|to)|talked\s+(?:with|to)|discussed\s+with)",
                    r"(?:met\s+with|meeting\s+with)",
                    r"(?:called|phoned|contacted)",
                    r"(?:email\s+(?:from|to)|message\s+(?:from|to))",
                ],
                "confidence": 0.7,
            },
            "mentioned_together": {
                "patterns": [
                    r"(?:and|,\s*and|;\s*)",  # Simple co-occurrence
                ],
                "confidence": 0.4,
            },
        }

        # Context window for relationship detection (characters)
        self.context_window = 100

    def extract_relationships(
        self, entities: list[dict], text: str, message_id: str
    ) -> dict[str, Any]:
        """Extract relationships between entities in the given text.

        Args:
            entities: List of extracted entities from the text
            text: Source text content
            message_id: Email message identifier

        Returns:
            Dict with extracted relationships
        """
        if not entities or len(entities) < 2:
            return {"success": True, "relationships": [], "count": 0, "message_id": message_id}

        try:
            relationships = []

            # Sort entities by position for efficient processing
            sorted_entities = sorted(entities, key=lambda x: x.get("start", 0))

            # Find relationships between entity pairs
            for i, entity1 in enumerate(sorted_entities):
                for j, entity2 in enumerate(sorted_entities[i + 1 :], i + 1):
                    # Skip if entities are the same
                    if entity1.get("entity_id") == entity2.get("entity_id"):
                        continue

                    # Check proximity and extract relationships
                    rel_results = self._analyze_entity_pair(entity1, entity2, text, message_id)
                    relationships.extend(rel_results)

            # Deduplicate relationships
            unique_relationships = self._deduplicate_relationships(relationships)

            logger.debug(
                f"Extracted {len(unique_relationships)} relationships from {len(entities)} entities in {message_id}"
            )

            return {
                "success": True,
                "relationships": unique_relationships,
                "count": len(unique_relationships),
                "message_id": message_id,
            }

        except Exception as e:
            error_msg = f"Relationship extraction failed for {message_id}: {str(e)}"
            logger.error(error_msg)
            return {"success": False, "error": error_msg}

    def _analyze_entity_pair(
        self, entity1: dict, entity2: dict, text: str, message_id: str
    ) -> list[dict]:
        """
        Analyze relationship between two specific entities.
        """
        relationships = []

        # Get entity positions
        start1, end1 = entity1.get("start", 0), entity1.get("end", 0)
        start2, end2 = entity2.get("start", 0), entity2.get("end", 0)

        # Calculate distance between entities
        if end1 < start2:
            distance = start2 - end1
            context_start = max(0, end1 - self.context_window // 2)
            context_end = min(len(text), start2 + self.context_window // 2)
        else:
            distance = start1 - end2
            context_start = max(0, end2 - self.context_window // 2)
            context_end = min(len(text), start1 + self.context_window // 2)

        # Skip if entities are too far apart
        if distance > self.context_window:
            return relationships

        # Extract context between/around entities
        context = text[context_start:context_end].lower()

        # Check for relationship patterns in context
        for rel_type, rel_info in self.relationship_patterns.items():
            for pattern in rel_info["patterns"]:
                if re.search(pattern, context, re.IGNORECASE):
                    # Determine relationship direction based on pattern and position
                    if start1 < start2:
                        source_entity = entity1
                        target_entity = entity2
                    else:
                        source_entity = entity2
                        target_entity = entity1

                    relationship = {
                        "source_entity_id": source_entity.get("entity_id"),
                        "target_entity_id": target_entity.get("entity_id"),
                        "relationship_type": rel_type,
                        "confidence": self._calculate_confidence(
                            rel_info["confidence"], distance, context, pattern
                        ),
                        "source_message_id": message_id,
                        "context_snippet": context.strip(),
                        "source_entity_text": source_entity.get("text"),
                        "target_entity_text": target_entity.get("text"),
                    }
                    relationships.append(relationship)
                    break  # Found one pattern, don't duplicate

        return relationships

    def _calculate_confidence(
        self, base_confidence: float, distance: int, context: str, pattern: str
    ) -> float:
        """
        Calculate relationship confidence based on multiple factors.
        """
        confidence = base_confidence

        # Adjust for distance (closer entities = higher confidence)
        if distance < 20:
            confidence += 0.2
        elif distance < 50:
            confidence += 0.1
        elif distance > 80:
            confidence -= 0.1

        # Adjust for context richness
        if len(context.split()) > 10:
            confidence += 0.05

        # Adjust for pattern specificity
        if len(pattern) > 20:  # More specific patterns
            confidence += 0.1

        # Ensure confidence stays within bounds
        return min(1.0, max(0.1, confidence))

    def _deduplicate_relationships(self, relationships: list[dict]) -> list[dict]:
        """
        Remove duplicate relationships, keeping highest confidence.
        """
        seen = {}

        for rel in relationships:
            # Create unique key for relationship
            key = (rel["source_entity_id"], rel["target_entity_id"], rel["relationship_type"])

            # Keep relationship with higher confidence
            if key not in seen or rel["confidence"] > seen[key]["confidence"]:
                seen[key] = rel

        return list(seen.values())

    def extract_email_header_relationships(
        self, email_data: dict, entities: list[dict]
    ) -> list[dict]:
        """
        Extract relationships from email headers (sender, recipients)
        """
        relationships = []

        try:
            sender = email_data.get("sender", "")
            recipients = email_data.get("recipient_to", "")
            message_id = email_data.get("message_id", "")

            # Find entities that match email participants
            sender_entities = self._find_matching_entities(sender, entities)
            recipient_entities = self._find_matching_entities(recipients, entities)

            # Create communication relationships
            for sender_entity in sender_entities:
                for recipient_entity in recipient_entities:
                    if sender_entity.get("entity_id") != recipient_entity.get("entity_id"):
                        relationships.append(
                            {
                                "source_entity_id": sender_entity.get("entity_id"),
                                "target_entity_id": recipient_entity.get("entity_id"),
                                "relationship_type": "email_communication",
                                "confidence": 0.9,  # High confidence for email headers
                                "source_message_id": message_id,
                                "context_snippet": f"Email from {sender} to {recipients}",
                                "source_entity_text": sender_entity.get("text"),
                                "target_entity_text": recipient_entity.get("text"),
                            }
                        )

        except Exception as e:
            logger.warning(f"Failed to extract header relationships: {e}")

        return relationships

    def _find_matching_entities(self, text: str, entities: list[dict]) -> list[dict]:
        """
        Find entities that match text (e.g., email addresses, names)
        """
        matching = []
        text_lower = text.lower()

        for entity in entities:
            entity_text = entity.get("text", "").lower()
            normalized = entity.get("normalized_form", "").lower()

            # Check for matches
            if (
                entity_text in text_lower
                or normalized in text_lower
                or any(alias.lower() in text_lower for alias in entity.get("aliases", []))
            ):
                matching.append(entity)

        return matching

    def is_available(self) -> bool:
        """
        Relationship extractor is always available.
        """
        return True

    def get_supported_entity_types(self) -> list[str]:
        """
        This extractor works with any entity types.
        """
        return ["ALL"]  # Works with all entity types

    def get_relationship_types(self) -> list[str]:
        """
        Get supported relationship types.
        """
        return list(self.relationship_patterns.keys()) + ["email_communication"]
