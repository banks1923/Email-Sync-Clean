"""Semantic Pipeline - Orchestrates enrichment steps during email ingestion.

Simple, direct implementation following CLAUDE.md principles.
Each step is idempotent and can be safely rerun.
"""

import hashlib
import json
import time
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from loguru import logger

from config.settings import semantic_settings
from entity.main import EntityService
from shared.db.simple_db import SimpleDB
from utilities.embeddings import get_embedding_service
from utilities.timeline import TimelineService
from utilities.vector_store import get_vector_store
from utilities.chunk_pipeline import ChunkPipeline


class SemanticPipeline:
    """
    Orchestrates semantic enrichment during ingestion.
    """

    def __init__(
        self,
        db: Optional[SimpleDB] = None,
        embedding_service=None,
        vector_store=None,
        entity_service=None,
        timeline_service=None,
        chunk_pipeline=None,
    ):
        """
        Initialize with services (allows dependency injection for testing).
        """
        self.db = db or SimpleDB()
        self.embedding_service = embedding_service
        self.vector_store = vector_store
        self.entity_service = entity_service or EntityService()
        self.timeline_service = timeline_service or TimelineService()
        self.chunk_pipeline = chunk_pipeline or ChunkPipeline(db=self.db)
        self.timeout_s = semantic_settings.semantics_timeout_s

    def run_for_messages(
        self, message_ids: List[str], steps: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """Run semantic enrichment for a batch of message IDs.

        Args:
            message_ids: Email message IDs to process
            steps: Specific steps to run (default: from settings)

        Returns:
            Dict with results from each step
        """
        steps = steps or semantic_settings.semantics_steps
        results = {"total_messages": len(message_ids), "steps_run": steps, "step_results": {}}

        logger.info(f"Starting semantic pipeline for {len(message_ids)} messages")
        logger.info(f"Steps to run: {', '.join(steps)}")

        # Get email data with EIDs for processing
        emails_data = self._get_email_data(message_ids)

        if not emails_data:
            logger.warning("No emails found for provided message IDs")
            return results

        # Run each step with timeout
        for step in steps:
            if step == "summary":
                # Already handled in gmail ingestion, skip
                logger.debug("Summaries already processed during ingestion")
                continue

            logger.info(f"Running step: {step}")
            start_time = time.time()

            try:
                if step == "entities":
                    step_result = self._run_entity_extraction(emails_data)
                elif step == "embeddings":
                    step_result = self._run_embeddings(emails_data)
                elif step == "timeline":
                    step_result = self._run_timeline(emails_data)
                elif step == "chunks":
                    step_result = self._run_chunking(emails_data)
                else:
                    logger.warning(f"Unknown step: {step}")
                    continue

                elapsed = time.time() - start_time
                step_result["elapsed_s"] = elapsed
                results["step_results"][step] = step_result

                # Log progress
                logger.info(
                    f"{step}: processed={step_result.get('processed', 0)}, "
                    f"skipped={step_result.get('skipped', 0)}, "
                    f"errors={step_result.get('errors', 0)}, "
                    f"time={elapsed:.2f}s"
                )

                # Check timeout
                if elapsed > self.timeout_s:
                    logger.warning(
                        f"Step {step} exceeded timeout ({elapsed:.2f}s > {self.timeout_s}s)"
                    )

            except Exception as e:
                logger.error(f"Error in step {step}: {e}")
                results["step_results"][step] = {
                    "error": str(e),
                    "processed": 0,
                    "skipped": 0,
                    "errors": len(emails_data),
                }

        return results

    def _get_email_data(self, message_ids: List[str]) -> List[Dict[str, Any]]:
        """
        Get email data from v2.0 schema (individual_messages +
        content_unified).
        """
        if not message_ids:
            return []

        # Use v2.0 schema: individual_messages and content_unified
        placeholders = ",".join(["?" for _ in message_ids])
        query = f"""
            SELECT 
                im.message_hash as id,
                im.message_hash as message_id,
                im.subject,
                im.sender_email as sender,
                im.date_sent as datetime_utc,
                im.content,
                im.thread_id,
                c.id as content_id
            FROM individual_messages im
            LEFT JOIN content_unified c ON c.source_id = im.message_hash AND c.source_type = 'email_message'
            WHERE im.message_hash IN ({placeholders})
        """

        cursor = self.db.execute(query, message_ids)
        emails = []

        for row in cursor.fetchall():
            email = dict(row)
            # Add None for missing fields for backward compatibility
            if "eid" not in email:
                email["eid"] = None
            emails.append(email)

        return emails

    def _run_entity_extraction(self, emails_data: List[Dict]) -> Dict[str, Any]:
        """
        Extract entities from emails.
        """
        result = {"processed": 0, "skipped": 0, "errors": 0, "entities_found": 0}

        # Check cache cutoff
        cache_cutoff = datetime.now() - timedelta(days=semantic_settings.entity_cache_days)

        for email in emails_data:
            try:
                # Check if already processed recently
                cursor = self.db.execute(
                    """
                    SELECT COUNT(*) as count, MAX(created_at) as last_processed
                    FROM entity_content_mapping
                    WHERE content_id = ? OR message_id = ?
                """,
                    (email.get("content_id"), email["message_id"]),
                )

                row = cursor.fetchone()
                if row and row["count"] > 0:
                    last_processed = row.get("last_processed")
                    if last_processed:
                        # Parse datetime and check cache
                        try:
                            last_dt = datetime.fromisoformat(last_processed.replace("Z", "+00:00"))
                            if last_dt > cache_cutoff:
                                result["skipped"] += 1
                                continue
                        except:
                            pass  # Process if can't parse date

                # Extract entities
                extraction = self.entity_service.extract_email_entities(
                    message_id=email["message_id"],
                    content=email.get("content", ""),
                    email_data={
                        "subject": email.get("subject"),
                        "sender": email.get("sender"),
                        "eid": email.get("eid"),  # Include EID reference
                        "content_id": email.get("content_id"),
                    },
                )

                if extraction.get("success"):
                    result["processed"] += 1
                    result["entities_found"] += len(extraction.get("entities", []))
                else:
                    result["errors"] += 1

            except Exception as e:
                logger.error(f"Entity extraction failed for {email['message_id']}: {e}")
                result["errors"] += 1

        return result

    def _run_embeddings(self, emails_data: List[Dict]) -> Dict[str, Any]:
        """
        Generate and store embeddings for emails.
        """
        result = {"processed": 0, "skipped": 0, "errors": 0, "vectors_stored": 0}

        # Initialize services if not provided
        if not self.embedding_service:
            self.embedding_service = get_embedding_service()
        if not self.vector_store:
            self.vector_store = get_vector_store("emails")

        # Check which emails already have vectors
        existing_ids = set()
        for email in emails_data:
            if email.get("content_id"):
                # Check if vector exists
                try:
                    # Use content_id as vector ID
                    vector_id = str(email["content_id"])
                    # This is a simplified check - actual implementation may vary
                    cursor = self.db.execute(
                        """
                        SELECT id FROM content_unified 
                        WHERE id = ? AND embedding_generated = 1
                    """,
                        (vector_id,),
                    )

                    if cursor.fetchone():
                        existing_ids.add(email["message_id"])
                        result["skipped"] += 1
                except:
                    pass  # Process if check fails

        # Batch process emails without vectors
        to_process = [e for e in emails_data if e["message_id"] not in existing_ids]

        if not to_process:
            return result

        # Process in batches
        batch_size = min(50, semantic_settings.semantics_max_batch)

        for i in range(0, len(to_process), batch_size):
            batch = to_process[i : i + batch_size]

            try:
                # Extract texts
                texts = []
                metadata_list = []

                for email in batch:
                    # Combine subject and content for embedding
                    text = f"{email.get('subject', '')} {email.get('content', '')}"
                    texts.append(text)

                    # Prepare metadata with EID and content_id
                    metadata = {
                        "message_id": email["message_id"],
                        "content_id": email.get("content_id"),
                        "eid": email.get("eid"),
                        "thread_id": email.get("thread_id"),
                        "sender": email.get("sender"),
                        "datetime_utc": email.get("datetime_utc"),
                        "content_type": "email",
                    }
                    metadata_list.append(metadata)

                # Generate embeddings
                embeddings = self.embedding_service.batch_encode(texts, batch_size=batch_size)

                # Prepare points for vector store
                points = []
                for j, embedding in enumerate(embeddings):
                    email = batch[j]

                    # Use UUID-compatible vector ID - convert integer content_id to UUID format
                    import uuid

                    if email.get("content_id"):
                        # Create UUID from content_id for Qdrant compatibility
                        vector_id = str(
                            uuid.uuid5(uuid.NAMESPACE_URL, f"content_{email['content_id']}")
                        )
                    else:
                        # Use message_id directly if it's already a hash
                        vector_id = str(email["message_id"])

                    point = {"id": vector_id, "vector": embedding, "metadata": metadata_list[j]}
                    points.append(point)

                # Batch upsert to vector store
                self.vector_store.batch_upsert("emails", points)

                # Mark as vectorized in DB
                for email in batch:
                    if email.get("content_id"):
                        # Update content to mark as vectorized
                        self.db.execute(
                            """
                            UPDATE content_unified SET embedding_generated = 1, embedding_generated_at = CURRENT_TIMESTAMP WHERE id = ?
                        """,
                            (email["content_id"],),
                        )

                result["processed"] += len(batch)
                result["vectors_stored"] += len(points)

            except Exception as e:
                logger.error(f"Embedding batch failed: {e}")
                result["errors"] += len(batch)

        return result

    def _run_timeline(self, emails_data: List[Dict]) -> Dict[str, Any]:
        """
        Extract and store timeline events from emails.
        """
        result = {"processed": 0, "skipped": 0, "errors": 0, "events_created": 0}

        for email in emails_data:
            try:
                # Check if already in timeline
                cursor = self.db.execute(
                    """
                    SELECT COUNT(*) as count FROM timeline_events
                    WHERE content_id = ? OR (metadata IS NOT NULL AND metadata LIKE ?)
                """,
                    (email.get("content_id"), f'%{email["message_id"]}%'),
                )

                if cursor.fetchone()["count"] > 0:
                    result["skipped"] += 1
                    continue

                # Extract temporal events from content
                events = self._extract_temporal_events(email)

                for event in events:
                    # Generate event hash for deduplication
                    event_str = f"{email['message_id']}:{event['date']}:{event['description']}"
                    event_hash = hashlib.md5(event_str.encode()).hexdigest()

                    # Store event with EID reference
                    try:
                        self.db.execute(
                            """
                            INSERT INTO timeline_events 
                            (content_id, event_date, event_type, description, metadata)
                            VALUES (?, ?, ?, ?, ?)
                        """,
                            (
                                email.get("content_id"),
                                event["date"],
                                event.get("type", "email"),
                                event["description"],
                                json.dumps(
                                    {
                                        "message_id": email["message_id"],
                                        "eid_ref": email.get("eid"),
                                        "event_hash": event_hash,
                                        "thread_id": email.get("thread_id"),
                                    }
                                ),
                            ),
                        )
                        result["events_created"] += 1
                    except:
                        pass  # Skip duplicates

                result["processed"] += 1

            except Exception as e:
                logger.error(f"Timeline extraction failed for {email['message_id']}: {e}")
                result["errors"] += 1

        return result

    def _run_chunking(self, emails_data: List[Dict]) -> Dict[str, Any]:
        """
        Process emails through chunking pipeline for v2 semantic search.
        """
        result = {"processed": 0, "skipped": 0, "errors": 0, "chunks_created": 0, "chunks_dropped": 0}
        
        # Get source IDs for the emails
        source_ids = []
        for email in emails_data:
            if email.get("content_id"):
                # Get source_id from content_unified
                cursor = self.db.execute(
                    "SELECT source_id FROM content_unified WHERE id = ?",
                    (email["content_id"],)
                )
                row = cursor.fetchone()
                if row and row["source_id"]:
                    source_ids.append(row["source_id"])
        
        if not source_ids:
            logger.warning("No valid source_ids found for chunking")
            return result
        
        # Process through chunk pipeline
        try:
            # Process emails with specific source_ids
            chunk_result = self.chunk_pipeline.process_documents(
                limit=len(source_ids),
                source_types=["email_message"],
                dry_run=False
            )
            
            result["processed"] = chunk_result.get("documents_processed", 0)
            result["chunks_created"] = chunk_result.get("chunks_created", 0)
            result["chunks_dropped"] = chunk_result.get("chunks_dropped_quality", 0)
            result["skipped"] = chunk_result.get("chunks_already_exist", 0)
            
            logger.info(
                f"Chunking complete: {result['chunks_created']} chunks created, "
                f"{result['chunks_dropped']} dropped (low quality)"
            )
            
        except Exception as e:
            logger.error(f"Error in chunking pipeline: {e}")
            result["errors"] = len(emails_data)
        
        return result

    def _extract_temporal_events(self, email: Dict) -> List[Dict]:
        """
        Extract temporal events from email content.
        """
        events = []

        # Basic event: email sent/received
        if email.get("datetime_utc"):
            events.append(
                {
                    "date": email["datetime_utc"],
                    "type": "email",
                    "description": f"Email from {email.get('sender', 'unknown')}: {email.get('subject', 'No subject')}",
                }
            )

        # Extract dates mentioned in content
        content = email.get("content", "")
        if content:
            # Simple date pattern matching (could be enhanced with NLP)
            import re

            # Look for common date patterns
            date_patterns = [
                r"\b(\d{1,2}/\d{1,2}/\d{2,4})\b",  # MM/DD/YYYY
                r"\b(\d{4}-\d{2}-\d{2})\b",  # YYYY-MM-DD
                r"\b(January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2},?\s+\d{4}\b",
            ]

            for pattern in date_patterns:
                matches = re.findall(pattern, content, re.IGNORECASE)
                for match in matches[:3]:  # Limit to 3 dates per email
                    # Extract context around date
                    context_match = re.search(
                        rf".{{0,50}}{re.escape(match)}.{{0,50}}", content, re.IGNORECASE | re.DOTALL
                    )

                    if context_match:
                        context = context_match.group(0).strip()
                        # Clean up context
                        context = re.sub(r"\s+", " ", context)

                        events.append(
                            {"date": match, "type": "mentioned_date", "description": context[:200]}
                        )

        return events


# Simple factory function
def get_semantic_pipeline(**kwargs) -> SemanticPipeline:
    """
    Get semantic pipeline instance.
    """
    return SemanticPipeline(**kwargs)
