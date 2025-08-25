#!/usr/bin/env python3
"""
Standalone Legal Document Boilerplate Removal Tool

A complete, self-contained script for processing legal documents with OCR
and boilerplate removal. Uses the boilerplate removal components but doesn't
depend on the existing project infrastructure.

Usage:
    python standalone_boilerplate_remover.py input.pdf
    python standalone_boilerplate_remover.py --help
"""

import os
import sys
import argparse
import json
from typing import Dict, List, Any, Optional
from pathlib import Path

# Add current directory to path to import our boilerplate removal components
sys.path.append(str(Path(__file__).parent))

# Check dependencies
try:
    import pytesseract
    import pdf2image
    TESSERACT_AVAILABLE = True
except ImportError as e:
    print(f"Missing OCR dependencies: {e}")
    print("Install with: pip install pytesseract pillow pdf2image")
    TESSERACT_AVAILABLE = False

try:
    SKLEARN_AVAILABLE = True
except ImportError:
    print("Warning: sklearn not available - similarity detection disabled")
    print("Install with: pip install scikit-learn numpy")
    SKLEARN_AVAILABLE = False

# Import our boilerplate removal components
try:
    from legal_intelligence.boilerplate_removal.boilerplate_detector import LegalBoilerplateDetector
    from legal_intelligence.boilerplate_removal.text_processor import LegalTextProcessor
    COMPONENTS_AVAILABLE = True
except ImportError as e:
    print(f"Error importing boilerplate removal components: {e}")
    COMPONENTS_AVAILABLE = False


