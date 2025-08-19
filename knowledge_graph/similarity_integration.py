"""Integration between SimilarityAnalyzer and KnowledgeGraphService.

Automatically discovers and stores similarity relationships in the
knowledge graph. Follows CLAUDE.md principles: simple integration
patterns under 450 lines.
"""

import time

from loguru import logger

from shared.simple_db import SimpleDB

from .main import KnowledgeGraphService
from .similarity_analyzer import SimilarityAnalyzer

# Logger is now imported globally from loguru


class SimilarityIntegration:
    """
    Integrate similarity analysis with knowledge graph storage.
    """

    def __init__(self, db_path: str = "emails.db", similarity_threshold: float = 0.7):
        self.kg_service = KnowledgeGraphService(db_path)
        self.similarity_analyzer = SimilarityAnalyzer(db_path, similarity_threshold)
        self.db = SimpleDB(db_path)

    def discover_and_store_similarities(
        self, content_type: str = None, batch_size: int = 100
    ) -> dict:
        """
        Discover similarities and store them as knowledge graph edges.
        """
        logger.info(f"Starting similarity discovery for {content_type or 'all'} content")
        start_time = time.time()

        # Get content to analyze
        content_ids = self._get_content_ids(content_type)

        if len(content_ids) < 2:
            logger.warning("Not enough content for similarity analysis")
            return {"processed": 0, "relationships_created": 0, "time_seconds": 0}

        logger.info(f"Analyzing {len(content_ids)} documents for similarities")

        # Compute similarities in batches
        relationships_created = 0
        processed_pairs = 0

        for i in range(0, len(content_ids), batch_size):
            batch_ids = content_ids[i : i + batch_size]

            # Compute similarities for this batch
            similarities = self.similarity_analyzer.batch_compute_similarities(batch_ids)

            # Store as knowledge graph edges
            for source_id, target_id, similarity in similarities:
                edge_id = self.kg_service.add_edge(
                    source_id,
                    target_id,
                    "similar_to",
                    similarity,
                    metadata={
                        "method": "legal_bert",
                        "model": "pile-of-law/legalbert-large-1.7M-2",
                        "threshold": self.similarity_analyzer.similarity_threshold,
                        "computed_at": time.time(),
                    },
                )

                if edge_id:
                    relationships_created += 1

            processed_pairs += len(similarities)

            logger.info(
                f"Batch {i//batch_size + 1}: {len(similarities)} similarities "
                f"-> {relationships_created} relationships created"
            )

        elapsed_time = time.time() - start_time

        result = {
            "processed_documents": len(content_ids),
            "processed_pairs": processed_pairs,
            "relationships_created": relationships_created,
            "time_seconds": elapsed_time,
            "content_type": content_type,
        }

        logger.info(f"Similarity discovery complete: {result}")
        return result

    def find_and_link_similar_content(self, content_id: str, limit: int = 10) -> list[str]:
        """
        Find similar content and create knowledge graph links.
        """
        similar_content = self.similarity_analyzer.find_similar_content(content_id, limit)

        created_edges = []

        for item in similar_content:
            target_id = item["content_id"]
            similarity = item["similarity"]

            # Create knowledge graph edge
            edge_id = self.kg_service.add_edge(
                content_id,
                target_id,
                "similar_to",
                similarity,
                metadata={
                    "method": "legal_bert",
                    "threshold": self.similarity_analyzer.similarity_threshold,
                    "computed_at": time.time(),
                },
            )

            if edge_id:
                created_edges.append(edge_id)
                logger.debug(
                    f"Created similarity edge: {content_id} -> {target_id} "
                    f"(score: {similarity:.3f})"
                )

        return created_edges

    def update_existing_relationships(self, recalculate: bool = False) -> dict:
        """
        Update similarity scores for existing relationships.
        """
        logger.info("Updating existing similarity relationships")

        # Get existing similarity edges
        similarity_edges = self.db.fetch(
            """
            SELECT edge_id, source_node_id, target_node_id, strength, edge_metadata
            FROM kg_edges
            WHERE relationship_type = 'similar_to'
        """
        )

        updated_count = 0
        skipped_count = 0

        for edge in similarity_edges:
            # Get content IDs for the nodes
            source_node = self.kg_service.get_node(edge["source_node_id"])
            target_node = self.kg_service.get_node(edge["target_node_id"])

            if not source_node or not target_node:
                logger.warning(f"Missing nodes for edge {edge['edge_id']}")
                continue

            source_content_id = source_node["content_id"]
            target_content_id = target_node["content_id"]

            # Check if we should recalculate
            if not recalculate:
                # Check if similarity is already cached
                cached_sim = self.similarity_analyzer._get_cached_similarity(
                    source_content_id, target_content_id
                )
                if cached_sim is not None:
                    skipped_count += 1
                    continue

            # Compute new similarity
            new_similarity = self.similarity_analyzer.compute_similarity(
                source_content_id, target_content_id
            )

            if new_similarity is not None:
                # Update edge strength
                self.db.execute(
                    """
                    UPDATE kg_edges
                    SET strength = ?, edge_metadata = ?
                    WHERE edge_id = ?
                """,
                    (
                        new_similarity,
                        f'{{"method": "legal_bert", "updated_at": {time.time()}}}',
                        edge["edge_id"],
                    ),
                )
                updated_count += 1

        result = {
            "total_edges": len(similarity_edges),
            "updated": updated_count,
            "skipped": skipped_count,
        }

        logger.info(f"Relationship update complete: {result}")
        return result

    def get_similarity_network_stats(self) -> dict:
        """
        Get statistics about the similarity network in the knowledge graph.
        """
        # Count similarity edges
        similarity_stats = self.db.fetch_one(
            """
            SELECT
                COUNT(*) as total_similarity_edges,
                AVG(strength) as avg_similarity,
                MIN(strength) as min_similarity,
                MAX(strength) as max_similarity
            FROM kg_edges
            WHERE relationship_type = 'similar_to'
        """
        )

        # Get node degree distribution for similarity network
        node_degrees = self.db.fetch(
            """
            SELECT
                n.id,
                n.content_type,
                COUNT(e.edge_id) as similarity_degree
            FROM kg_nodes n
            LEFT JOIN kg_edges e ON (
                n.node_id = e.source_node_id OR n.node_id = e.target_node_id
            ) AND e.relationship_type = 'similar_to'
            GROUP BY n.node_id, n.id, n.content_type
            HAVING similarity_degree > 0
        """
        )

        # Content type distribution in similarity network
        content_type_stats = self.db.fetch(
            """
            SELECT
                n.content_type,
                COUNT(DISTINCT n.node_id) as node_count,
                COUNT(e.edge_id) as edge_count
            FROM kg_nodes n
            LEFT JOIN kg_edges e ON (
                n.node_id = e.source_node_id OR n.node_id = e.target_node_id
            ) AND e.relationship_type = 'similar_to'
            GROUP BY n.content_type
        """
        )

        return {
            "similarity_edges": dict(similarity_stats) if similarity_stats else {},
            "connected_nodes": len(node_degrees),
            "content_types": {
                row["content_type"]: {"nodes": row["node_count"], "edges": row["edge_count"]}
                for row in content_type_stats
            },
            "avg_node_degree": (
                sum(row["similarity_degree"] for row in node_degrees) / len(node_degrees)
                if node_degrees
                else 0
            ),
        }

    def find_similarity_clusters(self, min_cluster_size: int = 3) -> list[dict]:
        """
        Find clusters of highly similar content.
        """
        # Get all similarity edges above a high threshold
        high_similarity_edges = self.db.fetch(
            """
            SELECT
                n1.id as source_content,
                n2.id as target_content,
                e.strength
            FROM kg_edges e
            JOIN kg_nodes n1 ON e.source_node_id = n1.node_id
            JOIN kg_nodes n2 ON e.target_node_id = n2.node_id
            WHERE e.relationship_type = 'similar_to'
            AND e.strength >= 0.85
            ORDER BY e.strength DESC
        """
        )

        # Simple clustering using connected components
        clusters = []
        visited = set()

        for edge in high_similarity_edges:
            source = edge["source_content"]
            target = edge["target_content"]

            if source in visited or target in visited:
                continue

            # Find all connected nodes starting from this edge
            cluster = self._find_connected_cluster(source, high_similarity_edges, visited)

            if len(cluster) >= min_cluster_size:
                clusters.append(
                    {
                        "cluster_id": len(clusters) + 1,
                        "content_ids": list(cluster),
                        "size": len(cluster),
                        "avg_similarity": self._calculate_cluster_similarity(cluster),
                    }
                )

        return clusters

    def _get_content_ids(self, content_type: str = None) -> list[str]:
        """
        Get content IDs for analysis.
        """
        if content_type:
            query = "SELECT id FROM content WHERE content_type = ?"
            params = (content_type,)
        else:
            query = "SELECT id FROM content"
            params = ()

        rows = self.db.fetch(query, params)
        return [row["content_id"] for row in rows]

    def _find_connected_cluster(
        self, start_node: str, edges: list[dict], visited: set[str]
    ) -> set[str]:
        """
        Find all nodes connected to start_node through high similarity edges.
        """
        cluster = {start_node}
        visited.add(start_node)
        queue = [start_node]

        while queue:
            current = queue.pop(0)

            # Find all edges connected to current node
            for edge in edges:
                other_node = None
                if edge["source_content"] == current and edge["target_content"] not in visited:
                    other_node = edge["target_content"]
                elif edge["target_content"] == current and edge["source_content"] not in visited:
                    other_node = edge["source_content"]

                if other_node:
                    cluster.add(other_node)
                    visited.add(other_node)
                    queue.append(other_node)

        return cluster

    def _calculate_cluster_similarity(self, cluster: set[str]) -> float:
        """
        Calculate average similarity within a cluster.
        """
        if len(cluster) < 2:
            return 0.0

        similarities = []
        cluster_list = list(cluster)

        for i, content_id_1 in enumerate(cluster_list):
            for content_id_2 in cluster_list[i + 1 :]:
                sim = self.similarity_analyzer._get_cached_similarity(content_id_1, content_id_2)
                if sim is not None:
                    similarities.append(sim)

        return sum(similarities) / len(similarities) if similarities else 0.0


def get_similarity_integration(
    db_path: str = "emails.db", similarity_threshold: float = 0.7
) -> SimilarityIntegration:
    """
    Get similarity integration instance.
    """
    return SimilarityIntegration(db_path, similarity_threshold)
