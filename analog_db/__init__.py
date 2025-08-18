"""
Analog Database - File-based document and email storage system.

Provides markdown-aware search capabilities for documents and email threads
stored as human-readable markdown files with YAML frontmatter.
"""

from .search_interface import SearchInterface
from .content_search import ContentSearcher
from .metadata_search import MetadataSearcher
from .vector_search import VectorSearcher

__all__ = ["SearchInterface", "ContentSearcher", "MetadataSearcher", "VectorSearcher"]