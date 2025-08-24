"""
Legal Document Text Processor

Handles the removal and replacement of detected boilerplate text
while preserving document structure and important legal content.
"""

import re
from typing import Dict, List, Any, Tuple
from dataclasses import dataclass
from loguru import logger

from .boilerplate_detector import BoilerplateSegment


@dataclass
class ProcessingResult:
    """Result of text processing operation"""
    original_text: str
    cleaned_text: str
    removed_segments: list[BoilerplateSegment]
    processing_stats: dict[str, Any]
    preservation_log: list[str]


class LegalTextProcessor:
    """
    Processes legal documents by removing boilerplate while preserving
    essential legal content and document structure.
    """
    
    def __init__(self, 
                 confidence_threshold: float = 0.7,
                 preserve_structure: bool = True,
                 replacement_mode: str = 'placeholder'):
        """
        Initialize text processor.
        
        Args:
            confidence_threshold: Minimum confidence to remove boilerplate
            preserve_structure: Whether to maintain document formatting
            replacement_mode: 'placeholder', 'summary', or 'remove'
        """
        self.confidence_threshold = confidence_threshold
        self.preserve_structure = preserve_structure
        self.replacement_mode = replacement_mode
        
        # Preservation rules - content to never remove
        self.preservation_patterns = {
            'case_numbers': [
                r'\b\d{2}[A-Z]{2,4}\d{5,8}\b',  # Case number format
                r'Case No\.?\s*[:\-]?\s*\d+[A-Z]*\d+',
                r'Civil Case\s*[:\-]?\s*[A-Z0-9\-]+',
            ],
            'party_names': [
                r'PLAINTIFF[S]?\s*[:\-]?\s*[A-Z\s]+(?=\s*(?:vs?\.?|v\.?|and|\n))',
                r'DEFENDANT[S]?\s*[:\-]?\s*[A-Z\s]+(?=\s*(?:\n|,|and))',
                r'PETITIONER[S]?\s*[:\-]?\s*[A-Z\s]+(?=\s*(?:vs?\.?|v\.?|and|\n))',
                r'RESPONDENT[S]?\s*[:\-]?\s*[A-Z\s]+(?=\s*(?:\n|,|and))',
            ],
            'dates': [
                r'\b(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2},?\s+\d{4}\b',
                r'\b\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b',
                r'\b\d{4}[-/]\d{1,2}[-/]\d{1,2}\b',
            ],
            'court_info': [
                r'SUPERIOR COURT.*?CALIFORNIA',
                r'COURT OF.*?CALIFORNIA',
                r'IN THE.*?COURT.*?OF.*?CALIFORNIA',
                r'Hon\.?\s+[A-Z][a-z]+\s+[A-Z][a-z]+',  # Judge names
            ],
            'document_headers': [
                r'REQUEST FOR PRODUCTION.*?NO\.\s*\d+:',
                r'FORM INTERROGATORY.*?NO\.\s*\d+:',
                r'SPECIAL INTERROGATORY.*?NO\.\s*\d+:',
                r'DEFENDANT.*?RESPONSES?.*?TO.*?PLAINTIFF',
                r'PLAINTIFF.*?RESPONSES?.*?TO.*?DEFENDANT',
            ]
        }
        
        # Compile patterns for performance
        self.compiled_preservation_patterns = {}
        for category, patterns in self.preservation_patterns.items():
            self.compiled_preservation_patterns[category] = [
                re.compile(pattern, re.IGNORECASE | re.MULTILINE)
                for pattern in patterns
            ]
    
    def process_document(self, 
                        text: str, 
                        boilerplate_segments: list[BoilerplateSegment],
                        document_metadata: dict[str, Any] = None) -> ProcessingResult:
        """
        Process a document by removing boilerplate text.
        
        Args:
            text: Original document text
            boilerplate_segments: Detected boilerplate segments
            document_metadata: Optional document metadata
            
        Returns:
            ProcessingResult with cleaned text and processing information
        """
        logger.info(f"Processing document with {len(boilerplate_segments)} boilerplate segments")
        
        preservation_log = []
        
        # Step 1: Identify content to preserve
        preserved_ranges = self._identify_preserved_content(text, preservation_log)
        
        # Step 2: Filter boilerplate segments based on confidence and preservation
        filtered_segments = self._filter_segments_for_removal(
            boilerplate_segments, preserved_ranges, preservation_log
        )
        
        # Step 3: Remove/replace boilerplate text
        cleaned_text = self._apply_boilerplate_removal(
            text, filtered_segments, preservation_log
        )
        
        # Step 4: Post-processing cleanup
        cleaned_text = self._post_process_text(cleaned_text, preservation_log)
        
        # Step 5: Generate processing statistics
        stats = self._generate_processing_stats(text, cleaned_text, filtered_segments)
        
        result = ProcessingResult(
            original_text=text,
            cleaned_text=cleaned_text,
            removed_segments=filtered_segments,
            processing_stats=stats,
            preservation_log=preservation_log
        )
        
        logger.info(f"Processing complete: {stats['removal_percentage']:.1f}% boilerplate removed")
        
        return result
    
    def process_multiple_documents(self, 
                                 documents: list[dict[str, Any]], 
                                 boilerplate_segments_list: list[list[BoilerplateSegment]]) -> list[ProcessingResult]:
        """Process multiple documents in batch"""
        
        results = []
        
        for doc, segments in zip(documents, boilerplate_segments_list):
            text = doc.get('text') or doc.get('content') or doc.get('body', '')
            metadata = {k: v for k, v in doc.items() if k not in ['text', 'content', 'body']}
            
            result = self.process_document(text, segments, metadata)
            results.append(result)
        
        return results
    
    def _identify_preserved_content(self, text: str, log: list[str]) -> list[tuple[int, int, str]]:
        """Identify text ranges that should never be removed"""
        preserved_ranges = []
        
        for category, compiled_patterns in self.compiled_preservation_patterns.items():
            for pattern in compiled_patterns:
                matches = list(pattern.finditer(text))
                
                for match in matches:
                    preserved_ranges.append((match.start(), match.end(), category))
                    log.append(f"Preserved {category}: '{match.group()[:50]}...'")
        
        # Sort by start position
        preserved_ranges.sort(key=lambda x: x[0])
        
        # Merge overlapping ranges
        merged_ranges = self._merge_overlapping_ranges(preserved_ranges)
        
        log.append(f"Total preserved ranges: {len(merged_ranges)}")
        
        return merged_ranges
    
    def _merge_overlapping_ranges(self, ranges: list[tuple[int, int, str]]) -> list[tuple[int, int, str]]:
        """Merge overlapping preservation ranges"""
        if not ranges:
            return []
        
        merged = [ranges[0]]
        
        for current in ranges[1:]:
            last_merged = merged[-1]
            
            # Check for overlap
            if current[0] <= last_merged[1]:
                # Merge ranges
                merged[-1] = (
                    min(last_merged[0], current[0]),
                    max(last_merged[1], current[1]),
                    f"{last_merged[2]},{current[2]}"
                )
            else:
                merged.append(current)
        
        return merged
    
    def _filter_segments_for_removal(self, 
                                    segments: list[BoilerplateSegment],
                                    preserved_ranges: list[tuple[int, int, str]],
                                    log: list[str]) -> list[BoilerplateSegment]:
        """Filter boilerplate segments that should be removed"""
        
        filtered = []
        
        for segment in segments:
            # Check confidence threshold
            if segment.confidence < self.confidence_threshold:
                log.append(f"Skipped low confidence segment: {segment.confidence:.2f}")
                continue
            
            # Check if segment overlaps with preserved content
            overlaps_preserved = False
            for preserve_start, preserve_end, preserve_type in preserved_ranges:
                if (segment.start_pos < preserve_end and segment.end_pos > preserve_start):
                    overlaps_preserved = True
                    log.append(f"Skipped segment overlapping {preserve_type}")
                    break
            
            if not overlaps_preserved:
                # Additional safety checks
                if self._is_safe_to_remove(segment, log):
                    filtered.append(segment)
                else:
                    log.append(f"Skipped segment due to safety check")
        
        log.append(f"Filtered {len(filtered)} segments for removal (from {len(segments)} detected)")
        
        return filtered
    
    def _is_safe_to_remove(self, segment: BoilerplateSegment, log: list[str]) -> bool:
        """Additional safety checks before removing segment"""
        
        # Don't remove very short segments (might be important)
        if len(segment.text.strip()) < 20:
            return False
        
        # Don't remove segments that look like unique content
        text_lower = segment.text.lower()
        
        # Check for specific content indicators
        important_indicators = [
            'damages', 'relief', 'wherefore', 'prayer', 'verdict',
            'findings', 'conclusions', 'orders', 'judgment',
            'settlement', 'agreement', 'stipulation'
        ]
        
        for indicator in important_indicators:
            if indicator in text_lower:
                return False
        
        # Check for monetary amounts
        if re.search(r'\$[\d,]+', segment.text):
            return False
        
        # Check for specific dates or deadlines
        if re.search(r'\b(?:by|before|within|deadline|due)\s+\w+\s+\d', text_lower):
            return False
        
        return True
    
    def _apply_boilerplate_removal(self, 
                                  text: str,
                                  segments: list[BoilerplateSegment],
                                  log: list[str]) -> str:
        """Apply boilerplate removal based on replacement mode"""
        
        # Sort segments by position (reverse order to maintain indices)
        sorted_segments = sorted(segments, key=lambda s: s.start_pos, reverse=True)
        
        cleaned_text = text
        
        for segment in sorted_segments:
            replacement = self._get_replacement_text(segment)
            
            cleaned_text = (
                cleaned_text[:segment.start_pos] + 
                replacement + 
                cleaned_text[segment.end_pos:]
            )
            
            log.append(f"Removed {segment.category} boilerplate: {len(segment.text)} chars -> {len(replacement)} chars")
        
        return cleaned_text
    
    def _get_replacement_text(self, segment: BoilerplateSegment) -> str:
        """Generate replacement text based on replacement mode"""
        
        if self.replacement_mode == 'remove':
            return '\n' if self.preserve_structure else ''
        
        elif self.replacement_mode == 'placeholder':
            category_labels = {
                'standard_objections': 'STANDARD OBJECTIONS',
                'discovery_responses': 'STANDARD DISCOVERY RESPONSE',
                'case_citations': 'CASE CITATION',
                'procedural_language': 'PROCEDURAL LANGUAGE',
                'formatting_elements': ''
            }
            
            label = category_labels.get(segment.category, 'BOILERPLATE')
            
            if label:
                return f'\n[{label} REMOVED]\n' if self.preserve_structure else f'[{label}] '
            else:
                return '\n' if self.preserve_structure else ''
        
        elif self.replacement_mode == 'summary':
            return self._generate_summary_replacement(segment)
        
        else:
            return ''
    
    def _generate_summary_replacement(self, segment: BoilerplateSegment) -> str:
        """Generate a summary replacement for boilerplate text"""
        
        summaries = {
            'standard_objections': '[Standard legal objections regarding burden, privilege, and scope]',
            'discovery_responses': '[Standard discovery response with reservation of rights]',
            'case_citations': '[Legal citation]',
            'procedural_language': '[Standard procedural language]',
        }
        
        summary = summaries.get(segment.category, '[Boilerplate legal language]')
        
        return f'\n{summary}\n' if self.preserve_structure else f'{summary} '
    
    def _post_process_text(self, text: str, log: list[str]) -> str:
        """Post-processing cleanup of the text"""
        
        # Remove excessive whitespace
        cleaned = re.sub(r'\n\s*\n\s*\n', '\n\n', text)  # Reduce multiple line breaks
        cleaned = re.sub(r'[ \t]+', ' ', cleaned)  # Normalize spaces
        
        # Fix spacing around preserved elements
        cleaned = re.sub(r'\n\s*\[([^\]]+)\]\s*\n', r'\n[\1]\n', cleaned)
        
        # Remove orphaned line numbers
        cleaned = re.sub(r'^\s*\d+\s*$', '', cleaned, flags=re.MULTILINE)
        
        log.append("Applied post-processing cleanup")
        
        return cleaned.strip()
    
    def _generate_processing_stats(self, 
                                  original: str, 
                                  cleaned: str, 
                                  removed_segments: list[BoilerplateSegment]) -> dict[str, Any]:
        """Generate processing statistics"""
        
        original_length = len(original)
        cleaned_length = len(cleaned)
        removed_length = sum(len(seg.text) for seg in removed_segments)
        
        stats = {
            'original_length': original_length,
            'cleaned_length': cleaned_length,
            'removed_length': removed_length,
            'removal_percentage': (removed_length / original_length * 100) if original_length > 0 else 0,
            'compression_ratio': cleaned_length / original_length if original_length > 0 else 1.0,
            'segments_removed': len(removed_segments),
            'avg_segment_confidence': sum(seg.confidence for seg in removed_segments) / len(removed_segments) if removed_segments else 0,
            'removal_by_category': {}
        }
        
        # Category breakdown
        category_stats = {}
        for segment in removed_segments:
            category = segment.category
            if category not in category_stats:
                category_stats[category] = {'count': 0, 'length': 0}
            category_stats[category]['count'] += 1
            category_stats[category]['length'] += len(segment.text)
        
        stats['removal_by_category'] = category_stats
        
        return stats
    
    def generate_processing_report(self, results: list[ProcessingResult]) -> dict[str, Any]:
        """Generate comprehensive processing report for multiple documents"""
        
        if not results:
            return {'error': 'No processing results provided'}
        
        # Aggregate statistics
        total_original = sum(len(r.original_text) for r in results)
        total_cleaned = sum(len(r.cleaned_text) for r in results)
        total_segments = sum(len(r.removed_segments) for r in results)
        
        avg_removal_percentage = sum(r.processing_stats['removal_percentage'] for r in results) / len(results)
        avg_compression_ratio = sum(r.processing_stats['compression_ratio'] for r in results) / len(results)
        
        # Category analysis across all documents
        category_totals = {}
        for result in results:
            for category, stats in result.processing_stats['removal_by_category'].items():
                if category not in category_totals:
                    category_totals[category] = {'count': 0, 'length': 0}
                category_totals[category]['count'] += stats['count']
                category_totals[category]['length'] += stats['length']
        
        report = {
            'summary': {
                'documents_processed': len(results),
                'total_original_length': total_original,
                'total_cleaned_length': total_cleaned,
                'total_removed_segments': total_segments,
                'avg_removal_percentage': avg_removal_percentage,
                'avg_compression_ratio': avg_compression_ratio,
            },
            'category_breakdown': category_totals,
            'document_details': [
                {
                    'original_length': r.processing_stats['original_length'],
                    'cleaned_length': r.processing_stats['cleaned_length'],
                    'removal_percentage': r.processing_stats['removal_percentage'],
                    'segments_removed': r.processing_stats['segments_removed'],
                }
                for r in results
            ],
            'processing_efficiency': {
                'high_removal': len([r for r in results if r.processing_stats['removal_percentage'] > 50]),
                'medium_removal': len([r for r in results if 20 < r.processing_stats['removal_percentage'] <= 50]),
                'low_removal': len([r for r in results if r.processing_stats['removal_percentage'] <= 20]),
            }
        }
        
        return report


def get_text_processor(confidence_threshold: float = 0.7,
                      preserve_structure: bool = True,
                      replacement_mode: str = 'placeholder') -> LegalTextProcessor:
    """Factory function for creating text processor"""
    return LegalTextProcessor(
        confidence_threshold=confidence_threshold,
        preserve_structure=preserve_structure,
        replacement_mode=replacement_mode
    )
