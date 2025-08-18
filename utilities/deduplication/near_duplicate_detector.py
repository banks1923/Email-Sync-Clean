"""
Near-duplicate detection using MinHash and LSH
Finds similar content even with minor variations
"""

import hashlib
import re
from typing import List, Dict, Set, Tuple, Optional
from collections import defaultdict
import numpy as np
from loguru import logger

class MinHasher:
    """MinHash implementation for similarity detection"""
    
    def __init__(self, num_perm: int = 128, seed: int = 42):
        """
        Initialize MinHasher
        
        Args:
            num_perm: Number of permutation functions (higher = more accurate but slower)
            seed: Random seed for reproducibility
        """
        self.num_perm = num_perm
        self.seed = seed
        np.random.seed(seed)
        
        # Generate hash functions (a, b parameters for universal hashing)
        self.permutations = self._generate_permutations()
        
    def _generate_permutations(self) -> List[Tuple[int, int]]:
        """Generate permutation functions for MinHash"""
        # Use large prime for modulo
        self.prime = 4294967311  # Next prime after 2^32
        
        # Generate random a, b for hash functions: (a*x + b) % prime
        permutations = []
        for _ in range(self.num_perm):
            a = np.random.randint(1, self.prime)
            b = np.random.randint(0, self.prime)
            permutations.append((a, b))
        return permutations
        
    def _shingle_text(self, text: str, k: int = 3) -> Set[int]:
        """
        Convert text to k-shingles (k-grams)
        
        Args:
            text: Input text
            k: Size of shingles (3 = trigrams)
            
        Returns:
            Set of shingle hashes
        """
        # Normalize text
        text = text.lower()
        text = re.sub(r'\s+', ' ', text)  # Normalize whitespace
        text = re.sub(r'[^\w\s]', '', text)  # Remove punctuation
        
        # Generate shingles
        shingles = set()
        for i in range(len(text) - k + 1):
            shingle = text[i:i+k]
            # Hash the shingle to integer
            shingle_hash = int(hashlib.md5(shingle.encode()).hexdigest(), 16)
            shingles.add(shingle_hash)
            
        return shingles
        
    def compute_signature(self, text: str) -> np.ndarray:
        """
        Compute MinHash signature for text
        
        Args:
            text: Input text
            
        Returns:
            MinHash signature vector
        """
        if not text or len(text) < 3:
            return np.zeros(self.num_perm, dtype=np.uint32)
            
        shingles = self._shingle_text(text)
        if not shingles:
            return np.zeros(self.num_perm, dtype=np.uint32)
            
        # Initialize signature with max values
        signature = np.full(self.num_perm, np.iinfo(np.uint32).max, dtype=np.uint32)
        
        # For each shingle, update signature
        for shingle in shingles:
            for i, (a, b) in enumerate(self.permutations):
                # Universal hash function
                hash_val = (a * shingle + b) % self.prime
                signature[i] = min(signature[i], hash_val)
                
        return signature
        
    def jaccard_similarity(self, sig1: np.ndarray, sig2: np.ndarray) -> float:
        """
        Estimate Jaccard similarity from signatures
        
        Args:
            sig1, sig2: MinHash signatures
            
        Returns:
            Estimated Jaccard similarity (0-1)
        """
        if len(sig1) != len(sig2):
            raise ValueError("Signatures must have same length")
            
        return np.mean(sig1 == sig2)


