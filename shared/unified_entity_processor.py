#!/usr/bin/env python3
"""Unified Entity Processor.

Integrates entity extraction into the unified content pipeline.
Processes all content in content_unified table and extracts entities with proper attribution.

Key Features:
- Processes all content types (emails, PDFs, documents)
- Creates entity_content_mapping for proper attribution
- Updates consolidated entities with source links
- Batch processing for performance
- Progress tracking and error handling

Status: NEW - Addresses missing entity extraction in unified pipeline
"""

import time
import uuid
from datetime import datetime
from typing import Any

from loguru import logger

from .simple_db import SimpleDB


class UnifiedEntityProcessor:
    """
    Extract and map entities from unified content with proper attribution.
    """

    def __init__(self):
        self.db = SimpleDB()
        self._entity_service = None  # Lazy load to avoid circular imports

    def _get_entity_service(self):
        """
        Lazy load entity extractor to avoid import cycles.
        """
        if self._entity_service is None:
            try:
                from entity.extractors.extractor_factory import ExtractorFactory

                self._entity_service = ExtractorFactory.get_best_available_extractor()
                logger.info("✅ Entity extractor initialized")
            except ImportError as e:
                logger.error(f"❌ Failed to import entity extractor: {e}")
                return None
        return self._entity_service

    def process_content_entities(
        self, content_ids: list[str] = None, batch_size: int = 50, max_content: int = None
    ) -> dict[str, Any]:
        """Process entities from content_unified table with proper attribution.

        Args:
            content_ids: Specific content IDs to process (None = all)
            batch_size: Number of content items to process per batch
            max_content: Maximum content items to process (None = all)

        Returns:
            Processing statistics and results
        """
        entity_extractor = self._get_entity_service()
        if not entity_extractor:
            return {"error": "Entity extractor unavailable"}

        logger.info("🔬 Starting unified entity processing...")
        start_time = time.time()

        # Build query based on parameters - filter out OCR garbage content
        where_clause = """WHERE body IS NOT NULL 
            AND LENGTH(TRIM(body)) > 20
            AND (LENGTH(body) - LENGTH(REPLACE(REPLACE(REPLACE(body, '&', ''), '=', ''), '%', ''))) * 100.0 / LENGTH(body) < 3.0"""
        params = ()

        if content_ids:
            placeholders = ",".join("?" * len(content_ids))
            where_clause += f" AND id IN ({placeholders})"
            params = tuple(content_ids)

        limit_clause = f"LIMIT {max_content}" if max_content else ""

        query = f"""
            SELECT id, source_type, source_id, title, body, created_at
            FROM content_unified 
            {where_clause}
            ORDER BY created_at DESC
            {limit_clause}
        """

        content_records = self.db.fetch(query, params)
        logger.info(f"Found {len(content_records)} content records to process")

        if not content_records:
            return {
                "success": True,
                "processed": 0,
                "entities_extracted": 0,
                "entities_mapped": 0,
                "message": "No content found to process",
            }

        stats = {
            "processed": 0,
            "entities_extracted": 0,
            "entities_mapped": 0,
            "errors": 0,
            "skipped": 0,
        }

        # Process in batches
        for i in range(0, len(content_records), batch_size):
            batch = content_records[i : i + batch_size]
            batch_stats = self._process_batch(entity_extractor, batch)

            # Update stats
            for key in stats:
                stats[key] += batch_stats.get(key, 0)

            # Progress logging
            processed_so_far = min(i + batch_size, len(content_records))
            logger.info(
                f"Processed {processed_so_far}/{len(content_records)} content items "
                f"({stats['entities_extracted']} entities extracted)"
            )

            # Brief pause between batches to prevent overwhelming
            if i + batch_size < len(content_records):
                time.sleep(0.1)

        elapsed_time = time.time() - start_time

        result = {
            "success": True,
            "processed": stats["processed"],
            "entities_extracted": stats["entities_extracted"],
            "entities_mapped": stats["entities_mapped"],
            "errors": stats["errors"],
            "skipped": stats["skipped"],
            "elapsed_seconds": elapsed_time,
            "content_types_processed": self._get_content_type_breakdown(content_records),
        }

        logger.info(
            f"✅ Entity processing complete: {stats['processed']} content items, "
            f"{stats['entities_extracted']} entities in {elapsed_time:.1f}s"
        )

        return result

    def _process_batch(self, entity_extractor, batch: list[dict]) -> dict[str, int]:
        """
        Process a batch of content records for entity extraction.
        """
        batch_stats = {
            "processed": 0,
            "entities_extracted": 0,
            "entities_mapped": 0,
            "errors": 0,
            "skipped": 0,
        }

        for record in batch:
            try:
                content_id = record["id"]
                source_type = record["source_type"]
                source_id = record["source_id"]
                title = record["title"] or ""
                body = record["body"]

                # Check if already processed
                existing_mappings = self.db.fetch(
                    "SELECT COUNT(*) as count FROM entity_content_mapping WHERE content_id = ?",
                    (content_id,),
                )

                if existing_mappings[0]["count"] > 0:
                    batch_stats["skipped"] += 1
                    continue

                # Clean HTML artifacts from email content before extraction
                cleaned_text = self._clean_html_artifacts(f"{title}\n\n{body}".strip())

                # Extract entities
                extraction_result = entity_extractor.extract_entities(cleaned_text, content_id)
                raw_entities = (
                    extraction_result.get("entities", [])
                    if extraction_result.get("success")
                    else []
                )

                # Filter out low-quality entities
                entities = self._filter_quality_entities(raw_entities)

                if entities and len(entities) > 0:
                    # Store entity mappings
                    mapped_count = self._store_entity_mappings(
                        content_id, source_id, source_type, entities
                    )

                    batch_stats["entities_extracted"] += len(entities)
                    batch_stats["entities_mapped"] += mapped_count

                batch_stats["processed"] += 1

            except Exception as e:
                logger.error(f"Error processing content {record.get('id', 'unknown')}: {e}")
                batch_stats["errors"] += 1
                continue

        return batch_stats

    def _clean_html_artifacts(self, text: str) -> str:
        """
        Clean HTML artifacts and entities from text before entity extraction.
        """
        import re

        # Remove HTML entities like &nbsp;, &amp;, etc.
        text = re.sub(r"&[a-zA-Z0-9#]+;", " ", text)

        # Remove HTML tags
        text = re.sub(r"<[^>]+>", " ", text)

        # Clean up multiple whitespaces
        text = re.sub(r"\s+", " ", text)

        return text.strip()

    def _filter_quality_entities(self, entities: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """
        Enhanced quality filtering to remove gibberish entities.
        """
        import re

        filtered = []

        # Day names that get misclassified as PERSON
        day_names = {
            "mon",
            "tue",
            "wed",
            "thu",
            "fri",
            "sat",
            "sun",
            "monday",
            "tuesday",
            "wednesday",
            "thursday",
            "friday",
            "saturday",
            "sunday",
        }

        # Common OCR garbage patterns
        ocr_patterns = [
            r"^[a-z]{1,3}$",  # Single/double/triple lowercase letters like "ql", "hie"
            r"^[A-Z]{1,2}[a-z]$",  # Patterns like "Bak", "Qr"
            r"^\d{1,3}$",  # Single digits or short numbers alone
        ]

        for entity in entities:
            text = entity.get("text", "").strip()
            entity_type = entity.get("label", "")
            text_lower = text.lower()

            # Skip if empty or too short
            if not text or len(text) < 2:
                continue

            # Filter day names misclassified as PERSON
            if entity_type == "PERSON" and text_lower in day_names:
                continue

            # Filter HTML artifacts and remnants
            if (
                ("&" in text and len(text) < 50)
                or text.startswith("timing")
                or text.endswith("net")
            ):
                continue

            # Filter OCR garbage with excessive symbols/mixed characters
            if re.search(r"[&=%£€<>©#@]{2,}", text) or re.search(
                r"[A-Z]{3,}[a-z]{3,}[A-Z]{3,}", text
            ):
                continue

            # Filter money entities that are clearly OCR garbage
            if entity_type == "MONEY" and (len(text) > 30 or re.search(r"[&<>=:]{2,}", text)):
                continue

            # Filter date/phone fragments misclassified as STATUTE
            if entity_type == "STATUTE":
                # Skip things like "at 518", "from 518", "Feb 27", standalone numbers
                if re.match(r"^(at\s+\d+|from\s+\d+|[A-Za-z]{3}\s+\d+|\d+)$", text):
                    continue

            # Filter OCR garbage patterns
            skip_ocr = False
            for pattern in ocr_patterns:
                if re.match(pattern, text):
                    skip_ocr = True
                    break
            if skip_ocr:
                continue

            # Skip single digit numbers (usually OCR noise)
            if entity_type == "CARDINAL" and text.isdigit() and len(text) == 1:
                continue

            # Skip entities with too many symbols (OCR garbage)
            symbol_count = len([c for c in text if c in "&=%£€<>©#@"])
            if len(text) > 0 and symbol_count / len(text) > 0.3:
                continue

            # Skip very long entities (usually OCR errors)
            if len(text) > 100:
                continue

            # Skip entities that are mostly punctuation
            punct_count = len([c for c in text if c in ".,;:!?"])
            if len(text) > 0 and punct_count / len(text) > 0.5:
                continue

            # Skip meaningless single characters or symbols
            if len(text) == 1 and not text.isalnum():
                continue

            filtered.append(entity)

        return filtered

    def _store_entity_mappings(
        self, content_id: str, source_id: str, source_type: str, entities: list[dict[str, Any]]
    ) -> int:
        """
        Store entity-to-content mappings in database.
        """
        if not entities:
            return 0

        mappings = []
        for entity in entities:
            # Generate entity_id if not present
            entity_id = entity.get("entity_id") or str(uuid.uuid4())

            mapping = {
                "entity_id": entity_id,
                "entity_text": entity.get("text", ""),  # Changed from entity_value to entity_text
                "entity_type": entity.get("label", ""),
                "entity_label": entity.get("label", ""),  # Added entity_label
                "content_id": content_id,
                "start_char": entity.get("start", 0),  # Added start_char
                "end_char": entity.get("end", 0),  # Added end_char
                "confidence": entity.get("confidence", 0.8),
                "normalized_form": entity.get("text", "").lower(),  # Added normalized_form
                "extractor_type": entity.get("extractor_type", "spacy"),  # Added extractor_type
            }
            mappings.append(mapping)

        if mappings:
            # Batch insert mappings (aligned with actual schema)
            columns = [
                "content_id",
                "entity_text",
                "entity_type",
                "entity_label",
                "start_char",
                "end_char",
                "confidence",
                "normalized_form",
                "entity_id",
                "extractor_type",
            ]
            values = [[m[col] for col in columns] for m in mappings]

            try:
                self.db.batch_insert("entity_content_mapping", columns, values)
                return len(mappings)
            except Exception as e:
                logger.error(f"Failed to store entity mappings: {e}")
                return 0

        return 0

    def _build_entity_metadata(self, entity: dict[str, Any], source_type: str) -> str:
        """
        Build metadata JSON for entity mapping.
        """
        import json

        metadata = {
            "start_char": entity.get("start", 0),
            "end_char": entity.get("end", 0),
            "source_type": source_type,
            "extraction_method": entity.get("extractor", "spacy"),
            "processed_at": datetime.now().isoformat(),
        }
        return json.dumps(metadata)

    def _get_content_type_breakdown(self, content_records: list[dict]) -> dict[str, int]:
        """
        Get breakdown of processed content by type.
        """
        breakdown = {}
        for record in content_records:
            source_type = record["source_type"]
            breakdown[source_type] = breakdown.get(source_type, 0) + 1
        return breakdown

    def get_processing_status(self) -> dict[str, Any]:
        """
        Get current entity processing status for unified content.
        """

        # Content with and without entity mappings
        content_stats = self.db.fetch(
            """
            SELECT 
                cu.source_type,
                COUNT(cu.id) as total_content,
                COUNT(DISTINCT ecm.content_id) as content_with_entities,
                COUNT(ecm.id) as total_entity_mappings
            FROM content_unified cu
            LEFT JOIN entity_content_mapping ecm ON cu.id = ecm.content_id
            WHERE cu.body IS NOT NULL AND LENGTH(TRIM(cu.body)) > 20
            GROUP BY cu.source_type
            ORDER BY total_content DESC
        """
        )

        # Entity type distribution
        entity_types = self.db.fetch(
            """
            SELECT entity_type, COUNT(*) as count
            FROM entity_content_mapping
            GROUP BY entity_type
            ORDER BY count DESC
        """
        )

        # Recent processing activity
        recent_mappings_result = self.db.fetch(
            """
            SELECT COUNT(*) as count
            FROM entity_content_mapping
            WHERE processed_time > datetime('now', '-24 hours')
        """
        )
        recent_mappings = recent_mappings_result[0]["count"] if recent_mappings_result else 0

        return {
            "content_statistics": [dict(row) for row in content_stats],
            "entity_type_distribution": {row["entity_type"]: row["count"] for row in entity_types},
            "recent_mappings_24h": recent_mappings,
            "timestamp": datetime.now().isoformat(),
        }

    def process_missing_entities_only(self, max_content: int = 100) -> dict[str, Any]:
        """
        Process only content that doesn't have entity mappings yet.
        """

        # Find content without entity mappings
        content_without_entities = self.db.fetch(
            """
            SELECT cu.id
            FROM content_unified cu
            LEFT JOIN entity_content_mapping ecm ON cu.id = ecm.content_id
            WHERE ecm.content_id IS NULL
            AND cu.body IS NOT NULL 
            AND LENGTH(TRIM(cu.body)) > 20
            ORDER BY cu.created_at DESC
            LIMIT ?
        """,
            (max_content,),
        )

        content_ids = [record["id"] for record in content_without_entities]

        if not content_ids:
            return {
                "success": True,
                "message": "All content already has entity mappings",
                "processed": 0,
            }

        logger.info(f"Processing {len(content_ids)} content items without entity mappings")

        return self.process_content_entities(content_ids=content_ids, batch_size=25)
