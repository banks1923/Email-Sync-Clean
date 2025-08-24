"""
Integration Module for Legal Document Boilerplate Removal

Integrates boilerplate removal with existing OCR pipeline and legal intelligence system.
"""

import os
from typing import Dict, List, Any, Optional
from pathlib import Path
from loguru import logger

# Import existing services
import sys
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.append(project_root)

from pdf.ocr.enhanced_ocr_engine import get_enhanced_ocr_engine
from .boilerplate_detector import get_boilerplate_detector
from .text_processor import get_text_processor


class LegalDocumentProcessor:
    """
    Integrated legal document processor combining OCR and boilerplate removal.
    
    Seamlessly integrates with existing Enhanced OCR Engine and Legal Intelligence system.
    """
    
    def __init__(self, 
                 ocr_dpi: int = 300,
                 similarity_threshold: float = 0.85,
                 confidence_threshold: float = 0.7,
                 replacement_mode: str = 'placeholder'):
        """
        Initialize integrated processor.
        
        Args:
            ocr_dpi: DPI for OCR processing
            similarity_threshold: Threshold for boilerplate similarity detection
            confidence_threshold: Minimum confidence to remove boilerplate
            replacement_mode: 'placeholder', 'summary', or 'remove'
        """
        # Initialize integrated components
        self.ocr_engine = get_enhanced_ocr_engine(dpi=ocr_dpi)
        self.boilerplate_detector = get_boilerplate_detector(similarity_threshold=similarity_threshold)
        self.text_processor = get_text_processor(
            confidence_threshold=confidence_threshold,
            replacement_mode=replacement_mode
        )
        
        # Configuration
        self.config = {
            'ocr_dpi': ocr_dpi,
            'similarity_threshold': similarity_threshold,
            'confidence_threshold': confidence_threshold,
            'replacement_mode': replacement_mode
        }
        
        logger.info("Legal Document Processor initialized with integrated OCR and boilerplate removal")
    
    def process_pdf_with_boilerplate_removal(self, 
                                           pdf_path: str,
                                           output_dir: str | None = None,
                                           save_intermediates: bool = True) -> dict[str, Any]:
        """
        Process a PDF with full OCR and boilerplate removal pipeline.
        
        Args:
            pdf_path: Path to PDF file
            output_dir: Directory to save outputs
            save_intermediates: Whether to save intermediate processing files
            
        Returns:
            Complete processing results
        """
        logger.info(f"Processing PDF with boilerplate removal: {pdf_path}")
        
        try:
            # Setup output directory
            if output_dir:
                os.makedirs(output_dir, exist_ok=True)
            
            # Step 1: OCR extraction using enhanced pipeline
            logger.info("Step 1: OCR text extraction")
            ocr_result = self._extract_text_with_enhanced_ocr(pdf_path)
            
            if not ocr_result['success']:
                return {
                    'success': False,
                    'error': f"OCR failed: {ocr_result.get('error', 'Unknown error')}",
                    'pdf_path': pdf_path
                }
            
            # Step 2: Boilerplate detection
            logger.info("Step 2: Boilerplate detection")
            document = {
                'content_id': Path(pdf_path).stem,
                'text': ocr_result['text'],
                'metadata': {
                    'file_path': pdf_path,
                    'ocr_method': ocr_result.get('method', 'unknown'),
                    'ocr_confidence': ocr_result.get('confidence', 0.0)
                }
            }
            
            boilerplate_segments = self.boilerplate_detector.detect_boilerplate_in_documents([document])
            document_segments = boilerplate_segments[0] if boilerplate_segments else []
            
            # Step 3: Text processing and boilerplate removal
            logger.info("Step 3: Boilerplate removal")
            processing_result = self.text_processor.process_document(
                text=ocr_result['text'],
                boilerplate_segments=document_segments,
                document_metadata=document['metadata']
            )
            
            # Step 4: Generate comprehensive results
            results = {
                'success': True,
                'pdf_path': pdf_path,
                'processing_pipeline': {
                    'ocr_result': ocr_result,
                    'boilerplate_detection': {
                        'segments_detected': len(document_segments),
                        'detection_report': self.boilerplate_detector.generate_boilerplate_report([document_segments], [document])
                    },
                    'text_processing': processing_result,
                },
                'final_outputs': {
                    'original_text': ocr_result['text'],
                    'cleaned_text': processing_result.cleaned_text,
                    'processing_stats': processing_result.processing_stats,
                    'preservation_log': processing_result.preservation_log
                },
                'metadata': {
                    'file_size': os.path.getsize(pdf_path) if os.path.exists(pdf_path) else 0,
                    'processing_config': self.config,
                    'ocr_validation_status': ocr_result.get('validation_status', 'unknown')
                }
            }
            
            # Step 5: Save outputs if requested
            if output_dir and save_intermediates:
                self._save_processing_outputs(results, output_dir)
            
            logger.info(f"Processing complete: {processing_result.processing_stats['removal_percentage']:.1f}% boilerplate removed")
            
            return results
            
        except Exception as e:
            logger.error(f"Error processing PDF {pdf_path}: {e}")
            return {
                'success': False,
                'error': str(e),
                'pdf_path': pdf_path
            }
    
    def process_multiple_pdfs(self, 
                             pdf_paths: list[str],
                             output_dir: str | None = None,
                             batch_analysis: bool = True) -> dict[str, Any]:
        """
        Process multiple PDFs with cross-document boilerplate analysis.
        
        Args:
            pdf_paths: List of PDF file paths
            output_dir: Directory to save outputs
            batch_analysis: Whether to analyze boilerplate across all documents
            
        Returns:
            Batch processing results
        """
        logger.info(f"Processing {len(pdf_paths)} PDFs with batch boilerplate analysis")
        
        if output_dir:
            os.makedirs(output_dir, exist_ok=True)
        
        # Step 1: OCR all documents
        logger.info("Step 1: OCR extraction for all documents")
        documents = []
        ocr_results = []
        
        for pdf_path in pdf_paths:
            logger.info(f"Processing: {os.path.basename(pdf_path)}")
            ocr_result = self._extract_text_with_enhanced_ocr(pdf_path)
            ocr_results.append(ocr_result)
            
            if ocr_result['success']:
                document = {
                    'content_id': Path(pdf_path).stem,
                    'text': ocr_result['text'],
                    'metadata': {
                        'file_path': pdf_path,
                        'ocr_method': ocr_result.get('method', 'unknown'),
                        'ocr_confidence': ocr_result.get('confidence', 0.0)
                    }
                }
                documents.append(document)
            else:
                logger.warning(f"OCR failed for {pdf_path}: {ocr_result.get('error', 'Unknown error')}")
        
        if not documents:
            return {
                'success': False,
                'error': 'No documents successfully processed with OCR',
                'pdf_paths': pdf_paths
            }
        
        # Step 2: Cross-document boilerplate detection
        logger.info("Step 2: Cross-document boilerplate analysis")
        if batch_analysis and len(documents) > 1:
            all_boilerplate_segments = self.boilerplate_detector.detect_boilerplate_in_documents(documents)
        else:
            # Process each document individually
            all_boilerplate_segments = []
            for doc in documents:
                segments = self.boilerplate_detector.detect_boilerplate_in_documents([doc])
                all_boilerplate_segments.extend(segments)
        
        # Step 3: Process all documents
        logger.info("Step 3: Boilerplate removal for all documents")
        processing_results = self.text_processor.process_multiple_documents(
            documents, all_boilerplate_segments
        )
        
        # Step 4: Generate batch results
        batch_results = {
            'success': True,
            'pdf_paths': pdf_paths,
            'documents_processed': len(documents),
            'documents_failed': len(pdf_paths) - len(documents),
            'individual_results': [],
            'batch_analysis': {
                'boilerplate_report': self.boilerplate_detector.generate_boilerplate_report(
                    all_boilerplate_segments, documents
                ),
                'processing_report': self.text_processor.generate_processing_report(processing_results)
            },
            'configuration': self.config
        }
        
        # Combine individual results
        for i, (doc, ocr_result, processing_result) in enumerate(zip(documents, ocr_results, processing_results)):
            individual_result = {
                'pdf_path': doc['metadata']['file_path'],
                'success': True,
                'ocr_result': ocr_result,
                'processing_result': processing_result,
                'final_text': processing_result.cleaned_text
            }
            batch_results['individual_results'].append(individual_result)
        
        # Step 5: Save batch outputs
        if output_dir:
            self._save_batch_outputs(batch_results, output_dir)
        
        logger.info(f"Batch processing complete: {len(documents)} documents processed")
        
        return batch_results
    
    def _extract_text_with_enhanced_ocr(self, pdf_path: str) -> dict[str, Any]:
        """Extract text using the enhanced OCR pipeline"""
        
        try:
            # Use existing PDF processing pipeline
            from pdf2image import convert_from_path
            
            # Convert PDF to images
            pages = convert_from_path(pdf_path, dpi=self.config['ocr_dpi'])
            
            if not pages:
                return {'success': False, 'error': 'Failed to convert PDF to images'}
            
            # Process each page with enhanced OCR
            full_text_parts = []
            processing_logs = []
            overall_confidence = 0.0
            
            for page_num, page_image in enumerate(pages):
                logger.debug(f"Processing page {page_num + 1}/{len(pages)}")
                
                # Use enhanced OCR engine
                page_result = self.ocr_engine.extract_text_with_dual_pass(
                    image=page_image,
                    page_count=len(pages),
                    force_enhanced=False
                )
                
                if page_result['success']:
                    page_text = page_result.get('text', '')
                    if page_text.strip():  # Only add non-empty pages
                        full_text_parts.append(f"[PAGE {page_num + 1}]\n{page_text}")
                        overall_confidence += page_result.get('confidence', 0.0)
                        
                        if 'processing_log' in page_result:
                            processing_logs.extend(page_result['processing_log'])
                else:
                    logger.warning(f"Page {page_num + 1} OCR failed: {page_result.get('error', 'Unknown error')}")
            
            if not full_text_parts:
                return {'success': False, 'error': 'No text extracted from any pages'}
            
            # Combine all pages
            full_text = '\n\n'.join(full_text_parts)
            avg_confidence = overall_confidence / len(pages) if pages else 0.0
            
            return {
                'success': True,
                'text': full_text,
                'confidence': avg_confidence,
                'method': 'enhanced_dual_pass',
                'pages_processed': len(pages),
                'pages_successful': len(full_text_parts),
                'processing_log': processing_logs,
                'validation_status': 'text_validated' if avg_confidence > 0.7 else 'ocr_done'
            }
            
        except Exception as e:
            logger.error(f"Enhanced OCR failed for {pdf_path}: {e}")
            return {'success': False, 'error': str(e)}
    
    def _save_processing_outputs(self, results: dict[str, Any], output_dir: str):
        """Save individual processing outputs"""
        
        pdf_path = results['pdf_path']
        base_name = Path(pdf_path).stem
        
        # Save original OCR text
        ocr_file = os.path.join(output_dir, f"{base_name}_ocr.txt")
        with open(ocr_file, 'w', encoding='utf-8') as f:
            f.write(results['final_outputs']['original_text'])
        
        # Save cleaned text
        cleaned_file = os.path.join(output_dir, f"{base_name}_cleaned.txt")
        with open(cleaned_file, 'w', encoding='utf-8') as f:
            f.write(results['final_outputs']['cleaned_text'])
        
        # Save processing report
        import json
        report_file = os.path.join(output_dir, f"{base_name}_report.json")
        with open(report_file, 'w', encoding='utf-8') as f:
            # Make results JSON serializable
            serializable_results = self._make_json_serializable(results)
            json.dump(serializable_results, f, indent=2)
        
        logger.info(f"Saved processing outputs for {base_name} to {output_dir}")
    
    def _save_batch_outputs(self, results: dict[str, Any], output_dir: str):
        """Save batch processing outputs"""
        
        import json
        
        # Save batch report
        batch_report_file = os.path.join(output_dir, "batch_processing_report.json")
        with open(batch_report_file, 'w', encoding='utf-8') as f:
            serializable_results = self._make_json_serializable(results)
            json.dump(serializable_results, f, indent=2)
        
        # Save individual cleaned texts
        for result in results['individual_results']:
            if result['success']:
                base_name = Path(result['pdf_path']).stem
                cleaned_file = os.path.join(output_dir, f"{base_name}_cleaned.txt")
                with open(cleaned_file, 'w', encoding='utf-8') as f:
                    f.write(result['processing_result'].cleaned_text)
        
        logger.info(f"Saved batch outputs to {output_dir}")
    
    def _make_json_serializable(self, obj: Any) -> Any:
        """Make object JSON serializable"""
        
        if hasattr(obj, '__dict__'):
            # Convert dataclass or object to dict
            return {k: self._make_json_serializable(v) for k, v in obj.__dict__.items()}
        elif isinstance(obj, dict):
            return {k: self._make_json_serializable(v) for k, v in obj.items()}
        elif isinstance(obj, (list, tuple)):
            return [self._make_json_serializable(item) for item in obj]
        elif isinstance(obj, set):
            return list(obj)
        elif hasattr(obj, 'isoformat'):  # datetime objects
            return obj.isoformat()
        else:
            return obj
    
    def validate_setup(self) -> dict[str, Any]:
        """Validate complete setup"""
        
        validation = {
            'ocr_engine': self.ocr_engine.validate_enhanced_setup(),
            'boilerplate_detector': self.boilerplate_detector.validate_setup(),
            'configuration': self.config,
            'integrated_pipeline': True
        }
        
        validation['ready'] = (
            validation['ocr_engine'].get('ready', False) and
            validation['boilerplate_detector'].get('ready', False)
        )
        
        return validation
    
    def get_processing_statistics(self) -> dict[str, Any]:
        """Get processing statistics and capabilities"""
        
        return {
            'ocr_capabilities': {
                'enhanced_dual_pass': True,
                'born_digital_detection': True,
                'quality_validation': True,
                'supported_formats': ['PDF']
            },
            'boilerplate_detection': {
                'pattern_based': True,
                'similarity_based': self.boilerplate_detector.available,
                'cross_document_analysis': True,
                'pattern_categories': list(self.boilerplate_detector.boilerplate_patterns.keys())
            },
            'text_processing': {
                'preservation_rules': True,
                'multiple_replacement_modes': True,
                'structure_preservation': True,
                'safety_checks': True
            },
            'configuration': self.config
        }


def get_legal_document_processor(**kwargs) -> LegalDocumentProcessor:
    """Factory function for creating integrated legal document processor"""
    return LegalDocumentProcessor(**kwargs)


# Example usage
if __name__ == "__main__":
    # Example of how to use the integrated processor
    processor = get_legal_document_processor()
    
    # Validate setup
    validation = processor.validate_setup()
    if validation['ready']:
        print("✓ Legal Document Processor ready")
        
        # Process single document
        # result = processor.process_pdf_with_boilerplate_removal(
        #     pdf_path="path/to/legal_document.pdf",
        #     output_dir="./processed_output"
        # )
        
        # Process multiple documents
        # batch_result = processor.process_multiple_pdfs(
        #     pdf_paths=["doc1.pdf", "doc2.pdf", "doc3.pdf"],
        #     output_dir="./batch_output"
        # )
    else:
        print("✗ Legal Document Processor setup incomplete")
        print(validation)