class StandaloneLegalProcessor:
    """Standalone legal document processor with OCR and boilerplate removal"""
    
    def __init__(self, 
                 ocr_dpi: int = 300,
                 similarity_threshold: float = 0.85,
                 confidence_threshold: float = 0.7,
                 replacement_mode: str = 'placeholder'):
        
        if not COMPONENTS_AVAILABLE:
            raise ImportError("Boilerplate removal components not available")
        
        self.ocr_dpi = ocr_dpi
        self.similarity_threshold = similarity_threshold
        self.confidence_threshold = confidence_threshold
        self.replacement_mode = replacement_mode
        
        # Initialize boilerplate removal components
        self.detector = LegalBoilerplateDetector(similarity_threshold=similarity_threshold)
        self.processor = LegalTextProcessor(
            confidence_threshold=confidence_threshold,
            replacement_mode=replacement_mode
        )
    
    def process_pdf(self, pdf_path: str, output_dir: str | None = None) -> dict[str, Any]:
        """Process a PDF file with OCR and boilerplate removal"""
        
        print(f"Processing: {os.path.basename(pdf_path)}")
        
        # Step 1: OCR
        print("  1. Extracting text with OCR...")
        text = self.extract_text_from_pdf(pdf_path)
        
        if not text.strip():
            raise ValueError("No text extracted from PDF")
        
        print(f"     Extracted {len(text):,} characters")
        
        # Step 2: Detect boilerplate
        print("  2. Detecting boilerplate...")
        document = {
            'content_id': Path(pdf_path).stem,
            'text': text,
            'metadata': {'file_path': pdf_path}
        }
        
        boilerplate_segments = self.detector.detect_boilerplate_in_documents([document])
        document_segments = boilerplate_segments[0] if boilerplate_segments else []
        
        print(f"     Found {len(document_segments)} boilerplate segments")
        
        # Step 3: Remove boilerplate
        print("  3. Removing boilerplate...")
        result = self.processor.process_document(text, document_segments, document['metadata'])
        
        print(f"     Removed {result.processing_stats['removal_percentage']:.1f}% of text")
        print(f"     Final length: {len(result.cleaned_text):,} characters")
        
        # Step 4: Save outputs
        if output_dir:
            self.save_outputs(result, pdf_path, output_dir)
        
        return {
            'pdf_path': pdf_path,
            'original_text': result.original_text,
            'cleaned_text': result.cleaned_text,
            'processing_stats': result.processing_stats,
            'removed_segments': result.removed_segments,
            'preservation_log': result.preservation_log
        }
    
    def process_multiple_pdfs(self, pdf_paths: list[str], output_dir: str | None = None) -> dict[str, Any]:
        """Process multiple PDFs with cross-document boilerplate analysis"""
        
        print(f"Processing {len(pdf_paths)} PDFs with batch analysis...")
        
        results = []
        all_documents = []
        
        # Step 1: OCR all documents
        print("  1. OCR extraction for all documents...")
        for pdf_path in pdf_paths:
            print(f"     Processing: {os.path.basename(pdf_path)}")
            
            try:
                text = self.extract_text_from_pdf(pdf_path)
                if text.strip():
                    document = {
                        'content_id': Path(pdf_path).stem,
                        'text': text,
                        'metadata': {'file_path': pdf_path}
                    }
                    all_documents.append(document)
                    print(f"       ✓ Extracted {len(text):,} characters")
                else:
                    print(f"       ✗ No text extracted")
            except Exception as e:
                print(f"       ✗ Error: {e}")
                continue
        
        if not all_documents:
            return {'success': False, 'error': 'No documents successfully processed'}
        
        # Step 2: Cross-document boilerplate detection
        print("  2. Cross-document boilerplate analysis...")
        all_boilerplate_segments = self.detector.detect_boilerplate_in_documents(all_documents)
        
        total_segments = sum(len(segments) for segments in all_boilerplate_segments)
        print(f"     Found {total_segments} total boilerplate segments")
        
        # Step 3: Process all documents
        print("  3. Removing boilerplate from all documents...")
        processing_results = self.processor.process_multiple_documents(
            all_documents, all_boilerplate_segments
        )
        
        # Step 4: Combine results
        for doc, processing_result in zip(all_documents, processing_results):
            result = {
                'pdf_path': doc['metadata']['file_path'],
                'success': True,
                'original_text': processing_result.original_text,
                'cleaned_text': processing_result.cleaned_text,
                'processing_stats': processing_result.processing_stats,
                'removed_segments': processing_result.removed_segments
            }
            results.append(result)
            
            # Save individual outputs
            if output_dir:
                self.save_outputs(processing_result, doc['metadata']['file_path'], output_dir)
        
        # Generate batch report
        batch_stats = self._generate_batch_stats(results)
        
        if output_dir:
            self._save_batch_report(batch_stats, output_dir)
        
        return {
            'success': True,
            'total_documents': len(pdf_paths),
            'processed_documents': len(results),
            'individual_results': results,
            'batch_statistics': batch_stats
        }
    
    def extract_text_from_pdf(self, pdf_path: str) -> str:
        """Extract text from PDF using OCR"""
        
        if not TESSERACT_AVAILABLE:
            raise ImportError("OCR dependencies not available. Install: pip install pytesseract pillow pdf2image")
        
        try:
            # Convert PDF to images
            pages = pdf2image.convert_from_path(pdf_path, dpi=self.ocr_dpi)
            
            if not pages:
                raise ValueError("Failed to convert PDF to images")
            
            full_text = []
            successful_pages = 0
            
            for page_num, page in enumerate(pages):
                try:
                    # OCR configuration optimized for legal documents
                    custom_config = r'--oem 3 --psm 6 -l eng -c tessedit_char_whitelist=ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789.,;:!?()[]{}"\'-/\\ '
                    
                    text = pytesseract.image_to_string(page, config=custom_config)
                    
                    if text.strip():
                        full_text.append(f"[PAGE {page_num + 1}]\n{text}")
                        successful_pages += 1
                    
                except Exception as e:
                    print(f"       Warning: OCR failed for page {page_num + 1}: {e}")
                    continue
            
            if successful_pages == 0:
                raise ValueError("OCR failed for all pages")
            
            print(f"       OCR successful on {successful_pages}/{len(pages)} pages")
            return "\n\n".join(full_text)
            
        except Exception as e:
            raise RuntimeError(f"OCR processing failed: {e}")
    
    def save_outputs(self, result, pdf_path: str, output_dir: str):
        """Save processing outputs"""
        
        os.makedirs(output_dir, exist_ok=True)
        base_name = Path(pdf_path).stem
        
        # Save cleaned text
        cleaned_file = os.path.join(output_dir, f"{base_name}_cleaned.txt")
        with open(cleaned_file, 'w', encoding='utf-8') as f:
            f.write(result.cleaned_text)
        
        # Save original OCR text
        original_file = os.path.join(output_dir, f"{base_name}_original_ocr.txt")
        with open(original_file, 'w', encoding='utf-8') as f:
            f.write(result.original_text)
        
        # Save processing report
        report_file = os.path.join(output_dir, f"{base_name}_report.json")
        
        # Convert result to JSON-serializable format
        report = {
            'file': pdf_path,
            'statistics': result.processing_stats,
            'processing_log': result.preservation_log,
            'removed_segments': [
                {
                    'category': seg.category,
                    'confidence': seg.confidence,
                    'pattern_type': seg.pattern_type,
                    'text_preview': seg.text[:100] + '...' if len(seg.text) > 100 else seg.text,
                    'text_length': len(seg.text)
                }
                for seg in result.removed_segments
            ],
            'configuration': {
                'similarity_threshold': self.similarity_threshold,
                'confidence_threshold': self.confidence_threshold,
                'replacement_mode': self.replacement_mode
            }
        }
        
        with open(report_file, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, default=str)
    
    def _generate_batch_stats(self, results: list[dict[str, Any]]) -> dict[str, Any]:
        """Generate batch processing statistics"""
        
        if not results:
            return {}
        
        total_original = sum(len(r.get('original_text', '')) for r in results)
        total_cleaned = sum(len(r.get('cleaned_text', '')) for r in results)
        
        removal_percentages = [r['processing_stats']['removal_percentage'] for r in results]
        
        return {
            'documents_processed': len(results),
            'total_original_length': total_original,
            'total_cleaned_length': total_cleaned,
            'overall_removal_percentage': ((total_original - total_cleaned) / total_original * 100) if total_original > 0 else 0,
            'average_removal_percentage': sum(removal_percentages) / len(removal_percentages),
            'min_removal_percentage': min(removal_percentages),
            'max_removal_percentage': max(removal_percentages),
            'total_segments_removed': sum(r['processing_stats']['segments_removed'] for r in results)
        }
    
    def _save_batch_report(self, batch_stats: dict[str, Any], output_dir: str):
        """Save batch processing report"""
        
        report_file = os.path.join(output_dir, "batch_processing_report.json")
        with open(report_file, 'w', encoding='utf-8') as f:
            json.dump(batch_stats, f, indent=2)


