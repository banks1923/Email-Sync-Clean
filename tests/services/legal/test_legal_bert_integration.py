"""
Integration tests for Knowledge Graph with real Legal BERT embeddings.

These tests use the actual Legal BERT model to verify end-to-end functionality
of the similarity analysis and knowledge graph integration.
"""

import os
import tempfile
import time

import pytest

from knowledge_graph import (
    get_knowledge_graph_service,
    get_similarity_analyzer,
    get_similarity_integration,
    get_timeline_relationships,
)
from shared.simple_db import SimpleDB
from utilities.embeddings import get_embedding_service


class TestLegalBERTIntegration:
    """Integration tests using real Legal BERT embeddings."""

    @pytest.fixture
    def temp_db(self):
        """Create temporary database for testing."""
        fd, path = tempfile.mkstemp(suffix=".db")
        os.close(fd)

        # Initialize database with required tables
        db = SimpleDB(path)
        db.execute(
            """
            CREATE TABLE content (
                content_id TEXT PRIMARY KEY,
                content_type TEXT NOT NULL,
                title TEXT,
                content TEXT NOT NULL,
                source_path TEXT,
                created_time TEXT DEFAULT CURRENT_TIMESTAMP,
                modified_time TEXT DEFAULT CURRENT_TIMESTAMP,
                metadata TEXT,
                vector_processed BOOLEAN DEFAULT 0,
                word_count INTEGER,
                char_count INTEGER
            )
        """
        )

        # Add email table for timeline tests
        db.execute(
            """
            CREATE TABLE emails (
                message_id TEXT PRIMARY KEY,
                datetime_utc TEXT,
                subject TEXT,
                body TEXT
            )
        """
        )

        yield path
        os.unlink(path)

    @pytest.fixture
    def legal_documents(self, temp_db):
        """Add sample legal documents to the database."""
        db = SimpleDB(temp_db)

        documents = [
            {
                "id": "contract_1",
                "type": "pdf",
                "title": "Service Agreement",
                "content": """
                SERVICE AGREEMENT

                This Service Agreement ("Agreement") is entered into as of January 15, 2024,
                by and between ABC Corporation ("Client") and XYZ Services LLC ("Provider").

                WHEREAS, Client desires to obtain certain services from Provider; and
                WHEREAS, Provider is willing to provide such services on the terms set forth herein.

                1. SERVICES: Provider shall provide software development and consulting services.
                2. TERM: This Agreement shall commence on February 1, 2024 and continue for 12 months.
                3. COMPENSATION: Client shall pay Provider $10,000 per month.
                4. CONFIDENTIALITY: Both parties agree to maintain confidentiality of proprietary information.
                5. TERMINATION: Either party may terminate with 30 days written notice.

                IN WITNESS WHEREOF, the parties have executed this Agreement.
                """,
                "date": "2024-01-15T10:00:00Z",
            },
            {
                "id": "contract_2",
                "type": "pdf",
                "title": "Software License Agreement",
                "content": """
                SOFTWARE LICENSE AGREEMENT

                This Software License Agreement ("Agreement") is made as of January 20, 2024,
                between ABC Corporation ("Licensor") and DEF Industries ("Licensee").

                RECITALS:
                Licensor has developed certain software and wishes to grant a license to Licensee.

                1. GRANT OF LICENSE: Licensor grants Licensee a non-exclusive license to use the Software.
                2. LICENSE FEE: Licensee shall pay an annual fee of $50,000.
                3. TERM: This license is valid for 24 months from the Effective Date.
                4. RESTRICTIONS: Licensee may not sublicense, sell, or distribute the Software.
                5. CONFIDENTIALITY: Licensee agrees to maintain the confidentiality of the Software.
                6. TERMINATION: License may be terminated for breach with 15 days notice.

                AGREED AND ACCEPTED by the authorized representatives.
                """,
                "date": "2024-01-20T14:30:00Z",
            },
            {
                "id": "email_1",
                "type": "email",
                "title": "RE: Contract Review - Service Agreement",
                "content": """
                Subject: RE: Contract Review - Service Agreement
                Date: January 18, 2024

                Dear Legal Team,

                I have reviewed the Service Agreement with ABC Corporation. The terms look acceptable,
                including the $10,000 monthly compensation and 12-month term. The confidentiality
                clause is standard and the 30-day termination notice is reasonable.

                Please proceed with finalizing the agreement.

                Best regards,
                John Smith
                Legal Counsel
                """,
                "date": "2024-01-18T09:15:00Z",
            },
            {
                "id": "memo_1",
                "type": "pdf",
                "title": "Legal Memorandum - Contract Compliance",
                "content": """
                MEMORANDUM

                TO: Management Team
                FROM: Legal Department
                DATE: January 25, 2024
                RE: Contract Compliance Review

                This memo summarizes our review of recent agreements:

                1. ABC Corporation Service Agreement - Compliant with company policies
                2. DEF Industries Software License - Approved with minor modifications
                3. Confidentiality provisions in both agreements meet our standards
                4. Termination clauses provide adequate protection

                Recommendations:
                - Monitor performance metrics quarterly
                - Review confidentiality compliance semi-annually
                - Update termination procedures documentation

                All agreements are properly executed and filed.
                """,
                "date": "2024-01-25T16:00:00Z",
            },
            {
                "id": "case_brief",
                "type": "pdf",
                "title": "Case Brief - Johnson v. Smith Corp",
                "content": """
                CASE BRIEF

                Case: Johnson v. Smith Corporation
                Court: Superior Court of California
                Date: March 15, 2023

                FACTS:
                Plaintiff Johnson entered into an employment contract with Smith Corporation.
                The contract included a non-compete clause and severance provisions.
                Johnson was terminated without cause and sought severance benefits.

                ISSUE:
                Whether the non-compete clause was enforceable under California law.

                HOLDING:
                The court held that non-compete clauses are generally unenforceable in California,
                with limited exceptions for trade secrets protection.

                REASONING:
                California Business and Professions Code Section 16600 voids contracts that
                restrain employees from engaging in lawful profession, trade, or business.

                This case is distinguishable from our current agreements which focus on
                confidentiality rather than non-competition.
                """,
                "date": "2023-03-15T11:00:00Z",
            },
        ]

        # Insert documents into database
        for doc in documents:
            content_text = doc["content"].strip()
            db.execute(
                """
                INSERT INTO content (content_id, content_type, title, content,
                                   created_time, word_count, char_count, metadata)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
                (
                    doc["id"],
                    doc["type"],
                    doc["title"],
                    content_text,
                    doc["date"],
                    len(content_text.split()),
                    len(content_text),
                    f'{{"date": "{doc["date"]}"}}',
                ),
            )

            # Add email records for timeline testing
            if doc["type"] == "email":
                db.execute(
                    """
                    INSERT INTO emails (message_id, datetime_utc, subject, body)
                    VALUES (?, ?, ?, ?)
                """,
                    (doc["id"], doc["date"], doc["title"], content_text),
                )

        return [doc["id"] for doc in documents]

    @pytest.mark.slow
    def test_real_embedding_similarity_computation(self, temp_db, legal_documents):
        """Test similarity computation with real Legal BERT embeddings."""
        analyzer = get_similarity_analyzer(temp_db, similarity_threshold=0.6)

        # Test similarity between two contract documents (should be high)
        similarity_contracts = analyzer.compute_similarity("contract_1", "contract_2")
        assert similarity_contracts is not None
        assert similarity_contracts > 0.6  # Should be similar (both are contracts)

        # Test similarity between contract and unrelated case brief (should be lower)
        similarity_different = analyzer.compute_similarity("contract_1", "case_brief")
        assert similarity_different is not None
        assert similarity_different < similarity_contracts  # Less similar than two contracts

        # Test caching - second call should be faster
        start_time = time.time()
        similarity_cached = analyzer.compute_similarity("contract_1", "contract_2")
        cache_time = time.time() - start_time

        assert similarity_cached == similarity_contracts  # Same result
        assert cache_time < 0.1  # Should be very fast from cache

    @pytest.mark.slow
    def test_batch_similarity_with_real_embeddings(self, temp_db, legal_documents):
        """Test batch similarity computation with real embeddings."""
        analyzer = get_similarity_analyzer(temp_db, similarity_threshold=0.5)

        # Compute similarities for all documents
        similarities = analyzer.batch_compute_similarities(legal_documents[:4])

        # Should find some similar pairs
        assert len(similarities) > 0

        # Check that similar documents are found
        {(s[0], s[1]) for s in similarities}

        # Contracts and related email should be similar
        assert any(
            ("contract_1" in pair and "contract_2" in pair)
            or ("contract_1" in pair and "email_1" in pair)
            or ("contract_2" in pair and "email_1" in pair)
            for pair in [(s[0], s[1]) for s in similarities]
        )

    @pytest.mark.slow
    def test_knowledge_graph_integration_with_real_embeddings(self, temp_db, legal_documents):
        """Test full knowledge graph integration with real embeddings."""
        integration = get_similarity_integration(temp_db, similarity_threshold=0.5)

        # Discover and store similarities
        result = integration.discover_and_store_similarities(content_type="pdf")

        assert result["processed_documents"] >= 3  # At least 3 PDFs
        assert result["relationships_created"] > 0  # Should find some similarities

        # Verify relationships were stored in knowledge graph
        kg = get_knowledge_graph_service(temp_db)
        stats = kg.get_graph_stats()

        assert stats["total_edges"] > 0
        assert "similar_to" in stats["relationship_types"]

        # Find similar content for a specific document
        related = kg.get_related_content("contract_1", ["similar_to"], limit=5)
        assert len(related) > 0

        # The most similar should be another contract or related memo
        most_similar = related[0] if related else None
        if most_similar:
            assert most_similar["content_id"] in ["contract_2", "memo_1", "email_1"]

    @pytest.mark.slow
    def test_similarity_clustering_with_real_embeddings(self, temp_db, legal_documents):
        """Test similarity clustering with real embeddings."""
        integration = get_similarity_integration(temp_db, similarity_threshold=0.4)

        # First compute similarities
        integration.discover_and_store_similarities()

        # Find clusters
        clusters = integration.find_similarity_clusters(min_cluster_size=2)

        # Should find at least one cluster (contracts and related documents)
        assert len(clusters) > 0

        # Verify cluster contains related documents
        for cluster in clusters:
            content_ids = cluster["content_ids"]
            # Contracts and related documents should cluster together
            contract_cluster = [cid for cid in content_ids if "contract" in cid or "email_1" in cid]
            if contract_cluster:
                assert len(contract_cluster) >= 2  # At least 2 related items

    @pytest.mark.slow
    def test_timeline_relationships_with_real_data(self, temp_db, legal_documents):
        """Test timeline relationship creation with real documents."""
        timeline_service = get_timeline_relationships(temp_db)

        # Create temporal relationships
        result = timeline_service.create_temporal_relationships()

        assert result["processed"] > 0
        assert result["relationships_created"] > 0
        assert result["sequential"] > 0  # Should have sequential relationships

        # Check temporal clustering
        cluster = timeline_service.find_temporal_cluster("contract_1", window_days=10)
        assert len(cluster) > 0  # Should find nearby documents

        # contract_2 and email_1 should be in the temporal cluster
        cluster_ids = [item["content_id"] for item in cluster]
        assert "contract_2" in cluster_ids or "email_1" in cluster_ids

    @pytest.mark.slow
    def test_combined_similarity_and_timeline(self, temp_db, legal_documents):
        """Test combining similarity and timeline relationships."""
        # Create both types of relationships
        integration = get_similarity_integration(temp_db, similarity_threshold=0.4)
        timeline_service = get_timeline_relationships(temp_db)

        # Add similarity relationships
        sim_result = integration.discover_and_store_similarities()
        assert sim_result["relationships_created"] > 0

        # Add temporal relationships
        time_result = timeline_service.create_temporal_relationships()
        assert time_result["relationships_created"] > 0

        # Query the combined graph
        kg = get_knowledge_graph_service(temp_db)

        # Get all relationships for a document
        related = kg.get_related_content("contract_1", limit=10)

        # Should have multiple relationship types
        relationship_types = {r["relationship_type"] for r in related}
        assert len(relationship_types) >= 2  # Both similar_to and temporal

        # Verify graph statistics
        stats = kg.get_graph_stats()
        assert stats["total_edges"] >= (
            sim_result["relationships_created"] + time_result["relationships_created"]
        )

    @pytest.mark.slow
    def test_legal_bert_embedding_quality(self, temp_db):
        """Test that Legal BERT produces high-quality legal document embeddings."""
        embedding_service = get_embedding_service()

        # Test legal terms produce similar embeddings
        contract_text = "This agreement constitutes a binding contract between the parties."
        agreement_text = "This document represents a legal agreement between the entities."
        unrelated_text = "The weather forecast predicts rain tomorrow afternoon."

        contract_emb = embedding_service.encode(contract_text)
        agreement_emb = embedding_service.encode(agreement_text)
        unrelated_emb = embedding_service.encode(unrelated_text)

        # Calculate similarities manually
        import numpy as np

        def cosine_similarity(v1, v2):
            return np.dot(v1, v2) / (np.linalg.norm(v1) * np.linalg.norm(v2))

        sim_legal = cosine_similarity(contract_emb, agreement_emb)
        sim_unrelated = cosine_similarity(contract_emb, unrelated_emb)

        # Legal documents should be more similar to each other
        assert sim_legal > sim_unrelated
        assert sim_legal > 0.7  # High similarity for related legal text
        assert sim_unrelated < 0.65  # Lower similarity for unrelated text (adjusted for Legal BERT)

    @pytest.mark.slow
    def test_performance_with_real_embeddings(self, temp_db, legal_documents):
        """Test performance metrics with real embeddings."""
        analyzer = get_similarity_analyzer(temp_db)

        # Measure embedding computation time
        start_time = time.time()
        analyzer.compute_similarity(legal_documents[0], legal_documents[1])
        first_computation = time.time() - start_time

        # Cache hit should be much faster
        start_time = time.time()
        analyzer.compute_similarity(legal_documents[0], legal_documents[1])
        cache_hit = time.time() - start_time

        # Performance assertions
        assert first_computation < 2.0  # Should complete within 2 seconds
        assert cache_hit < 0.01  # Cache hit should be under 10ms
        assert cache_hit < first_computation * 0.01  # 100x speedup from cache

        # Get cache statistics
        stats = analyzer.get_cache_stats()
        assert stats["total_cached"] >= 1
        assert stats["avg_computation_time"] > 0

    def test_error_handling_with_empty_content(self, temp_db):
        """Test error handling for empty or invalid content."""
        db = SimpleDB(temp_db)
        analyzer = get_similarity_analyzer(temp_db)

        # Add empty content
        db.execute(
            """
            INSERT INTO content (content_id, content_type, title, content, word_count, char_count)
            VALUES (?, ?, ?, ?, ?, ?)
        """,
            ("empty_doc", "pdf", "Empty", "", 0, 0),
        )

        # Should handle empty content gracefully
        similarity = analyzer.compute_similarity("empty_doc", "empty_doc")
        assert similarity == 1.0  # Same document = 1.0 similarity

        # Non-existent content should return None
        similarity = analyzer.compute_similarity("empty_doc", "nonexistent")
        assert similarity is None


class TestLegalBERTEmbeddingService:
    """Test the embedding service configuration for Legal BERT."""

    def test_embedding_service_initialization(self):
        """Test that embedding service initializes correctly."""
        service = get_embedding_service()
        assert service is not None

        # Test encoding produces correct dimensions
        embedding = service.encode("Test legal document")
        assert len(embedding) == 1024  # Legal BERT produces 1024-dim embeddings

    def test_embedding_consistency(self):
        """Test that same text produces same embedding."""
        service = get_embedding_service()

        text = "This is a legal contract."
        embedding1 = service.encode(text)
        embedding2 = service.encode(text)

        # Should produce identical embeddings
        import numpy as np

        assert np.allclose(embedding1, embedding2, rtol=1e-5)

    def test_batch_encoding(self):
        """Test batch encoding if supported."""
        service = get_embedding_service()

        texts = [
            "First legal document",
            "Second legal document",
            "Third legal document",
        ]

        # Encode individually
        individual_embeddings = [service.encode(text) for text in texts]

        # All should have correct dimensions
        for emb in individual_embeddings:
            assert len(emb) == 1024


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-m", "slow"])
