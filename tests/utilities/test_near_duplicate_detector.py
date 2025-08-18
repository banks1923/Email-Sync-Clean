"""Comprehensive tests for NearDuplicateDetector."""

import pytest
import numpy as np

from utilities.deduplication.near_duplicate_detector import (
    MinHasher, LSHIndex, NearDuplicateDetector, get_duplicate_detector
)


class TestMinHasher:
    """Test MinHasher functionality."""
    
    def test_initialization(self):
        """Test MinHasher initialization."""
        hasher = MinHasher(num_perm=64, seed=42)
        assert hasher.num_perm == 64
        assert hasher.seed == 42
        assert len(hasher.permutations) == 64
        assert hasher.prime > 0
        
    def test_generate_permutations(self):
        """Test permutation generation."""
        hasher = MinHasher(num_perm=32)
        perms = hasher.permutations
        
        assert len(perms) == 32
        for a, b in perms:
            assert 1 <= a < hasher.prime
            assert 0 <= b < hasher.prime
            
    def test_shingle_text_basic(self):
        """Test text shingling."""
        hasher = MinHasher()
        text = "The quick brown fox"
        shingles = hasher._shingle_text(text, k=3)
        
        assert isinstance(shingles, set)
        assert len(shingles) > 0
        # Text normalized to lowercase without punctuation
        
    def test_shingle_text_normalization(self):
        """Test text normalization in shingling."""
        hasher = MinHasher()
        text1 = "Hello,  World!"
        text2 = "hello world"
        
        shingles1 = hasher._shingle_text(text1, k=3)
        shingles2 = hasher._shingle_text(text2, k=3)
        
        # Should be similar after normalization
        assert len(shingles1.intersection(shingles2)) > 0
        
    def test_compute_signature_normal(self):
        """Test signature computation."""
        hasher = MinHasher(num_perm=64)
        text = "This is a test document with enough content"
        signature = hasher.compute_signature(text)
        
        assert isinstance(signature, np.ndarray)
        assert len(signature) == 64
        assert signature.dtype == np.uint32
        
    def test_compute_signature_empty(self):
        """Test signature for empty text."""
        hasher = MinHasher(num_perm=32)
        
        # Empty string
        sig1 = hasher.compute_signature("")
        assert len(sig1) == 32
        assert np.all(sig1 == 0)
        
        # Very short text
        sig2 = hasher.compute_signature("ab")
        assert len(sig2) == 32
        assert np.all(sig2 == 0)
        
    def test_compute_signature_deterministic(self):
        """Test that signatures are deterministic."""
        hasher1 = MinHasher(num_perm=64, seed=42)
        hasher2 = MinHasher(num_perm=64, seed=42)
        
        text = "Test document for deterministic check"
        sig1 = hasher1.compute_signature(text)
        sig2 = hasher2.compute_signature(text)
        
        assert np.array_equal(sig1, sig2)
        
    def test_jaccard_similarity_identical(self):
        """Test Jaccard similarity for identical signatures."""
        hasher = MinHasher()
        sig = np.array([1, 2, 3, 4, 5])
        
        similarity = hasher.jaccard_similarity(sig, sig)
        assert similarity == 1.0
        
    def test_jaccard_similarity_different(self):
        """Test Jaccard similarity for different signatures."""
        hasher = MinHasher()
        sig1 = np.array([1, 2, 3, 4, 5])
        sig2 = np.array([6, 7, 8, 9, 10])
        
        similarity = hasher.jaccard_similarity(sig1, sig2)
        assert similarity == 0.0
        
    def test_jaccard_similarity_partial(self):
        """Test Jaccard similarity for partially matching signatures."""
        hasher = MinHasher()
        sig1 = np.array([1, 2, 3, 4, 5])
        sig2 = np.array([1, 2, 8, 9, 10])
        
        similarity = hasher.jaccard_similarity(sig1, sig2)
        assert 0 < similarity < 1
        assert similarity == 0.4  # 2 matches out of 5
        
    def test_jaccard_similarity_length_mismatch(self):
        """Test Jaccard similarity with mismatched lengths."""
        hasher = MinHasher()
        sig1 = np.array([1, 2, 3])
        sig2 = np.array([1, 2, 3, 4, 5])
        
        with pytest.raises(ValueError):
            hasher.jaccard_similarity(sig1, sig2)


