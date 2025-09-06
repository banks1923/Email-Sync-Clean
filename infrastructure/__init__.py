"""
Infrastructure services including pipelines, documents, and MCP servers.
"""

# Document processing
from .documents.chunker.document_chunker import DocumentChunk, DocumentChunker, DocumentType
from .documents.quality.quality_score import ChunkQualityScorer as QualityScoreCalculator
from .documents.quality.quality_score import (
    QualitySettings,
    quality_gate,
)
from .mcp_servers.legal_intelligence_mcp import (
    legal_case_tracking,
    legal_document_analysis,
    legal_extract_entities,
    legal_knowledge_graph,
    legal_relationship_discovery,
    legal_timeline_events,
)

# MCP Servers
from .mcp_servers.search_intelligence_mcp import (
    find_literal,
    search_cluster,
    search_entities,
    search_process_all,
    search_similar,
    search_smart,
    search_summarize,
)

# Define public API
__all__ = [
    # Document Processing
    "DocumentChunker",
    "DocumentChunk",
    "DocumentType",
    "QualityScoreCalculator",
    "QualitySettings",
    "quality_gate",
    # Search Intelligence MCP
    "search_smart",
    "find_literal",
    "search_similar",
    "search_entities",
    "search_summarize",
    "search_cluster",
    "search_process_all",
    # Legal Intelligence MCP
    "legal_extract_entities",
    "legal_timeline_events",
    "legal_knowledge_graph",
    "legal_document_analysis",
    "legal_case_tracking",
    "legal_relationship_discovery",
]
