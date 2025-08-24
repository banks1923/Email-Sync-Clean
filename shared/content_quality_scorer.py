"""
Content Quality Scorer - Text Validation Gates
Implements the quality scoring system with hard gates for OCR validation.
"""

import re
from typing import Tuple
from enum import Enum
from dataclasses import dataclass

class ValidationStatus(Enum):
    """Content validation status - 4-stage progression"""
    INGESTED = "ingested"          # File ingested, not processed
    OCR_DONE = "ocr_done"          # OCR completed (may be garbage)  
    TEXT_VALIDATED = "text_validated"  # Passed quality gates
    ENTITIES_EXTRACTED = "entities_extracted"  # Entities successfully extracted

@dataclass
class QualityMetrics:
    """Quality metrics for content scoring"""
    text_length: int
    alpha_ratio: float
    digit_punct_ratio: float
    symbol_ratio: float
    unique_bigrams: int
    english_dict_hits: int
    total_words: int
    chars_per_page: float
    quality_score: float
    validation_status: ValidationStatus
    failure_reasons: list

class ContentQualityScorer:
    """
    Implements text validation gates with hard quality thresholds.
    Based on the systematic OCR quality requirements.
    """
    
    def __init__(self):
        # Quality gate thresholds (calibrated from requirements)
        self.MIN_TEXT_LENGTH = 1500
        self.MIN_CHARS_PER_PAGE = 300
        self.MIN_ALPHA_RATIO = 0.55
        self.MAX_DIGIT_PUNCT_RATIO = 0.35
        self.MAX_SYMBOL_RATIO = 0.15
        self.MIN_UNIQUE_BIGRAMS = 200
        self.MIN_ENGLISH_DICT_HIT_RATE = 0.35
        self.MIN_ENTITIES_PER_KB = 0.3
        
        # Common English words for basic dictionary check (expanded for better validation)
        self.english_words = {
            # Common English words
            'the', 'and', 'for', 'are', 'but', 'not', 'you', 'all', 'can', 'had', 'her', 'was', 'one',
            'our', 'out', 'day', 'get', 'has', 'him', 'his', 'how', 'man', 'new', 'now', 'old', 'see',
            'two', 'way', 'who', 'its', 'did', 'yes', 'she', 'may', 'say', 'use', 'own', 'under',
            'this', 'that', 'with', 'have', 'from', 'they', 'will', 'been', 'each', 'which', 'their',
            'said', 'if', 'up', 'out', 'many', 'then', 'them', 'these', 'so', 'some', 'her', 'would',
            'make', 'like', 'time', 'very', 'when', 'come', 'its', 'now', 'over', 'think', 'also',
            'back', 'after', 'first', 'well', 'year', 'work', 'where', 'get', 'through', 'much',
            'before', 'right', 'too', 'any', 'same', 'should', 'those', 'people', 'take', 'state',
            'good', 'between', 'never', 'world', 'here', 'while', 'high', 'every', 'still', 'public',
            'human', 'both', 'local', 'sure', 'something', 'without', 'come', 'me', 'back', 'better',
            'general', 'process', 'she', 'heat', 'thanks', 'specific', 'long', 'small', 'book', 'great',
            # Legal terms
            'court', 'case', 'legal', 'law', 'document', 'order', 'file', 'notice', 'date', 'county',
            'california', 'superior', 'judgment', 'plaintiff', 'defendant', 'motion', 'hearing', 'trial',
            'attorney', 'counsel', 'evidence', 'matter', 'proceedings', 'filing', 'service', 'jurisdiction',
            'contract', 'agreement', 'party', 'parties', 'breach', 'damages', 'relief', 'statute',
            'code', 'section', 'civil', 'criminal', 'federal', 'state', 'appeal', 'decision', 'ruling',
            'testimony', 'witness', 'deposition', 'discovery', 'settlement', 'mediation', 'arbitration',
            'judge', 'jury', 'verdict', 'sentence', 'penalty', 'fine', 'prison', 'probation', 'parole',
            # Common document words
            'page', 'line', 'paragraph', 'section', 'chapter', 'title', 'subject', 'regarding',
            'pursuant', 'whereas', 'therefore', 'hereby', 'furthermore', 'however', 'nevertheless',
            'contained', 'including', 'excluding', 'unless', 'except', 'provided', 'required',
            'shall', 'must', 'may', 'will', 'should', 'could', 'would', 'might', 'need', 'want'
        }
    
    def score_content(self, text: str, page_count: int = 1, entity_count: int = 0) -> QualityMetrics:
        """
        Score content quality and apply validation gates.
        Returns QualityMetrics with validation status and failure reasons.
        """
        if not text or not text.strip():
            return QualityMetrics(
                text_length=0,
                alpha_ratio=0.0,
                digit_punct_ratio=1.0,
                symbol_ratio=0.0,
                unique_bigrams=0,
                english_dict_hits=0,
                total_words=0,
                chars_per_page=0.0,
                quality_score=0.0,
                validation_status=ValidationStatus.OCR_DONE,
                failure_reasons=['empty_text']
            )
        
        # Basic metrics
        text_length = len(text)
        chars_per_page = text_length / max(page_count, 1)
        
        # Character type analysis
        alpha_chars = len(re.findall(r'[A-Za-z]', text))
        digit_chars = len(re.findall(r'[0-9]', text))
        punct_chars = len(re.findall(r'[.,;:!?()\[\]{}"\'-]', text))
        symbol_chars = len(re.findall(r'[&=%£€<>©#@$*+^~|\\]', text))
        
        alpha_ratio = alpha_chars / text_length if text_length > 0 else 0
        digit_punct_ratio = (digit_chars + punct_chars) / text_length if text_length > 0 else 0
        symbol_ratio = symbol_chars / text_length if text_length > 0 else 0
        
        # Bigram uniqueness (crude de-garble indicator)
        unique_bigrams = self._count_unique_bigrams(text)
        
        # English dictionary hit rate
        words = re.findall(r'\b\w+\b', text.lower())
        english_hits = sum(1 for word in words if word in self.english_words)
        english_dict_hit_rate = english_hits / len(words) if words else 0
        
        # Apply validation gates
        failure_reasons = []
        
        # Gate 1: Minimum length OR chars per page
        if text_length < self.MIN_TEXT_LENGTH and chars_per_page < self.MIN_CHARS_PER_PAGE:
            failure_reasons.append(f'insufficient_content (len={text_length}, cpp={chars_per_page:.0f})')
        
        # Gate 2: Alpha ratio
        if alpha_ratio < self.MIN_ALPHA_RATIO:
            failure_reasons.append(f'low_alpha_ratio ({alpha_ratio:.2f} < {self.MIN_ALPHA_RATIO})')
        
        # Gate 3: Digit/punct ratio
        if digit_punct_ratio > self.MAX_DIGIT_PUNCT_RATIO:
            failure_reasons.append(f'high_noise_ratio ({digit_punct_ratio:.2f} > {self.MAX_DIGIT_PUNCT_RATIO})')
        
        # Gate 4: Symbol ratio (OCR garbage)
        if symbol_ratio > self.MAX_SYMBOL_RATIO:
            failure_reasons.append(f'high_symbol_ratio ({symbol_ratio:.2f} > {self.MAX_SYMBOL_RATIO})')
        
        # Gate 5: Unique bigrams (de-garble)
        if unique_bigrams < self.MIN_UNIQUE_BIGRAMS:
            failure_reasons.append(f'low_bigram_diversity ({unique_bigrams} < {self.MIN_UNIQUE_BIGRAMS})')
        
        # Gate 6: English dictionary hits
        if english_dict_hit_rate < self.MIN_ENGLISH_DICT_HIT_RATE:
            failure_reasons.append(f'low_english_hits ({english_dict_hit_rate:.2f} < {self.MIN_ENGLISH_DICT_HIT_RATE})')
        
        # Calculate composite quality score (0-1)
        quality_score = self._calculate_quality_score(
            alpha_ratio, digit_punct_ratio, symbol_ratio, 
            unique_bigrams, english_dict_hit_rate, chars_per_page
        )
        
        # Determine validation status
        if failure_reasons:
            validation_status = ValidationStatus.OCR_DONE
        else:
            # Check entity density if entities available
            if entity_count > 0:
                entities_per_kb = entity_count / (text_length / 1024.0)
                if entities_per_kb >= self.MIN_ENTITIES_PER_KB:
                    validation_status = ValidationStatus.ENTITIES_EXTRACTED
                else:
                    validation_status = ValidationStatus.TEXT_VALIDATED
                    failure_reasons.append(f'low_entity_density ({entities_per_kb:.2f} < {self.MIN_ENTITIES_PER_KB})')
            else:
                validation_status = ValidationStatus.TEXT_VALIDATED
        
        return QualityMetrics(
            text_length=text_length,
            alpha_ratio=alpha_ratio,
            digit_punct_ratio=digit_punct_ratio,
            symbol_ratio=symbol_ratio,
            unique_bigrams=unique_bigrams,
            english_dict_hits=english_hits,
            total_words=len(words),
            chars_per_page=chars_per_page,
            quality_score=quality_score,
            validation_status=validation_status,
            failure_reasons=failure_reasons
        )
    
    def _count_unique_bigrams(self, text: str) -> int:
        """Count unique character bigrams (crude garble detection)"""
        # Clean text and create bigrams
        clean_text = re.sub(r'\s+', ' ', text.lower())
        bigrams = set()
        
        for i in range(len(clean_text) - 1):
            bigram = clean_text[i:i+2]
            if bigram.isalpha():  # Only count alphabetic bigrams
                bigrams.add(bigram)
        
        return len(bigrams)
    
    def _calculate_quality_score(self, alpha_ratio: float, digit_punct_ratio: float, 
                                symbol_ratio: float, unique_bigrams: int, 
                                english_hit_rate: float, chars_per_page: float) -> float:
        """
        Calculate weighted composite quality score (0-1).
        Higher scores indicate better quality content.
        """
        # Component scores (normalized to 0-1)
        alpha_score = min(alpha_ratio / self.MIN_ALPHA_RATIO, 1.0)
        noise_score = max(0, 1.0 - (digit_punct_ratio / self.MAX_DIGIT_PUNCT_RATIO))
        symbol_score = max(0, 1.0 - (symbol_ratio / self.MAX_SYMBOL_RATIO))
        bigram_score = min(unique_bigrams / self.MIN_UNIQUE_BIGRAMS, 1.0)
        english_score = min(english_hit_rate / self.MIN_ENGLISH_DICT_HIT_RATE, 1.0)
        length_score = min(chars_per_page / self.MIN_CHARS_PER_PAGE, 1.0)
        
        # Weighted combination (emphasize alpha ratio and english hits)
        weights = {
            'alpha': 0.25,
            'noise': 0.15,
            'symbol': 0.15,
            'bigram': 0.15,
            'english': 0.20,
            'length': 0.10
        }
        
        quality_score = (
            weights['alpha'] * alpha_score +
            weights['noise'] * noise_score +
            weights['symbol'] * symbol_score +
            weights['bigram'] * bigram_score +
            weights['english'] * english_score +
            weights['length'] * length_score
        )
        
        return round(quality_score, 3)
    
    def classify_quality(self, quality_score: float) -> tuple[str, str]:
        """
        Classify content quality based on score.
        Returns (status, description) tuple.
        """
        if quality_score >= 0.7:
            return ("PASS", "High quality content")
        elif quality_score >= 0.5:
            return ("BORDERLINE", "May need manual review")
        else:
            return ("FAIL", "Poor quality content")

def score_content_quality(text: str, page_count: int = 1, entity_count: int = 0) -> QualityMetrics:
    """
    Convenience function to score content quality.
    """
    scorer = ContentQualityScorer()
    return scorer.score_content(text, page_count, entity_count)