"""Tests for Search Intelligence Module.

Tests the unified search intelligence service including smart search,
document similarity, clustering, and duplicate detection.
"""

import os
import sys
from unittest.mock import MagicMock, patch

import pytest

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from search_intelligence.main import (
    SearchIntelligenceService,
    get_search_intelligence_service,
)
from search_intelligence.similarity import (
    DocumentSimilarityAnalyzer,
    DocumentClusterer,
)
from search_intelligence.duplicate_detector import DuplicateDetector


class TestSearchIntelligenceService:
    """
    Test SearchIntelligenceService functionality.
    """

    @pytest.fixture
    def service(self):
        """
        Create service instance for testing.
        """
        with patch("search_intelligence.main.get_search_service"):
            with patch("search_intelligence.main.get_embedding_service"):
                with patch("search_intelligence.main.get_vector_store"):
                    with patch("search_intelligence.main.SimpleDB"):
                        service = SearchIntelligenceService()
                        # Mock entity service
                        service.entity_service = MagicMock()
                        service.entity_service.extract_entities = MagicMock(
                            return_value=[
                                {"text": "John Doe", "label": "PERSON"},
                                {"text": "Apple Inc", "label": "ORG"},
                            ]
                        )
                        return service

    def test_service_initialization(self, service):
        """
        Test service initializes correctly.
        """
        assert service is not None
        assert service.collection == "emails"
        assert hasattr(service, "synonyms")
        assert hasattr(service, "abbreviations")
        assert hasattr(service, "clusterer")
        assert hasattr(service, "duplicate_detector")

    def test_query_preprocessing(self, service):
        """
        Test query preprocessing functionality.
        """
        # Test abbreviation expansion
        query = "The LLC vs the corp re: Q1 meeting"
        processed = service._preprocess_query(query)

        assert "limited liability company" in processed
        assert "corporation" in processed
        assert "versus" in processed
        assert "regarding" in processed
        assert "first quarter" in processed

    def test_query_expansion(self, service):
        """
        Test query expansion with synonyms.
        """
        query = "contract attorney meeting"
        expanded = service._expand_query(query)

        # Should include synonyms
        assert any(
            "agreement" in term or "lawyer" in term or "conference" in term for term in expanded
        )

    def test_smart_search_preprocessing(self, service):
        """
        Test smart search with preprocessing.
        """
        # Mock the search service
        service.search_service.search = MagicMock(
            return_value=[
                {
                    "id": "doc1",
                    "score": 0.9,
                    "content": {"body": "Contract agreement with attorney"},
                    "metadata": {},
                }
            ]
        )

        results = service.smart_search_with_preprocessing(
            "contract attorney", limit=5, use_expansion=True
        )

        # Validate result shape and size
        assert isinstance(results, list)
        assert len(results) <= 5

    def test_entity_relevance_calculation(self, service):
        """
        Test entity relevance scoring.
        """
        content = {"body": "John Doe from Apple Inc contacted us about the deal"}
        query = "John Doe Apple"

        score = service._calculate_entity_relevance(content, query)

        # Should find entity overlap
        assert score > 0

    def test_recency_boost_calculation(self, service):
        """
        Test recency boost for recent documents.
        """
        from datetime import datetime, timedelta

        # Recent document (3 days old)
        recent_date = (datetime.now() - timedelta(days=3)).strftime("%Y-%m-%d")
        recent_content = {"date": recent_date}
        recent_score = service._calculate_recency_boost(recent_content)

        # Old document (200 days old)
        old_date = (datetime.now() - timedelta(days=200)).strftime("%Y-%m-%d")
        old_content = {"date": old_date}
        old_score = service._calculate_recency_boost(old_content)

        # Recent should score higher
        assert recent_score > old_score
        assert recent_score == 1.0  # Within 7 days
        assert old_score < 0.5  # Older than 90 days

    def test_extract_and_cache_entities(self, service):
        """
        Test entity extraction and caching.
        """
        # Mock document retrieval
        service._get_document_content = MagicMock(return_value={"body": "John Doe from Apple Inc"})
        service._cache_data = MagicMock()
        service.db.add_relationship_cache = MagicMock()

        result = service.extract_and_cache_entities("doc1")

        assert result["success"] is True
        assert "entities" in result
        assert result["total_entities"] == 2
        assert "PERSON" in result["entities_by_type"]
        assert "ORG" in result["entities_by_type"]

        # Should cache the results
        service._cache_data.assert_called_once()

    def test_auto_summarize_document(self, service):
        """
        Test document summarization.
        """
        # Mock summarizer
        service.summarizer.extract_summary = MagicMock(
            return_value={
                "summary": "This is a summary",
                "keywords": {"legal": 0.8, "contract": 0.6},
                "sentences": ["Key sentence 1", "Key sentence 2"],
            }
        )
        service._cache_data = MagicMock()
        service.db.add_document_summary = MagicMock()

        result = service.auto_summarize_document(
            "doc1", text="Long document text here...", cache=True
        )

        assert result["success"] is True
        assert result["summary"] == "This is a summary"
        assert "legal" in result["keywords"]
        assert len(result["sentences"]) == 2

        # Should cache and store in DB
        service._cache_data.assert_called_once()
        service.db.add_document_summary.assert_called_once()

    def test_cluster_similar_content(self, service):
        """
        Test content clustering.
        """
        # Mock clustering function
        with patch("search_intelligence.main.cluster_similar_content") as mock_cluster:
            mock_cluster.return_value = [
                {"cluster_id": 0, "members": ["doc1", "doc2", "doc3"], "size": 3}
            ]

            service._get_document_content = MagicMock(return_value={"title": "Test Document"})

            clusters = service.cluster_similar_content(threshold=0.7, limit=10)

            assert len(clusters) == 1
            assert clusters[0]["size"] == 3
            assert "sample_title" in clusters[0]

    def test_detect_duplicates(self, service):
        """
        Test duplicate detection.
        """
        # Mock duplicate detector
        service.duplicate_detector.detect_duplicates = MagicMock(
            return_value={
                "exact_duplicates": [{"type": "exact", "members": ["doc1", "doc2"], "count": 2}],
                "near_duplicates": [{"type": "semantic", "members": ["doc3", "doc4"], "count": 2}],
                "total_documents": 10,
                "duplicate_count": 4,
            }
        )

        service._get_document_content = MagicMock(return_value={"title": "Test Doc"})

        results = service.detect_duplicates(similarity_threshold=0.95)

        assert len(results["exact_duplicates"]) == 1
        assert len(results["near_duplicates"]) == 1
        assert results["duplicate_count"] == 4

        # Should enhance with document details
        assert "member_details" in results["exact_duplicates"][0]


