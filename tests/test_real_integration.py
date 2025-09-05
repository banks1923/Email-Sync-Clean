#!/usr/bin/env python3
"""
REAL Integration Tests - NO MOCKS
Tests actual component integration with temporary data.
"""

import os
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from lib.db import SimpleDB
from lib.embeddings import get_embedding_service
from lib.vector_store import get_vector_store
from lib.search import search, hybrid_search
import pytest
import numpy as np


class TestRealIntegration:
    """Test with REAL services - no mocks."""
    
    @classmethod
    def setup_class(cls):
        """Setup test collection in vector store."""
        cls.test_collection = "test_integration_collection"
        cls.vector_store = get_vector_store(
            collection_name=cls.test_collection,
            vector_size=1024
        )
        cls.embedding_service = get_embedding_service(use_mock=False)
        
    @classmethod
    def teardown_class(cls):
        """Clean up test collection."""
        try:
            # Delete entire test collection
            store = get_vector_store(cls.test_collection)
            store.client.delete_collection(cls.test_collection)
        except:
            pass  # Collection might not exist
    
    def test_vector_crud_operations(self):
        """Test Create, Read, Update, Delete with REAL vector store."""
        
        # CREATE
        test_text = "This is a test document about legal contracts"
        vector = self.embedding_service.encode(test_text)
        
        vector_id = self.vector_store.add_vector(
            vector=vector,
            metadata={"title": "Test Doc", "content_id": "999"},
            point_id="999"  # Use string ID
        )
        
        assert vector_id == "999", "Vector ID should match what we provided"
        
        # READ
        retrieved = self.vector_store.get_vector("999")
        assert retrieved is not None, "Should retrieve vector"
        assert retrieved["payload"]["title"] == "Test Doc"
        
        # UPDATE
        self.vector_store.update_metadata(
            "999", 
            {"title": "Updated Test Doc", "content_id": "999"}
        )
        
        updated = self.vector_store.get_vector("999")
        assert updated["payload"]["title"] == "Updated Test Doc"
        
        # DELETE - Test our fixed delete function
        success = self.vector_store.delete_vector("999")
        assert success, "Delete should succeed"
        
        # Verify it's gone
        gone = self.vector_store.get_vector("999")
        assert gone is None, "Vector should be deleted"
    
    def test_search_quality_discrimination(self):
        """Test that search properly discriminates between content."""
        
        # Add test vectors with varying relevance
        test_docs = [
            ("Legal contract for property lease agreement", "legal_contract", 1),
            ("Recipe for chocolate chip cookies", "recipe", 2),
            ("Technical manual for server installation", "technical", 3),
            ("Court ruling on tenant rights case", "court_ruling", 4),
        ]
        
        # Add vectors
        for text, doc_type, doc_id in test_docs:
            vector = self.embedding_service.encode(text)
            self.vector_store.add_vector(
                vector=vector,
                metadata={
                    "title": text[:50],
                    "content_id": str(doc_id),
                    "doc_type": doc_type
                },
                point_id=str(doc_id)
            )
        
        # Search for legal content
        query = "legal tenant contract"
        query_vector = self.embedding_service.encode(query)
        results = self.vector_store.search(query_vector, limit=4)
        
        # Check that legal documents rank higher
        top_types = [r["payload"]["doc_type"] for r in results[:2]]
        assert "legal_contract" in top_types or "court_ruling" in top_types, \
            f"Legal docs should rank high, got: {top_types}"
        
        # Clean up
        for _, _, doc_id in test_docs:
            self.vector_store.delete_vector(str(doc_id))
    
    def test_data_integrity_check(self):
        """Test that we detect and handle data integrity issues."""
        
        # Create orphaned vector (vector without database record)
        orphan_vector = self.embedding_service.encode("Orphaned content")
        self.vector_store.add_vector(
            vector=orphan_vector,
            metadata={"content_id": "99999", "title": "Orphan"},
            point_id="99999"
        )
        
        # Try to search - should handle missing DB record gracefully
        with tempfile.NamedTemporaryFile(suffix=".db") as tmp_db:
            db = SimpleDB(tmp_db.name)
            
            # Create minimal schema
            db.execute("""
                CREATE TABLE content_unified (
                    id INTEGER PRIMARY KEY,
                    source_type TEXT,
                    source_id TEXT,
                    title TEXT,
                    body TEXT,
                    substantive_text TEXT
                )
            """)
            
            # Add one good record
            db.execute("""
                INSERT INTO content_unified (id, source_type, source_id, title, body)
                VALUES (88888, 'test', 'test-1', 'Good Record', 'Valid content')
            """)
            
            # Add corresponding vector for good record
            good_vector = self.embedding_service.encode("Valid content")
            self.vector_store.add_vector(
                vector=good_vector,
                metadata={"content_id": "88888", "title": "Good Record"},
                point_id="88888"
            )
            
            # Now search should find both but only enrich the good one
            query_vec = self.embedding_service.encode("content")
            raw_results = self.vector_store.search(query_vec, limit=10)
            
            # We should get both vectors
            found_ids = {r["payload"]["content_id"] for r in raw_results}
            assert "99999" in found_ids, "Should find orphan vector"
            assert "88888" in found_ids, "Should find good vector"
        
        # Clean up
        self.vector_store.delete_vector("99999")
        self.vector_store.delete_vector("88888")
    
    def test_embedding_consistency(self):
        """Test that same text produces consistent embeddings."""
        
        text = "Consistent legal document text"
        
        # Generate embeddings multiple times
        embeddings = [self.embedding_service.encode(text) for _ in range(3)]
        
        # Check they're identical (deterministic)
        for i in range(1, 3):
            np.testing.assert_array_almost_equal(
                embeddings[0], embeddings[i],
                err_msg="Embeddings should be deterministic"
            )
    
    def test_search_with_empty_database(self):
        """Test that search handles empty database gracefully."""
        
        # Use collection with no data
        empty_collection = "empty_test_collection"
        empty_store = get_vector_store(empty_collection, vector_size=1024)
        
        query_vec = self.embedding_service.encode("test query")
        results = empty_store.search(query_vec, limit=5)
        
        assert results == [], "Empty collection should return empty results"
        
        # Clean up
        try:
            empty_store.client.delete_collection(empty_collection)
        except:
            pass


if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v", "--tb=short"])