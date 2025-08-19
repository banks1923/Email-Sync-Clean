"""Knowledge Graph Service for Email Sync System.

Simple, flat implementation for building content relationship maps.
Follows CLAUDE.md principles: under 450 lines, direct patterns, no
enterprise abstractions.
"""

import json
import uuid
from datetime import datetime

from loguru import logger

from shared.simple_db import SimpleDB

# Logger is now imported globally from loguru


class KnowledgeGraphService:
    """
    Knowledge graph for content relationships using SQLite JSON storage.
    """

    def __init__(self, db_path: str = "emails.db"):
        self.db = SimpleDB(db_path)
        self.db_path = db_path
        self._ensure_schema()

    def _ensure_schema(self):
        """
        Create knowledge graph tables if they don't exist.
        """
        try:
            self._create_tables()
            self._create_indexes()
        except Exception as e:
            logger.error(f"Error creating knowledge graph schema: {e}")
            raise

    def _create_tables(self):
        """
        Create the main knowledge graph tables.
        """
        self._create_nodes_table()
        self._create_edges_table()
        self._create_metadata_table()

    def _create_nodes_table(self):
        """
        Create the kg_nodes table.
        """
        self.db.execute(
            """
            CREATE TABLE IF NOT EXISTS kg_nodes (
                node_id TEXT PRIMARY KEY, content_id TEXT NOT NULL,
                content_type TEXT NOT NULL, title TEXT,
                node_metadata TEXT, created_time TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (content_id) REFERENCES content(content_id)
            )
        """
        )

    def _create_edges_table(self):
        """
        Create the kg_edges table.
        """
        self.db.execute(
            """
            CREATE TABLE IF NOT EXISTS kg_edges (
                edge_id TEXT PRIMARY KEY, source_node_id TEXT NOT NULL,
                target_node_id TEXT NOT NULL, relationship_type TEXT NOT NULL,
                strength REAL DEFAULT 0.0, edge_metadata TEXT,
                created_time TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (source_node_id) REFERENCES kg_nodes(node_id),
                FOREIGN KEY (target_node_id) REFERENCES kg_nodes(node_id)
            )
        """
        )

    def _create_metadata_table(self):
        """
        Create the kg_metadata table.
        """
        self.db.execute(
            """
            CREATE TABLE IF NOT EXISTS kg_metadata (
                key TEXT PRIMARY KEY, value TEXT,
                updated_time TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """
        )

    def _create_indexes(self):
        """
        Create performance indexes for knowledge graph tables.
        """
        indexes = [
            "CREATE INDEX IF NOT EXISTS idx_kg_nodes_content ON kg_nodes(content_id)",
            "CREATE INDEX IF NOT EXISTS idx_kg_nodes_type ON kg_nodes(content_type)",
            "CREATE INDEX IF NOT EXISTS idx_kg_edges_source ON kg_edges(source_node_id)",
            "CREATE INDEX IF NOT EXISTS idx_kg_edges_target ON kg_edges(target_node_id)",
            "CREATE INDEX IF NOT EXISTS idx_kg_edges_type ON kg_edges(relationship_type)",
        ]
        for index_sql in indexes:
            self.db.execute(index_sql)

    # Node operations
    def add_node(
        self, content_id: str, content_type: str, title: str = None, metadata: dict = None
    ) -> str:
        """Add a node to the knowledge graph.

        Returns node_id.
        """
        node_id = str(uuid.uuid4())
        metadata_json = json.dumps(metadata) if metadata else None

        self.db.execute(
            """
            INSERT OR IGNORE INTO kg_nodes
            (node_id, content_id, content_type, title, node_metadata)
            VALUES (?, ?, ?, ?, ?)
        """,
            (node_id, content_id, content_type, title, metadata_json),
        )

        logger.debug(f"Added node {node_id} for content {content_id}")
        return node_id

    def get_node_by_content(self, content_id: str) -> dict | None:
        """
        Get node by content_id.
        """
        result = self.db.fetch_one("SELECT * FROM kg_nodes WHERE content_id = ?", (content_id,))
        if result and result.get("node_metadata"):
            try:
                result["node_metadata"] = json.loads(result["node_metadata"])
            except (json.JSONDecodeError, TypeError):
                result["node_metadata"] = None
        return result

    def get_node(self, node_id: str) -> dict | None:
        """
        Get node by node_id.
        """
        result = self.db.fetch_one("SELECT * FROM kg_nodes WHERE node_id = ?", (node_id,))
        if result and result.get("node_metadata"):
            try:
                result["node_metadata"] = json.loads(result["node_metadata"])
            except (json.JSONDecodeError, TypeError):
                result["node_metadata"] = None
        return result

    # Edge operations
    def add_edge(
        self,
        source_content_id: str,
        target_content_id: str,
        relationship_type: str,
        strength: float = 0.0,
        metadata: dict = None,
    ) -> str:
        """Add an edge between two content items.

        Returns edge_id.
        """
        source_node_id = self._get_or_create_node(source_content_id)
        target_node_id = self._get_or_create_node(target_content_id)

        if not source_node_id or not target_node_id:
            return None

        edge_id = str(uuid.uuid4())
        metadata_json = json.dumps(metadata) if metadata else None

        self.db.execute(
            """
            INSERT OR IGNORE INTO kg_edges
            (edge_id, source_node_id, target_node_id, relationship_type, strength, edge_metadata)
            VALUES (?, ?, ?, ?, ?, ?)
        """,
            (edge_id, source_node_id, target_node_id, relationship_type, strength, metadata_json),
        )

        logger.debug(f"Added edge {edge_id}: {relationship_type} ({strength})")
        return edge_id

    def _get_or_create_node(self, content_id: str) -> str | None:
        """Get existing node or create new one.

        Returns node_id.
        """
        node = self.get_node_by_content(content_id)
        if node:
            return node["node_id"]

        # Create new node
        content = self.db.get_content(content_id)
        if content:
            return self.add_node(content_id, content["type"], content.get("title"))
        else:
            logger.error(f"Cannot find content {content_id}")
            return None

    def get_edges_by_node(self, node_id: str, direction: str = "both") -> list[dict]:
        """Get edges connected to a node.

        Direction: 'outgoing', 'incoming', or 'both'.
        """
        if direction == "outgoing":
            query = "SELECT * FROM kg_edges WHERE source_node_id = ?"
            params = (node_id,)
        elif direction == "incoming":
            query = "SELECT * FROM kg_edges WHERE target_node_id = ?"
            params = (node_id,)
        else:  # both
            query = "SELECT * FROM kg_edges WHERE source_node_id = ? OR target_node_id = ?"
            params = (node_id, node_id)

        results = self.db.fetch(query, params)
        for result in results:
            if result.get("edge_metadata"):
                try:
                    result["edge_metadata"] = json.loads(result["edge_metadata"])
                except (json.JSONDecodeError, TypeError):
                    result["edge_metadata"] = None
        return results

    def get_related_content(
        self, content_id: str, relationship_types: list[str] = None, limit: int = 50
    ) -> list[dict]:
        """
        Get content items related to the given content_id.
        """
        node = self.get_node_by_content(content_id)
        if not node:
            return []

        query = self._build_related_content_query(relationship_types)
        params = self._build_related_content_params(content_id, relationship_types, limit)

        return self.db.fetch(query, tuple(params))

    def _build_related_content_query(self, relationship_types: list[str] = None) -> str:
        """
        Build SQL query for related content.
        """
        base_query = """
            SELECT DISTINCT c.*, e.relationship_type, e.strength
            FROM kg_edges e
            JOIN kg_nodes n1 ON (e.source_node_id = n1.node_id OR e.target_node_id = n1.node_id)
            JOIN kg_nodes n2 ON (
                (e.source_node_id = n2.node_id AND n1.node_id != n2.node_id) OR
                (e.target_node_id = n2.node_id AND n1.node_id != n2.node_id)
            )
            JOIN content c ON n2.content_id = c.content_id
            WHERE n1.content_id = ?
        """

        if relationship_types:
            placeholders = ",".join(["?"] * len(relationship_types))
            base_query += f" AND e.relationship_type IN ({placeholders})"

        return base_query + " ORDER BY e.strength DESC, e.created_time DESC LIMIT ?"

    def _build_related_content_params(
        self, content_id: str, relationship_types: list[str], limit: int
    ) -> list:
        """
        Build parameters for related content query.
        """
        params = [content_id]
        if relationship_types:
            params.extend(relationship_types)
        params.append(limit)
        return params

    # Batch operations for performance
    def batch_add_nodes(self, node_data: list[dict], batch_size: int = 1000) -> dict:
        """
        Batch add nodes for better performance.
        """
        if not node_data:
            return {"total": 0, "inserted": 0, "ignored": 0}

        # Prepare data tuples
        prepared_data = []
        for item in node_data:
            node_id = item.get("node_id", str(uuid.uuid4()))
            metadata_json = json.dumps(item.get("metadata")) if item.get("metadata") else None
            prepared_data.append(
                (
                    node_id,
                    item["content_id"],
                    item["content_type"],
                    item.get("title"),
                    metadata_json,
                )
            )

        columns = ["node_id", "content_id", "content_type", "title", "node_metadata"]
        return self.db.batch_insert("kg_nodes", columns, prepared_data, batch_size)

    def batch_add_edges(self, edge_data: list[dict], batch_size: int = 1000) -> dict:
        """
        Batch add edges for better performance.
        """
        if not edge_data:
            return {"total": 0, "inserted": 0, "ignored": 0}

        # Prepare data tuples
        prepared_data = []
        for item in edge_data:
            edge_id = item.get("edge_id", str(uuid.uuid4()))
            metadata_json = json.dumps(item.get("metadata")) if item.get("metadata") else None
            prepared_data.append(
                (
                    edge_id,
                    item["source_node_id"],
                    item["target_node_id"],
                    item["relationship_type"],
                    item.get("strength", 0.0),
                    metadata_json,
                )
            )

        columns = [
            "edge_id",
            "source_node_id",
            "target_node_id",
            "relationship_type",
            "strength",
            "edge_metadata",
        ]
        return self.db.batch_insert("kg_edges", columns, prepared_data, batch_size)

    # Graph statistics and metadata
    def get_graph_stats(self) -> dict:
        """
        Get knowledge graph statistics.
        """
        stats = {}
        stats["total_nodes"] = self.db.fetch_one("SELECT COUNT(*) as count FROM kg_nodes")["count"]
        stats["total_edges"] = self.db.fetch_one("SELECT COUNT(*) as count FROM kg_edges")["count"]

        # Content type distribution
        content_types = self.db.fetch(
            """
            SELECT content_type, COUNT(*) as count
            FROM kg_nodes
            GROUP BY content_type
        """
        )
        stats["content_types"] = {row["content_type"]: row["count"] for row in content_types}

        # Relationship type distribution
        rel_types = self.db.fetch(
            """
            SELECT relationship_type, COUNT(*) as count
            FROM kg_edges
            GROUP BY relationship_type
        """
        )
        stats["relationship_types"] = {row["relationship_type"]: row["count"] for row in rel_types}

        return stats

    def set_metadata(self, key: str, value: any):
        """
        Store graph-level metadata.
        """
        value_json = json.dumps(value) if not isinstance(value, str) else value
        self.db.execute(
            """
            INSERT OR REPLACE INTO kg_metadata (key, value, updated_time)
            VALUES (?, ?, ?)
        """,
            (key, value_json, datetime.now().isoformat()),
        )

    def get_metadata(self, key: str) -> any:
        """
        Get graph-level metadata.
        """
        result = self.db.fetch_one("SELECT value FROM kg_metadata WHERE key = ?", (key,))
        if result:
            try:
                return json.loads(result["value"])
            except json.JSONDecodeError:
                return result["value"]
        return None

    # Simple graph queries
    def find_shortest_path(
        self, source_content_id: str, target_content_id: str, max_depth: int = 5
    ) -> list[str] | None:
        """Find shortest path between two content items.

        Returns list of content_ids.
        """
        source_node = self.get_node_by_content(source_content_id)
        target_node = self.get_node_by_content(target_content_id)

        if not source_node or not target_node:
            return None

        return self._breadth_first_search(source_node, target_node, max_depth)

    def _breadth_first_search(
        self, source_node: dict, target_node: dict, max_depth: int
    ) -> list[str] | None:
        """
        Perform breadth-first search between nodes.
        """
        visited = set()
        queue = [(source_node["node_id"], [source_node["content_id"]])]

        while queue and len(queue[0][1]) <= max_depth:
            current_node_id, path = queue.pop(0)

            if current_node_id in visited:
                continue
            visited.add(current_node_id)

            if current_node_id == target_node["node_id"]:
                return path

            self._add_neighbors_to_queue(current_node_id, path, visited, queue)

        return None

    def _add_neighbors_to_queue(
        self, current_node_id: str, path: list[str], visited: set[str], queue: list[tuple]
    ) -> None:
        """
        Add neighboring nodes to the search queue.
        """
        edges = self.get_edges_by_node(current_node_id)
        for edge in edges:
            next_node_id = (
                edge["target_node_id"]
                if edge["source_node_id"] == current_node_id
                else edge["source_node_id"]
            )

            if next_node_id not in visited:
                next_node = self.get_node(next_node_id)
                if next_node:
                    new_path = path + [next_node["content_id"]]
                    queue.append((next_node_id, new_path))


# Factory function for consistent service access
def get_knowledge_graph_service(db_path: str = "emails.db") -> KnowledgeGraphService:
    """
    Get knowledge graph service instance.
    """
    return KnowledgeGraphService(db_path)
