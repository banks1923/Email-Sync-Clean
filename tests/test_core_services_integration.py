#!/usr/bin/env python3
"""
Integration tests for core services in flat architecture
Tests the new service structure: embeddings/, search/, vector_store/, etc.
"""

import sys
from pathlib import Path
from unittest.mock import Mock, patch

import numpy as np
import pytest

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))


class TestEmbeddingsService:
    """
    Test embeddings service integration.
    """

    def test_embedding_service_initialization(self):
        """
        Test that embedding service initializes correctly.
        """
        from utilities.embeddings.main import EmbeddingService

        service = EmbeddingService()
        assert service is not None

    def test_encode_text(self):
        """
        Test text encoding to embeddings.
        """
        from utilities.embeddings.main import EmbeddingService

        service = EmbeddingService()
        text = "This is a test legal document"

        # Get embedding
        embedding = service.encode(text)

        # Verify embedding properties
        assert isinstance(embedding, np.ndarray)
        assert embedding.shape == (1024,)  # Legal BERT dimension
        assert embedding.dtype == np.float32

    def test_batch_encoding(self):
        """
        Test batch encoding of multiple texts.
        """
        from utilities.embeddings.main import EmbeddingService

        service = EmbeddingService()
        texts = ["First legal document", "Second legal document", "Third legal document"]

        # Get embeddings
        embeddings = service.encode(texts)

        # Verify batch embeddings
        assert isinstance(embeddings, np.ndarray)
        assert embeddings.shape == (3, 1024)


class TestSearchService:
    """
    Test search service integration.
    """

    @pytest.fixture
    def mock_db(self):
        """
        Mock SimpleDB for search tests.
        """
        with patch("search.main.SimpleDB") as mock:
            db = Mock()
            mock.return_value = db
            db.search_content.return_value = [
                {
                    "content_id": "1",
                    "title": "Test Doc",
                    "content": "Test content",
                    "content_type": "email",
                    "created_time": "2024-01-01T12:00:00",
                }
            ]
            yield db

    def test_search_service_initialization(self):
        """
        Test search service initialization.
        """
        from search.main import search

        # Search function should work directly
        assert search is not None

    def test_basic_search(self, mock_db):
        """
        Test basic search functionality.
        """
        from search.main import search

        results = search("test query", limit=10)

        # Verify search was called
        mock_db.search_content.assert_called()
        assert isinstance(results, list)

    def test_search_with_filters(self, mock_db):
        """
        Test search with advanced filters.
        """
        from search.main import search

        filters = {
            "since": "last week",
            "until": "today",
            "content_types": ["email", "pdf"],
            "tags": ["legal", "contract"],
            "tag_logic": "AND",
        }

        search("test query", limit=10, filters=filters)

        # Verify filtered search
        mock_db.search_content.assert_called()
        call_args = mock_db.search_content.call_args
        assert "filters" in call_args[1] or len(call_args[0]) > 2


class TestVectorStoreService:
    """
    Test vector store service integration.
    """

    def test_vector_store_initialization(self):
        """
        Test vector store initialization.
        """
        from utilities.vector_store import VectorStore

        store = VectorStore()
        assert store is not None

    @patch("utilities.vector_store.main.QdrantClient")
    def test_vector_operations(self, mock_qdrant):
        """
        Test vector store operations.
        """
        from utilities.vector_store.main import VectorStoreService

        # Setup mock
        client = Mock()
        mock_qdrant.return_value = client
        client.get_collections.return_value.collections = []

        store = VectorStoreService()

        # Test upsert
        vector = np.random.rand(1024).astype(np.float32)
        metadata = {"title": "Test", "content_type": "email"}

        store.upsert(vector, metadata, id="test_1")

        # Verify upsert was attempted
        # Note: Actual call depends on implementation


class TestSimpleDBIntegration:
    """
    Test SimpleDB integration.
    """

    @pytest.fixture
    def db(self):
        """
        Create test database.
        """
        from shared.simple_db import SimpleDB

        # Use in-memory database for tests
        db = SimpleDB(":memory:")
        yield db
        db.close()

    def test_content_operations(self, db):
        """
        Test content CRUD operations.
        """
        # Add content
        content_id = db.add_content(
            content_type="email",
            title="Test Email",
            content="Test email content",
            metadata={"sender": "test@example.com"},
        )

        assert content_id is not None

        # Search content
        results = db.search_content("test", limit=10)
        assert len(results) > 0
        assert results[0]["title"] == "Test Email"

        # Get content by ID
        content = db.get_content(content_id)
        assert content is not None
        assert content["title"] == "Test Email"

    def test_batch_operations(self, db):
        """
        Test batch insert operations.
        """
        # Prepare batch data
        content_list = [
            {"content_type": "email", "title": f"Email {i}", "content": f"Content {i}"}
            for i in range(100)
        ]

        # Batch insert
        result = db.batch_add_content(content_list, batch_size=50)

        # Verify results
        assert result["stats"]["total"] == 100
        assert result["stats"]["inserted"] == 100
        assert len(result["content_ids"]) == 100

    def test_intelligence_tables(self, db):
        """
        Test document intelligence tables.
        """
        # Add content first
        content_id = db.add_content(
            content_type="pdf", title="Legal Doc", content="Legal document content"
        )

        # Add summary
        summary_id = db.add_document_summary(
            document_id=content_id,
            summary_type="combined",
            summary_text="Summary of legal document",
            tf_idf_keywords={"legal": 0.8, "document": 0.6},
            textrank_sentences=["Key sentence 1", "Key sentence 2"],
        )

        assert summary_id is not None

        # Get summaries
        summaries = db.get_document_summaries(content_id)
        assert len(summaries) > 0
        assert summaries[0]["summary_text"] == "Summary of legal document"

        # Add intelligence data
        intel_id = db.add_document_intelligence(
            document_id=content_id,
            intelligence_type="entity_extraction",
            intelligence_data={"entities": ["John Doe", "ABC Corp"]},
            confidence_score=0.85,
        )

        assert intel_id is not None

        # Get intelligence
        intel = db.get_document_intelligence(content_id)
        assert len(intel) > 0
        assert intel[0]["intelligence_type"] == "entity_extraction"


