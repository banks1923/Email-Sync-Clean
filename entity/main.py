"""Main EntityService class for named entity recognition.

Follows service independence patterns from existing codebase.
"""

import os
import sys
from typing import Any

from loguru import logger

# Add project root to path for shared imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from .config import EntityConfig
from .database import EntityDatabase
from .extractors.extractor_factory import ExtractorFactory
from .extractors.relationship_extractor import RelationshipExtractor
from .processors.entity_normalizer import EntityNormalizer


class EntityService:
    """Named Entity Recognition service for email content.

    Provides entity extraction capabilities using spaCy NLP models.
    Follows service independence with database-only communication.
    """

    def __init__(self, db_path: str = "emails.db") -> None:
        """
        Initialize EntityService with configuration validation.
        """
        # Logger is now imported globally from loguru
        self.config = EntityConfig()
        self.db = EntityDatabase(db_path)

        # Initialize extractor via factory
        try:
            self.extractor = ExtractorFactory.get_best_available_extractor()
        except Exception as e:
            self.extractor = None
            logger.error(f"Failed to initialize extractor: {e}")

        # Initialize relationship extractor
        try:
            self.relationship_extractor = RelationshipExtractor()
        except Exception as e:
            self.relationship_extractor = None
            logger.error(f"Failed to initialize relationship extractor: {e}")

        # Initialize entity normalizer
        try:
            self.normalizer = EntityNormalizer()
        except Exception as e:
            self.normalizer = None
            logger.error(f"Failed to initialize entity normalizer: {e}")

        # Service validation result
        self.validation_result = self._validate_service()

    def _validate_service(self) -> dict[str, Any]:
        """
        Validate service initialization.
        """
        if not self.config.is_valid():
            return self.config.validation_result

        if not self.db.init_result["success"]:
            return {
                "success": False,
                "error": f"Database initialization failed: {self.db.init_result['error']}",
            }

        if not self.extractor or not self.extractor.is_available():
            return {"success": False, "error": "No entity extractor available"}

        return {"success": True}

    def extract_email_entities(
        self, message_id: str, content: str, email_data: dict = None
    ) -> dict[str, Any]:
        """Extract named entities from email content with relationships and
        deduplication.

        Args:
            message_id: Email message identifier
            content: Email text content
            email_data: Optional email metadata for header analysis

        Returns:
            Dict with success status, entities, relationships, and consolidation info
        """
        if not self.validation_result["success"]:
            return {
                "success": False,
                "error": f"Service not initialized: {self.validation_result['error']}",
            }

        try:
            # Extract entities using the configured extractor
            extraction_result = self.extractor.extract_entities(content, message_id)

            if not extraction_result["success"]:
                return extraction_result

            raw_entities = extraction_result.get("entities", [])

            # Add extractor type to entities
            for entity in raw_entities:
                if "extractor_type" not in entity:
                    entity["extractor_type"] = getattr(self.extractor, "name", "unknown")

            # Extract relationships if relationship extractor is available
            relationships = []
            if self.relationship_extractor and len(raw_entities) > 1:
                rel_result = self.relationship_extractor.extract_relationships(
                    raw_entities, content, message_id
                )
                if rel_result["success"]:
                    relationships.extend(rel_result.get("relationships", []))

                # Extract email header relationships if email data provided
                if email_data:
                    header_rels = self.relationship_extractor.extract_email_header_relationships(
                        email_data, raw_entities
                    )
                    relationships.extend(header_rels)

            # Deduplicate and normalize entities if normalizer is available
            consolidated_info = None
            if self.normalizer:
                dedup_result = self.normalizer.deduplicate_entities(raw_entities)
                if dedup_result["success"]:
                    consolidated_info = dedup_result

                    # Store consolidated entities
                    for entity_id, cons_entity in dedup_result["consolidated_entities"].items():
                        self.db.store_consolidated_entity(
                            entity_id,
                            cons_entity["primary_name"],
                            cons_entity["entity_type"],
                            cons_entity.get("aliases"),
                            cons_entity.get("additional_info"),
                        )

            # Store raw entities in database
            if raw_entities:
                store_result = self.db.store_entities(raw_entities)
                if not store_result["success"]:
                    logger.warning(f"Failed to store entities: {store_result.get('error')}")

            # Store relationships
            relationship_count = 0
            if relationships:
                for rel in relationships:
                    rel_result = self.db.store_entity_relationship(
                        rel["source_entity_id"],
                        rel["target_entity_id"],
                        rel["relationship_type"],
                        rel.get("confidence", 0.5),
                        rel.get("source_message_id"),
                        rel.get("context_snippet"),
                    )
                    if rel_result["success"]:
                        relationship_count += 1

            return {
                "success": True,
                "message_id": message_id,
                "entities": raw_entities,
                "entity_count": len(raw_entities),
                "relationships": relationships,
                "relationship_count": relationship_count,
                "consolidated_info": consolidated_info,
                "extractor_used": getattr(self.extractor, "name", "unknown"),
            }

        except Exception as e:
            error_msg = f"Entity extraction failed for {message_id}: {str(e)}"
            logger.error(error_msg)
            return {"success": False, "error": error_msg}

    def process_emails(self, limit: int | None = None) -> dict[str, Any]:
        """Process multiple emails for entity extraction.

        Args:
            limit: Maximum number of emails to process

        Returns:
            Dict with processing results
        """
        if not self.validation_result["success"]:
            return {
                "success": False,
                "error": f"Service not initialized: {self.validation_result['error']}",
            }

        try:
            # Get unprocessed emails from database
            # This will be implemented as part of batch processing (Task 1.5)
            processed_count = 0

            return {"success": True, "processed": processed_count, "limit_requested": limit}

        except Exception as e:
            error_msg = f"Batch processing failed: {str(e)}"
            logger.error(error_msg)
            return {"success": False, "error": error_msg}

    def get_entities_for_email(self, message_id: str) -> dict[str, Any]:
        """
        Retrieve all entities for a specific email.
        """
        if not self.validation_result["success"]:
            return {
                "success": False,
                "error": f"Service not initialized: {self.validation_result['error']}",
            }

        return self.db.get_entities_for_email(message_id)

    def get_entity_stats(self) -> dict[str, Any]:
        """
        Get comprehensive entity extraction statistics.
        """
        if not self.validation_result["success"]:
            return {
                "success": False,
                "error": f"Service not initialized: {self.validation_result['error']}",
            }

        try:
            # Get enhanced statistics from database
            stats_result = self.db.get_entity_statistics()
            if stats_result["success"]:
                return stats_result
            else:
                # Fallback to basic stats
                total_entities = self.db.count_entities()
                entities_by_type = self.db.count_entities_by_type()

                return {
                    "success": True,
                    "total_entities": total_entities,
                    "entities_by_type": (
                        entities_by_type["data"] if entities_by_type["success"] else []
                    ),
                }

        except Exception as e:
            error_msg = f"Failed to get entity stats: {str(e)}"
            logger.error(error_msg)
            return {"success": False, "error": error_msg}

    def search_entities(
        self, entity_type: str = None, name_pattern: str = None, limit: int = 100
    ) -> dict[str, Any]:
        """
        Search consolidated entities.
        """
        if not self.validation_result["success"]:
            return {
                "success": False,
                "error": f"Service not initialized: {self.validation_result['error']}",
            }

        try:
            result = self.db.search_consolidated_entities(entity_type, name_pattern, limit)
            return result

        except Exception as e:
            error_msg = f"Failed to search entities: {str(e)}"
            logger.error(error_msg)
            return {"success": False, "error": error_msg}

    def get_entity_relationships(
        self, entity_id: str, relationship_type: str = None
    ) -> dict[str, Any]:
        """
        Get relationships for a specific entity.
        """
        if not self.validation_result["success"]:
            return {
                "success": False,
                "error": f"Service not initialized: {self.validation_result['error']}",
            }

        try:
            result = self.db.get_entity_relationships(entity_id, relationship_type)
            return result

        except Exception as e:
            error_msg = f"Failed to get entity relationships: {str(e)}"
            logger.error(error_msg)
            return {"success": False, "error": error_msg}

    def get_knowledge_graph(
        self, entity_ids: list[str] = None, max_depth: int = 2
    ) -> dict[str, Any]:
        """
        Get knowledge graph data for visualization.
        """
        if not self.validation_result["success"]:
            return {
                "success": False,
                "error": f"Service not initialized: {self.validation_result['error']}",
            }

        try:
            result = self.db.get_knowledge_graph(entity_ids, max_depth)
            return result

        except Exception as e:
            error_msg = f"Failed to get knowledge graph: {str(e)}"
            logger.error(error_msg)
            return {"success": False, "error": error_msg}

    def extract_entities_batch(self, email_data_list: list[dict]) -> dict[str, Any]:
        """
        Process multiple emails for entity extraction in batch.
        """
        if not self.validation_result["success"]:
            return {
                "success": False,
                "error": f"Service not initialized: {self.validation_result['error']}",
            }

        try:
            processed_count = 0
            total_entities = 0
            total_relationships = 0
            errors = []

            for email_data in email_data_list:
                message_id = email_data.get("message_id", "")
                content = email_data.get("content", "")

                if not message_id or not content:
                    errors.append("Missing message_id or content in email data")
                    continue

                result = self.extract_email_entities(message_id, content, email_data)

                if result["success"]:
                    processed_count += 1
                    total_entities += result.get("entity_count", 0)
                    total_relationships += result.get("relationship_count", 0)
                else:
                    errors.append(f"Failed to process {message_id}: {result.get('error')}")

            return {
                "success": True,
                "processed_count": processed_count,
                "total_entities": total_entities,
                "total_relationships": total_relationships,
                "errors": errors,
                "limit_requested": len(email_data_list),
            }

        except Exception as e:
            error_msg = f"Batch processing failed: {str(e)}"
            logger.error(error_msg)
            return {"success": False, "error": error_msg}


def get_entity_service(db_path: str = "emails.db") -> EntityService:
    """Factory function to create EntityService instance.
    
    Args:
        db_path: Path to the database file
        
    Returns:
        EntityService instance
    """
    return EntityService(db_path)