class TestDocumentSimilarity:
    """
    Test document similarity analyzer.
    """

    @pytest.fixture
    def analyzer(self):
        """
        Create analyzer instance.
        """
        with patch("search_intelligence.similarity.get_embedding_service"):
            with patch("search_intelligence.similarity.get_vector_store"):
                with patch("search_intelligence.similarity.SimpleDB"):
                    return DocumentSimilarityAnalyzer()

    def test_find_similar_documents(self, analyzer):
        """
        Test finding similar documents.
        """
        # Mock vector store search
        analyzer.vector_store.search = MagicMock(
            return_value=[
                {"id": "doc1", "score": 0.95, "payload": {}},
                {"id": "doc2", "score": 0.85, "payload": {}},
                {"id": "doc3", "score": 0.75, "payload": {}},
            ]
        )

        analyzer._get_document_vector = MagicMock(return_value=[0.1, 0.2, 0.3])  # Mock vector

        similar = analyzer.find_similar_documents("doc1", limit=5, threshold=0.7)

        # Should exclude the document itself
        assert all(doc["id"] != "doc1" for doc in similar)
        assert len(similar) <= 5

    def test_compute_pairwise_similarity(self, analyzer):
        """
        Test pairwise similarity computation.
        """
        import numpy as np

        # Mock document vectors
        analyzer._get_document_vector = MagicMock(
            side_effect=[np.array([1, 0, 0]), np.array([0.9, 0.1, 0]), np.array([0, 0, 1])]
        )

        similarity_matrix, valid_ids = analyzer.compute_pairwise_similarity(
            ["doc1", "doc2", "doc3"]
        )

        assert similarity_matrix.shape == (3, 3)
        assert len(valid_ids) == 3

        # Diagonal should be 1 (self-similarity)
        assert np.allclose(np.diag(similarity_matrix), 1.0)

        # doc1 and doc2 should be similar
        assert similarity_matrix[0, 1] > 0.8

        # doc1 and doc3 should be dissimilar
        assert similarity_matrix[0, 2] < 0.2


class TestDocumentClusterer:
    """
    Test document clustering.
    """

    @pytest.fixture
    def clusterer(self):
        """
        Create clusterer instance.
        """
        with patch("search_intelligence.similarity.DocumentSimilarityAnalyzer"):
            with patch("search_intelligence.similarity.SimpleDB"):
                return DocumentClusterer()

    def test_cluster_documents(self, clusterer):
        """
        Test DBSCAN clustering.
        """
        import numpy as np

        # Mock similarity matrix (3 clusters)
        similarity_matrix = np.array(
            [
                [1.0, 0.9, 0.1, 0.1],  # doc1, doc2 similar
                [0.9, 1.0, 0.1, 0.1],
                [0.1, 0.1, 1.0, 0.8],  # doc3, doc4 similar
                [0.1, 0.1, 0.8, 1.0],
            ]
        )

        clusterer.analyzer.compute_pairwise_similarity = MagicMock(
            return_value=(similarity_matrix, ["doc1", "doc2", "doc3", "doc4"])
        )

        clusters = clusterer.cluster_documents(
            ["doc1", "doc2", "doc3", "doc4"], threshold=0.7, min_samples=2
        )

        # Should find 2 clusters
        assert len(clusters) == 2

        # Each cluster should have 2 members
        for cluster_id, members in clusters.items():
            if cluster_id != -1:  # Not noise
                assert len(members) == 2

    def test_store_cluster_relationships(self, clusterer):
        """
        Test storing cluster relationships.
        """
        clusterer.db.add_relationship_cache = MagicMock()

        clusters = {0: ["doc1", "doc2", "doc3"], 1: ["doc4", "doc5"]}

        clusterer.store_cluster_relationships(clusters)

        # Should store relationships between cluster members
        # Cluster 0: 3 members = 3 relationships (1-2, 1-3, 2-3)
        # Cluster 1: 2 members = 1 relationship (4-5)
        assert clusterer.db.add_relationship_cache.call_count == 4