def test_with_sample():
    """Test the system with sample legal text"""
    
    sample_text = """
DEFENDANT BRAD MARTINEZ'S RESPONSES TO PLAINTIFF JAMES BURBANK'S 
REQUEST FOR PRODUCTION OF DOCUMENTS, SET ONE

REQUEST FOR PRODUCTION OF DOCUMENTS NO. 1:
ALL DOCUMENTS RELATING TO any lease, rental agreement, or any other agreement
between YOU and PLAINTIFF relating to the PROPERTY.

RESPONSE TO REQUEST FOR PRODUCTION OF DOCUMENTS NO. 1:
Responding Party objects to this request on the grounds that it is burdensome, oppressive, 
and harassing in its entirety. Responding Party objects that this request calls for documents already in the 
Propounding Party's possession. Responding Party does not have an obligation to obtain 
information that is equally available to the Propounding Party. (CCP § 2030.220(c).) Responding 
Party is not required to prepare the Plaintiff's case. (Sav-On Drugs, Inc. v. Superior Court of Los
Angeles County (1975) 15 Cal. 3d 1, 5.). Responding Party objects to this request on the basis that it calls for an expert opinion and/or a 
legal conclusion.

Subject to these objections but without waiving, Responding Party responds as follows: 
After diligent search and reasonable inquiry, Responding Party identifies and produces the 
following documents: DEF 000001- DEF 000046; DEF 000404. Discovery is ongoing and 
Responding Party reserves the right to amend, modify, or supplement its response as additional 
information is revealed through the discovery process.

REQUEST FOR PRODUCTION OF DOCUMENTS NO. 25:
Produce all documents, reports, photographs, invoices, estimates, communications, or other
writings that refer to, describe, or support a determination that the ceiling damage was caused by the
removal of the shower doors.

RESPONSE TO REQUEST FOR PRODUCTION OF DOCUMENTS NO. 25:
Responding Party objects to this request on the grounds that it is burdensome, oppressive, 
and harassing in its entirety. Responding Party objects to this request on the grounds and to the 
extent that it seeks information protected from disclosure as confidential financial information. 
Responding Party objects to this request on the basis as vague, and ambiguous as to the term "the 
tenants" which is nowhere defined by Propounding Party.
    """
    
    print("Testing with sample legal text...")
    print("="*80)
    
    try:
        from legal_intelligence.boilerplate_removal.boilerplate_detector import get_boilerplate_detector
        from legal_intelligence.boilerplate_removal.text_processor import get_text_processor
        
        detector = get_boilerplate_detector(similarity_threshold=0.85)
        processor = get_text_processor(confidence_threshold=0.7, replacement_mode='placeholder')
        
        # Create document
        document = {
            'content_id': 'sample_doc',
            'text': sample_text,
            'metadata': {'file_path': 'sample.txt'}
        }
        
        # Detect boilerplate
        print("Detecting boilerplate...")
        boilerplate_segments = detector.detect_boilerplate_in_documents([document])
        document_segments = boilerplate_segments[0] if boilerplate_segments else []
        
        print(f"Found {len(document_segments)} boilerplate segments:")
        for i, segment in enumerate(document_segments[:5]):  # Show first 5
            print(f"  {i+1}. {segment.category} (confidence: {segment.confidence:.2f})")
            print(f"     Text: {segment.text[:60]}...")
        
        # Process text
        print("\nRemoving boilerplate...")
        result = processor.process_document(sample_text, document_segments)
        
        print("\n" + "="*80)
        print("ORIGINAL TEXT:")
        print("="*80)
        print(sample_text[:500] + "..." if len(sample_text) > 500 else sample_text)
        
        print("\n" + "="*80)
        print("CLEANED TEXT:")
        print("="*80)
        print(result.cleaned_text[:500] + "..." if len(result.cleaned_text) > 500 else result.cleaned_text)
        
        print("\n" + "="*80)
        print("STATISTICS:")
        print("="*80)
        stats = result.processing_stats
        print(f"Original length: {stats['original_length']:,} characters")
        print(f"Cleaned length:  {stats['cleaned_length']:,} characters")
        print(f"Removed:         {stats['removed_length']:,} characters ({stats['removal_percentage']:.1f}%)")
        print(f"Segments removed: {stats['segments_removed']}")
        
        print(f"\nCategory breakdown:")
        for category, data in stats['removal_by_category'].items():
            print(f"  {category}: {data['count']} segments, {data['length']:,} characters")
        
    except Exception as e:
        print(f"Test failed: {e}")
        import traceback
        traceback.print_exc()


