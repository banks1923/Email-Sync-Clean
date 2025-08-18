"""
Search Intelligence Service

Core service that provides intelligent search capabilities including query expansion,
document similarity analysis, entity extraction caching, and content clustering.
"""

import hashlib
import json
import re
import uuid
from datetime import datetime
from typing import Any

import numpy as np
from loguru import logger
from sklearn.cluster import DBSCAN
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from entity import EntityService
from shared.simple_db import SimpleDB
from summarization import get_document_summarizer
from utilities.embeddings import get_embedding_service
from utilities.vector_store import get_vector_store

# Import analog database search interface
try:
    from analog_db.search_interface import SearchInterface
    ANALOG_DB_AVAILABLE = True
except ImportError:
    ANALOG_DB_AVAILABLE = False
    logger.warning("Analog database search not available")


class SearchIntelligenceService:
    """Unified search intelligence service"""

    def __init__(self, db_path: str = "emails.db", enable_analog_db: bool = True):
        """Initialize Search Intelligence Service
        
        Args:
            db_path: Path to the SQLite database
            enable_analog_db: Whether to enable analog database (markdown) search
        """
        # Logger is now imported globally from loguru
        self.db = SimpleDB(db_path)

        # Initialize dependent services with error handling
        try:
            self.vector_store = get_vector_store()
        except Exception as e:
            logger.warning(f"Vector store initialization failed: {e}")
            self.vector_store = None
            
        self.entity_service = EntityService()
        
        try:
            self.embedding_service = get_embedding_service()
        except Exception as e:
            logger.warning(f"Embedding service initialization failed: {e}")
            self.embedding_service = None
            
        self.summarizer = get_document_summarizer()
        
        # Initialize analog database search if available and enabled
        self.analog_search = None
        if enable_analog_db and ANALOG_DB_AVAILABLE:
            try:
                from pathlib import Path
                self.analog_search = SearchInterface(base_path=Path.cwd())
                logger.info("Analog database search initialized")
            except Exception as e:
                logger.warning(f"Failed to initialize analog database search: {e}")

        # Query expansion configuration
        self.query_synonyms = {
            "contract": ["agreement", "deal", "terms"],
            "legal": ["law", "judicial", "court"],
            "email": ["message", "mail", "correspondence"],
            "document": ["file", "paper", "record"],
            "meeting": ["conference", "discussion", "session"],
            "invoice": ["bill", "statement", "receipt"],
            "report": ["analysis", "summary", "review"],
            "attorney": ["lawyer", "counsel", "solicitor"],
            "client": ["customer", "patron", "account"],
            "case": ["matter", "lawsuit", "litigation"],
        }

        # Abbreviation expansion
        self.abbreviations = {
            "llc": "limited liability company",
            "inc": "incorporated",
            "corp": "corporation",
            "atty": "attorney",
            "esq": "esquire",
            "dba": "doing business as",
            "roi": "return on investment",
            "nda": "non disclosure agreement",
            "sla": "service level agreement",
            "ip": "intellectual property",
        }

        logger.info("SearchIntelligenceService initialized")

    def unified_search(
        self,
        query: str,
        mode: str = "hybrid",
        limit: int = 10,
        use_expansion: bool = True,
        filters: dict | None = None,
    ) -> list[dict[str, Any]]:
        """Unified search supporting both database and analog (markdown) search
        
        Args:
            query: Search query string
            mode: Search mode - 'database', 'analog', or 'hybrid' (default)
            limit: Maximum number of results
            use_expansion: Whether to expand query with synonyms
            filters: Additional filters for search
        
        Returns:
            List of search results from the selected source(s)
        """
        results = []
        
        # Preprocess query if needed
        if use_expansion:
            query = self._preprocess_and_expand_query(query)
        
        if mode == "database" or mode == "hybrid":
            # Search SQLite database
            db_results = self.smart_search_with_preprocessing(
                query, limit, use_expansion=False, filters=filters
            )
            results.extend(self._add_source_tag(db_results, "database"))
        
        if (mode == "analog" or mode == "hybrid") and self.analog_search:
            # Search analog database (markdown files)
            try:
                # Convert filters to analog format if needed
                analog_filters = self._convert_filters_to_analog(filters) if filters else {}
                
                # Perform analog search
                analog_results = self.analog_search.hybrid_search(
                    query=query,
                    metadata_filters=analog_filters,
                    limit=limit,
                    use_vector=bool(self.vector_store)
                )
                
                # Convert analog results to standard format
                standardized = self._standardize_analog_results(analog_results)
                results.extend(self._add_source_tag(standardized, "analog"))
                
            except Exception as e:
                logger.error(f"Analog search failed: {e}")
        
        # Remove duplicates and re-rank if hybrid mode
        if mode == "hybrid" and len(results) > 0:
            results = self._merge_and_rank_results(results, limit)
        
        return results[:limit]
    
    def _preprocess_and_expand_query(self, query: str) -> str:
        """Preprocess and expand query with synonyms"""
        processed = self._preprocess_query(query)
        expanded_terms = self._expand_query(processed)
        if expanded_terms:
            processed = f"{processed} {' '.join(expanded_terms)}"
        return processed
    
    def _add_source_tag(self, results: list[dict], source: str) -> list[dict]:
        """Add source tag to results"""
        for result in results:
            result["search_source"] = source
        return results
    
    def _convert_filters_to_analog(self, filters: dict) -> dict:
        """Convert standard filters to analog database format"""
        analog_filters = {}
        
        # Map common filter fields
        if "content_type" in filters:
            analog_filters["doc_type"] = filters["content_type"]
        if "sender" in filters:
            analog_filters["sender"] = filters["sender"]
        if "created_after" in filters:
            analog_filters["since"] = filters["created_after"]
        if "created_before" in filters:
            analog_filters["until"] = filters["created_before"]
        if "tags" in filters:
            analog_filters["tags"] = filters["tags"]
            
        return analog_filters
    
    def _standardize_analog_results(self, analog_results: list[dict]) -> list[dict]:
        """Convert analog search results to standard format"""
        standardized = []
        
        for result in analog_results:
            metadata = result.get("metadata", {})
            
            # Build standardized result
            std_result = {
                "content_id": metadata.get("doc_id", str(uuid.uuid4())),
                "title": metadata.get("title", "Untitled"),
                "content": result.get("content_preview", ""),
                "content_type": metadata.get("doc_type", "document"),
                "created_time": metadata.get("date_created"),
                "score": result.get("score", 0.0),
                "file_path": result.get("file_path"),
                "metadata": metadata
            }
            
            # Add sender info if it's an email
            if metadata.get("doc_type") == "email":
                std_result["sender"] = metadata.get("sender", "")
                std_result["recipient"] = metadata.get("recipient", "")
            
            standardized.append(std_result)
        
        return standardized
    
    def _merge_and_rank_results(self, results: list[dict], limit: int) -> list[dict]:
        """Merge and re-rank results from multiple sources"""
        # Remove exact duplicates based on content_id
        seen_ids = set()
        unique_results = []
        
        for result in results:
            content_id = result.get("content_id")
            if content_id and content_id not in seen_ids:
                seen_ids.add(content_id)
                unique_results.append(result)
            elif not content_id:
                # Keep results without IDs (shouldn't happen but be safe)
                unique_results.append(result)
        
        # Re-rank by score
        unique_results.sort(key=lambda x: x.get("score", 0.0), reverse=True)
        
        return unique_results[:limit]

    def smart_search_with_preprocessing(
        self,
        query: str,
        limit: int = 10,
        use_expansion: bool = True,
        filters: dict | None = None,
    ) -> list[dict[str, Any]]:
        """Smart search with query preprocessing and expansion"""
        try:
            # Preprocess query
            processed_query = self._preprocess_query(query)

            # Expand query if enabled
            if use_expansion:
                expanded_terms = self._expand_query(processed_query)
                if expanded_terms:
                    processed_query = f"{processed_query} {' '.join(expanded_terms)}"
                    logger.debug(f"Expanded query: {processed_query}")

            # Perform search using direct database query
            results = self.db.search_content(processed_query, limit=limit, filters=filters)

            # Enhance results with intelligence
            if results:
                results = self._enhance_search_results(results, query)

            return results

        except Exception as e:
            logger.error(f"Smart search failed: {e}")
            return []

    def _preprocess_query(self, query: str) -> str:
        """Preprocess query for better search"""
        # Convert to lowercase
        query = query.lower()

        # Expand abbreviations
        for abbr, full in self.abbreviations.items():
            pattern = r"\b" + re.escape(abbr) + r"\b"
            query = re.sub(pattern, full, query)

        # Remove extra whitespace
        query = " ".join(query.split())

        return query

    def _expand_query(self, query: str) -> list[str]:
        """Expand query with synonyms"""
        expanded = []
        words = query.split()

        for word in words:
            if word in self.query_synonyms:
                # Add first 2 synonyms to avoid over-expansion
                expanded.extend(self.query_synonyms[word][:2])

        return expanded

    def _enhance_search_results(self, results: list[dict], query: str) -> list[dict]:
        """Enhance search results with additional intelligence"""
        for result in results:
            # Add relevance score based on entity overlap
            content_id = result.get("content_id")
            if content_id:
                # Check if entities are cached
                entities = self._get_cached_entities(content_id)
                if entities:
                    result["extracted_entities"] = entities[:5]  # Top 5 entities

                # Add recency boost
                created_time = result.get("created_time")
                if created_time:
                    result["recency_score"] = self._calculate_recency_score(created_time)

        # Re-rank based on combined scores
        results = self._rerank_results(results)
        return results

    def _calculate_recency_score(self, created_time: str) -> float:
        """Calculate recency score (0-1) based on age"""
        try:
            # Parse date
            if isinstance(created_time, str):
                created_dt = datetime.fromisoformat(created_time.replace(" ", "T"))
            else:
                created_dt = created_time

            # Calculate days old
            days_old = (datetime.now() - created_dt).days

            # Exponential decay: newer = higher score
            score = np.exp(-days_old / 30.0)  # 30-day half-life
            return min(1.0, max(0.0, score))

        except Exception:
            return 0.5  # Default middle score

    def _rerank_results(self, results: list[dict]) -> list[dict]:
        """Re-rank results based on multiple factors"""
        for result in results:
            # Combine scores
            base_score = result.get("score", 0.5)
            recency = result.get("recency_score", 0.5)
            entity_boost = 0.1 if result.get("extracted_entities") else 0

            # Weighted combination
            result["combined_score"] = (
                0.6 * base_score  # Original relevance
                + 0.3 * recency  # Recency factor
                + 0.1 * entity_boost  # Entity presence
            )

        # Sort by combined score
        results.sort(key=lambda x: x.get("combined_score", 0), reverse=True)
        return results

    def analyze_document_similarity(
        self, doc_id: str, threshold: float = 0.7, limit: int = 10
    ) -> list[dict[str, Any]]:
        """Analyze similarity between documents using Legal BERT"""
        try:
            # Get document content
            doc = self.db.get_content(content_id=doc_id)
            if not doc:
                return []

            # Get document embedding
            doc_text = doc.get("content", "")
            if not doc_text:
                return []

            doc_embedding = self.embedding_service.encode(doc_text)

            # Search for similar documents
            all_docs = self.db.search_content("", limit=100)
            similar_docs = []

            for other_doc in all_docs:
                if other_doc["content_id"] == doc_id:
                    continue

                other_text = other_doc.get("content", "")
                if not other_text:
                    continue

                # Calculate similarity
                other_embedding = self.embedding_service.encode(other_text)
                similarity = cosine_similarity(
                    doc_embedding.reshape(1, -1), other_embedding.reshape(1, -1)
                )[0][0]

                if similarity >= threshold:
                    similar_docs.append(
                        {
                            "content_id": other_doc["content_id"],
                            "title": other_doc.get("title", ""),
                            "content_type": other_doc.get("content_type"),
                            "similarity_score": float(similarity),
                            "created_time": other_doc.get("created_time"),
                        }
                    )

            # Sort by similarity
            similar_docs.sort(key=lambda x: x["similarity_score"], reverse=True)
            return similar_docs[:limit]

        except Exception as e:
            logger.error(f"Document similarity analysis failed: {e}")
            return []

    def extract_and_cache_entities(
        self, doc_id: str, force_refresh: bool = False
    ) -> list[dict[str, Any]]:
        """Extract entities and cache in relationship_cache table"""
        try:
            # Check cache first
            if not force_refresh:
                cached = self._get_cached_entities(doc_id)
                if cached:
                    return cached

            # Get document content
            doc = self.db.get_content(content_id=doc_id)
            if not doc:
                return []

            # Extract entities
            content = doc.get("content", "")
            entities = self.entity_service.extract_entities(content)

            # Cache results
            if entities:
                self._cache_entities(doc_id, entities)

            return entities

        except Exception as e:
            logger.error(f"Entity extraction failed: {e}")
            return []

    def _get_cached_entities(self, doc_id: str) -> list[dict] | None:
        """Get cached entities from relationship_cache"""
        try:
            # Query relationship_cache
            query = """
                SELECT cache_data, created_at
                FROM relationship_cache
                WHERE source_id = ? AND cache_type = 'entities'
                ORDER BY created_at DESC LIMIT 1
            """
            result = self.db.fetch(query, (doc_id,))

            if result:
                # Check TTL (7 days)
                created_at = datetime.fromisoformat(result[0][1])
                if (datetime.now() - created_at).days < 7:
                    return json.loads(result[0][0])

            return None

        except Exception:
            return None

    def _cache_entities(self, doc_id: str, entities: list[dict]):
        """Cache entities in relationship_cache"""
        try:
            # Prepare cache data
            cache_data = json.dumps(entities)

            # Insert or update cache
            query = """
                INSERT OR REPLACE INTO relationship_cache
                (source_id, target_id, cache_type, cache_data, created_at, ttl_seconds)
                VALUES (?, ?, 'entities', ?, datetime('now'), 604800)
            """
            self.db.execute(query, (doc_id, doc_id, cache_data))

        except Exception as e:
            logger.warning(f"Failed to cache entities: {e}")

    def auto_summarize_document(
        self, doc_id: str, force_refresh: bool = False
    ) -> dict[str, Any] | None:
        """Automatically summarize document if not already done"""
        try:
            # Check if summary exists
            if not force_refresh:
                existing = self.db.get_document_summaries(doc_id)
                if existing:
                    return existing[0]

            # Get document content
            doc = self.db.get_content(content_id=doc_id)
            if not doc:
                return None

            content = doc.get("content", "")
            if not content:
                return None

            # Generate summary
            summary = self.summarizer.extract_summary(
                content, max_sentences=5, max_keywords=15, summary_type="combined"
            )

            # Store summary
            if summary:
                summary_id = self.db.add_document_summary(
                    document_id=doc_id,
                    summary_type="combined",
                    summary_text=summary.get("summary_text"),
                    tf_idf_keywords=summary.get("tf_idf_keywords"),
                    textrank_sentences=summary.get("textrank_sentences"),
                )

                if summary_id:
                    summary["summary_id"] = summary_id
                    return summary

            return None

        except Exception as e:
            logger.error(f"Auto-summarization failed: {e}")
            return None

    def cluster_similar_content(
        self, threshold: float = 0.7, min_samples: int = 2, limit: int = 100
    ) -> list[dict[str, Any]]:
        """Cluster similar content using DBSCAN"""
        try:
            # Get documents
            docs = self.db.search_content("", limit=limit)
            if len(docs) < min_samples:
                return []

            # Extract content
            texts = []
            doc_ids = []
            for doc in docs:
                content = doc.get("content", "")
                if content:
                    texts.append(content)
                    doc_ids.append(doc["content_id"])

            if len(texts) < min_samples:
                return []

            # Vectorize using TF-IDF
            vectorizer = TfidfVectorizer(max_features=1000, stop_words="english")
            X = vectorizer.fit_transform(texts)

            # Apply DBSCAN with cosine distance
            # Convert threshold to distance (1 - similarity)
            eps = 1 - threshold
            clustering = DBSCAN(eps=eps, min_samples=min_samples, metric="cosine")
            labels = clustering.fit_predict(X)

            # Group documents by cluster
            clusters = {}
            for i, label in enumerate(labels):
                if label == -1:  # Noise
                    continue

                if label not in clusters:
                    clusters[label] = []

                clusters[label].append(
                    {
                        "content_id": doc_ids[i],
                        "title": docs[i].get("title", ""),
                        "content_type": docs[i].get("content_type"),
                    }
                )

            # Format results
            result = []
            for cluster_id, members in clusters.items():
                result.append(
                    {"cluster_id": int(cluster_id), "size": len(members), "documents": members}
                )

            # Sort by cluster size
            result.sort(key=lambda x: x["size"], reverse=True)
            return result

        except Exception as e:
            logger.error(f"Content clustering failed: {e}")
            return []

    def detect_duplicates(self, similarity_threshold: float = 0.95) -> list[dict[str, Any]]:
        """Detect duplicate documents using hash and semantic similarity"""
        try:
            # Get all documents
            docs = self.db.search_content("", limit=1000)

            # Phase 1: Hash-based exact duplicates
            hash_groups = {}
            for doc in docs:
                content = doc.get("content", "")
                if not content:
                    continue

                # Create content hash
                content_hash = hashlib.sha256(content.encode()).hexdigest()

                if content_hash not in hash_groups:
                    hash_groups[content_hash] = []
                hash_groups[content_hash].append(doc)

            # Collect exact duplicates
            duplicates = []
            for hash_val, group in hash_groups.items():
                if len(group) > 1:
                    duplicates.append(
                        {
                            "type": "exact",
                            "hash": hash_val[:8],
                            "count": len(group),
                            "documents": [
                                {
                                    "content_id": d["content_id"],
                                    "title": d.get("title", ""),
                                    "created_time": d.get("created_time"),
                                }
                                for d in group
                            ],
                        }
                    )

            # Phase 2: Semantic near-duplicates (only for unique hashes)
            unique_docs = [group[0] for group in hash_groups.values()]

            if len(unique_docs) > 1:
                # Vectorize content
                texts = [d.get("content", "") for d in unique_docs]
                vectorizer = TfidfVectorizer(max_features=500, stop_words="english")
                X = vectorizer.fit_transform(texts)

                # Calculate pairwise similarity
                similarities = cosine_similarity(X)

                # Find near-duplicates
                near_dupes = []
                processed = set()

                for i in range(len(unique_docs)):
                    if i in processed:
                        continue

                    similar_group = [unique_docs[i]]
                    processed.add(i)

                    for j in range(i + 1, len(unique_docs)):
                        if j in processed:
                            continue

                        if similarities[i][j] >= similarity_threshold:
                            similar_group.append(unique_docs[j])
                            processed.add(j)

                    if len(similar_group) > 1:
                        near_dupes.append(
                            {
                                "type": "semantic",
                                "similarity": float(similarities[i][j]),
                                "count": len(similar_group),
                                "documents": [
                                    {
                                        "content_id": d["content_id"],
                                        "title": d.get("title", ""),
                                        "created_time": d.get("created_time"),
                                    }
                                    for d in similar_group
                                ],
                            }
                        )

                duplicates.extend(near_dupes)

            return duplicates

        except Exception as e:
            logger.error(f"Duplicate detection failed: {e}")
            return []