class TestDuplicateDetector:
    """
    Test duplicate detection.
    """

    @pytest.fixture
    def detector(self):
        """
        Create detector instance.
        """
        with patch("search_intelligence.duplicate_detector.get_embedding_service"):
            with patch("search_intelligence.duplicate_detector.get_vector_store"):
                with patch("search_intelligence.duplicate_detector.SimpleDB"):
                    return DuplicateDetector()

    def test_detect_exact_duplicates(self, detector):
        """
        Test exact duplicate detection using hashes.
        """
        documents = [
            {"content_id": "doc1", "content": "This is content A"},
            {"content_id": "doc2", "content": "This is content A"},  # Duplicate
            {"content_id": "doc3", "content": "This is content B"},
            {"content_id": "doc4", "content": "This is content B"},  # Duplicate
        ]

        exact_dups = detector._detect_exact_duplicates(documents)

        # Should find 2 duplicate groups
        assert len(exact_dups) == 2

        for group in exact_dups:
            assert group["type"] == "exact"
            assert group["count"] == 2

    def test_detect_semantic_duplicates(self, detector):
        """
        Test semantic duplicate detection.
        """
        import numpy as np

        documents = [
            {"content_id": "doc1", "content": "Content 1"},
            {"content_id": "doc2", "content": "Content 2"},
            {"content_id": "doc3", "content": "Content 3"},
        ]

        # Mock embeddings - doc1 and doc2 are similar
        detector._get_document_embedding = MagicMock(
            side_effect=[
                np.array([1, 0, 0]),
                np.array([0.98, 0.02, 0]),  # Similar to doc1
                np.array([0, 0, 1]),  # Different
            ]
        )

        near_dups = detector._detect_semantic_duplicates(documents, threshold=0.95, exact_groups=[])

        # Should find doc1 and doc2 as near duplicates
        assert len(near_dups) == 1
        assert set(near_dups[0]["members"]) == {"doc1", "doc2"}
        assert near_dups[0]["type"] == "semantic"

    def test_remove_duplicates(self, detector):
        """
        Test duplicate removal strategies.
        """
        detector.db.add_relationship_cache = MagicMock()
        detector._get_document = MagicMock(return_value={"created_at": "2024-01-01"})

        duplicate_groups = [{"members": ["doc1", "doc2", "doc3"]}, {"members": ["doc4", "doc5"]}]

        # Test "first" strategy
        result = detector.remove_duplicates(duplicate_groups, keep_strategy="first")

        assert result["kept_count"] == 2  # One from each group
        assert result["removed_count"] == 3  # Others removed
        assert "doc1" in result["kept_documents"]
        assert "doc4" in result["kept_documents"]

        # Should mark duplicates in database
        assert detector.db.add_relationship_cache.call_count == 3


class TestIntegration:
    """
    Integration tests for the complete module.
    """

    def test_singleton_pattern(self):
        """
        Test singleton pattern works correctly.
        """
        with patch("search_intelligence.main.get_search_service"):
            with patch("search_intelligence.main.get_embedding_service"):
                with patch("search_intelligence.main.get_vector_store"):
                    with patch("search_intelligence.main.SimpleDB"):
                        service1 = get_search_intelligence_service()
                        service2 = get_search_intelligence_service()

                        assert service1 is service2

                        # Different collection should create new instance
                        service3 = get_search_intelligence_service("documents")
                        assert service3 is not service1

    def test_end_to_end_search_flow(self):
        """
        Test complete search flow.
        """
        with patch("search_intelligence.main.get_search_service"):
            with patch("search_intelligence.main.get_embedding_service"):
                with patch("search_intelligence.main.get_vector_store"):
                    with patch("search_intelligence.main.SimpleDB"):
                        service = get_search_intelligence_service()

                        # Mock search results
                        service.search_service.search = MagicMock(
                            return_value=[
                                {
                                    "id": "doc1",
                                    "score": 0.9,
                                    "content": {"body": "Legal contract agreement"},
                                    "metadata": {},
                                }
                            ]
                        )

                        # Mock entity extraction
                        service.entity_service = MagicMock()
                        service.entity_service.extract_entities = MagicMock(
                            return_value=[{"text": "contract", "label": "LEGAL"}]
                        )

                        # Mock summarization
                        service.summarizer.extract_summary = MagicMock(
                            return_value={
                                "summary": "Legal agreement summary",
                                "keywords": {"legal": 0.9},
                                "sentences": ["Key point"],
                            }
                        )

                        # Perform smart search
                        results = service.smart_search_with_preprocessing("legal contract", limit=5)

                        assert len(results) > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