class LSHIndex:
    """Locality-Sensitive Hashing for fast similarity search"""
    
    def __init__(self, num_bands: int = 16, band_size: int = 8):
        """
        Initialize LSH index
        
        Args:
            num_bands: Number of bands to split signature
            band_size: Size of each band
        """
        self.num_bands = num_bands
        self.band_size = band_size
        self.buckets = defaultdict(list)
        self.signatures = {}
        
    def add(self, doc_id: str, signature: np.ndarray):
        """
        Add document to LSH index
        
        Args:
            doc_id: Document identifier
            signature: MinHash signature
        """
        self.signatures[doc_id] = signature
        
        # Split signature into bands
        for band_idx in range(self.num_bands):
            start = band_idx * self.band_size
            end = start + self.band_size
            
            # Hash the band
            band = signature[start:end]
            band_hash = hash(tuple(band))
            
            # Add to bucket
            bucket_id = (band_idx, band_hash)
            self.buckets[bucket_id].append(doc_id)
            
    def find_similar(self, signature: np.ndarray, threshold: float = 0.5) -> List[Tuple[str, float]]:
        """
        Find documents similar to given signature
        
        Args:
            signature: Query signature
            threshold: Minimum similarity threshold
            
        Returns:
            List of (doc_id, similarity) tuples
        """
        candidates = set()
        
        # Find candidate documents from buckets
        for band_idx in range(self.num_bands):
            start = band_idx * self.band_size
            end = start + self.band_size
            
            band = signature[start:end]
            band_hash = hash(tuple(band))
            bucket_id = (band_idx, band_hash)
            
            # Get documents in same bucket
            if bucket_id in self.buckets:
                candidates.update(self.buckets[bucket_id])
                
        # Calculate actual similarities for candidates
        results = []
        minhasher = MinHasher()
        
        for doc_id in candidates:
            if doc_id in self.signatures:
                similarity = minhasher.jaccard_similarity(signature, self.signatures[doc_id])
                if similarity >= threshold:
                    results.append((doc_id, similarity))
                    
        # Sort by similarity
        results.sort(key=lambda x: x[1], reverse=True)
        return results


class NearDuplicateDetector:
    """Main service for near-duplicate detection"""
    
    def __init__(self, threshold: float = 0.8, num_perm: int = 128):
        """
        Initialize detector
        
        Args:
            threshold: Similarity threshold for duplicates (0.8 = 80% similar)
            num_perm: Number of hash functions (accuracy vs speed tradeoff)
        """
        self.threshold = threshold
        self.minhasher = MinHasher(num_perm=num_perm)
        self.lsh_index = LSHIndex(
            num_bands=16,
            band_size=num_perm // 16
        )
        self.processed_docs = {}
        
    def add_document(self, doc_id: str, content: str, metadata: Dict = None):
        """
        Add document to duplicate detection index
        
        Args:
            doc_id: Unique document identifier
            content: Document text content
            metadata: Optional metadata
        """
        signature = self.minhasher.compute_signature(content)
        self.lsh_index.add(doc_id, signature)
        self.processed_docs[doc_id] = {
            'signature': signature,
            'metadata': metadata or {},
            'content_preview': content[:200] if content else ''
        }
        logger.debug(f"Added document {doc_id} to duplicate index")
        
    def check_duplicate(self, content: str) -> List[Dict]:
        """
        Check if content is duplicate/near-duplicate of existing documents
        
        Args:
            content: Content to check
            
        Returns:
            List of similar documents with similarity scores
        """
        signature = self.minhasher.compute_signature(content)
        similar = self.lsh_index.find_similar(signature, self.threshold)
        
        results = []
        for doc_id, similarity in similar:
            doc_info = self.processed_docs.get(doc_id, {})
            results.append({
                'doc_id': doc_id,
                'similarity': similarity,
                'is_exact': similarity > 0.99,
                'is_near_duplicate': similarity >= self.threshold,
                'metadata': doc_info.get('metadata', {}),
                'preview': doc_info.get('content_preview', '')
            })
            
        return results
        
    def find_all_duplicates(self) -> Dict[str, List[str]]:
        """
        Find all duplicate groups in the index
        
        Returns:
            Dictionary mapping representative doc to list of duplicates
        """
        duplicate_groups = {}
        processed = set()
        
        for doc_id, doc_info in self.processed_docs.items():
            if doc_id in processed:
                continue
                
            # Find similar documents
            similar = self.lsh_index.find_similar(
                doc_info['signature'], 
                self.threshold
            )
            
            if len(similar) > 1:
                # Create duplicate group
                group = [sim_id for sim_id, _ in similar]
                duplicate_groups[doc_id] = group
                processed.update(group)
                
        return duplicate_groups
        
    def batch_deduplicate(self, documents: List[Dict]) -> Dict:
        """
        Process batch of documents and identify duplicates
        
        Args:
            documents: List of dicts with 'id' and 'content' keys
            
        Returns:
            Dict with duplicate groups and statistics
        """
        stats = {
            'total': len(documents),
            'unique': 0,
            'duplicates': 0,
            'near_duplicates': 0,
            'groups': []
        }
        
        # Build index
        for doc in documents:
            self.add_document(
                doc.get('id', str(hash(doc['content']))),
                doc['content'],
                doc.get('metadata', {})
            )
            
        # Find duplicate groups
        groups = self.find_all_duplicates()
        
        # Calculate statistics
        all_duplicates = set()
        for leader, group in groups.items():
            all_duplicates.update(group[1:])  # Don't count leader as duplicate
            
            # Classify group
            signatures = [self.processed_docs[doc_id]['signature'] for doc_id in group]
            similarities = []
            for i in range(1, len(signatures)):
                sim = self.minhasher.jaccard_similarity(signatures[0], signatures[i])
                similarities.append(sim)
                
            avg_similarity = np.mean(similarities) if similarities else 1.0
            
            stats['groups'].append({
                'leader': leader,
                'members': group,
                'size': len(group),
                'avg_similarity': avg_similarity,
                'is_exact': avg_similarity > 0.99
            })
            
        stats['unique'] = len(documents) - len(all_duplicates)
        stats['duplicates'] = len(all_duplicates)
        stats['near_duplicates'] = sum(
            1 for g in stats['groups'] 
            if g['avg_similarity'] < 0.99 and g['avg_similarity'] >= self.threshold
        )
        
        return stats
        
    def get_similarity(self, content1: str, content2: str) -> float:
        """
        Calculate similarity between two pieces of content
        
        Args:
            content1, content2: Text content to compare
            
        Returns:
            Similarity score (0-1)
        """
        sig1 = self.minhasher.compute_signature(content1)
        sig2 = self.minhasher.compute_signature(content2)
        return self.minhasher.jaccard_similarity(sig1, sig2)