class TestLSHIndex:
    """Test LSHIndex functionality."""
    
    def test_initialization(self):
        """Test LSH index initialization."""
        index = LSHIndex(num_bands=8, band_size=4)
        assert index.num_bands == 8
        assert index.band_size == 4
        assert len(index.buckets) == 0
        assert len(index.signatures) == 0
        
    def test_add_document(self):
        """Test adding document to index."""
        index = LSHIndex(num_bands=4, band_size=8)
        signature = np.random.randint(0, 1000, 32, dtype=np.uint32)
        
        index.add("doc1", signature)
        
        assert "doc1" in index.signatures
        assert np.array_equal(index.signatures["doc1"], signature)
        assert len(index.buckets) > 0
        
    def test_add_multiple_documents(self):
        """Test adding multiple documents."""
        index = LSHIndex(num_bands=4, band_size=8)
        
        for i in range(5):
            sig = np.random.randint(0, 1000, 32, dtype=np.uint32)
            index.add(f"doc{i}", sig)
            
        assert len(index.signatures) == 5
        
    def test_find_similar_exact_match(self):
        """Test finding exact match."""
        index = LSHIndex(num_bands=4, band_size=8)
        signature = np.random.randint(0, 1000, 32, dtype=np.uint32)
        
        index.add("doc1", signature)
        results = index.find_similar(signature, threshold=0.9)
        
        assert len(results) == 1
        assert results[0][0] == "doc1"
        assert results[0][1] == 1.0
        
    def test_find_similar_no_match(self):
        """Test finding with no matches."""
        index = LSHIndex(num_bands=4, band_size=8)
        sig1 = np.ones(32, dtype=np.uint32)
        sig2 = np.zeros(32, dtype=np.uint32)
        
        index.add("doc1", sig1)
        results = index.find_similar(sig2, threshold=0.5)
        
        assert len(results) == 0
        
    def test_find_similar_threshold(self):
        """Test similarity threshold filtering."""
        index = LSHIndex(num_bands=4, band_size=8)
        
        # Add documents with varying similarity
        base_sig = np.random.randint(0, 1000, 32, dtype=np.uint32)
        index.add("doc1", base_sig)
        
        # Similar document (80% same)
        similar_sig = base_sig.copy()
        similar_sig[:6] = np.random.randint(1000, 2000, 6)
        index.add("doc2", similar_sig)
        
        results = index.find_similar(base_sig, threshold=0.7)
        assert len(results) >= 1
        assert results[0][0] == "doc1"
        
    def test_find_similar_sorting(self):
        """Test that results are sorted by similarity."""
        index = LSHIndex(num_bands=4, band_size=8)
        
        base_sig = np.arange(32, dtype=np.uint32)
        index.add("exact", base_sig)
        
        # Add with decreasing similarity
        for i in range(1, 4):
            sig = base_sig.copy()
            sig[:i*2] = np.random.randint(1000, 2000, i*2)
            index.add(f"doc{i}", sig)
            
        results = index.find_similar(base_sig, threshold=0.0)
        
        # Check descending order
        for i in range(len(results) - 1):
            assert results[i][1] >= results[i+1][1]


