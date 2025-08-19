"""
Qdrant operations - store and search vectors ONLY.
No complexity. Just vector storage.
"""

import uuid
from typing import Any

from loguru import logger
from qdrant_client import QdrantClient
from qdrant_client.models import (
    Distance,
    FieldCondition,
    Filter,
    MatchValue,
    PointStruct,
    VectorParams,
)

# Logger is now imported globally from loguru


class VectorStore:
    """Simple vector storage with Qdrant."""

    def __init__(self, host: str = "localhost", port: int = 6333, collection: str = "emails"):
        """Initialize connection to Qdrant."""
        self.host = host
        self.port = port
        self.collection = collection
        self.client = None
        self.dimensions = 1024  # Legal BERT dimensions
        self._connect()

    def _connect(self):
        """Connect to Qdrant."""
        try:
            self.client = QdrantClient(host=self.host, port=self.port)
            self._ensure_collection()
            logger.info(f"Connected to Qdrant at {self.host}:{self.port}")
        except Exception as e:
            logger.error(f"Failed to connect to Qdrant: {e}")
            raise

    def _ensure_collection(self):
        """Create collection if it doesn't exist."""
        try:
            self.client.get_collection(self.collection)
            logger.info(f"Collection '{self.collection}' exists")
        except Exception:
            logger.info(f"Creating collection '{self.collection}'")
            self.client.create_collection(
                collection_name=self.collection,
                vectors_config=VectorParams(size=self.dimensions, distance=Distance.COSINE),
            )

    def upsert(self, vector: list[float], payload: dict[str, Any] = None, id: str = None) -> str:
        """Store vector with metadata."""
        if id is None:
            id = str(uuid.uuid4())

        point = PointStruct(id=id, vector=vector, payload=payload or {})

        self.client.upsert(collection_name=self.collection, points=[point])

        return id

    def batch_upsert(
        self, vectors: list[list[float]], payloads: list[dict] = None, ids: list[str] = None
    ):
        """Batch insert vectors."""
        if ids is None:
            ids = [str(uuid.uuid4()) for _ in vectors]
        if payloads is None:
            payloads = [{} for _ in vectors]

        points = [
            PointStruct(id=id, vector=vector, payload=payload)
            for id, vector, payload in zip(ids, vectors, payloads)
        ]

        self.client.upsert(collection_name=self.collection, points=points)

        return ids

    def search(self, vector: list[float], limit: int = 10, filter: dict = None) -> list[dict]:
        """Search for similar vectors."""
        search_params = {"collection_name": self.collection, "query_vector": vector, "limit": limit}

        # Add filter if provided
        if filter:
            qdrant_filter = self._build_filter(filter)
            if qdrant_filter:
                search_params["query_filter"] = qdrant_filter

        results = self.client.search(**search_params)

        return [{"id": hit.id, "score": hit.score, "payload": hit.payload} for hit in results]

    def _build_filter(self, filter_dict: dict) -> Filter | None:
        """Build Qdrant filter from simple dict."""
        if not filter_dict:
            return None

        conditions = []
        for key, value in filter_dict.items():
            conditions.append(FieldCondition(key=key, match=MatchValue(value=value)))

        if conditions:
            return Filter(must=conditions)
        return None

    def get(self, id: str) -> dict | None:
        """Get vector by ID."""
        try:
            points = self.client.retrieve(
                collection_name=self.collection, ids=[id], with_vectors=True
            )
            if points:
                point = points[0]
                return {"id": point.id, "vector": point.vector, "payload": point.payload}
        except Exception:
            return None

    def delete(self, id: str):
        """Delete vector by ID."""
        self.client.delete(collection_name=self.collection, points_selector=[id])

    def delete_many(self, ids: list[str]):
        """Delete multiple vectors."""
        self.client.delete(collection_name=self.collection, points_selector=ids)

    def count(self) -> int:
        """Get total number of vectors."""
        info = self.client.get_collection(self.collection)
        return info.points_count

    def clear(self):
        """Delete all vectors in collection."""
        self.client.delete_collection(self.collection)
        self._ensure_collection()


# Singleton pattern - reuse connection
_vector_store: VectorStore | None = None


def get_vector_store(collection: str = "emails") -> VectorStore:
    """Get or create singleton vector store."""
    global _vector_store
    if _vector_store is None or _vector_store.collection != collection:
        _vector_store = VectorStore(collection=collection)
    return _vector_store
