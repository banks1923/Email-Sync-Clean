"""
Metadata search functionality for analog database markdown files.

Handles YAML frontmatter parsing and metadata-based filtering.
"""

from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, List, Optional

import frontmatter
from loguru import logger


class MetadataSearcher:
    """Handles metadata searching and filtering."""
    
    def __init__(self, base_path: Path):
        """Initialize metadata searcher."""
        self.base_path = base_path
        self.analog_db_path = base_path / "analog_db"
        self.documents_path = self.analog_db_path / "documents"
        self.email_threads_path = self.analog_db_path / "email_threads"
        
        # Cache for metadata
        self._metadata_cache: Dict[str, Dict] = {}
        self._cache_timestamps: Dict[str, float] = {}
    
    def search_metadata(
        self,
        filters: Dict[str, Any],
        limit: int = 20
    ) -> List[Dict[str, Any]]:
        """Search by metadata fields using frontmatter."""
        try:
            markdown_files = self._get_markdown_files()
            matching_files = []
            
            for file_path in markdown_files:
                metadata = self._get_file_metadata(file_path)
                if metadata and self._matches_filters(metadata, filters):
                    result = {
                        "file_path": str(file_path),
                        "metadata": metadata,
                        "content_preview": self._get_content_preview(file_path)
                    }
                    matching_files.append(result)
                    
                    if len(matching_files) >= limit:
                        break
            
            return matching_files
            
        except Exception as e:
            logger.error(f"Metadata search failed: {e}")
            return []
    
    def _get_markdown_files(self) -> List[Path]:
        """Get all markdown files in analog database."""
        markdown_files = []
        
        for search_dir in [self.documents_path, self.email_threads_path]:
            if search_dir.exists():
                markdown_files.extend(search_dir.rglob("*.md"))
        
        return markdown_files
    
    @lru_cache(maxsize=512)
    def _get_file_metadata(self, file_path: Path) -> Optional[Dict[str, Any]]:
        """Extract YAML frontmatter from markdown file."""
        try:
            cache_key = str(file_path)
            file_mtime = file_path.stat().st_mtime
            
            if (cache_key in self._cache_timestamps and 
                self._cache_timestamps[cache_key] >= file_mtime):
                return self._metadata_cache.get(cache_key)
            
            with open(file_path, 'r', encoding='utf-8') as f:
                post = frontmatter.load(f)
            
            metadata = post.metadata
            metadata['_content_preview'] = (
                post.content[:200] + "..." if len(post.content) > 200 else post.content
            )
            
            # Update cache
            self._metadata_cache[cache_key] = metadata
            self._cache_timestamps[cache_key] = file_mtime
            
            return metadata
            
        except Exception as e:
            logger.debug(f"Failed to extract metadata from {file_path}: {e}")
            return None
    
    def _matches_filters(self, metadata: Dict[str, Any], filters: Dict[str, Any]) -> bool:
        """Check if file metadata matches the provided filters."""
        return (
            self._check_title_filter(metadata, filters) and
            self._check_doc_type_filter(metadata, filters) and
            self._check_tags_filter(metadata, filters) and
            self._check_date_filter(metadata, filters) and
            self._check_sender_filter(metadata, filters)
        )
    
    def _check_title_filter(self, metadata: Dict[str, Any], filters: Dict[str, Any]) -> bool:
        """Check title filter match."""
        if "title" not in filters:
            return True
        title = metadata.get("title", "").lower()
        return filters["title"].lower() in title
    
    def _check_doc_type_filter(self, metadata: Dict[str, Any], filters: Dict[str, Any]) -> bool:
        """Check document type filter match."""
        if "doc_type" not in filters:
            return True
        return metadata.get("doc_type") == filters["doc_type"]
    
    def _check_tags_filter(self, metadata: Dict[str, Any], filters: Dict[str, Any]) -> bool:
        """Check tags filter match."""
        if "tags" not in filters:
            return True
            
        file_tags = metadata.get("tags", [])
        if isinstance(file_tags, str):
            file_tags = [file_tags]
            
        filter_tags = filters["tags"]
        if isinstance(filter_tags, str):
            filter_tags = [filter_tags]
            
        tag_logic = filters.get("tag_logic", "OR").upper()
        
        if tag_logic == "AND":
            return all(tag in file_tags for tag in filter_tags)
        else:  # OR logic
            return any(tag in file_tags for tag in filter_tags)
    
    def _check_date_filter(self, metadata: Dict[str, Any], filters: Dict[str, Any]) -> bool:
        """Check date range filter match."""
        if "since" not in filters and "until" not in filters:
            return True
        file_date = metadata.get("date_created") or metadata.get("datetime_utc")
        return file_date is not None
    
    def _check_sender_filter(self, metadata: Dict[str, Any], filters: Dict[str, Any]) -> bool:
        """Check sender filter match."""
        if "sender" not in filters:
            return True
        sender = metadata.get("sender", "").lower()
        return filters["sender"].lower() in sender
    
    def _get_content_preview(self, file_path: Path, lines: int = 3) -> str:
        """Get content preview from markdown file."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                post = frontmatter.load(f)
            
            content_lines = post.content.split('\n')[:lines]
            preview = '\n'.join(content_lines)
            
            return preview[:300] + "..." if len(preview) > 300 else preview
            
        except Exception as e:
            logger.debug(f"Failed to get content preview from {file_path}: {e}")
            return ""
    
    def clear_cache(self) -> None:
        """Clear metadata cache."""
        self._metadata_cache.clear()
        self._cache_timestamps.clear()
        self._get_file_metadata.cache_clear()