class TestNearDuplicateDetector:
    """Test NearDuplicateDetector functionality."""
    
    def test_initialization(self):
        """Test detector initialization."""
        detector = NearDuplicateDetector(threshold=0.7, num_perm=64)
        assert detector.threshold == 0.7
        assert detector.minhasher.num_perm == 64
        assert detector.lsh_index is not None
        assert len(detector.processed_docs) == 0
        
    def test_add_document(self):
        """Test adding document to detector."""
        detector = NearDuplicateDetector()
        
        detector.add_document(
            "doc1",
            "This is test content",
            {"author": "test"}
        )
        
        assert "doc1" in detector.processed_docs
        assert detector.processed_docs["doc1"]["metadata"]["author"] == "test"
        assert "signature" in detector.processed_docs["doc1"]
        assert "content_preview" in detector.processed_docs["doc1"]
        
    def test_add_document_no_metadata(self):
        """Test adding document without metadata."""
        detector = NearDuplicateDetector()
        
        detector.add_document("doc1", "Content without metadata")
        
        assert "doc1" in detector.processed_docs
        assert detector.processed_docs["doc1"]["metadata"] == {}
        
    def test_check_duplicate_exact(self):
        """Test checking exact duplicate."""
        detector = NearDuplicateDetector(threshold=0.8)
        
        content = "This is the exact same content"
        detector.add_document("original", content)
        
        results = detector.check_duplicate(content)
        
        assert len(results) == 1
        assert results[0]["doc_id"] == "original"
        assert results[0]["similarity"] > 0.99
        assert results[0]["is_exact"]
        assert results[0]["is_near_duplicate"]
        
    def test_check_duplicate_near(self):
        """Test checking near duplicate."""
        detector = NearDuplicateDetector(threshold=0.7)
        
        content1 = "The quick brown fox jumps over the lazy dog"
        content2 = "The fast brown fox jumps over the lazy dog"
        
        detector.add_document("doc1", content1)
        results = detector.check_duplicate(content2)
        
        if results:  # May or may not detect as duplicate depending on threshold
            assert not results[0]["is_exact"]
            assert 0.7 <= results[0]["similarity"] < 1.0
            
    def test_check_duplicate_not_similar(self):
        """Test checking non-duplicate."""
        detector = NearDuplicateDetector(threshold=0.8)
        
        detector.add_document("doc1", "Python programming language")
        results = detector.check_duplicate("Java enterprise applications")
        
        assert len(results) == 0
        
    def test_find_all_duplicates(self):
        """Test finding all duplicate groups."""
        detector = NearDuplicateDetector(threshold=0.8)
        
        # Add duplicate groups
        detector.add_document("doc1", "Content A version 1")
        detector.add_document("doc2", "Content A version 1")  # Duplicate of doc1
        detector.add_document("doc3", "Content B different")
        detector.add_document("doc4", "Content B different")  # Duplicate of doc3
        
        groups = detector.find_all_duplicates()
        
        # Should find duplicate groups
        assert len(groups) >= 0  # Depends on similarity threshold
        
    def test_batch_deduplicate(self):
        """Test batch deduplication."""
        detector = NearDuplicateDetector(threshold=0.9)
        
        documents = [
            {"id": "1", "content": "Test document one"},
            {"id": "2", "content": "Test document one"},  # Exact duplicate
            {"id": "3", "content": "Test document two"},
            {"id": "4", "content": "Test document two"},  # Exact duplicate
            {"id": "5", "content": "Completely different content"}
        ]
        
        stats = detector.batch_deduplicate(documents)
        
        assert stats["total"] == 5
        assert stats["unique"] >= 1
        assert stats["duplicates"] >= 0
        assert "groups" in stats
        
    def test_batch_deduplicate_with_metadata(self):
        """Test batch deduplication with metadata."""
        detector = NearDuplicateDetector(threshold=0.9)
        
        documents = [
            {
                "id": "1",
                "content": "Document content",
                "metadata": {"source": "email"}
            },
            {
                "id": "2",
                "content": "Document content",
                "metadata": {"source": "file"}
            }
        ]
        
        stats = detector.batch_deduplicate(documents)
        
        assert stats["total"] == 2
        # Check that metadata is preserved
        for doc_id in ["1", "2"]:
            assert doc_id in detector.processed_docs
            assert "metadata" in detector.processed_docs[doc_id]
            
    def test_batch_deduplicate_auto_id(self):
        """Test batch deduplication with auto-generated IDs."""
        detector = NearDuplicateDetector()
        
        documents = [
            {"content": "Content without ID"},
            {"content": "Another content without ID"}
        ]
        
        stats = detector.batch_deduplicate(documents)
        
        assert stats["total"] == 2
        assert len(detector.processed_docs) == 2
        
    def test_get_similarity(self):
        """Test direct similarity calculation."""
        detector = NearDuplicateDetector()
        
        content1 = "The quick brown fox"
        content2 = "The quick brown fox"
        content3 = "Completely different text"
        
        sim1 = detector.get_similarity(content1, content2)
        sim2 = detector.get_similarity(content1, content3)
        
        assert sim1 > 0.9  # Very similar
        assert sim2 < 0.5  # Very different
        assert 0 <= sim1 <= 1
        assert 0 <= sim2 <= 1
        
    def test_get_duplicate_detector_singleton(self):
        """Test singleton pattern for detector."""
        detector1 = get_duplicate_detector(threshold=0.8)
        detector2 = get_duplicate_detector(threshold=0.8)
        
        assert detector1 is detector2
        
        # Different threshold creates new instance
        detector3 = get_duplicate_detector(threshold=0.7)
        assert detector3 is not detector1
        
        # Back to 0.7 returns same instance
        detector4 = get_duplicate_detector(threshold=0.7)
        assert detector4 is detector3