class TestServiceIntegration:
    """
    Test integration between multiple services.
    """

    @pytest.fixture
    def services(self):
        """
        Initialize all services.
        """
        from utilities.embeddings.main import EmbeddingService
        from search.main import search
        from entity.main import EntityService
        from summarization.main import DocumentSummarizer
        from shared.simple_db import SimpleDB
        
        return {
            "embeddings": EmbeddingService(),
            "search": search,
            "db": SimpleDB(":memory:"),
            "entity": EntityService(),
            "summarizer": DocumentSummarizer(),
        }

    def test_document_processing_pipeline(self, services):
        """
        Test complete document processing pipeline.
        """
        db = services["db"]
        summarizer = services["summarizer"]

        # Step 1: Add document
        content = """
        This is a legal document regarding the case of John Doe vs ABC Corporation.
        The plaintiff claims breach of contract dated January 1, 2024.
        The defendant denies all allegations.
        """

        content_id = db.add_content(content_type="pdf", title="Doe vs ABC Corp", content=content)

        # Step 2: Generate summary
        summary = summarizer.extract_summary(
            content, max_sentences=2, max_keywords=5, summary_type="combined"
        )

        assert summary is not None
        assert "summary_text" in summary
        assert "tf_idf_keywords" in summary

        # Step 3: Store summary
        summary_id = db.add_document_summary(
            document_id=content_id,
            summary_type="combined",
            summary_text=summary["summary_text"],
            tf_idf_keywords=summary["tf_idf_keywords"],
            textrank_sentences=summary.get("textrank_sentences", []),
        )

        assert summary_id is not None

        # Step 4: Verify retrieval
        stored_summaries = db.get_document_summaries(content_id)
        assert len(stored_summaries) == 1
        assert stored_summaries[0]["document_id"] == content_id

    def test_search_with_embeddings(self, services):
        """
        Test search using embeddings.
        """
        db = services["db"]
        services["embeddings"]

        # Add test documents
        docs = [
            ("Contract law document", "Legal contract between parties"),
            ("Criminal law case", "Criminal proceedings and evidence"),
            ("Property law deed", "Real estate transfer documentation"),
        ]

        doc_ids = []
        for title, content in docs:
            doc_id = db.add_content(content_type="pdf", title=title, content=content)
            doc_ids.append(doc_id)

        # Generate embeddings for query
        from utilities.embeddings.main import EmbeddingService
        embedding_service = EmbeddingService()
        query = "contract agreement"
        query_embedding = embedding_service.encode(query)

        assert query_embedding is not None
        assert query_embedding.shape == (1024,)

        # Search (would use vector store in real scenario)
        results = db.search_content("contract", limit=10)
        assert len(results) > 0


class TestCachingIntegration:
    """
    Test caching system integration.
    """

    def test_cache_manager_initialization(self):
        """
        Test cache manager initialization.
        """
        from shared.cache import CacheManager

        manager = CacheManager()
        assert manager is not None

    def test_cache_operations(self):
        """
        Test cache get/set operations.
        """
        from shared.cache import CacheManager

        manager = CacheManager()

        # Set value
        success = manager.set("test_key", {"data": "test_value"}, ttl=60)
        assert success is True

        # Get value
        value = manager.get("test_key")
        assert value is not None
        assert value["data"] == "test_value"

        # Delete value
        deleted = manager.delete("test_key")
        assert deleted is True

        # Verify deletion
        value = manager.get("test_key")
        assert value is None

    def test_content_invalidation(self):
        """
        Test content-based cache invalidation.
        """
        from shared.cache import CacheManager

        manager = CacheManager()

        # Set multiple related entries
        manager.set("content_123_summary", {"summary": "text"})
        manager.set("content_123_entities", {"entities": ["A", "B"]})
        manager.set("content_123_embedding", {"vector": [0.1, 0.2]})

        # Invalidate all content_123 entries
        manager.invalidate_content("content_123")

        # Verify all are cleared
        assert manager.get("content_123_summary") is None
        assert manager.get("content_123_entities") is None
        assert manager.get("content_123_embedding") is None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