def main():
    """Main command-line interface"""
    
    parser = argparse.ArgumentParser(
        description="Standalone Legal Document Boilerplate Removal Tool",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python standalone_boilerplate_remover.py document.pdf
  python standalone_boilerplate_remover.py document.pdf --output ./cleaned/
  python standalone_boilerplate_remover.py document.pdf --confidence 0.8 --mode summary
  python standalone_boilerplate_remover.py --test
  python standalone_boilerplate_remover.py doc1.pdf doc2.pdf doc3.pdf --output ./batch/
        """
    )
    
    parser.add_argument('pdf_paths', nargs='*', help='Path(s) to PDF file(s) to process')
    parser.add_argument('--output', '-o', help='Output directory for results')
    parser.add_argument('--confidence', '-c', type=float, default=0.7, 
                       help='Confidence threshold for boilerplate removal (0.0-1.0)')
    parser.add_argument('--similarity', '-s', type=float, default=0.85,
                       help='Similarity threshold for cross-document detection (0.0-1.0)')
    parser.add_argument('--mode', '-m', choices=['placeholder', 'remove', 'summary'], 
                       default='placeholder', help='Replacement mode for boilerplate')
    parser.add_argument('--dpi', type=int, default=300, help='DPI for OCR processing')
    parser.add_argument('--test', action='store_true', help='Run test with sample text')
    parser.add_argument('--check-deps', action='store_true', help='Check dependencies')
    
    args = parser.parse_args()
    
    # Check dependencies
    if args.check_deps:
        print("Dependency Check:")
        print(f"  Tesseract OCR:        {'✓' if TESSERACT_AVAILABLE else '✗'}")
        print(f"  scikit-learn:         {'✓' if SKLEARN_AVAILABLE else '✗'}")
        print(f"  Boilerplate modules:  {'✓' if COMPONENTS_AVAILABLE else '✗'}")
        
        if TESSERACT_AVAILABLE:
            try:
                version = pytesseract.get_tesseract_version()
                print(f"  Tesseract version:    {version}")
            except:
                print("  Tesseract version:    Unable to determine")
        
        return 0
    
    # Test mode
    if args.test:
        test_with_sample()
        return 0
    
    # Validate inputs
    if not args.pdf_paths:
        parser.print_help()
        return 1
    
    if not TESSERACT_AVAILABLE:
        print("Error: OCR dependencies not available.")
        print("Install with: pip install pytesseract pillow pdf2image")
        return 1
    
    if not COMPONENTS_AVAILABLE:
        print("Error: Boilerplate removal components not available.")
        return 1
    
    # Check if files exist
    for pdf_path in args.pdf_paths:
        if not os.path.exists(pdf_path):
            print(f"Error: File not found: {pdf_path}")
            return 1
    
    try:
        # Initialize processor
        processor = StandaloneLegalProcessor(
            ocr_dpi=args.dpi,
            similarity_threshold=args.similarity,
            confidence_threshold=args.confidence,
            replacement_mode=args.mode
        )
        
        # Process files
        if len(args.pdf_paths) == 1:
            # Single file processing
            result = processor.process_pdf(args.pdf_paths[0], args.output)
            
            print(f"\n{'='*60}")
            print("PROCESSING COMPLETE")
            print(f"{'='*60}")
            print(f"File: {os.path.basename(result['pdf_path'])}")
            print(f"Removal: {result['processing_stats']['removal_percentage']:.1f}%")
            print(f"Segments: {result['processing_stats']['segments_removed']}")
            
        else:
            # Batch processing
            batch_result = processor.process_multiple_pdfs(args.pdf_paths, args.output)
            
            if batch_result['success']:
                print(f"\n{'='*60}")
                print("BATCH PROCESSING COMPLETE")
                print(f"{'='*60}")
                stats = batch_result['batch_statistics']
                print(f"Documents processed: {stats['documents_processed']}")
                print(f"Overall removal: {stats['overall_removal_percentage']:.1f}%")
                print(f"Average removal: {stats['average_removal_percentage']:.1f}%")
                print(f"Total segments removed: {stats['total_segments_removed']}")
            else:
                print(f"Batch processing failed: {batch_result.get('error', 'Unknown error')}")
                return 1
        
        return 0
        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit(main())