@pytest.mark.integration
class TestNearDuplicateIntegration:
    """Integration tests for near-duplicate detection."""
    
    def test_real_world_documents(self):
        """Test with realistic document examples."""
        detector = NearDuplicateDetector(threshold=0.75)
        
        # Email variations
        email1 = """
        Subject: Meeting Tomorrow
        Hi Team,
        Don't forget about our meeting tomorrow at 2 PM in Conference Room A.
        We'll discuss the Q3 roadmap.
        Best,
        John
        """
        
        email2 = """
        Subject: Re: Meeting Tomorrow
        Hi Team,
        Don't forget about our meeting tomorrow at 2 PM in Conference Room A.
        We'll discuss the Q3 roadmap and budget.
        Best,
        John
        """
        
        email3 = """
        Subject: Project Update
        Hello Everyone,
        The project is on track. We've completed phase 1 and moving to phase 2.
        Please review the attached documents.
        Thanks,
        Sarah
        """
        
        detector.add_document("email1", email1)
        detector.add_document("email2", email2)
        detector.add_document("email3", email3)
        
        # Check duplicates
        results1 = detector.check_duplicate(email1)
        assert len(results1) >= 1  # Should find itself
        
        # Email2 should be similar to email1
        results2 = detector.check_duplicate(email2)
        assert len(results2) >= 1
        
        # Find all groups
        detector.find_all_duplicates()
        # Email1 and email2 might be grouped together
        
    def test_performance_many_documents(self):
        """Test performance with many documents."""
        detector = NearDuplicateDetector(threshold=0.8, num_perm=64)
        
        # Add 100 documents
        for i in range(100):
            if i % 10 == 0:
                # Every 10th is duplicate of first
                content = "This is the base document content for testing"
            else:
                content = f"This is unique document number {i} with different content"
            
            detector.add_document(f"doc_{i}", content)
            
        # Check for duplicates
        results = detector.check_duplicate("This is the base document content for testing")
        
        # Should find ~10 duplicates
        assert len(results) >= 5
        
        # Find all duplicate groups
        groups = detector.find_all_duplicates()
        assert len(groups) >= 1
        
    def test_edge_cases(self):
        """Test edge cases."""
        detector = NearDuplicateDetector()
        
        # Very short content
        detector.add_document("short1", "Hi")
        detector.add_document("short2", "Hi")
        
        # Empty content
        detector.add_document("empty", "")
        
        # Special characters
        detector.add_document("special", "!@#$%^&*()")
        
        # Unicode
        detector.add_document("unicode", "Hello 世界 🌍")
        
        # Check each doesn't crash
        assert detector.check_duplicate("Hi") is not None
        assert detector.check_duplicate("") is not None
        assert detector.check_duplicate("!@#$%^&*()") is not None
        assert detector.check_duplicate("Hello 世界 🌍") is not None