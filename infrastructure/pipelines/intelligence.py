"""Document Intelligence Extraction

Integrates summarization, entity extraction, and relationship building.
"""

from datetime import datetime
from typing import Any

from loguru import logger

# Logger is now imported globally from loguru


class DocumentIntelligence:
    """Extract intelligence from documents."""

    def __init__(self):
        """Initialize document intelligence extractor."""
        self._summarizer = None
        self._entity_extractor = None
        self._db = None

    @property
    def summarizer(self):
        """Lazy load summarizer."""
        if self._summarizer is None:
            try:
                from summarization import get_document_summarizer

                self._summarizer = get_document_summarizer()
            except ImportError:
                logger.warning("Summarization module not available")
        return self._summarizer

    @property
    def entity_extractor(self):
        """Lazy load entity extractor."""
        if self._entity_extractor is None:
            try:
                from entity.main import EntityService

                self._entity_extractor = EntityService()
            except ImportError:
                logger.warning("Entity extraction module not available")
        return self._entity_extractor

    @property
    def db(self):
        """Lazy load database connection."""
        if self._db is None:
            from shared.simple_db import SimpleDB

            self._db = SimpleDB()
        return self._db

    def extract_summary(
        self, text: str, max_sentences: int = 5, max_keywords: int = 15
    ) -> dict[str, Any]:
        """Extract document summary.

        Args:
            text: Document text
            max_sentences: Maximum sentences in summary
            max_keywords: Maximum keywords to extract

        Returns:
            Dict with summary data
        """
        if not self.summarizer:
            return {}

        try:
            summary = self.summarizer.extract_summary(
                text=text,
                max_sentences=max_sentences,
                max_keywords=max_keywords,
                summary_type="combined",
            )

            return {
                "summary_text": summary.get("combined_summary", ""),
                "tf_idf_keywords": summary.get("tfidf_keywords", {}),
                "textrank_sentences": summary.get("textrank_sentences", []),
                "extracted_at": datetime.utcnow().isoformat() + "Z",
            }
        except Exception as e:
            logger.error(f"Failed to extract summary: {e}")
            return {}

    def extract_entities(self, text: str) -> dict[str, Any]:
        """Extract named entities from document.

        Args:
            text: Document text

        Returns:
            Dict with entity data
        """
        if not self.entity_extractor:
            return {}

        try:
            entities = self.entity_extractor.extract_entities(text)

            # Organize entities by type
            organized = {
                "persons": [],
                "organizations": [],
                "locations": [],
                "dates": [],
                "case_numbers": [],
                "monetary_values": [],
                "other": [],
            }

            for entity in entities:
                entity_type = entity.get("type", "OTHER").lower()
                entity_text = entity.get("text", "")

                if entity_type == "person":
                    organized["persons"].append(entity_text)
                elif entity_type in ["org", "organization"]:
                    organized["organizations"].append(entity_text)
                elif entity_type in ["loc", "location", "gpe"]:
                    organized["locations"].append(entity_text)
                elif entity_type == "date":
                    organized["dates"].append(entity_text)
                elif entity_type == "money":
                    organized["monetary_values"].append(entity_text)
                elif "case" in entity_text.lower() or "cv-" in entity_text.lower():
                    organized["case_numbers"].append(entity_text)
                else:
                    organized["other"].append(entity_text)

            # Remove duplicates
            for key in organized:
                organized[key] = list(set(organized[key]))

            return {
                "entities": organized,
                "total_entities": sum(len(v) for v in organized.values()),
                "extracted_at": datetime.utcnow().isoformat() + "Z",
            }
        except Exception as e:
            logger.error(f"Failed to extract entities: {e}")
            return {}

    def build_relationships(
        self, content_id: str, text: str, metadata: dict[str, Any]
    ) -> dict[str, Any]:
        """Build document relationships.

        Args:
            content_id: Document content ID
            text: Document text
            metadata: Document metadata

        Returns:
            Dict with relationship data
        """
        relationships = []

        try:
            # Find similar documents by content
            if self.db:
                # Search for similar content
                search_terms = metadata.get("title", metadata.get("subject", ""))
                if search_terms:
                    similar = self.db.search_content(search_terms, limit=5)
                    for doc in similar:
                        if doc.get("content_id") != content_id:
                            relationships.append(
                                {
                                    "to": doc.get("content_id"),
                                    "type": "similar_to",
                                    "confidence": 0.0,  # Would need embedding comparison
                                    "title": doc.get("title", "Unknown"),
                                }
                            )

            # Extract date for temporal relationships
            doc_date = metadata.get("date")
            if doc_date and self.db:
                # This would need more sophisticated date parsing
                # For now, just mark that temporal relationships could be built
                relationships.append(
                    {
                        "type": "temporal",
                        "date": doc_date,
                        "note": "Temporal relationships available",
                    }
                )

            # Check for references to other documents
            # Simple heuristic: look for document IDs or case numbers
            import re

            case_pattern = r"(?:Case No\.|CV-|Case:)\s*(\d{4}-\d+|\d+-CV-\d+)"
            matches = re.findall(case_pattern, text, re.IGNORECASE)
            for match in matches:
                relationships.append(
                    {"type": "references", "case_number": match, "confidence": 0.9}
                )

            return {
                "relationships": relationships,
                "total_relationships": len(relationships),
                "built_at": datetime.utcnow().isoformat() + "Z",
            }
        except Exception as e:
            logger.error(f"Failed to build relationships: {e}")
            return {"relationships": [], "total_relationships": 0}

    def extract_all(self, text: str, metadata: dict[str, Any]) -> dict[str, Any]:
        """Extract all intelligence from document.

        Args:
            text: Document text
            metadata: Document metadata

        Returns:
            Dict with all intelligence data
        """
        intelligence = {"extracted_at": datetime.utcnow().isoformat() + "Z"}

        # Extract summary
        summary_data = self.extract_summary(text)
        if summary_data:
            intelligence["summary"] = summary_data

        # Extract entities
        entity_data = self.extract_entities(text)
        if entity_data:
            intelligence["entities"] = entity_data

        # Build relationships
        content_id = metadata.get("content_id", metadata.get("pipeline_id", ""))
        if content_id:
            relationship_data = self.build_relationships(content_id, text, metadata)
            if relationship_data:
                intelligence["relationships"] = relationship_data

        # Store in database if available
        if self.db and content_id:
            try:
                # Store summary
                if "summary" in intelligence:
                    self.db.add_document_summary(
                        document_id=content_id,
                        summary_type="combined",
                        summary_text=intelligence["summary"].get("summary_text", ""),
                        tf_idf_keywords=intelligence["summary"].get("tf_idf_keywords", {}),
                        textrank_sentences=intelligence["summary"].get("textrank_sentences", []),
                    )

                # Store intelligence data
                self.db.add_document_intelligence(
                    document_id=content_id,
                    intelligence_type="comprehensive",
                    intelligence_data=intelligence,
                    confidence_score=0.85,
                )

                logger.info(f"Stored intelligence for document {content_id}")
            except Exception as e:
                logger.error(f"Failed to store intelligence: {e}")

        return intelligence
