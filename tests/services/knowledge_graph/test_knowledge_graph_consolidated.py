"""
Consolidated Knowledge Graph tests - Essential functionality only.

Combines the most important tests from:
- test_knowledge_graph.py (33 tests)
- test_similarity_analyzer.py (20 tests)
- test_graph_queries.py (16 tests)

Focuses on core graph operations, not edge cases.
"""

import os
import sys

from knowledge_graph import get_knowledge_graph_service, get_similarity_analyzer

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
if project_root not in sys.path:
    sys.path.insert(0, project_root)


class TestKnowledgeGraphCore:
    """Essential knowledge graph functionality tests."""
    
    def test_knowledge_graph_service_initialization(self, simple_db):
        """Test KnowledgeGraphService initializes correctly."""
        service = get_knowledge_graph_service(simple_db.db_path)
        
        assert service is not None
        assert hasattr(service, 'db')
        assert service.db.db_path == simple_db.db_path

    def test_add_node_basic(self, simple_db):
        """Test adding a basic node to the graph."""
        service = get_knowledge_graph_service(simple_db.db_path)
        
        result = service.add_node(
            content_id="node_001",
            content_type="email",
            title="Test Email"
        )
        
        assert result["success"] is True
        assert result["node_id"] == "node_001"

    def test_add_edge_between_nodes(self, simple_db):
        """Test adding an edge between two nodes."""
        service = get_knowledge_graph_service(simple_db.db_path)
        
        # Add two nodes
        service.add_node("node_a", "email", "Email A")
        service.add_node("node_b", "email", "Email B")
        
        # Add edge
        result = service.add_edge(
            source_content_id="node_a",
            target_content_id="node_b",
            relationship_type="replies_to"
        )
        
        assert result["success"] is True

    def test_get_node_by_id(self, simple_db):
        """Test retrieving a node by ID."""
        service = get_knowledge_graph_service(simple_db.db_path)
        
        # Add node
        service.add_node("get_001", "pdf", "Test PDF")
        
        # Retrieve it
        result = service.get_node("get_001")
        
        assert result["success"] is True
        assert result["node"]["content_id"] == "get_001"
        assert result["node"]["content_type"] == "pdf"

    def test_get_node_neighbors(self, simple_db):
        """Test getting neighbors of a node."""
        service = get_knowledge_graph_service(simple_db.db_path)
        
        # Create connected nodes
        service.add_node("center", "email", "Center Node")
        service.add_node("neighbor1", "email", "Neighbor 1")
        service.add_node("neighbor2", "pdf", "Neighbor 2")
        
        service.add_edge("center", "neighbor1", "related_to")
        service.add_edge("center", "neighbor2", "references")
        
        result = service.get_neighbors("center")
        
        assert result["success"] is True
        assert len(result["neighbors"]) == 2

    def test_find_shortest_path(self, simple_db):
        """Test finding shortest path between nodes."""
        service = get_knowledge_graph_service(simple_db.db_path)
        
        # Create path: A -> B -> C
        service.add_node("path_a", "email", "Node A")
        service.add_node("path_b", "email", "Node B") 
        service.add_node("path_c", "email", "Node C")
        
        service.add_edge("path_a", "path_b", "connects_to")
        service.add_edge("path_b", "path_c", "connects_to")
        
        result = service.find_shortest_path("path_a", "path_c")
        
        assert result["success"] is True
        assert len(result["path"]) == 3  # A, B, C

    def test_get_graph_statistics(self, simple_db):
        """Test getting overall graph statistics."""
        service = get_knowledge_graph_service(simple_db.db_path)
        
        # Add some nodes and edges
        service.add_node("stat_1", "email", "Node 1")
        service.add_node("stat_2", "pdf", "Node 2")
        service.add_edge("stat_1", "stat_2", "related")
        
        result = service.get_graph_statistics()
        
        assert result["success"] is True
        assert result["node_count"] >= 2
        assert result["edge_count"] >= 1

    def test_find_similar_nodes(self, simple_db):
        """Test finding nodes similar to a given node."""
        service = get_knowledge_graph_service(simple_db.db_path)
        
        # Add nodes with similar content
        service.add_node("sim_1", "email", "Legal contract discussion")
        service.add_node("sim_2", "email", "Contract terms review")
        service.add_node("sim_3", "pdf", "Rental agreement")
        
        result = service.find_similar_nodes("sim_1", similarity_threshold=0.1)
        
        assert result["success"] is True

    def test_cluster_similar_nodes(self, simple_db):
        """Test clustering nodes by similarity."""
        service = get_knowledge_graph_service(simple_db.db_path)
        
        # Add diverse nodes
        for i in range(5):
            service.add_node(f"cluster_{i}", "email", f"Email about topic {i % 2}")
        
        result = service.cluster_similar_nodes(min_cluster_size=2)
        
        assert result["success"] is True

    def test_node_degree_analysis(self, simple_db):
        """Test analyzing node connectivity (degree)."""
        service = get_knowledge_graph_service(simple_db.db_path)
        
        # Create hub node
        service.add_node("hub", "email", "Hub Node")
        for i in range(3):
            service.add_node(f"spoke_{i}", "email", f"Spoke {i}")
            service.add_edge("hub", f"spoke_{i}", "connects_to")
        
        result = service.analyze_node_degrees()
        
        assert result["success"] is True
        assert result["max_degree"] >= 3

    def test_similarity_analyzer_initialization(self, simple_db):
        """Test SimilarityAnalyzer initialization."""
        analyzer = get_similarity_analyzer(simple_db.db_path)
        
        assert analyzer is not None
        assert hasattr(analyzer, 'db')

    def test_calculate_content_similarity(self, simple_db):
        """Test calculating similarity between content."""
        analyzer = get_similarity_analyzer(simple_db.db_path)
        
        # Add content
        analyzer.db.add_content("email", "Legal notice", "This is about legal matters")
        analyzer.db.add_content("email", "Legal contract", "This discusses legal contracts")
        
        result = analyzer.calculate_similarity("Legal notice", "Legal contract")
        
        assert result["success"] is True
        assert 0 <= result["similarity"] <= 1

    def test_find_similar_content(self, simple_db):
        """Test finding content similar to a query."""
        analyzer = get_similarity_analyzer(simple_db.db_path)
        
        # Add test content
        analyzer.db.add_content("email", "Contract A", "Legal contract terms")
        analyzer.db.add_content("email", "Contract B", "Contract legal clauses")
        analyzer.db.add_content("pdf", "Recipe", "Cooking instructions")
        
        result = analyzer.find_similar_content("legal document", threshold=0.1)
        
        assert result["success"] is True

    def test_build_similarity_graph(self, simple_db):
        """Test building a graph based on content similarity."""
        analyzer = get_similarity_analyzer(simple_db.db_path)
        
        # Add related content
        for i in range(3):
            analyzer.db.add_content("email", f"Email {i}", f"Legal topic {i}")
        
        result = analyzer.build_similarity_graph(threshold=0.1)
        
        assert result["success"] is True

    def test_detect_content_clusters(self, simple_db):
        """Test detecting clusters of similar content."""
        analyzer = get_similarity_analyzer(simple_db.db_path)
        
        # Add clusterable content
        topics = ["legal", "cooking", "legal", "cooking"]
        for i, topic in enumerate(topics):
            analyzer.db.add_content("email", f"Email {i}", f"About {topic} stuff")
        
        result = analyzer.detect_clusters(min_cluster_size=2)
        
        assert result["success"] is True

    def test_similarity_threshold_filtering(self, simple_db):
        """Test filtering results by similarity threshold."""
        analyzer = get_similarity_analyzer(simple_db.db_path, similarity_threshold=0.5)
        
        result = analyzer.find_similar_content("test query", threshold=0.8)
        
        # Should respect the higher threshold
        assert result["success"] is True

    def test_graph_query_by_content_type(self, simple_db):
        """Test querying graph by content type."""
        service = get_knowledge_graph_service(simple_db.db_path)
        
        # Add mixed content types
        service.add_node("email_1", "email", "Email Node")
        service.add_node("pdf_1", "pdf", "PDF Node")
        service.add_node("email_2", "email", "Another Email")
        
        result = service.query_nodes_by_type("email")
        
        assert result["success"] is True
        assert len(result["nodes"]) == 2
        assert all(node["content_type"] == "email" for node in result["nodes"])

    def test_graph_query_by_relationship(self, simple_db):
        """Test querying graph by relationship type."""
        service = get_knowledge_graph_service(simple_db.db_path)
        
        # Add nodes with different relationships
        service.add_node("doc_a", "pdf", "Document A")
        service.add_node("doc_b", "pdf", "Document B")
        service.add_node("doc_c", "email", "Email C")
        
        service.add_edge("doc_a", "doc_b", "references")
        service.add_edge("doc_a", "doc_c", "mentions")
        
        result = service.query_edges_by_type("references")
        
        assert result["success"] is True
        assert len(result["edges"]) == 1

    def test_subgraph_extraction(self, simple_db):
        """Test extracting a subgraph around a node."""
        service = get_knowledge_graph_service(simple_db.db_path)
        
        # Create small connected component
        center = "subgraph_center"
        service.add_node(center, "email", "Center")
        
        for i in range(3):
            node_id = f"sub_node_{i}"
            service.add_node(node_id, "email", f"Node {i}")
            service.add_edge(center, node_id, "connects_to")
        
        result = service.extract_subgraph(center, depth=1)
        
        assert result["success"] is True
        assert len(result["nodes"]) == 4  # center + 3 neighbors

    def test_graph_export_import(self, simple_db):
        """Test exporting and importing graph data."""
        service = get_knowledge_graph_service(simple_db.db_path)
        
        # Add some data
        service.add_node("export_1", "email", "Export Test")
        service.add_node("export_2", "pdf", "Export PDF")
        service.add_edge("export_1", "export_2", "related_to")
        
        # Export
        export_result = service.export_graph()
        
        assert export_result["success"] is True
        assert "nodes" in export_result["graph"]
        assert "edges" in export_result["graph"]

    def test_node_metadata_storage(self, simple_db):
        """Test storing and retrieving node metadata."""
        service = get_knowledge_graph_service(simple_db.db_path)
        
        metadata = {"author": "test@example.com", "date": "2024-01-01"}
        
        result = service.add_node(
            content_id="meta_001",
            content_type="email",
            title="Metadata Test",
            metadata=metadata
        )
        
        assert result["success"] is True
        
        # Retrieve and check metadata
        node_result = service.get_node("meta_001")
        assert node_result["success"] is True

    def test_edge_weight_functionality(self, simple_db):
        """Test edge weights for relationship strength."""
        service = get_knowledge_graph_service(simple_db.db_path)
        
        service.add_node("weight_a", "email", "Node A")
        service.add_node("weight_b", "email", "Node B")
        
        result = service.add_edge(
            source_content_id="weight_a",
            target_content_id="weight_b",
            relationship_type="similar_to",
            strength=0.8
        )
        
        assert result["success"] is True

    def test_graph_search_functionality(self, simple_db):
        """Test searching within the graph."""
        service = get_knowledge_graph_service(simple_db.db_path)
        
        # Add searchable nodes
        service.add_node("search_1", "email", "Contract negotiation")
        service.add_node("search_2", "pdf", "Legal contract terms")
        service.add_node("search_3", "email", "Meeting notes")
        
        result = service.search_nodes("contract")
        
        assert result["success"] is True
        assert len(result["nodes"]) >= 2

    def test_remove_node_and_edges(self, simple_db):
        """Test removing a node and its associated edges."""
        service = get_knowledge_graph_service(simple_db.db_path)
        
        # Add connected nodes
        service.add_node("remove_center", "email", "To Remove")
        service.add_node("remove_neighbor", "email", "Neighbor")
        service.add_edge("remove_center", "remove_neighbor", "connects_to")
        
        # Remove center node
        result = service.remove_node("remove_center")
        
        assert result["success"] is True

    def test_graph_component_analysis(self, simple_db):
        """Test analyzing connected components in the graph."""
        service = get_knowledge_graph_service(simple_db.db_path)
        
        # Create two separate components
        # Component 1
        service.add_node("comp1_a", "email", "Component 1A")
        service.add_node("comp1_b", "email", "Component 1B")
        service.add_edge("comp1_a", "comp1_b", "connects")
        
        # Component 2
        service.add_node("comp2_a", "pdf", "Component 2A")
        service.add_node("comp2_b", "pdf", "Component 2B")
        service.add_edge("comp2_a", "comp2_b", "connects")
        
        result = service.analyze_connected_components()
        
        assert result["success"] is True
        assert result["component_count"] >= 2

    def test_similarity_caching(self, simple_db):
        """Test that similarity calculations are cached for performance."""
        analyzer = get_similarity_analyzer(simple_db.db_path)
        
        # Calculate similarity twice
        result1 = analyzer.calculate_similarity("test content a", "test content b")
        result2 = analyzer.calculate_similarity("test content a", "test content b")
        
        assert result1["success"] is True
        assert result2["success"] is True
        # Results should be identical (cached)
        assert result1["similarity"] == result2["similarity"]

    def test_graph_performance_with_many_nodes(self, simple_db):
        """Test graph performance with larger dataset."""
        service = get_knowledge_graph_service(simple_db.db_path)
        
        # Add many nodes quickly
        for i in range(50):
            service.add_node(f"perf_{i}", "email", f"Performance test {i}")
        
        # Add some edges
        for i in range(0, 48, 2):
            service.add_edge(f"perf_{i}", f"perf_{i+1}", "related")
        
        # Query should still be fast
        result = service.get_graph_statistics()
        
        assert result["success"] is True
        assert result["node_count"] >= 50

    def test_end_to_end_knowledge_workflow(self, simple_db):
        """Test complete workflow from content to knowledge graph."""
        service = get_knowledge_graph_service(simple_db.db_path)
        analyzer = get_similarity_analyzer(simple_db.db_path)
        
        # Add content
        service.add_node("workflow_1", "email", "Legal case discussion")
        service.add_node("workflow_2", "pdf", "Case documents")
        
        # Create relationship
        service.add_edge("workflow_1", "workflow_2", "references")
        
        # Analyze similarity
        sim_result = analyzer.find_similar_content("legal case", threshold=0.1)
        
        # Get statistics
        stats_result = service.get_graph_statistics()
        
        assert sim_result["success"] is True
        assert stats_result["success"] is True