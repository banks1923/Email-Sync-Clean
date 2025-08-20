"""
Adapter for VectorMaintenance vs SimpleDB API mismatches.

PROBLEM: VectorMaintenance expects methods like get_all_content_ids that SimpleDB doesn't have.
SOLUTION: This adapter provides the missing methods using SimpleDB's existing API.
REMOVAL DATE: 2025-09-01
"""

from typing import List
from loguru import logger


class VectorMaintenanceAdapter:
    """Adapts SimpleDB to provide methods expected by VectorMaintenance."""
    
    def __init__(self, db):
        """Wrap SimpleDB instance."""
        self.db = db
        logger.warning("VectorMaintenanceAdapter in use - remove by 2025-09-01")
    
    def get_all_content_ids(self, content_type: str = None) -> list[str]:
        """
        Get all content IDs, optionally filtered by type.
        
        VectorMaintenance expects this method but SimpleDB doesn't have it.
        We synthesize it from existing SimpleDB methods.
        """
        try:
            if content_type:
                # Map collection names to content types (plural -> singular)
                type_mapping = {
                    'emails': 'email',
                    'pdfs': 'pdf',
                    'transcriptions': 'transcription',
                    'notes': 'note',
                    'documents': 'document'
                }
                db_type = type_mapping.get(content_type, content_type)
                
                # Use search with type filter
                query = f"""
                    SELECT id FROM content 
                    WHERE content_type = ?
                """
                result = self.db.execute(query, (db_type,))
            else:
                # Get all IDs
                query = "SELECT id FROM content"
                result = self.db.execute(query)
            
            return [row["id"] for row in result.fetchall()]
        except Exception as e:
            logger.error(f"Failed to get content IDs: {e}")
            return []
    
    def get_content_by_ids(self, ids: list[str]) -> list[dict]:
        """
        Batch fetch content by IDs.
        
        VectorMaintenance expects batch operations.
        """
        if not ids:
            return []
        
        try:
            placeholders = ",".join("?" * len(ids))
            query = f"""
                SELECT id, content_type, title, content, metadata
                FROM content
                WHERE id IN ({placeholders})
            """
            result = self.db.execute(query, tuple(ids))
            return [dict(row) for row in result.fetchall()]
        except Exception as e:
            logger.error(f"Failed to get content by IDs: {e}")
            return []
    
    def update_vector_status(self, content_id: str, processed: bool = True) -> bool:
        """
        Update vector processing status for content.
        
        Maps to SimpleDB's update_content method.
        """
        try:
            return self.db.update_content(
                content_id,
                {"vector_processed": 1 if processed else 0}
            )
        except Exception as e:
            logger.error(f"Failed to update vector status: {e}")
            return False
    
    def get_content_by_id(self, content_id: str) -> dict | None:
        """
        Get a single content item by ID.
        
        Returns content with id, text, and metadata fields.
        """
        try:
            query = """
                SELECT id, content_type, content, metadata 
                FROM content 
                WHERE id = ?
            """
            result = self.db.execute(query, (content_id,))
            row = result.fetchone()
            
            if row:
                # Parse metadata if it's a JSON string
                import json
                metadata = {}
                metadata_str = row["metadata"] if row["metadata"] else None
                if metadata_str:
                    try:
                        metadata = json.loads(metadata_str)
                    except:
                        metadata = {}
                
                return {
                    "id": row["id"],
                    "text": row["content"],  # Map 'content' column to 'text' field
                    "metadata": {
                        "content_type": row["content_type"],
                        **metadata
                    }
                }
            return None
        except Exception as e:
            logger.error(f"Failed to get content by ID {content_id}: {e}")
            return None
    
    def get_content_count(self, content_type: str = None) -> int:
        """
        Get count of content items, optionally filtered by type.
        
        Maps to SimpleDB's get_content_stats method.
        """
        try:
            stats = self.db.get_content_stats()
            if content_type:
                # Map common content types to their database equivalents
                type_map = {
                    "emails": "email",
                    "pdfs": "pdf", 
                    "transcriptions": "transcription",
                    "notes": "note"
                }
                mapped_type = type_map.get(content_type, content_type)
                
                # Get count for specific type
                query = "SELECT COUNT(*) as count FROM content WHERE content_type = ?"
                result = self.db.execute(query, (mapped_type,))
                row = result.fetchone()
                return row["count"] if row else 0
            else:
                # Return total count
                return stats.get("total_documents", 0)
        except Exception as e:
            logger.error(f"Failed to get content count: {e}")
            return 0
    
    def __getattr__(self, name):
        """Forward all other methods directly to SimpleDB."""
        return getattr(self.db, name)