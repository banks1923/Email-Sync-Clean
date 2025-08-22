"""Graph Traversal and Query Service for Knowledge Graph.

Advanced graph algorithms and query methods for content discovery.
Follows CLAUDE.md principles: simple > complex, under 450 lines,
functions under 30 lines.
"""

import json
from collections import defaultdict, deque
from collections.abc import Generator

from loguru import logger

from shared.simple_db import SimpleDB

# Logger is now imported globally from loguru

# Singleton instance
_graph_query_service = None


class GraphQueryService:
    """
    Advanced graph traversal and query operations for knowledge graph.
    """

    def __init__(self, db_path: str = "data/emails.db"):
        """
        Initialize graph query service with database connection.
        """
        self.db = SimpleDB(db_path)
        self.db_path = db_path
        logger.info(f"GraphQueryService initialized with database: {db_path}")

    def breadth_first_traversal(
        self,
        start_content_id: str,
        max_depth: int = 3,
        relationship_types: list[str] | None = None,
    ) -> Generator[tuple[dict, int, list[str]], None, None]:
        """Perform breadth-first traversal from starting node.

        Yields: (node_info, depth, path) tuples
        """
        # Get starting node
        start_node = self._get_node_by_content(start_content_id)
        if not start_node:
            logger.warning(f"Start node not found for content_id: {start_content_id}")
            return

        visited = set()
        queue = deque([(start_node, 0, [start_content_id])])

        while queue:
            current_node, depth, path = queue.popleft()

            if current_node["node_id"] in visited or depth > max_depth:
                continue

            visited.add(current_node["node_id"])
            yield (current_node, depth, path)

            # Get adjacent nodes
            neighbors = self._get_neighbors(current_node["node_id"], relationship_types)

            for neighbor in neighbors:
                if neighbor["node_id"] not in visited:
                    new_path = path + [neighbor["content_id"]]
                    queue.append((neighbor, depth + 1, new_path))

    def _get_node_by_content(self, content_id: str) -> dict | None:
        """
        Get node by content ID.
        """
        return self.db.fetch_one("SELECT * FROM kg_nodes WHERE id = ?", (content_id,))

    def _get_neighbors(
        self, node_id: str, relationship_types: list[str] | None = None
    ) -> list[dict]:
        """
        Get neighboring nodes with optional relationship type filter.
        """
        # Build query for edges
        base_query = """
            SELECT DISTINCT n.*
            FROM kg_nodes n
            JOIN kg_edges e ON (
                (e.source_node_id = ? AND e.target_node_id = n.node_id) OR
                (e.target_node_id = ? AND e.source_node_id = n.node_id)
            )
        """

        params = [node_id, node_id]

        if relationship_types:
            placeholders = ",".join(["?" for _ in relationship_types])
            base_query += f" WHERE e.relationship_type IN ({placeholders})"
            params.extend(relationship_types)

        return self.db.fetch(base_query, params)

    def format_bfs_results(
        self, traversal_results: list[tuple[dict, int, list[str]]], include_metadata: bool = True
    ) -> list[dict]:
        """
        Format BFS traversal results with content information.
        """
        formatted = []

        for node, depth, path in traversal_results:
            result = {
                "content_id": node["id"],  # Fixed: column is now 'id', not 'content_id'
                "content_type": node["content_type"],
                "title": node.get("title", ""),
                "depth": depth,
                "path": path,
            }

            if include_metadata and node.get("node_metadata"):
                try:
                    result["metadata"] = json.loads(node["node_metadata"])
                except json.JSONDecodeError:
                    result["metadata"] = {}

            formatted.append(result)

        return formatted

    def find_all_paths(
        self, source_content_id: str, target_content_id: str, max_paths: int = 5, max_depth: int = 5
    ) -> list[dict]:
        """Find multiple paths between two nodes.

        Returns paths sorted by length and cumulative strength.
        """
        source_node = self._get_node_by_content(source_content_id)
        target_node = self._get_node_by_content(target_content_id)

        if not source_node or not target_node:
            return []

        all_paths = []
        visited_paths = set()

        # Modified BFS to track all paths
        queue = deque([(source_node["node_id"], [source_content_id], 0.0, 0)])

        while queue and len(all_paths) < max_paths:
            current_id, path, strength_sum, depth = queue.popleft()

            if depth > max_depth:
                continue

            if current_id == target_node["node_id"]:
                path_tuple = tuple(path)
                if path_tuple not in visited_paths:
                    visited_paths.add(path_tuple)
                    all_paths.append(
                        {
                            "path": path,
                            "length": len(path),
                            "total_strength": strength_sum / max(len(path) - 1, 1),
                        }
                    )
                continue

            # Explore neighbors
            edges = self._get_edges_for_node(current_id)
            for edge in edges:
                next_id = (
                    edge["target_node_id"]
                    if edge["source_node_id"] == current_id
                    else edge["source_node_id"]
                )

                # Avoid cycles in current path
                next_node = self.db.fetch_one(
                    "SELECT id FROM kg_nodes WHERE node_id = ?", (next_id,)
                )

                if next_node and next_node["id"] not in path:
                    new_path = path + [next_node["id"]]
                    new_strength = strength_sum + edge.get("strength", 0.5)
                    queue.append((next_id, new_path, new_strength, depth + 1))

        # Sort by length first, then by strength
        all_paths.sort(key=lambda x: (x["length"], -x["total_strength"]))
        return all_paths

    def _get_edges_for_node(self, node_id: str) -> list[dict]:
        """
        Get all edges connected to a node.
        """
        return self.db.fetch(
            """
            SELECT * FROM kg_edges
            WHERE source_node_id = ? OR target_node_id = ?
            """,
            (node_id, node_id),
        )

    def calculate_pagerank(
        self, damping: float = 0.85, max_iterations: int = 100, epsilon: float = 0.0001
    ) -> dict[str, float]:
        """Calculate PageRank scores for all nodes in the graph.

        Returns dict mapping content_id to PageRank score.
        """
        # Get all nodes
        nodes = self.db.fetch("SELECT node_id, id FROM kg_nodes")
        if not nodes:
            return {}

        # Initialize scores
        n = len(nodes)
        scores = {node["node_id"]: 1.0 / n for node in nodes}
        node_to_content = {node["node_id"]: node["id"] for node in nodes}

        # Build adjacency lists
        outgoing_edges = defaultdict(list)
        incoming_edges = defaultdict(list)

        edges = self.db.fetch("SELECT source_node_id, target_node_id, strength FROM kg_edges")
        for edge in edges:
            outgoing_edges[edge["source_node_id"]].append(edge["target_node_id"])
            incoming_edges[edge["target_node_id"]].append(edge["source_node_id"])

        # Power iteration
        for iteration in range(max_iterations):
            new_scores = {}
            max_change = 0

            for node_id in scores:
                # Calculate new score
                rank = (1 - damping) / n

                for source_id in incoming_edges.get(node_id, []):
                    out_degree = len(outgoing_edges.get(source_id, []))
                    if out_degree > 0:
                        rank += damping * scores[source_id] / out_degree

                new_scores[node_id] = rank
                max_change = max(max_change, abs(new_scores[node_id] - scores[node_id]))

            scores = new_scores

            # Check convergence
            if max_change < epsilon:
                logger.info(f"PageRank converged after {iteration + 1} iterations")
                break

        # Normalize scores to sum to 1
        total = sum(scores.values())
        if total > 0:
            scores = {k: v / total for k, v in scores.items()}

        # Map to content IDs
        return {node_to_content[k]: v for k, v in scores.items()}

    def get_top_nodes_by_pagerank(self, limit: int = 10) -> list[dict]:
        """
        Get top nodes by PageRank score.
        """
        pagerank_scores = self.calculate_pagerank()

        # Sort by score
        sorted_nodes = sorted(pagerank_scores.items(), key=lambda x: x[1], reverse=True)[:limit]

        # Get full node information
        results = []
        for content_id, score in sorted_nodes:
            node = self._get_node_by_content(content_id)
            if node:
                results.append(
                    {
                        "content_id": content_id,
                        "content_type": node["content_type"],
                        "title": node.get("title", ""),
                        "pagerank_score": score,
                    }
                )

        return results

    def find_related_content(
        self,
        content_id: str,
        relationship_types: list[str] | None = None,
        max_depth: int = 2,
        limit: int = 20,
    ) -> list[dict]:
        """Find related content using BFS traversal.

        Scores by distance and relationship strength.
        """
        results = []
        seen_content = set()

        # Perform BFS traversal
        for node, depth, path in self.breadth_first_traversal(
            content_id, max_depth, relationship_types
        ):
            if node["id"] == content_id:
                continue  # Skip self

            if node["id"] not in seen_content:
                seen_content.add(node["id"])

                # Calculate relevance score (closer = higher score)
                distance_score = 1.0 / (depth + 1)

                # Get relationship strength if available
                if len(path) >= 2:
                    edge = self._get_edge_between_contents(path[-2], path[-1])
                    strength = edge.get("strength", 0.5) if edge else 0.5
                else:
                    strength = 0.5

                relevance_score = distance_score * strength

                results.append(
                    {
                        "content_id": node["id"],
                        "content_type": node["content_type"],
                        "title": node.get("title", ""),
                        "depth": depth,
                        "relevance_score": relevance_score,
                        "path": path,
                    }
                )

        # Sort by relevance score
        results.sort(key=lambda x: x["relevance_score"], reverse=True)
        return results[:limit]

    def get_timeline_context(
        self, content_id: str, window_days: int = 7, include_related: bool = True
    ) -> dict:
        """Get timeline context using temporal relationships.

        Integrates with timeline_relationships service.
        """
        # Get temporal edges
        node = self._get_node_by_content(content_id)
        if not node:
            return {"error": f"Content {content_id} not found"}

        # Find temporal relationships
        temporal_edges = self.db.fetch(
            """
            SELECT e.*, n1.id as source_content, n2.id as target_content,
                   n1.title as source_title, n2.title as target_title
            FROM kg_edges e
            JOIN kg_nodes n1 ON e.source_node_id = n1.node_id
            JOIN kg_nodes n2 ON e.target_node_id = n2.node_id
            WHERE (e.source_node_id = ? OR e.target_node_id = ?)
              AND e.relationship_type IN ('followed_by', 'preceded_by', 'concurrent_with')
            ORDER BY e.created_time
            """,
            (node["node_id"], node["node_id"]),
        )

        before = []
        after = []
        concurrent = []

        for edge in temporal_edges:
            if edge["relationship_type"] == "preceded_by":
                before.append(
                    {
                        "content_id": edge["source_content"],
                        "title": edge["source_title"],
                        "relationship": "preceded_by",
                    }
                )
            elif edge["relationship_type"] == "followed_by":
                after.append(
                    {
                        "content_id": edge["target_content"],
                        "title": edge["target_title"],
                        "relationship": "followed_by",
                    }
                )
            elif edge["relationship_type"] == "concurrent_with":
                other_content = (
                    edge["target_content"]
                    if edge["source_content"] == content_id
                    else edge["source_content"]
                )
                other_title = (
                    edge["target_title"]
                    if edge["source_content"] == content_id
                    else edge["source_title"]
                )
                concurrent.append(
                    {
                        "content_id": other_content,
                        "title": other_title,
                        "relationship": "concurrent_with",
                    }
                )

        result = {
            "target": {"content_id": content_id, "title": node.get("title", "")},
            "before": before,
            "after": after,
            "concurrent": concurrent,
        }

        # Include related content if requested
        if include_related:
            related = self.find_related_content(
                content_id, ["similar_to", "references"], max_depth=1, limit=5
            )
            result["related"] = related

        return result

    def discover_entity_networks(self, entity_name: str, min_cooccurrence: int = 2) -> dict:
        """Discover entity co-occurrence networks.

        Uses contains_entities edges from topic clustering.
        """
        # Find nodes that contain this entity
        nodes_with_entity = self.db.fetch(
            """
            SELECT DISTINCT n.*
            FROM kg_nodes n
            JOIN kg_edges e ON (n.node_id = e.source_node_id OR n.node_id = e.target_node_id)
            WHERE e.relationship_type = 'contains_entities'
              AND e.edge_metadata LIKE ?
            """,
            (f'%"{entity_name}"%',),
        )

        if not nodes_with_entity:
            return {"entity": entity_name, "network": [], "message": "No entity network found"}

        # Build co-occurrence map
        entity_counts = defaultdict(int)
        entity_docs = defaultdict(set)

        for node in nodes_with_entity:
            # Get all entities in this document
            edges = self.db.fetch(
                """
                SELECT edge_metadata
                FROM kg_edges
                WHERE (source_node_id = ? OR target_node_id = ?)
                  AND relationship_type = 'contains_entities'
                """,
                (node["node_id"], node["node_id"]),
            )

            for edge in edges:
                if edge["edge_metadata"]:
                    try:
                        metadata = json.loads(edge["edge_metadata"])
                        entities = metadata.get("entities", [])
                        for ent in entities:
                            if ent != entity_name:
                                entity_counts[ent] += 1
                                entity_docs[ent].add(node["id"])
                    except json.JSONDecodeError:
                        continue

        # Filter by minimum co-occurrence
        network = []
        for ent, count in entity_counts.items():
            if count >= min_cooccurrence:
                network.append(
                    {
                        "entity": ent,
                        "cooccurrence_count": count,
                        "shared_documents": list(entity_docs[ent])[:5],  # Limit for readability
                    }
                )

        # Sort by co-occurrence count
        network.sort(key=lambda x: x["cooccurrence_count"], reverse=True)

        return {
            "entity": entity_name,
            "network": network[:20],  # Top 20 co-occurring entities
            "total_documents": len(nodes_with_entity),
        }

    def _get_edge_between_contents(self, content1: str, content2: str) -> dict | None:
        """
        Get edge between two content items.
        """
        node1 = self._get_node_by_content(content1)
        node2 = self._get_node_by_content(content2)

        if not node1 or not node2:
            return None

        return self.db.fetch_one(
            """
            SELECT * FROM kg_edges
            WHERE (source_node_id = ? AND target_node_id = ?)
               OR (source_node_id = ? AND target_node_id = ?)
            """,
            (node1["node_id"], node2["node_id"], node2["node_id"], node1["node_id"]),
        )

    def _select_nodes_for_export(self, node_ids: list[str] | None = None) -> list[dict]:
        """Select nodes for export based on provided IDs or PageRank."""
        if node_ids:
            placeholders = ",".join(["?" for _ in node_ids])
            return self.db.fetch(
                f"SELECT * FROM kg_nodes WHERE node_id IN ({placeholders})", node_ids
            )
        else:
            # Export top nodes by PageRank
            pagerank_scores = self.calculate_pagerank()
            top_content = sorted(pagerank_scores.items(), key=lambda x: x[1], reverse=True)[:50]

            nodes = []
            for content_id, score in top_content:
                node = self._get_node_by_content(content_id)
                if node:
                    node["pagerank"] = score
                    nodes.append(node)
            return nodes
    
    def _filter_relevant_edges(self, node_ids_set: set[str]) -> list[dict]:
        """Filter edges to only include those between selected nodes."""
        edges = []
        for node_id in node_ids_set:
            node_edges = self.db.fetch(
                """
                SELECT * FROM kg_edges
                WHERE source_node_id = ? OR target_node_id = ?
                """,
                (node_id, node_id),
            )

            for edge in node_edges:
                # Only include edges where both nodes are in our set
                if (
                    edge["source_node_id"] in node_ids_set
                    and edge["target_node_id"] in node_ids_set
                ):
                    edges.append(edge)
        return edges

    def export_for_visualization(
        self, node_ids: list[str] | None = None, format: str = "d3"
    ) -> dict:
        """Export graph subset for visualization - simplified orchestrator.

        Default format is D3.js compatible JSON.
        """
        # Select nodes for export
        nodes = self._select_nodes_for_export(node_ids)
        
        if not nodes:
            return {"nodes": [], "links": []}

        node_ids_set = {n["node_id"] for n in nodes}
        
        # Get relevant edges
        edges = self._filter_relevant_edges(node_ids_set)

        # Format according to requested format
        if format == "d3":
            return self._format_for_d3(nodes, edges)
        else:
            # Raw format
            return {
                "nodes": [self._format_node_for_export(n) for n in nodes],
                "edges": [self._format_edge_for_export(e) for e in edges],
            }

    def _format_for_d3(self, nodes: list[dict], edges: list[dict]) -> dict:
        """
        Format graph data for D3.js visualization.
        """
        # Create node lookup
        node_lookup = {n["node_id"]: i for i, n in enumerate(nodes)}

        # Format nodes
        d3_nodes = []
        for node in nodes:
            d3_node = {
                "id": node["id"],
                "node_id": node["node_id"],
                "group": node["content_type"],
                "label": node.get("title", node["id"])[:50],
                "value": node.get("pagerank", 1.0) * 100,  # Size by PageRank
            }

            # Add metadata if present
            if node.get("node_metadata"):
                try:
                    d3_node["metadata"] = json.loads(node["node_metadata"])
                except json.JSONDecodeError:
                    pass

            d3_nodes.append(d3_node)

        # Format edges as links
        d3_links = []
        seen_links = set()

        for edge in edges:
            # Create unique link identifier
            link_id = tuple(sorted([edge["source_node_id"], edge["target_node_id"]]))
            if link_id not in seen_links:
                seen_links.add(link_id)

                if edge["source_node_id"] in node_lookup and edge["target_node_id"] in node_lookup:
                    d3_links.append(
                        {
                            "source": node_lookup[edge["source_node_id"]],
                            "target": node_lookup[edge["target_node_id"]],
                            "value": edge.get("strength", 0.5) * 10,
                            "type": edge["relationship_type"],
                        }
                    )

        return {
            "nodes": d3_nodes,
            "links": d3_links,
            "metadata": {
                "total_nodes": len(d3_nodes),
                "total_links": len(d3_links),
                "relationship_types": list({e["relationship_type"] for e in edges}),
            },
        }

    def _format_node_for_export(self, node: dict) -> dict:
        """
        Format node for export.
        """
        return {
            "node_id": node["node_id"],
            "content_id": node["id"],
            "content_type": node["content_type"],
            "title": node.get("title", ""),
            "created_time": node.get("created_time", ""),
            "pagerank": node.get("pagerank", 0),
        }

    def _format_edge_for_export(self, edge: dict) -> dict:
        """
        Format edge for export.
        """
        return {
            "edge_id": edge["edge_id"],
            "source": edge["source_node_id"],
            "target": edge["target_node_id"],
            "type": edge["relationship_type"],
            "strength": edge.get("strength", 0.5),
        }


def get_graph_query_service(db_path: str = "data/emails.db") -> GraphQueryService:
    """
    Get singleton instance of GraphQueryService.
    """
    global _graph_query_service
    if _graph_query_service is None:
        _graph_query_service = GraphQueryService(db_path)
    return _graph_query_service
