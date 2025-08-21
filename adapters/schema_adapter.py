"""
Adapter for schema mismatches (missing columns).

PROBLEM: Code expects source_path column but it may not exist in content table.
SOLUTION: This adapter handles missing columns gracefully.
REMOVAL DATE: 2025-09-01
"""

import sqlite3
from loguru import logger


class SchemaAdapter:
    """Handles schema mismatches gracefully."""
    
    def __init__(self, db):
        """Wrap database connection."""
        self.db = db
        self._check_schema()
        logger.warning("SchemaAdapter in use - remove by 2025-09-01")
    
    def _check_schema(self):
        """Check which columns actually exist."""
        try:
            # Get actual schema
            cursor = self.db.execute(
                "PRAGMA table_info(content)"
            )
            columns = cursor.fetchall()
            self.existing_columns = {col[1] for col in columns}
            
            # Check for missing expected columns
            expected = {"source_path", "vector_processed", "word_count"}
            missing = expected - self.existing_columns
            
            if missing:
                logger.warning(f"Missing columns in content table: {missing}")
                logger.warning("Run schema migration or update SimpleDB._init_tables()")
        except Exception as e:
            logger.error(f"Failed to check schema: {e}")
            self.existing_columns = set()
    
    def safe_add_content(
        self,
        content_type: str,
        title: str,
        content: str,
        metadata: dict = None,
        source_path: str = None,
        **kwargs
    ) -> str | None:
        """
        Add content, handling missing columns gracefully.
        
        If source_path column doesn't exist, store in metadata instead.
        """
        # Filter out fields that don't exist in schema
        if source_path and "source_path" not in self.existing_columns:
            logger.debug(f"source_path column missing, storing in metadata")
            if metadata is None:
                metadata = {}
            metadata["source_path"] = source_path
            source_path = None
        
        # Remove any kwargs that reference missing columns
        filtered_kwargs = {}
        for key, value in kwargs.items():
            if key in self.existing_columns:
                filtered_kwargs[key] = value
            else:
                logger.debug(f"Ignoring field {key} - column doesn't exist")
        
        # Call original method with filtered params
        try:
            if source_path and "source_path" in self.existing_columns:
                return self.db.add_content(
                    content_type=content_type,
                    title=title,
                    content=content,
                    metadata=metadata,
                    source_path=source_path,
                    **filtered_kwargs
                )
            else:
                return self.db.add_content(
                    content_type=content_type,
                    title=title,
                    content=content,
                    metadata=metadata,
                    **filtered_kwargs
                )
        except sqlite3.OperationalError as e:
            if "no column named" in str(e).lower():
                # Try again without the problematic field
                logger.warning(f"Column error: {e}, retrying without extra fields")
                return self.db.add_content(
                    content_type=content_type,
                    title=title,
                    content=content,
                    metadata=metadata
                )
            raise
    
    def __getattr__(self, name):
        """Forward all other methods directly to the database."""
        return getattr(self.db, name)