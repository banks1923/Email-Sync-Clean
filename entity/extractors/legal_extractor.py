"""Legal-specific entity extractor for legal documents and correspondence.

Extracts case numbers, courts, legal roles, statutes, and legal
concepts.
"""

import re
from typing import Any

from loguru import logger

from .base_extractor import BaseExtractor


class LegalExtractor(BaseExtractor):
    """
    Legal domain-specific entity extractor using pattern matching.
    """

    def __init__(self):
        super().__init__("legal")
        # Logger is now imported globally from loguru
        self._initialize_patterns()
        self.validation_result = {"success": True}

    def _initialize_patterns(self):
        """
        Initialize legal entity patterns.
        """
        # Case number patterns (various formats)
        self.case_patterns = [
            r"(?i)\b(?:case|matter|docket)\s*(?:no\.?|number)?\s*[:\-]?\s*([A-Z0-9\-\/\.\s]{3,20})",
            r"(?i)\b(?:cv|cr|civ|criminal)\s*[:\-]?\s*(\d{2,4}[\-\/]\d{1,6})",
            r"\b(\d{1,2}:\d{2}-(?:cv|cr)-\d{5}(?:-[A-Z]{2,3})?)\b",  # Federal format
            r"\b([A-Z]{1,3}\d{6,10})\b",  # State court format
        ]

        # Court name patterns
        self.court_patterns = [
            r"(?i)\b((?:supreme|superior|district|circuit|family|probate|municipal)\s+court(?:\s+of\s+[A-Za-z\s]+)?)",
            r"(?i)\b(united\s+states\s+(?:district\s+)?court(?:\s+for\s+the\s+[A-Za-z\s]+)?)",
            r"(?i)\b([A-Za-z\s]+\s+(?:court|tribunal|commission))\b",
        ]

        # Legal role keywords with context
        self.legal_roles = {
            "attorney": ["attorney", "lawyer", "counsel", "esq", "esquire"],
            "judge": ["judge", "justice", "magistrate", "honorable"],
            "client": ["client", "plaintiff", "defendant", "petitioner", "respondent"],
            "witness": ["witness", "deponent", "affiant"],
            "expert": ["expert", "consultant", "specialist"],
            "court_staff": ["clerk", "bailiff", "reporter", "stenographer"],
        }

        # Legal concepts and terms
        self.legal_concepts = [
            "contract",
            "agreement",
            "settlement",
            "verdict",
            "ruling",
            "motion",
            "deposition",
            "discovery",
            "subpoena",
            "summons",
            "complaint",
            "answer",
            "counterclaim",
            "cross-claim",
            "appeal",
            "hearing",
            "trial",
            "arbitration",
            "mediation",
            "injunction",
            "restraining order",
            "damages",
            "liability",
            "negligence",
            "breach",
            "violation",
            "statute",
            "regulation",
            "ordinance",
            "code",
            "law",
        ]

        # Statute/citation patterns
        self.statute_patterns = [
            r"(?i)\b(\d+\s+u\.?s\.?c\.?\s+§?\s*\d+(?:\([a-z0-9]+\))*)",  # USC
            r"(?i)\b(\d+\s+cfr\s+§?\s*\d+(?:\.\d+)*)",  # CFR
            r"(?i)\b([A-Z]{2,4}\s+§?\s*\d+(?:[\.\-]\d+)*)",  # State statutes
            r"(?i)\b(rule\s+\d+(?:\([a-z0-9]+\))*)",  # Rules
        ]

    def extract_entities(self, text: str, message_id: str) -> dict[str, Any]:
        """
        Extract legal entities from text.
        """
        if not self.validation_result["success"]:
            return {"success": False, "error": "Legal extractor not available"}

        validation = self.validate_text(text)
        if not validation["success"]:
            return validation

        try:
            entities = []

            # Extract case numbers
            entities.extend(self._extract_case_numbers(text, message_id))

            # Extract courts
            entities.extend(self._extract_courts(text, message_id))

            # Extract legal roles (context-aware)
            entities.extend(self._extract_legal_roles(text, message_id))

            # Extract legal concepts
            entities.extend(self._extract_legal_concepts(text, message_id))

            # Extract statutes/citations
            entities.extend(self._extract_statutes(text, message_id))

            logger.debug(f"Extracted {len(entities)} legal entities from {message_id}")

            return {
                "success": True,
                "entities": entities,
                "count": len(entities),
                "message_id": message_id,
            }

        except Exception as e:
            error_msg = f"Legal entity extraction failed for {message_id}: {str(e)}"
            logger.error(error_msg)
            return {"success": False, "error": error_msg}

    def _extract_case_numbers(self, text: str, message_id: str) -> list[dict]:
        """
        Extract case numbers using multiple patterns.
        """
        entities = []

        for pattern in self.case_patterns:
            for match in re.finditer(pattern, text):
                case_number = match.group(1).strip()
                if len(case_number) >= 3:  # Filter very short matches
                    entities.append(
                        {
                            "message_id": message_id,
                            "text": case_number,
                            "type": "CASE_NUMBER",
                            "label": "CASE_NUMBER",
                            "start": match.start(),
                            "end": match.end(),
                            "confidence": 0.9,  # High confidence for pattern matches
                            "normalized_form": self._normalize_case_number(case_number),
                        }
                    )

        return entities

    def _extract_courts(self, text: str, message_id: str) -> list[dict]:
        """
        Extract court names.
        """
        entities = []

        for pattern in self.court_patterns:
            for match in re.finditer(pattern, text):
                court_name = match.group(1).strip()
                entities.append(
                    {
                        "message_id": message_id,
                        "text": court_name,
                        "type": "COURT",
                        "label": "COURT",
                        "start": match.start(),
                        "end": match.end(),
                        "confidence": 0.85,
                        "normalized_form": self.normalize_entity(court_name),
                    }
                )

        return entities

    def _extract_legal_roles(self, text: str, message_id: str) -> list[dict]:
        """
        Extract legal roles with context awareness.
        """
        entities = []

        # Find person names first (simple pattern)
        name_pattern = r"\b([A-Z][a-z]+\s+[A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)\b"

        for name_match in re.finditer(name_pattern, text):
            name = name_match.group(1)
            start_pos = name_match.start()
            end_pos = name_match.end()

            # Look for role indicators near the name (within 50 characters)
            context_start = max(0, start_pos - 50)
            context_end = min(len(text), end_pos + 50)
            context = text[context_start:context_end].lower()

            for role_type, role_keywords in self.legal_roles.items():
                for keyword in role_keywords:
                    if keyword in context:
                        entities.append(
                            {
                                "message_id": message_id,
                                "text": name,
                                "type": "LEGAL_ROLE",
                                "label": f"LEGAL_ROLE_{role_type.upper()}",
                                "start": start_pos,
                                "end": end_pos,
                                "confidence": 0.75,
                                "normalized_form": self.normalize_entity(name),
                                "role_type": role_type,
                            }
                        )
                        break  # Found one role, don't duplicate

        return entities

    def _extract_legal_concepts(self, text: str, message_id: str) -> list[dict]:
        """
        Extract legal concepts and terms.
        """
        entities = []
        text_lower = text.lower()

        for concept in self.legal_concepts:
            # Use word boundaries to avoid partial matches
            pattern = r"\b" + re.escape(concept) + r"\b"

            for match in re.finditer(pattern, text_lower):
                # Get original case from source text
                original_text = text[match.start() : match.end()]

                entities.append(
                    {
                        "message_id": message_id,
                        "text": original_text,
                        "type": "LEGAL_CONCEPT",
                        "label": "LEGAL_CONCEPT",
                        "start": match.start(),
                        "end": match.end(),
                        "confidence": 0.8,
                        "normalized_form": concept,  # Use the standardized form
                    }
                )

        return entities

    def _extract_statutes(self, text: str, message_id: str) -> list[dict]:
        """
        Extract statute citations and legal references.
        """
        entities = []

        for pattern in self.statute_patterns:
            for match in re.finditer(pattern, text):
                statute = match.group(1).strip()
                entities.append(
                    {
                        "message_id": message_id,
                        "text": statute,
                        "type": "STATUTE",
                        "label": "STATUTE",
                        "start": match.start(),
                        "end": match.end(),
                        "confidence": 0.9,
                        "normalized_form": self._normalize_statute(statute),
                    }
                )

        return entities

    def _normalize_case_number(self, case_number: str) -> str:
        """
        Normalize case number format.
        """
        # Remove extra spaces and standardize separators
        normalized = re.sub(r"\s+", " ", case_number.strip())
        normalized = re.sub(r"[\-\/]", "-", normalized)
        return normalized.upper()

    def _normalize_statute(self, statute: str) -> str:
        """
        Normalize statute citation format.
        """
        # Standardize spacing and formatting
        normalized = re.sub(r"\s+", " ", statute.strip())
        normalized = re.sub(r"u\.?s\.?c\.?", "USC", normalized, flags=re.IGNORECASE)
        normalized = re.sub(r"cfr", "CFR", normalized, flags=re.IGNORECASE)
        return normalized

    def is_available(self) -> bool:
        """
        Legal extractor is always available (no external dependencies)
        """
        return True

    def get_supported_entity_types(self) -> list[str]:
        """
        Get legal entity types supported by this extractor.
        """
        return [
            "CASE_NUMBER",
            "COURT",
            "LEGAL_ROLE",
            "LEGAL_CONCEPT",
            "STATUTE",
        ]

    def get_legal_role_types(self) -> list[str]:
        """
        Get specific legal role types.
        """
        return list(self.legal_roles.keys())