# Singleton instance
_detector: Optional[NearDuplicateDetector] = None

def get_duplicate_detector(threshold: float = 0.8) -> NearDuplicateDetector:
    """Get or create singleton duplicate detector"""
    global _detector
    if _detector is None or _detector.threshold != threshold:
        _detector = NearDuplicateDetector(threshold=threshold)
    return _detector


def test_duplicate_detection():
    """Test the duplicate detection system"""
    detector = NearDuplicateDetector(threshold=0.7)
    
    # Test documents with varying similarity
    docs = [
        {
            'id': 'doc1',
            'content': 'The quick brown fox jumps over the lazy dog. This is a test document about animals.'
        },
        {
            'id': 'doc2',
            'content': 'The quick brown fox jumps over the lazy dog. This is a test document about animals.'  # Exact duplicate
        },
        {
            'id': 'doc3', 
            'content': 'The fast brown fox jumps over the lazy dog. This is a test document about animals and nature.'  # Near duplicate
        },
        {
            'id': 'doc4',
            'content': 'Machine learning is a subset of artificial intelligence that enables systems to learn.'  # Different
        },
        {
            'id': 'doc5',
            'content': 'Machine learning is a subset of AI that enables systems to learn and improve.'  # Near duplicate of doc4
        }
    ]
    
    # Process documents
    result = detector.batch_deduplicate(docs)
    
    print(f"Total documents: {result['total']}")
    print(f"Unique documents: {result['unique']}")
    print(f"Duplicates: {result['duplicates']}")
    print(f"Near-duplicates: {result['near_duplicates']}")
    print(f"\nDuplicate groups found: {len(result['groups'])}")
    
    for group in result['groups']:
        print(f"\nGroup (similarity: {group['avg_similarity']:.2%}):")
        print(f"  Leader: {group['leader']}")
        print(f"  Members: {group['members']}")
        
    # Test similarity calculation
    sim1 = detector.get_similarity(docs[0]['content'], docs[1]['content'])
    sim2 = detector.get_similarity(docs[0]['content'], docs[2]['content'])
    sim3 = detector.get_similarity(docs[0]['content'], docs[3]['content'])
    
    print("\nPairwise similarities:")
    print(f"  doc1 vs doc2 (exact): {sim1:.2%}")
    print(f"  doc1 vs doc3 (near): {sim2:.2%}")
    print(f"  doc1 vs doc4 (different): {sim3:.2%}")


if __name__ == "__main__":
    test_duplicate_detection()