"""
Legal Boilerplate Detection Engine

Specialized detection system for identifying boilerplate text in legal documents.
Integrates with the existing enhanced OCR pipeline and legal intelligence system.
"""

import re
from typing import Dict, List, Set, Tuple, Any
from dataclasses import dataclass, field
from collections import defaultdict
import numpy as np
from loguru import logger

# Import existing services
try:
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.metrics.pairwise import cosine_similarity
    SKLEARN_AVAILABLE = True
except ImportError:
    SKLEARN_AVAILABLE = False

try:
    import spacy
    SPACY_AVAILABLE = True
except ImportError:
    SPACY_AVAILABLE = False


@dataclass
class BoilerplateSegment:
    """Represents a detected boilerplate text segment"""
    text: str
    start_pos: int
    end_pos: int
    confidence: float
    pattern_type: str
    category: str = ""
    frequency: int = 1
    document_ids: set[str] = field(default_factory=set)


@dataclass
class DocumentSection:
    """Represents a section of a legal document"""
    text: str
    start_pos: int
    end_pos: int
    section_type: str
    is_boilerplate: bool = False
    confidence: float = 0.0
    metadata: dict[str, Any] = field(default_factory=dict)


class LegalBoilerplateDetector:
    """
    Advanced boilerplate detection for legal documents.
    
    Uses pattern matching, statistical analysis, and ML techniques
    to identify repetitive legal language across documents.
    """
    
    def __init__(self, similarity_threshold: float = 0.85):
        self.similarity_threshold = similarity_threshold
        self.available = SKLEARN_AVAILABLE and SPACY_AVAILABLE
        
        # Load spaCy model if available
        self.nlp = None
        if SPACY_AVAILABLE:
            try:
                self.nlp = spacy.load("en_core_web_sm")
            except OSError:
                logger.warning("spaCy English model not found. Install with: python -m spacy download en_core_web_sm")
        
        # Legal document boilerplate patterns from your sample documents
        self.boilerplate_patterns = {
            'standard_objections': [
                r'Responding Party objects.*?on the grounds that.*?burdensome.*?oppressive.*?harassing.*?in its entirety',
                r'Responding Party objects that this request calls for documents already in the Propounding Party.*?s possession',
                r'Responding Party does not have an obligation to obtain information that is equally available to the Propounding Party',
                r'Responding Party is not required to prepare the Plaintiff.*?s case',
                r'Responding Party objects.*?on the basis.*?vague.*?ambiguous.*?overbroad',
                r'Responding Party objects.*?attorney-client privilege.*?attorney work-product doctrine',
                r'Responding Party objects.*?seeks information.*?confidential.*?proprietary',
            ],
            'discovery_responses': [
                r'Subject to.*?objections.*?without waiving.*?Responding Party responds as follows',
                r'After diligent search and reasonable inquiry.*?Responding Party identifies and produces.*?following',
                r'Discovery is ongoing.*?Responding Party reserves the right to amend.*?modify.*?supplement.*?response',
                r'additional information.*?revealed through.*?discovery process',
            ],
            'case_citations': [
                r'\(Sav-On Drugs.*?Inc\..*?v\..*?Superior Court.*?Los Angeles County.*?\(1975\).*?15 Cal\..*?3d.*?1.*?5\.\)',
                r'\(CCP.*?§.*?2030\.220\(c\)\.\)',
                r'\([A-Z][a-z]+.*?v\..*?[A-Z][a-z]+.*?\([0-9]{4}\).*?[0-9]+.*?Cal\..*?[0-9]+.*?[0-9]+.*?\)',
                r'California Constitution.*?Article.*?section.*?[0-9]+',
            ],
            'formatting_elements': [
                r'^[0-9]+$',  # Line numbers
                r'^[A-Z\s]+:$',  # Section headers in all caps
                r'REQUEST FOR PRODUCTION.*?NO\..*?[0-9]+:',
                r'RESPONSE TO REQUEST.*?NO\..*?[0-9]+:',
                r'FORM INTERROGATORY.*?NO\..*?[0-9]+:',
                r'DEFENDANT.*?RESPONSES TO PLAINTIFF.*?REQUEST',
            ],
            'procedural_language': [
                r'The request.*?duplicative of other requests herein',
                r'seeks information.*?disclosure.*?constitute.*?unwarranted invasion.*?privacy',
                r'seeks information.*?protected by federal and state constitutional.*?statutory.*?rights',
                r'court ordered.*?common law rights of privacy',
                r'compilation of information from multiple locations.*?voluminous records and files',
                r'substantial time of employees.*?great expense.*?little use or benefit',
            ]
        }
        
        # Compiled regex patterns for performance
        self.compiled_patterns = {}
        for category, patterns in self.boilerplate_patterns.items():
            self.compiled_patterns[category] = [
                re.compile(pattern, re.IGNORECASE | re.DOTALL | re.MULTILINE)
                for pattern in patterns
            ]
        
        # TF-IDF vectorizer for similarity detection
        self.tfidf_vectorizer = None
        self.pattern_cache = {}
    
    def detect_boilerplate_in_documents(
        self, 
        documents: list[dict[str, Any]]
    ) -> list[list[BoilerplateSegment]]:
        """
        Detect boilerplate across multiple documents.
        
        Args:
            documents: List of document dicts with 'text' or 'content' field
            
        Returns:
            List of boilerplate segments for each document
        """
        if not documents:
            return []
        
        logger.info(f"Analyzing boilerplate across {len(documents)} documents")
        
        # Extract text content
        document_texts = []
        for doc in documents:
            text = doc.get('text') or doc.get('content') or doc.get('body', '')
            document_texts.append(text)
        
        # Phase 1: Pattern-based detection
        pattern_segments = self._detect_pattern_boilerplate(documents, document_texts)
        
        # Phase 2: Statistical similarity detection
        if SKLEARN_AVAILABLE and len(documents) > 1:
            similarity_segments = self._detect_similarity_boilerplate(documents, document_texts)
            # Merge results
            all_segments = self._merge_detection_results(pattern_segments, similarity_segments)
        else:
            all_segments = pattern_segments
        
        # Phase 3: Frequency analysis
        frequency_segments = self._detect_frequency_boilerplate(all_segments, document_texts)
        
        logger.info(f"Detected boilerplate segments: {sum(len(segs) for segs in frequency_segments)}")
        
        return frequency_segments
    
    def _detect_pattern_boilerplate(
        self, 
        documents: list[dict[str, Any]], 
        texts: list[str]
    ) -> list[list[BoilerplateSegment]]:
        """Detect boilerplate using predefined legal patterns"""
        all_segments = []
        
        for doc_idx, (doc, text) in enumerate(zip(documents, texts)):
            doc_segments = []
            doc_id = doc.get('content_id', f'doc_{doc_idx}')
            
            # Apply each pattern category
            for category, compiled_patterns in self.compiled_patterns.items():
                for pattern_idx, pattern in enumerate(compiled_patterns):
                    matches = list(pattern.finditer(text))
                    
                    for match in matches:
                        segment = BoilerplateSegment(
                            text=match.group().strip(),
                            start_pos=match.start(),
                            end_pos=match.end(),
                            confidence=0.9,  # High confidence for exact pattern matches
                            pattern_type=f"{category}_{pattern_idx}",
                            category=category,
                            document_ids={doc_id}
                        )
                        doc_segments.append(segment)
            
            all_segments.append(doc_segments)
        
        return all_segments
    
    def _detect_similarity_boilerplate(
        self, 
        documents: list[dict[str, Any]], 
        texts: list[str]
    ) -> list[list[BoilerplateSegment]]:
        """Detect boilerplate using TF-IDF similarity analysis"""
        if not SKLEARN_AVAILABLE:
            return [[] for _ in documents]
        
        # Segment documents into sentences/paragraphs
        all_segments = []
        segment_to_doc = []
        segment_texts = []
        
        for doc_idx, text in enumerate(texts):
            doc_segments = self._segment_text(text)
            doc_segment_objects = []
            
            for seg_idx, (start, end, seg_text) in enumerate(doc_segments):
                segment_texts.append(seg_text)
                segment_to_doc.append(doc_idx)
                
                segment_obj = BoilerplateSegment(
                    text=seg_text,
                    start_pos=start,
                    end_pos=end,
                    confidence=0.0,  # Will be updated based on similarity
                    pattern_type="similarity_based",
                    category="statistical",
                    document_ids={documents[doc_idx].get('content_id', f'doc_{doc_idx}')}
                )
                doc_segment_objects.append(segment_obj)
            
            all_segments.append(doc_segment_objects)
        
        if len(segment_texts) < 2:
            return all_segments
        
        try:
            # Calculate TF-IDF similarity matrix
            vectorizer = TfidfVectorizer(
                max_features=1000,
                ngram_range=(1, 3),
                stop_words='english',
                min_df=2,  # Must appear in at least 2 segments
                max_df=0.8  # Ignore terms that appear in >80% of segments
            )
            
            tfidf_matrix = vectorizer.fit_transform(segment_texts)
            similarity_matrix = cosine_similarity(tfidf_matrix)
            
            # Find highly similar segments across documents
            for i, segment_i in enumerate(segment_texts):
                doc_i = segment_to_doc[i]
                similar_count = 0
                max_similarity = 0.0
                
                for j, segment_j in enumerate(segment_texts):
                    if i != j:
                        doc_j = segment_to_doc[j]
                        similarity = similarity_matrix[i][j]
                        
                        if similarity > self.similarity_threshold:
                            similar_count += 1
                            max_similarity = max(max_similarity, similarity)
                            
                            # Add document ID to the similar segment
                            all_segments[doc_i][i % len(all_segments[doc_i])].document_ids.add(
                                documents[doc_j].get('content_id', f'doc_{doc_j}')
                            )
                
                # Update confidence based on similarity
                if similar_count > 0:
                    segment_idx = i % len(all_segments[doc_i])
                    if segment_idx < len(all_segments[doc_i]):
                        all_segments[doc_i][segment_idx].confidence = max_similarity
                        all_segments[doc_i][segment_idx].frequency = similar_count + 1
        
        except Exception as e:
            logger.warning(f"Similarity detection failed: {e}")
        
        return all_segments
    
    def _detect_frequency_boilerplate(
        self, 
        segment_lists: list[list[BoilerplateSegment]], 
        texts: list[str]
    ) -> list[list[BoilerplateSegment]]:
        """Detect boilerplate based on frequency across documents"""
        
        # Collect all segments with their normalized text
        text_frequency = defaultdict(list)
        
        for doc_idx, segments in enumerate(segment_lists):
            for segment in segments:
                # Normalize text for frequency counting
                normalized = self._normalize_text_for_frequency(segment.text)
                text_frequency[normalized].append((doc_idx, segment))
        
        # Identify high-frequency segments
        frequent_texts = {
            text: occurrences for text, occurrences in text_frequency.items()
            if len(occurrences) >= max(2, len(texts) * 0.3)  # Appears in at least 30% of docs
        }
        
        # Update segments with frequency information
        for normalized_text, occurrences in frequent_texts.items():
            frequency_count = len(occurrences)
            
            for doc_idx, segment in occurrences:
                segment.frequency = frequency_count
                segment.confidence = max(segment.confidence, 
                                      min(0.95, frequency_count / len(texts)))
                segment.category = f"{segment.category}_frequent"
        
        return segment_lists
    
    def _merge_detection_results(
        self, 
        pattern_segments: list[list[BoilerplateSegment]], 
        similarity_segments: list[list[BoilerplateSegment]]
    ) -> list[list[BoilerplateSegment]]:
        """Merge results from different detection methods"""
        
        merged = []
        
        for doc_idx in range(len(pattern_segments)):
            doc_merged = []
            
            # Add pattern-based segments
            doc_merged.extend(pattern_segments[doc_idx])
            
            # Add similarity-based segments that don't overlap significantly
            for sim_segment in similarity_segments[doc_idx]:
                if sim_segment.confidence > 0.5:  # Only high-confidence similarity matches
                    # Check for overlap with existing segments
                    overlap = False
                    for existing in doc_merged:
                        if self._segments_overlap(existing, sim_segment, overlap_threshold=0.5):
                            # Merge information
                            existing.document_ids.update(sim_segment.document_ids)
                            existing.confidence = max(existing.confidence, sim_segment.confidence)
                            overlap = True
                            break
                    
                    if not overlap:
                        doc_merged.append(sim_segment)
            
            merged.append(doc_merged)
        
        return merged
    
    def _segment_text(self, text: str) -> list[tuple[int, int, str]]:
        """Segment text into meaningful units (sentences/paragraphs)"""
        segments = []
        
        if self.nlp:
            # Use spaCy for sentence segmentation
            doc = self.nlp(text)
            for sent in doc.sents:
                if len(sent.text.strip()) > 20:  # Ignore very short segments
                    segments.append((sent.start_char, sent.end_char, sent.text.strip()))
        else:
            # Fallback to simple paragraph segmentation
            paragraphs = text.split('\n\n')
            pos = 0
            for para in paragraphs:
                para = para.strip()
                if len(para) > 20:
                    segments.append((pos, pos + len(para), para))
                pos += len(para) + 2
        
        return segments
    
    def _normalize_text_for_frequency(self, text: str) -> str:
        """Normalize text for frequency comparison"""
        # Remove case differences
        normalized = text.lower()
        
        # Remove extra whitespace
        normalized = re.sub(r'\s+', ' ', normalized).strip()
        
        # Remove specific identifiers that might vary
        normalized = re.sub(r'\b\d+\b', '[NUM]', normalized)  # Numbers
        normalized = re.sub(r'\b[A-Z]{2,}\b', '[CAPS]', normalized)  # All caps words
        
        return normalized
    
    def _segments_overlap(
        self, 
        seg1: BoilerplateSegment, 
        seg2: BoilerplateSegment, 
        overlap_threshold: float = 0.3
    ) -> bool:
        """Check if two segments overlap significantly"""
        
        # Position-based overlap
        overlap_start = max(seg1.start_pos, seg2.start_pos)
        overlap_end = min(seg1.end_pos, seg2.end_pos)
        
        if overlap_end > overlap_start:
            overlap_length = overlap_end - overlap_start
            seg1_length = seg1.end_pos - seg1.start_pos
            seg2_length = seg2.end_pos - seg2.start_pos
            
            overlap_ratio = overlap_length / min(seg1_length, seg2_length)
            
            if overlap_ratio > overlap_threshold:
                return True
        
        # Text-based similarity for non-positional overlap
        if SKLEARN_AVAILABLE:
            try:
                vectorizer = TfidfVectorizer(stop_words='english')
                tfidf_matrix = vectorizer.fit_transform([seg1.text, seg2.text])
                similarity = cosine_similarity(tfidf_matrix[0:1], tfidf_matrix[1:2])[0][0]
                return similarity > 0.8
            except:
                pass
        
        return False
    
    def generate_boilerplate_report(
        self, 
        segment_lists: list[list[BoilerplateSegment]],
        document_info: list[dict[str, Any]] = None
    ) -> dict[str, Any]:
        """Generate comprehensive boilerplate analysis report"""
        
        total_segments = sum(len(segments) for segments in segment_lists)
        
        # Category analysis
        category_stats = defaultdict(int)
        pattern_stats = defaultdict(int)
        confidence_scores = []
        
        for segments in segment_lists:
            for segment in segments:
                category_stats[segment.category] += 1
                pattern_stats[segment.pattern_type] += 1
                confidence_scores.append(segment.confidence)
        
        # High-frequency boilerplate
        frequent_boilerplate = []
        text_counts = defaultdict(int)
        
        for segments in segment_lists:
            for segment in segments:
                if segment.frequency > 1:
                    text_counts[segment.text[:100]] += 1  # First 100 chars as key
        
        for text, count in sorted(text_counts.items(), key=lambda x: x[1], reverse=True)[:10]:
            frequent_boilerplate.append({
                'text_preview': text,
                'frequency': count,
                'percentage': count / len(segment_lists) * 100
            })
        
        report = {
            'summary': {
                'total_documents': len(segment_lists),
                'total_boilerplate_segments': total_segments,
                'avg_segments_per_document': total_segments / len(segment_lists) if segment_lists else 0,
                'avg_confidence': np.mean(confidence_scores) if confidence_scores else 0.0,
            },
            'categories': dict(category_stats),
            'pattern_types': dict(pattern_stats),
            'frequent_boilerplate': frequent_boilerplate,
            'confidence_distribution': {
                'high_confidence': len([c for c in confidence_scores if c > 0.8]),
                'medium_confidence': len([c for c in confidence_scores if 0.5 < c <= 0.8]),
                'low_confidence': len([c for c in confidence_scores if c <= 0.5]),
            }
        }
        
        return report
    
    def validate_setup(self) -> dict[str, Any]:
        """Validate detector setup and dependencies"""
        validation = {
            'sklearn_available': SKLEARN_AVAILABLE,
            'spacy_available': SPACY_AVAILABLE,
            'spacy_model_loaded': self.nlp is not None,
            'pattern_count': sum(len(patterns) for patterns in self.boilerplate_patterns.values()),
            'similarity_threshold': self.similarity_threshold,
            'ready': SKLEARN_AVAILABLE  # Minimum requirement
        }
        
        if not SKLEARN_AVAILABLE:
            validation['warning'] = "scikit-learn not available - similarity detection disabled"
        
        if not SPACY_AVAILABLE or not self.nlp:
            validation['warning'] = validation.get('warning', '') + " spaCy not available - using fallback text segmentation"
        
        return validation


def get_boilerplate_detector(similarity_threshold: float = 0.85) -> LegalBoilerplateDetector:
    """Factory function for creating boilerplate detector"""
    return LegalBoilerplateDetector(similarity_threshold=similarity_threshold)
