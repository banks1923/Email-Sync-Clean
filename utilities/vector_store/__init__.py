"""
Qdrant operations - store and search vectors ONLY.
No complexity. Just vector storage.
"""

import time
import uuid
from typing import Any
from collections.abc import Generator

from loguru import logger
from qdrant_client import QdrantClient
from qdrant_client.models import (
    Distance,
    FieldCondition,
    Filter,
    MatchAny,
    MatchValue,
    PointIdsList,
    PointStruct,
    Range,
    VectorParams,
)

# Logger is now imported globally from loguru


class VectorStore:
    """Simple vector storage with Qdrant."""

    def __init__(self, host: str = "localhost", port: int = 6333, collection: str = "emails", dimensions: int = 1024):
        """Initialize connection to Qdrant."""
        self.host = host
        self.port = port
        self.collection = collection
        self.client = None
        self.dimensions = dimensions
        self._connect()

    def _connect(self):
        """Connect to Qdrant with retry logic."""
        for attempt in range(2):
            try:
                self.client = QdrantClient(host=self.host, port=self.port, timeout=10.0)
                self._ensure_collection()
                logger.info(f"Connected to Qdrant at {self.host}:{self.port} collection={self.collection}")
                return
            except Exception as e:
                if attempt == 0:
                    logger.warning(f"Connection attempt {attempt + 1} failed, retrying in 0.5s: {e}")
                    time.sleep(0.5)
                else:
                    logger.error(f"Failed to connect to Qdrant (required for vector operations): {e}")
                    raise

    def _ensure_collection(self):
        """Create collection if it doesn't exist, validate dimensions."""
        try:
            info = self.client.get_collection(self.collection)
            # Validate dimensions match
            if hasattr(info.config, 'params') and hasattr(info.config.params, 'vectors'):
                existing_size = info.config.params.vectors.size
                if existing_size != self.dimensions:
                    raise ValueError(f"Collection {self.collection} has dimensions {existing_size}, expected {self.dimensions}")
            logger.info(f"Collection '{self.collection}' exists with {self.dimensions}D vectors")
        except Exception as e:
            if "not found" in str(e).lower() or "does not exist" in str(e).lower():
                logger.info(f"Creating collection '{self.collection}' with {self.dimensions}D vectors")
                self.client.create_collection(
                    collection_name=self.collection,
                    vectors_config=VectorParams(size=self.dimensions, distance=Distance.COSINE),
                )
            else:
                raise

    def upsert(self, vector: list[float], payload: dict[str, Any] = None, id: str = None) -> str:
        """Store vector with metadata."""
        if len(vector) != self.dimensions:
            raise ValueError(f"Vector size {len(vector)} != {self.dimensions}")
            
        if id is None:
            id = str(uuid.uuid4())

        point = PointStruct(id=id, vector=vector, payload=payload or {})

        self.client.upsert(collection_name=self.collection, points=[point])

        return id

    def _original_batch_upsert(
        self, vectors: list[list[float]], payloads: list[dict] = None, ids: list[str] = None
    ):
        """Original batch insert vectors method."""
        if ids is None:
            ids = [str(uuid.uuid4()) for _ in vectors]
        if payloads is None:
            payloads = [{} for _ in vectors]

        # Validate vector dimensions
        for vector in vectors:
            if len(vector) != self.dimensions:
                raise ValueError(f"Vector size {len(vector)} != {self.dimensions}")

        points = [
            PointStruct(id=id, vector=vector, payload=payload)
            for id, vector, payload in zip(ids, vectors, payloads)
        ]

        self.client.upsert(collection_name=self.collection, points=points)

        return ids

    def search(self, vector: list[float], limit: int = 10, filter: dict = None, 
               score_threshold: float | None = None, with_payload: bool = True, 
               with_vectors: bool = False, vector_name: str | None = None) -> list[dict]:
        """Search for similar vectors with enhanced options."""
        search_params = {
            "collection_name": self.collection, 
            "query_vector": vector, 
            "limit": limit,
            "with_payload": with_payload,
            "with_vectors": with_vectors
        }

        # Add score threshold if provided
        if score_threshold is not None:
            search_params["score_threshold"] = score_threshold

        # Add vector name if provided (for named vectors)
        if vector_name:
            search_params["using"] = vector_name

        # Add filter if provided
        if filter:
            qdrant_filter = self._build_filter(filter)
            if qdrant_filter:
                search_params["query_filter"] = qdrant_filter

        results = self.client.search(**search_params)

        return [{"id": hit.id, "score": hit.score, "payload": hit.payload, 
                 "vector": getattr(hit, "vector", None) if with_vectors else None} for hit in results]

    def _build_filter(self, filter_dict: dict) -> Filter | None:
        """Build Qdrant filter from dict with enhanced support."""
        if not filter_dict:
            return None

        # Support structured filter format
        if any(k in filter_dict for k in ["must", "should", "must_not"]):
            return self._build_structured_filter(filter_dict)

        # Simple conditions
        conditions = []
        for key, value in filter_dict.items():
            if isinstance(value, dict):
                # Range queries: {"key": "timestamp", "gt": 123, "lt": 456}
                if any(op in value for op in ["gt", "gte", "lt", "lte"]):
                    range_condition = {}
                    for op, val in value.items():
                        if op in ["gt", "gte", "lt", "lte"]:
                            range_condition[op] = val
                    conditions.append(FieldCondition(key=key, range=Range(**range_condition)))
                # Any match: {"key": "type", "any": ["email", "pdf"]}
                elif "any" in value:
                    conditions.append(FieldCondition(key=key, match=MatchAny(any=value["any"])))
                else:
                    conditions.append(FieldCondition(key=key, match=MatchValue(value=value)))
            elif isinstance(value, list):
                # List as any match
                conditions.append(FieldCondition(key=key, match=MatchAny(any=value)))
            else:
                conditions.append(FieldCondition(key=key, match=MatchValue(value=value)))

        if conditions:
            return Filter(must=conditions)
        return None

    def _build_structured_filter(self, filter_dict: dict) -> Filter:
        """Build structured filter from must/should/must_not format."""
        filter_params = {}
        
        for filter_type in ["must", "should", "must_not"]:
            if filter_type in filter_dict:
                conditions = []
                for condition in filter_dict[filter_type]:
                    if isinstance(condition, dict) and len(condition) == 1:
                        key, value = next(iter(condition.items()))
                        if isinstance(value, list):
                            conditions.append(FieldCondition(key=key, match=MatchAny(any=value)))
                        else:
                            conditions.append(FieldCondition(key=key, match=MatchValue(value=value)))
                if conditions:
                    filter_params[filter_type] = conditions
        
        return Filter(**filter_params)

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
        self.client.delete(collection_name=self.collection, points_selector=PointIdsList(points=[id]))
    
    def delete_vector(self, id: str, collection: str | None = None):
        """Delete vector by ID with optional collection override.
        
        Args:
            id: Vector ID to delete
            collection: Optional collection name (uses instance collection if not provided)
        """
        collection or self.collection
        
        if collection and collection != self.collection:
            # Create new store instance for different collection
            temp_store = VectorStore(
                host=self.host, 
                port=self.port, 
                collection=collection, 
                dimensions=self.dimensions
            )
            temp_store.delete(id)
        else:
            self.delete(id)

    def delete_many(self, ids: list[str]):
        """Delete multiple vectors."""
        self.client.delete(collection_name=self.collection, points_selector=PointIdsList(points=ids))

    def count(self) -> int:
        """Get total number of vectors."""
        info = self.client.get_collection(self.collection)
        return getattr(info, "points_count", None) or getattr(info, "vectors_count", 0)

    def clear(self):
        """Delete all vectors in collection."""
        self.client.delete_collection(self.collection)
        self._ensure_collection()
    
    # API alignment methods for maintenance code
    def add_email_vector(self, email_id: str, embedding: list[float], metadata: dict[str, Any]) -> str:
        """Add email vector - wrapper for upsert with email-specific naming."""
        return self.upsert(vector=embedding, payload=metadata, id=email_id)
    
    def add_vector(self, id: str, embedding: list[float], metadata: dict[str, Any], collection: str | None = None) -> str:
        """Add vector with optional collection override."""
        if collection and collection != self.collection:
            # Create new store instance for different collection
            temp_store = VectorStore(
                host=self.host, 
                port=self.port, 
                collection=collection, 
                dimensions=self.dimensions
            )
            return temp_store.upsert(vector=embedding, payload=metadata, id=id)
        return self.upsert(vector=embedding, payload=metadata, id=id)
    
    def batch_upsert(self, collection: str | None, points: list[dict]) -> list[str]:
        """Batch upsert with points format: [{'id', 'vector', 'metadata'}]."""
        
        if collection and collection != self.collection:
            # Create new store instance for different collection
            temp_store = VectorStore(
                host=self.host, 
                port=self.port, 
                collection=collection, 
                dimensions=self.dimensions
            )
            return temp_store._batch_upsert_points(points)
        
        # Fix method name collision - use original batch_upsert
        vectors = []
        payloads = []
        ids = []
        
        for point in points:
            ids.append(point['id'])
            vectors.append(point['vector'])
            payloads.append(point.get('metadata', {}))
        
        # Call original batch_upsert method
        return self._original_batch_upsert(vectors=vectors, payloads=payloads, ids=ids)
    
    def _batch_upsert_points(self, points: list[dict]) -> list[str]:
        """Internal batch upsert for points format."""
        vectors = []
        payloads = []
        ids = []
        
        for point in points:
            ids.append(point['id'])
            vectors.append(point['vector'])
            payloads.append(point.get('metadata', {}))
        
        # Validate vector dimensions
        for vector in vectors:
            if len(vector) != self.dimensions:
                raise ValueError(f"Vector size {len(vector)} != {self.dimensions}")
        
        # Create points and upsert directly
        points_list = [
            PointStruct(id=id, vector=vector, payload=payload)
            for id, vector, payload in zip(ids, vectors, payloads)
        ]
        
        self.client.upsert(collection_name=self.collection, points=points_list)
        return ids
    
    def list_all_ids(self, collection: str | None = None) -> list[str]:
        """List all vector IDs in collection."""
        target_collection = collection or self.collection
        all_ids = []
        for page_ids in self.iter_ids(collection=target_collection):
            all_ids.extend(page_ids)
        return all_ids
    
    def iter_ids(self, collection: str | None = None, page_size: int = 1000) -> Generator[list[str], None, None]:
        """Iterate through vector IDs in pages to avoid loading all at once."""
        target_collection = collection or self.collection
        next_page = None
        
        while True:
            try:
                page = self.client.scroll(
                    collection_name=target_collection,
                    limit=page_size,
                    with_payload=False,
                    with_vectors=False,
                    offset=next_page
                )
                points, next_page = page
                
                if not points:
                    break
                    
                yield [str(p.id) for p in points]
                
                if next_page is None:
                    break
            except Exception as e:
                logger.error(f"Error iterating IDs for {target_collection}: {e}")
                break
    
    def health(self) -> bool:
        """Check if Qdrant is healthy and accessible."""
        try:
            self.client.get_collections()
            return True
        except Exception as e:
            logger.error(f"Qdrant health check failed: {e}")
            return False
    
    def get_collection_stats(self, collection: str | None = None) -> dict:
        """Get collection statistics (normalized).
        
        Args:
            collection: Optional collection name (uses instance collection if not provided)
        
        Returns dict with points_count and compatibility aliases.
        """
        target_collection = collection or self.collection
        
        try:
            if collection and collection != self.collection:
                # Create new store instance for different collection
                temp_store = VectorStore(
                    host=self.host, 
                    port=self.port, 
                    collection=collection, 
                    dimensions=self.dimensions
                )
                return temp_store.get_collection_stats()
            
            info = self.client.get_collection(self.collection)
            points = getattr(info, "points_count", None)
            if points is None:
                points = getattr(info, "vectors_count", 0)
            if points is None:
                points = 0
            return {
                "points_count": points,
                "vectors_count": points,       # alias for compatibility
                "indexed_vectors": points,     # alias for dashboards
            }
        except Exception as e:
            # Collection doesn't exist or other error
            logger.debug(f"Collection {target_collection} stats unavailable: {e}")
            return {
                "points_count": 0,
                "vectors_count": 0,
                "indexed_vectors": 0,
            }


# Singleton pattern - reuse connection
_vector_store: VectorStore | None = None


def get_vector_store(collection: str = "emails") -> VectorStore:
    """Get or create singleton vector store."""
    global _vector_store
    if _vector_store is None or _vector_store.collection != collection:
        _vector_store = VectorStore(collection=collection)
    return _vector_store
