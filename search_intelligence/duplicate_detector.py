"""Duplicate Detection Module.

Provides hash-based and semantic duplicate detection for documents. Uses
SHA-256 for exact duplicates and cosine similarity for near-duplicates.
"""

import hashlib
from collections import defaultdict
from datetime import datetime

import numpy as np
from loguru import logger
from sklearn.metrics.pairwise import cosine_similarity

from shared.simple_db import SimpleDB
from utilities.embeddings import get_embedding_service
from utilities.vector_store import get_vector_store

# Logger is now imported globally from loguru


class DuplicateDetector:
    """
    Detect duplicate and near-duplicate documents.
    """

    def __init__(self, collection: str = "emails"):
        """
        Initialize duplicate detector.
        """
        self.logger = logger
        self.collection = collection
        self.embedding_service = get_embedding_service()
        self.vector_store = get_vector_store(collection)
        self.db = SimpleDB()

        # Cache for document hashes
        self._hash_cache = {}

    def detect_duplicates(
        self,
        doc_ids: list[str] = None,
        content_type: str = None,
        similarity_threshold: float = 0.95,
        check_semantic: bool = True,
    ) -> dict:
        """Detect duplicate documents using hash and semantic similarity.

        Args:
            doc_ids: Optional list of document IDs to check
            content_type: Optional content type filter
            similarity_threshold: Threshold for semantic duplicates (0-1)
            check_semantic: Whether to check semantic similarity

        Returns:
            Dict with duplicate groups and statistics
        """
        logger.info(
            f"Detecting duplicates with threshold={similarity_threshold}, "
            f"semantic={check_semantic}"
        )

        # Get documents to check
        documents = self._get_documents_to_check(doc_ids, content_type)

        if not documents:
            return {
                "exact_duplicates": [],
                "near_duplicates": [],
                "total_documents": 0,
                "duplicate_count": 0,
            }

        # Detect exact duplicates using hashes
        exact_duplicates = self._detect_exact_duplicates(documents)

        # Detect near duplicates using semantic similarity
        near_duplicates = []
        if check_semantic:
            near_duplicates = self._detect_semantic_duplicates(
                documents, similarity_threshold, exact_duplicates
            )

        # Compile results
        all_duplicate_ids = set()
        for group in exact_duplicates:
            all_duplicate_ids.update(group["members"])
        for group in near_duplicates:
            all_duplicate_ids.update(group["members"])

        results = {
            "exact_duplicates": exact_duplicates,
            "near_duplicates": near_duplicates,
            "total_documents": len(documents),
            "duplicate_count": len(all_duplicate_ids),
            "duplicate_percentage": (
                len(all_duplicate_ids) / len(documents) * 100 if documents else 0
            ),
        }

        logger.info(
            f"Found {len(exact_duplicates)} exact duplicate groups and "
            f"{len(near_duplicates)} near duplicate groups"
        )

        return results

    def _get_documents_to_check(
        self, doc_ids: list[str] = None, content_type: str = None
    ) -> list[dict]:
        """
        Get documents to check for duplicates.
        """
        try:
            if doc_ids:
                # Get specific documents
                documents = []
                for doc_id in doc_ids:
                    doc = self._get_document(doc_id)
                    if doc:
                        documents.append(doc)
                return documents

            # Get all documents of type
            if content_type:
                query = """
                    SELECT id, source_type, title, content
                    FROM content_unified
                    WHERE source_type = ?
                """
                params = (content_type,)
            else:
                query = """
                    SELECT id, source_type, title, content
                    FROM content_unified
                """
                params = ()

            results = self.db.fetch(query, params)
            return results

        except Exception as e:
            logger.error(f"Failed to get documents: {e}")
            return []

    def _get_document(self, doc_id: str) -> dict | None:
        """
        Get single document.
        """
        result = self.db.fetch_one("SELECT * FROM content_unified WHERE id = ?", (doc_id,))
        if result:
            return result

        # Try individual_messages table for emails (v2 schema)
        result = self.db.fetch_one(
            """SELECT im.message_hash as content_id, 'email' as source_type,
               im.subject as title, cu.body as content
               FROM individual_messages im
               JOIN content_unified cu ON cu.source_id = im.message_hash
               WHERE cu.source_type = 'email_message'
                 AND im.message_hash = ?""",
            (doc_id,),
        )
        if result:
            return result

        result = self.db.fetch_one(
            "SELECT chunk_id as content_id, 'document' as source_type, "  # ALLOWED: content_id
            "file_name as title, text_content as content "
            "FROM documents WHERE chunk_id = ?",
            (doc_id,),
        )
        return result

    def _detect_exact_duplicates(self, documents: list[dict]) -> list[dict]:
        """
        Detect exact duplicates using SHA-256 hashing.
        """
        hash_groups = defaultdict(list)

        for doc in documents:
            # Compute hash of content
            doc_hash = self._compute_document_hash(doc)
            if doc_hash:
                doc_id = doc.get("id") or doc.get("content_id")
                hash_groups[doc_hash].append(doc_id)

        # Find groups with duplicates
        duplicate_groups = []
        for hash_value, doc_ids in hash_groups.items():
            if len(doc_ids) > 1:
                duplicate_groups.append(
                    {
                        "type": "exact",
                        "hash": hash_value[:16],  # Shortened for display
                        "members": doc_ids,
                        "count": len(doc_ids),
                    }
                )

        return duplicate_groups

    def _compute_document_hash(self, doc: dict) -> str:
        """
        Compute SHA-256 hash of document content.
        """
        doc_id = doc.get("id") or doc.get("content_id")

        # Check cache
        if doc_id in self._hash_cache:
            return self._hash_cache[doc_id]

        # Extract and normalize content
        content = doc.get("content_unified", "") or doc.get("body", "") or doc.get("content", "")
        title = doc.get("title", "") or doc.get("subject", "")

        # Combine title and content for hashing
        text = f"{title}\n{content}".strip()

        if not text:
            return ""

        # Normalize whitespace
        text = " ".join(text.split())

        # Compute hash
        hash_value = hashlib.sha256(text.encode("utf-8")).hexdigest()

        # Cache result
        self._hash_cache[doc_id] = hash_value

        return hash_value

    def _detect_semantic_duplicates(
        self, documents: list[dict], threshold: float, exact_groups: list[dict]
    ) -> list[dict]:
        """
        Detect near-duplicates using semantic similarity.
        """
        # Get documents not in exact duplicate groups
        exact_duplicate_ids = set()
        for group in exact_groups:
            exact_duplicate_ids.update(group["members"])

        # Filter out exact duplicates
        docs_to_check = [doc for doc in documents if (doc.get("id") or doc.get("content_id")) not in exact_duplicate_ids]

        if len(docs_to_check) < 2:
            return []

        # Get embeddings for documents
        doc_ids = []
        embeddings = []

        for doc in docs_to_check:
            doc_id = doc.get("id") or doc.get("content_id")
            embedding = self._get_document_embedding(doc)

            if embedding is not None:
                doc_ids.append(doc_id)
                embeddings.append(embedding)

        if len(embeddings) < 2:
            return []

        # Compute similarity matrix
        embedding_matrix = np.vstack(embeddings)
        similarity_matrix = cosine_similarity(embedding_matrix)

        # Find similar pairs above threshold
        similar_pairs = []
        n_docs = len(doc_ids)

        for i in range(n_docs):
            for j in range(i + 1, n_docs):
                similarity = similarity_matrix[i, j]
                if similarity >= threshold:
                    similar_pairs.append((doc_ids[i], doc_ids[j], similarity))

        # Group similar documents
        duplicate_groups = self._group_similar_documents(similar_pairs)

        return duplicate_groups

    def _get_document_embedding(self, doc: dict) -> np.ndarray | None:
        """
        Get or generate embedding for document.
        """
        doc_id = doc.get("id") or doc.get("content_id")

        try:
            # Try to get from vector store
            result = self.vector_store.get(doc_id)
            if result and "vector" in result:
                return np.array(result["vector"])

            # Generate new embedding
            text = doc.get("content_unified", "") or doc.get("body", "") or doc.get("content", "")
            title = doc.get("title", "") or doc.get("subject", "")

            full_text = f"{title} {text}".strip()
            if not full_text:
                return None

            embedding = self.embedding_service.encode(full_text)

            # Store for future use
            self.vector_store.upsert(
                id=doc_id,
                vector=embedding.tolist(),
                payload={"content_type": doc.get("content_type", "unknown")},
            )

            return embedding

        except Exception as e:
            logger.error(f"Failed to get embedding for {doc_id}: {e}")
            return None

    def _group_similar_documents(self, similar_pairs: list[tuple[str, str, float]]) -> list[dict]:
        """
        Group similar document pairs into clusters.
        """
        # Build adjacency list
        graph = defaultdict(set)
        similarity_scores = {}

        for doc1, doc2, similarity in similar_pairs:
            graph[doc1].add(doc2)
            graph[doc2].add(doc1)
            similarity_scores[(doc1, doc2)] = similarity
            similarity_scores[(doc2, doc1)] = similarity

        # Find connected components (duplicate groups)
        visited = set()
        groups = []

        for node in graph:
            if node not in visited:
                # BFS to find connected component
                component = set()
                queue = [node]

                while queue:
                    current = queue.pop(0)
                    if current not in visited:
                        visited.add(current)
                        component.add(current)
                        queue.extend(graph[current] - visited)

                if len(component) > 1:
                    # Calculate average similarity for group
                    total_similarity = 0
                    pair_count = 0

                    members = list(component)
                    for i, doc1 in enumerate(members):
                        for doc2 in members[i + 1 :]:
                            key = (
                                (doc1, doc2) if (doc1, doc2) in similarity_scores else (doc2, doc1)
                            )
                            if key in similarity_scores:
                                total_similarity += similarity_scores[key]
                                pair_count += 1

                    avg_similarity = total_similarity / pair_count if pair_count > 0 else 0

                    groups.append(
                        {
                            "type": "semantic",
                            "members": members,
                            "count": len(members),
                            "avg_similarity": round(avg_similarity, 3),
                        }
                    )

        return groups

    def remove_duplicates(self, duplicate_groups: list[dict], keep_strategy: str = "first") -> dict:
        """Remove duplicate documents based on strategy.

        Args:
            duplicate_groups: List of duplicate groups from detect_duplicates
            keep_strategy: Strategy for keeping documents ('first', 'last', 'newest')

        Returns:
            Dict with removal statistics
        """
        removed_count = 0
        kept_docs = []
        removed_docs = []

        for group in duplicate_groups:
            members = group["members"]

            if keep_strategy == "first":
                keep = members[0]
                remove = members[1:]
            elif keep_strategy == "last":
                keep = members[-1]
                remove = members[:-1]
            elif keep_strategy == "newest":
                # Get creation dates and keep newest
                dated_members = []
                for doc_id in members:
                    doc = self._get_document(doc_id)
                    if doc:
                        date = doc.get("created_at", "")
                        dated_members.append((doc_id, date))

                if dated_members:
                    dated_members.sort(key=lambda x: x[1], reverse=True)
                    keep = dated_members[0][0]
                    remove = [m[0] for m in dated_members[1:]]
                else:
                    keep = members[0]
                    remove = members[1:]
            else:
                keep = members[0]
                remove = members[1:]

            kept_docs.append(keep)
            removed_docs.extend(remove)

            # Mark documents as duplicates in database
            for doc_id in remove:
                try:
                    self.db.add_relationship_cache(
                        source_id=doc_id,
                        target_id=keep,
                        relationship_type="duplicate_of",
                        relationship_data={
                            "marked_at": datetime.now().isoformat(),
                            "group_size": len(members),
                        },
                        ttl_seconds=86400 * 30,  # 30 days
                    )
                    removed_count += 1
                except Exception as e:
                    logger.error(f"Failed to mark duplicate {doc_id}: {e}")

        return {
            "removed_count": removed_count,
            "kept_count": len(kept_docs),
            "kept_documents": kept_docs,
            "removed_documents": removed_docs,
        }

    def find_duplicate_emails(self) -> dict:
        """
        Specialized method to find duplicate emails.
        """
        # Get all emails (v2 schema)
        emails = self.db.fetch(
            """
            SELECT im.message_id, im.subject, cu.body, im.date_sent as date
            FROM individual_messages im
            JOIN content_unified cu ON cu.source_id = im.message_hash
            WHERE cu.source_type = 'email_message'
            ORDER BY im.date_sent DESC
            """
        )

        # Convert to document format
        documents = [
            {
                "id": email["message_id"],
                "content_type": "email",
                "title": email.get("subject", ""),
                "content_unified": email.get("body", ""),
                "created_at": email.get("date", ""),
            }
            for email in emails
        ]

        # Detect duplicates with high threshold for emails
        return self.detect_duplicates(
            doc_ids=[d["id"] for d in documents],
            similarity_threshold=0.98,  # High threshold for email duplicates
            check_semantic=True,
        )


def detect_all_duplicates(content_type: str = None, similarity_threshold: float = 0.95) -> dict:
    """Convenience function to detect all duplicates.

    Args:
        content_type: Optional content type filter
        similarity_threshold: Threshold for semantic duplicates

    Returns:
        Dict with duplicate detection results
    """
    detector = DuplicateDetector()
    return detector.detect_duplicates(
        source_type=content_type, similarity_threshold=similarity_threshold, check_semantic=True
    )
