"""Document Similarity Analysis for Knowledge Graph.

Uses Legal BERT embeddings to compute document similarity and create
relationships. Follows CLAUDE.md principles: simple, direct
implementation under 450 lines.
"""

import hashlib
import time

import numpy as np
from loguru import logger

from shared.simple_db import SimpleDB
from utilities.embeddings import get_embedding_service

# Logger is now imported globally from loguru


class SimilarityAnalyzer:
    """
    Compute document similarity using Legal BERT embeddings.
    """

    def __init__(self, db_path: str = "data/emails.db", similarity_threshold: float = 0.7):
        self.db = SimpleDB(db_path)
        self.embedding_service = get_embedding_service()
        self.similarity_threshold = similarity_threshold
        self.cache = {}  # In-memory cache for computed similarities
        self._setup_cache_table()

    def _setup_cache_table(self):
        """
        Create similarity cache table for persistence.
        """
        self.db.execute(
            """
            CREATE TABLE IF NOT EXISTS similarity_cache (
                content_pair_hash TEXT PRIMARY KEY,
                content_id_1 TEXT NOT NULL,
                content_id_2 TEXT NOT NULL,
                similarity_score REAL NOT NULL,
                computation_time REAL NOT NULL,
                created_time TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """
        )

        # Index for efficient lookups
        self.db.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_similarity_cache_ids
            ON similarity_cache(content_id_1, content_id_2)
        """
        )

    def compute_similarity(self, content_id_1: str, content_id_2: str) -> float | None:
        """
        Compute cosine similarity between two content items.
        """
        if content_id_1 == content_id_2:
            return 1.0

        # Check cache first
        cached = self._get_cached_similarity(content_id_1, content_id_2)
        if cached is not None:
            return cached

        # Get content and compute embeddings
        content_1 = self.db.get_content(content_id_1)
        content_2 = self.db.get_content(content_id_2)

        if not content_1 or not content_2:
            logger.warning(f"Missing content: {content_id_1} or {content_id_2}")
            return None

        start_time = time.time()

        # Get embeddings
        embedding_1 = self.embedding_service.encode(content_1["body"])
        embedding_2 = self.embedding_service.encode(content_2["body"])

        # Compute cosine similarity
        similarity = self._cosine_similarity(embedding_1, embedding_2)

        computation_time = time.time() - start_time

        # Cache the result
        self._cache_similarity(content_id_1, content_id_2, similarity, computation_time)

        logger.debug(
            f"Similarity {content_id_1} <-> {content_id_2}: {similarity:.3f} "
            f"({computation_time:.2f}s)"
        )

        return similarity

    def _cosine_similarity(self, vec1: np.ndarray, vec2: np.ndarray) -> float:
        """
        Compute cosine similarity between two vectors.
        """
        # Handle zero vectors
        norm1 = np.linalg.norm(vec1)
        norm2 = np.linalg.norm(vec2)

        if norm1 == 0 or norm2 == 0:
            return 0.0

        return np.dot(vec1, vec2) / (norm1 * norm2)

    def batch_compute_similarities(
        self, content_ids: list[str], batch_size: int = 50
    ) -> list[tuple[str, str, float]]:
        """
        Compute similarities for all pairs in a list of content IDs.
        """
        similarities = []
        total_pairs = len(content_ids) * (len(content_ids) - 1) // 2
        processed = 0

        logger.info(
            f"Computing similarities for {len(content_ids)} documents " f"({total_pairs} pairs)"
        )

        for i, content_id_1 in enumerate(content_ids):
            for j, content_id_2 in enumerate(content_ids[i + 1 :], i + 1):
                similarity = self.compute_similarity(content_id_1, content_id_2)

                if similarity is not None and similarity >= self.similarity_threshold:
                    similarities.append((content_id_1, content_id_2, similarity))

                processed += 1

                # Progress logging
                if processed % 100 == 0:
                    progress = (processed / total_pairs) * 100
                    logger.info(
                        f"Similarity computation progress: {progress:.1f}% "
                        f"({processed}/{total_pairs})"
                    )

        logger.info(
            f"Found {len(similarities)} similar pairs above threshold "
            f"{self.similarity_threshold}"
        )

        return similarities

    def find_similar_content(self, content_id: str, limit: int = 20) -> list[dict]:
        """
        Find content items similar to the given content_id.
        """
        # Get all content IDs except the target
        all_content = self.db.fetch(
            "SELECT id FROM content_unified WHERE id != ?", (content_id,)
        )

        similarities = []

        for row in all_content:
            other_id = row["id"]  # Fixed: column is 'id', not 'content_id'
            similarity = self.compute_similarity(content_id, other_id)

            if similarity is not None and similarity >= self.similarity_threshold:
                similarities.append({"content_id": other_id, "similarity": similarity})

        # Sort by similarity (highest first) and limit results
        similarities.sort(key=lambda x: x["similarity"], reverse=True)
        return similarities[:limit]

    def _get_cached_similarity(self, content_id_1: str, content_id_2: str) -> float | None:
        """
        Get cached similarity score, checking both orderings.
        """
        pair_hash = self._hash_content_pair(content_id_1, content_id_2)

        # Check in-memory cache first
        if pair_hash in self.cache:
            return self.cache[pair_hash]

        # Check database cache
        cached = self.db.fetch_one(
            "SELECT similarity_score FROM similarity_cache WHERE content_pair_hash = ?",
            (pair_hash,),
        )

        if cached:
            score = cached["similarity_score"]
            self.cache[pair_hash] = score  # Update in-memory cache
            return score

        return None

    def _cache_similarity(
        self, content_id_1: str, content_id_2: str, similarity: float, computation_time: float
    ):
        """
        Cache similarity score in both memory and database.
        """
        pair_hash = self._hash_content_pair(content_id_1, content_id_2)

        # Update in-memory cache
        self.cache[pair_hash] = similarity

        # Update database cache
        self.db.execute(
            """
            INSERT OR REPLACE INTO similarity_cache
            (content_pair_hash, content_id_1, content_id_2, similarity_score, computation_time)
            VALUES (?, ?, ?, ?, ?)
        """,
            (pair_hash, content_id_1, content_id_2, similarity, computation_time),
        )

    def _hash_content_pair(self, content_id_1: str, content_id_2: str) -> str:
        """
        Create consistent hash for content pair regardless of order.
        """
        # Sort IDs to ensure consistent hash regardless of order
        sorted_ids = sorted([content_id_1, content_id_2])
        pair_string = f"{sorted_ids[0]}||{sorted_ids[1]}"
        return hashlib.md5(pair_string.encode()).hexdigest()

    def get_cache_stats(self) -> dict:
        """
        Get statistics about the similarity cache.
        """
        stats = self.db.fetch_one(
            """
            SELECT
                COUNT(*) as total_cached,
                AVG(similarity_score) as avg_similarity,
                AVG(computation_time) as avg_computation_time,
                MIN(similarity_score) as min_similarity,
                MAX(similarity_score) as max_similarity
            FROM similarity_cache
        """
        )

        stats["memory_cache_size"] = len(self.cache)
        stats["threshold"] = self.similarity_threshold

        return dict(stats)

    def clear_cache(self, older_than_days: int = None):
        """Clear similarity cache.

        Optionally only clear old entries.
        """
        if older_than_days:
            self.db.execute(
                """
                DELETE FROM similarity_cache
                WHERE created_time < datetime('now', '-{} days')
            """.format(
                    older_than_days
                )
            )
            logger.info(f"Cleared cache entries older than {older_than_days} days")
        else:
            self.db.execute("DELETE FROM similarity_cache")
            self.cache.clear()
            logger.info("Cleared all similarity cache")

    def precompute_similarities(self, content_type: str = None, batch_size: int = 100):
        """
        Precompute similarities for all content of a given type.
        """
        if content_type:
            content_query = "SELECT id FROM content_unified WHERE source_type = ?"
            params = (content_type,)
        else:
            content_query = "SELECT id FROM content_unified"
            params = ()

        content_rows = self.db.fetch(content_query, params)
        content_ids = [row["id"] for row in content_rows]  # Fixed: column is 'id', not 'content_id'

        logger.info(
            f"Precomputing similarities for {len(content_ids)} "
            f"{content_type or 'all'} documents"
        )

        # Process in batches to manage memory
        for i in range(0, len(content_ids), batch_size):
            batch_ids = content_ids[i : i + batch_size]
            self.batch_compute_similarities(batch_ids)

            logger.info(f"Completed batch {i//batch_size + 1}/{len(content_ids)//batch_size + 1}")

    def get_similarity_distribution(self) -> dict:
        """
        Get distribution of similarity scores for analysis.
        """
        scores = self.db.fetch("SELECT similarity_score FROM similarity_cache")

        if not scores:
            return {"message": "No similarity data available"}

        score_values = [row["similarity_score"] for row in scores]

        return {
            "total_pairs": len(score_values),
            "mean": np.mean(score_values),
            "median": np.median(score_values),
            "std": np.std(score_values),
            "min": np.min(score_values),
            "max": np.max(score_values),
            "above_threshold": len([s for s in score_values if s >= self.similarity_threshold]),
            "threshold": self.similarity_threshold,
        }


def get_similarity_analyzer(
    db_path: str = "data/emails.db", similarity_threshold: float = 0.7
) -> SimilarityAnalyzer:
    """
    Get similarity analyzer instance.
    """
    return SimilarityAnalyzer(db_path, similarity_threshold)
