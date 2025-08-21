"""Semantic Pipeline - Orchestrates enrichment steps during email ingestion.

Simple, direct implementation following CLAUDE.md principles.
Each step is idempotent and can be safely rerun.
"""

import time
import hashlib
import json
import uuid
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from loguru import logger

from config.settings import semantic_settings
from shared.simple_db import SimpleDB
from utilities.embeddings import get_embedding_service
from utilities.vector_store import get_vector_store
from entity.main import EntityService
from utilities.timeline import TimelineService


class SemanticPipeline:
    """Orchestrates semantic enrichment during ingestion."""
    
    def __init__(self, 
                 db: SimpleDB | None = None,
                 embedding_service=None,
                 vector_store=None,
                 entity_service=None,
                 timeline_service=None):
        """Initialize with services (allows dependency injection for testing)."""
        self.db = db or SimpleDB()
        self.embedding_service = embedding_service
        self.vector_store = vector_store
        self.entity_service = entity_service or EntityService()
        self.timeline_service = timeline_service or TimelineService()
        self.timeout_s = semantic_settings.semantics_timeout_s
        
    def run_for_messages(self, 
                        message_ids: list[str], 
                        steps: list[str] | None = None) -> dict[str, Any]:
        """Run semantic enrichment for a batch of message IDs.
        
        Args:
            message_ids: Email message IDs to process
            steps: Specific steps to run (default: from settings)
            
        Returns:
            Dict with results from each step
        """
        steps = steps or semantic_settings.semantics_steps
        results = {
            'total_messages': len(message_ids),
            'steps_run': steps,
            'step_results': {}
        }
        
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
                else:
                    logger.warning(f"Unknown step: {step}")
                    continue
                    
                elapsed = time.time() - start_time
                step_result['elapsed_s'] = elapsed
                results['step_results'][step] = step_result
                
                # Log progress
                logger.info(
                    f"{step}: processed={step_result.get('processed', 0)}, "
                    f"skipped={step_result.get('skipped', 0)}, "
                    f"errors={step_result.get('errors', 0)}, "
                    f"time={elapsed:.2f}s"
                )
                
                # Check timeout
                if elapsed > self.timeout_s:
                    logger.warning(f"Step {step} exceeded timeout ({elapsed:.2f}s > {self.timeout_s}s)")
                    
            except Exception as e:
                logger.error(f"Error in step {step}: {e}")
                results['step_results'][step] = {
                    'error': str(e),
                    'processed': 0,
                    'skipped': 0,
                    'errors': len(emails_data)
                }
                
        return results
    
    def _get_email_data(self, message_ids: list[str]) -> list[dict[str, Any]]:
        """Get email data including EIDs and content IDs."""
        if not message_ids:
            return []
            
        # Check what columns exist in emails table
        cursor = self.db.execute("PRAGMA table_info(emails)")
        columns = [col[1] for col in cursor.fetchall()]
        
        # Build query based on available columns
        select_fields = "e.id, e.message_id, e.subject, e.sender, e.datetime_utc, e.content"
        
        if 'eid' in columns:
            select_fields += ", e.eid"
        if 'thread_id' in columns:
            select_fields += ", e.thread_id"
            
        # Build query with placeholders
        placeholders = ','.join(['?' for _ in message_ids])
        query = f"""
            SELECT {select_fields},
                   c.id as content_id
            FROM emails e
            LEFT JOIN content c ON c.metadata LIKE '%' || e.message_id || '%'
            WHERE e.message_id IN ({placeholders})
        """
        
        cursor = self.db.execute(query, message_ids)
        emails = []
        
        for row in cursor.fetchall():
            email = dict(row)
            # Add None for missing fields
            if 'eid' not in email:
                email['eid'] = None
            if 'thread_id' not in email:
                email['thread_id'] = None
            emails.append(email)
        
        return emails
    
    def _run_entity_extraction(self, emails_data: list[dict]) -> dict[str, Any]:
        """Extract entities from emails."""
        result = {
            'processed': 0,
            'skipped': 0,
            'errors': 0,
            'entities_found': 0
        }
        
        # Check cache cutoff
        cache_cutoff = datetime.now() - timedelta(days=semantic_settings.entity_cache_days)
        
        for email in emails_data:
            try:
                # Check if already processed recently
                cursor = self.db.execute("""
                    SELECT COUNT(*) as count, MAX(created_at) as last_processed
                    FROM entity_content_mapping
                    WHERE content_id = ? OR message_id = ?
                """, (email.get('content_id'), email['message_id']))
                
                row = cursor.fetchone()
                if row and row['count'] > 0:
                    last_processed = row.get('last_processed')
                    if last_processed:
                        # Parse datetime and check cache
                        try:
                            last_dt = datetime.fromisoformat(last_processed.replace('Z', '+00:00'))
                            if last_dt > cache_cutoff:
                                result['skipped'] += 1
                                continue
                        except:
                            pass  # Process if can't parse date
                            
                # Extract entities
                extraction = self.entity_service.extract_email_entities(
                    message_id=email['message_id'],
                    content=email.get('content', ''),
                    email_data={
                        'subject': email.get('subject'),
                        'sender': email.get('sender'),
                        'eid': email.get('eid'),  # Include EID reference
                        'content_id': email.get('content_id')
                    }
                )
                
                if extraction.get('success'):
                    result['processed'] += 1
                    result['entities_found'] += len(extraction.get('entities', []))
                else:
                    result['errors'] += 1
                    
            except Exception as e:
                logger.error(f"Entity extraction failed for {email['message_id']}: {e}")
                result['errors'] += 1
                
        return result
    
    def _run_embeddings(self, emails_data: list[dict]) -> dict[str, Any]:
        """Generate and store embeddings for emails."""
        result = {
            'processed': 0,
            'skipped': 0,
            'errors': 0,
            'vectors_stored': 0
        }
        
        # Initialize services if not provided
        if not self.embedding_service:
            self.embedding_service = get_embedding_service()
        if not self.vector_store:
            self.vector_store = get_vector_store('emails')
            
        # Check which emails already have vectors
        existing_ids = set()
        for email in emails_data:
            if email.get('content_id'):
                # Check if vector exists
                try:
                    # Use content_id as vector ID
                    vector_id = str(email['content_id'])
                    # This is a simplified check - actual implementation may vary
                    cursor = self.db.execute("""
                        SELECT id FROM content 
                        WHERE id = ? AND metadata LIKE '%vectorized%'
                    """, (vector_id,))
                    
                    if cursor.fetchone():
                        existing_ids.add(email['message_id'])
                        result['skipped'] += 1
                except:
                    pass  # Process if check fails
                    
        # Batch process emails without vectors
        to_process = [e for e in emails_data if e['message_id'] not in existing_ids]
        
        if not to_process:
            return result
            
        # Process in batches
        batch_size = min(50, semantic_settings.semantics_max_batch)
        
        for i in range(0, len(to_process), batch_size):
            batch = to_process[i:i + batch_size]
            
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
                        'message_id': email['message_id'],
                        'content_id': email.get('content_id'),
                        'eid': email.get('eid'),
                        'thread_id': email.get('thread_id'),
                        'sender': email.get('sender'),
                        'datetime_utc': email.get('datetime_utc'),
                        'content_type': 'email'
                    }
                    metadata_list.append(metadata)
                    
                # Generate embeddings
                embeddings = self.embedding_service.batch_encode(texts, batch_size=batch_size)
                
                # Prepare points for vector store
                points = []
                for j, embedding in enumerate(embeddings):
                    email = batch[j]
                    
                    # Generate valid Qdrant point ID using UUID
                    vector_id = self._normalize_point_id(
                        content_id=email.get('content_id'), 
                        message_id=email['message_id']
                    )
                    
                    point = {
                        'id': vector_id,
                        'vector': embedding,
                        'metadata': metadata_list[j]
                    }
                    points.append(point)
                    
                # Batch upsert to vector store
                self.vector_store.batch_upsert('emails', points)
                
                # Mark as vectorized in DB
                for email in batch:
                    if email.get('content_id'):
                        # Update content metadata to mark as vectorized
                        cursor = self.db.execute("""
                            SELECT metadata FROM content WHERE id = ?
                        """, (email['content_id'],))
                        
                        row = cursor.fetchone()
                        if row:
                            import json
                            metadata = json.loads(row['metadata'] or '{}')
                            metadata['vectorized'] = True
                            metadata['vectorized_at'] = datetime.now().isoformat()
                            
                            self.db.execute("""
                                UPDATE content SET metadata = ? WHERE id = ?
                            """, (json.dumps(metadata), email['content_id']))
                            
                result['processed'] += len(batch)
                result['vectors_stored'] += len(points)
                
            except Exception as e:
                logger.error(f"Embedding batch failed: {e}")
                result['errors'] += len(batch)
                
        return result
    
    def _run_timeline(self, emails_data: list[dict]) -> dict[str, Any]:
        """Extract and store timeline events from emails."""
        result = {
            'processed': 0,
            'skipped': 0,
            'errors': 0,
            'events_created': 0
        }
        
        for email in emails_data:
            try:
                # Check if already in timeline
                cursor = self.db.execute("""
                    SELECT COUNT(*) as count FROM timeline_events
                    WHERE content_id = ? OR metadata LIKE ?
                """, (email.get('content_id'), f'%{email["message_id"]}%'))
                
                if cursor.fetchone()['count'] > 0:
                    result['skipped'] += 1
                    continue
                    
                # Extract temporal events from content
                events = self._extract_temporal_events(email)
                
                for event in events:
                    # Generate event hash for deduplication
                    event_str = f"{email['message_id']}:{event['date']}:{event['description']}"
                    event_hash = hashlib.md5(event_str.encode()).hexdigest()
                    
                    # Generate meaningful title
                    title = self._generate_event_title(event, email)
                    
                    # Store event with EID reference
                    try:
                        self.db.execute("""
                            INSERT INTO timeline_events 
                            (content_id, event_date, event_type, title, description, metadata)
                            VALUES (?, ?, ?, ?, ?, ?)
                        """, (
                            email.get('content_id'),
                            event['date'],
                            event.get('type', 'email'),
                            title,
                            event['description'],
                            json.dumps({
                                'message_id': email['message_id'],
                                'eid_ref': email.get('eid'),
                                'event_hash': event_hash,
                                'thread_id': email.get('thread_id')
                            })
                        ))
                        result['events_created'] += 1
                    except:
                        pass  # Skip duplicates
                        
                result['processed'] += 1
                
            except Exception as e:
                logger.error(f"Timeline extraction failed for {email['message_id']}: {e}")
                result['errors'] += 1
                
        return result
    
    def _normalize_point_id(self, content_id: str = None, message_id: str = None) -> str:
        """Generate a deterministic UUID for Qdrant point ID from email identifiers."""
        # Fixed namespace UUID for this project
        NAMESPACE = uuid.UUID("00000000-0000-0000-0000-00000000E1D0")
        
        # Use message_id if available, otherwise content_id
        key = (message_id or content_id or '').strip()
        if not key:
            # Fallback - generate random UUID (shouldn't happen in practice)
            return str(uuid.uuid4())
            
        # Generate deterministic UUIDv5 from the key
        return str(uuid.uuid5(NAMESPACE, key))
    
    def _generate_event_title(self, event: dict, email: dict) -> str:
        """Generate a meaningful title for timeline event."""
        action = event.get('type', 'Event')
        
        # Extract date part (first 10 chars for YYYY-MM-DD)
        date_str = event.get('date', '')[:10] if event.get('date') else ''
        
        # Get subject, clean and truncate
        subject = (email.get('subject') or '').strip()
        if len(subject) > 40:
            subject = subject[:37] + '...'
            
        # Build title
        if date_str and subject:
            return f"{action} – {date_str} – {subject}"
        elif date_str:
            return f"{action} – {date_str}"
        elif subject:
            return f"{action} – {subject}"
        else:
            return action
    
    def _extract_temporal_events(self, email: dict) -> list[dict]:
        """Extract temporal events from email content."""
        events = []
        
        # Basic event: email sent/received
        if email.get('datetime_utc'):
            events.append({
                'date': email['datetime_utc'],
                'type': 'email',
                'description': f"Email from {email.get('sender', 'unknown')}: {email.get('subject', 'No subject')}"
            })
            
        # Extract dates mentioned in content
        content = email.get('content', '')
        if content:
            # Simple date pattern matching (could be enhanced with NLP)
            import re
            
            # Look for common date patterns
            date_patterns = [
                r'\b(\d{1,2}/\d{1,2}/\d{2,4})\b',  # MM/DD/YYYY
                r'\b(\d{4}-\d{2}-\d{2})\b',  # YYYY-MM-DD
                r'\b(January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2},?\s+\d{4}\b'
            ]
            
            for pattern in date_patterns:
                matches = re.findall(pattern, content, re.IGNORECASE)
                for match in matches[:3]:  # Limit to 3 dates per email
                    # Extract context around date
                    context_match = re.search(
                        rf'.{{0,50}}{re.escape(match)}.{{0,50}}',
                        content,
                        re.IGNORECASE | re.DOTALL
                    )
                    
                    if context_match:
                        context = context_match.group(0).strip()
                        # Clean up context
                        context = re.sub(r'\s+', ' ', context)
                        
                        events.append({
                            'date': match,
                            'type': 'mentioned_date',
                            'description': context[:200]
                        })
                        
        return events
    
    def process_content_unified(self, content_type: str = 'all', limit: int = 100) -> dict[str, Any]:
        """Process content from content_unified table for embedding generation.
        
        Simple extension of existing pipeline to handle PDFs and other content types.
        Following CLAUDE.md principles: extend existing systems, don't duplicate.
        
        Args:
            content_type: 'all', 'pdf', 'email', or specific type
            limit: Maximum documents to process
            
        Returns:
            Dict with processing results
        """
        result = {
            'processed': 0,
            'skipped': 0,
            'errors': 0,
            'vectors_stored': 0
        }
        
        # Build query for content ready for embedding
        where_clause = "WHERE ready_for_embedding = 1"
        params = []
        
        if content_type != 'all':
            where_clause += " AND source_type = ?"
            params.append(content_type)
        
        # Get content needing embeddings
        query = f"""
            SELECT id, source_type, source_id, title, body, created_at
            FROM content_unified 
            {where_clause}
            ORDER BY created_at DESC
            LIMIT ?
        """
        params.append(limit)
        
        cursor = self.db.execute(query, tuple(params))
        content_items = cursor.fetchall()
        
        if not content_items:
            logger.info(f"No content ready for embedding (type={content_type})")
            return result
            
        logger.info(f"Processing {len(content_items)} {content_type} documents for embeddings")
        
        # Initialize services if needed
        if not self.embedding_service:
            self.embedding_service = get_embedding_service()
        if not self.vector_store:
            self.vector_store = get_vector_store('emails')
        
        for item in content_items:
            try:
                content_id = item['id']
                source_type = item['source_type']
                text_content = item['body'] or item['title'] or ''
                
                if len(text_content.strip()) < 10:  # Skip very short content
                    result['skipped'] += 1
                    continue
                
                # Check if embedding already exists
                cursor = self.db.execute("""
                    SELECT id FROM embeddings 
                    WHERE content_id = ? AND model = 'legal-bert'
                """, (content_id,))
                
                if cursor.fetchone():
                    result['skipped'] += 1
                    # Mark as not ready since it's already processed
                    self.db.execute("""
                        UPDATE content_unified 
                        SET ready_for_embedding = 0 
                        WHERE id = ?
                    """, (content_id,))
                    continue
                
                # Generate embedding
                embedding = self.embedding_service.get_embedding(text_content)
                if embedding is None or len(embedding) != 1024:
                    logger.warning(f"Invalid embedding for content {content_id}")
                    result['errors'] += 1
                    continue
                
                # Store in embeddings table
                self.db.execute("""
                    INSERT INTO embeddings (content_id, vector, dim, model, created_at)
                    VALUES (?, ?, ?, ?, ?)
                """, (
                    content_id,
                    str(embedding),  # Store as string for now
                    1024,
                    'legal-bert',
                    datetime.now().isoformat()
                ))
                
                # Store in Qdrant vector store
                vector_id = self._normalize_point_id(content_id=str(content_id))
                payload = {
                    'content_id': content_id,
                    'source_type': source_type,
                    'source_id': item['source_id'],
                    'title': item['title'],
                    'created_at': item['created_at']
                }
                
                self.vector_store.upsert(
                    vector=embedding,
                    payload=payload,
                    id=vector_id
                )
                
                # Mark as processed
                self.db.execute("""
                    UPDATE content_unified 
                    SET ready_for_embedding = 0 
                    WHERE id = ?
                """, (content_id,))
                
                result['processed'] += 1
                result['vectors_stored'] += 1
                
            except Exception as e:
                try:
                    content_id = item['id']
                except (KeyError, TypeError):
                    content_id = 'unknown'
                logger.error(f"Failed to process content {content_id}: {e}")
                result['errors'] += 1
        
        # Changes are committed automatically by SimpleDB
        
        logger.info(f"Content processing complete: {result['processed']} processed, {result['skipped']} skipped, {result['errors']} errors")
        return result


# Simple factory function
def get_semantic_pipeline(**kwargs) -> SemanticPipeline:
    """Get semantic pipeline instance."""
    return SemanticPipeline(**kwargs)