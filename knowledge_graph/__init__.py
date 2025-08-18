"""Knowledge Graph Service for Email Sync System.

Simple knowledge graph implementation for content relationship mapping
with similarity analysis.
"""

from .graph_queries import GraphQueryService, get_graph_query_service
from .main import KnowledgeGraphService, get_knowledge_graph_service
from .similarity_analyzer import SimilarityAnalyzer, get_similarity_analyzer
from .similarity_integration import SimilarityIntegration, get_similarity_integration
from .timeline_relationships import TimelineRelationships, get_timeline_relationships
from .topic_clustering import TopicClusteringService, get_topic_clustering_service

__all__ = [
    "KnowledgeGraphService",
    "get_knowledge_graph_service",
    "SimilarityAnalyzer",
    "get_similarity_analyzer",
    "SimilarityIntegration",
    "get_similarity_integration",
    "TimelineRelationships",
    "get_timeline_relationships",
    "TopicClusteringService",
    "get_topic_clustering_service",
    "GraphQueryService",
    "get_graph_query_service",
]
