#!/usr/bin/env python3
"""
Process legal documents with Google Document AI using dual processors.
Using correct processor types: FORM_PARSER_PROCESSOR and OCR_PROCESSOR
"""

import os
import json
import hashlib
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Tuple
import time

from google.cloud import documentai_v1 as documentai
from google.cloud import bigquery
from google.api_core.client_options import ClientOptions
from tqdm import tqdm

# Set up credentials
os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = '/Users/jim/Secrets/modular-command-466820-p2-bc0974cd5852.json'

# Configuration
PROJECT_ID = "modular-command-466820-p2"
LOCATION = "us"  # Document AI location

# Paths
BASE_DIR = Path("data/Stoneman_dispute/pdfs_raw")
OUTPUT_DIR = Path("data/Stoneman_dispute/processed")
BIGQUERY_STAGING = Path("data/Stoneman_dispute/bigquery_staging")
LOW_CONFIDENCE = Path("data/Stoneman_dispute/low_confidence")

# Thresholds
MIN_CONFIDENCE = 0.7
DUAL_PROCESS = True  # Run both processors

class DocumentAIProcessor:
    """Process documents with Google Document AI."""
    
    def __init__(self):
        """Initialize Document AI client."""
        self.client = documentai.DocumentProcessorServiceClient(
            client_options=ClientOptions(api_endpoint=f"{LOCATION}-documentai.googleapis.com")
        )
        self.bq_client = bigquery.Client()
        
        # Create output directories
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        BIGQUERY_STAGING.mkdir(parents=True, exist_ok=True)
        LOW_CONFIDENCE.mkdir(parents=True, exist_ok=True)
        
        # List available processor types
        print("🔍 Checking available processor types...")
        parent = f"projects/{PROJECT_ID}/locations/{LOCATION}"
        
        # Get available processor types
        processor_types = self.client.fetch_processor_types(parent=parent)
        available_types = []
        for proc_type in processor_types.processor_types:
            available_types.append(proc_type.type_)
            if 'FORM' in proc_type.type_ or 'OCR' in proc_type.type_:
                print(f"  Found: {proc_type.type_} - {proc_type.category}")
        
        # Use the correct processor types
        # For forms: FORM_PARSER_PROCESSOR
        # For OCR: OCR_PROCESSOR or DOCUMENT_OCR_PROCESSOR
        self.form_parser = self._get_or_create_processor("FORM_PARSER_PROCESSOR")
        self.ocr_processor = self._get_or_create_processor("OCR_PROCESSOR")
        
        print(f"✅ Initialized Document AI processors")
    
    def _get_or_create_processor(self, processor_type: str) -> str:
        """Get existing processor or create new one."""
        parent = f"projects/{PROJECT_ID}/locations/{LOCATION}"
        
        # List existing processors
        try:
            processors = self.client.list_processors(parent=parent)
            
            for processor in processors:
                if processor.type_ == processor_type:
                    print(f"✅ Found existing {processor_type}: {processor.name}")
                    return processor.name
        except Exception as e:
            print(f"Note: {e}")
        
        # Create new processor
        try:
            processor = documentai.Processor(
                display_name=f"Stoneman-{processor_type}",
                type_=processor_type
            )
            
            response = self.client.create_processor(
                parent=parent,
                processor=processor
            )
            
            print(f"✅ Created new {processor_type}: {response.name}")
            return response.name
        except Exception as e:
            print(f"⚠️  Could not create {processor_type}: {e}")
            # Fall back to using simple OCR endpoint
            return None
    
    def determine_processor_type(self, file_path: Path) -> str:
        """Determine which processor to use based on filename patterns."""
        
        filename_lower = file_path.name.lower()
        
        # FORM_PARSER for structured legal forms
        form_patterns = ['3 day notice', '3-day', 'unlawful detainer', 'complaint', 
                        'motion', 'demur', 'judgment', 'summons']
        for pattern in form_patterns:
            if pattern in filename_lower:
                return 'FORM_PARSER'
        
        # Contract parser for discovery documents
        discovery_patterns = ['discovery', 'interrogator', 'rfa', 'rfp', 'rog', 
                            'request for', 'response']
        for pattern in discovery_patterns:
            if pattern in filename_lower:
                return 'FORM_PARSER'  # Use form parser for structured discovery
        
        # OCR for narrative documents
        narrative_patterns = ['report', 'inspection', 'letter', 'email', 
                            'narrative', 'assessment']
        for pattern in narrative_patterns:
            if pattern in filename_lower:
                return 'OCR'
        
        # Default to OCR for unknown types
        return 'OCR'
    
    def process_document_simple(self, file_path: Path) -> Dict:
        """Process document using appropriate processor based on document type."""
        
        # Determine processor type
        processor_type = self.determine_processor_type(file_path)
        print(f"  📄 Processing: {file_path.name} [Processor: {processor_type}]")
        
        # Read file
        with open(file_path, 'rb') as f:
            content = f.read()
        
        # Calculate document hash
        doc_hash = hashlib.sha256(content).hexdigest()
        
        # Prepare the document
        raw_document = documentai.RawDocument(
            content=content,
            mime_type='application/pdf'
        )
        
        # Configure OCR settings based on processor type
        if processor_type == 'FORM_PARSER':
            # Settings optimized for forms with checkboxes and fields
            process_options = documentai.ProcessOptions(
                ocr_config=documentai.OcrConfig(
                    enable_native_pdf_parsing=True,
                    enable_image_quality_scores=True
                )
            )
        else:
            # Settings optimized for narrative text
            process_options = documentai.ProcessOptions(
                ocr_config=documentai.OcrConfig(
                    enable_native_pdf_parsing=True,
                    enable_image_quality_scores=True
                )
            )
        
        results = {
            'document_id': doc_hash,
            'filename': file_path.name,
            'filepath': str(file_path),
            'processing_timestamp': datetime.utcnow().isoformat(),
            'processor_used': processor_type
        }
        
        try:
            # Select appropriate processor
            if processor_type == 'FORM_PARSER' and self.form_parser:
                processor_name = self.form_parser
            elif processor_type == 'OCR' and self.ocr_processor:
                processor_name = self.ocr_processor
            else:
                # If no processor available, skip this file
                print(f"    ⚠️  No processor available for {processor_type}")
                results['content'] = ''
                results['error'] = 'No processor available'
                return results
            
            # Process with selected processor
            request = documentai.ProcessRequest(
                name=processor_name,
                raw_document=raw_document,
                process_options=process_options
            )
            
            result = self.client.process_document(request=request)
            document = result.document
            
            # Extract text
            results['content'] = document.text
            results['page_count'] = len(document.pages) if document.pages else 1
            
            # Calculate confidence
            confidence_scores = []
            if document.pages:
                for page in document.pages:
                    if hasattr(page, 'image_quality_scores') and page.image_quality_scores:
                        if hasattr(page.image_quality_scores, 'quality_score'):
                            confidence_scores.append(page.image_quality_scores.quality_score)
            
            results['confidence'] = sum(confidence_scores) / len(confidence_scores) if confidence_scores else 0.85
            
            # DUAL PROCESSING: Run both processors if configured
            if DUAL_PROCESS and processor_type == 'FORM_PARSER':
                # Also run OCR processor for comparison
                print(f"    📝 Running dual processing with OCR...")
                try:
                    ocr_request = documentai.ProcessRequest(
                        name=self.ocr_processor if self.ocr_processor else processor_name,
                        raw_document=raw_document,
                        process_options=documentai.ProcessOptions(
                            ocr_config=documentai.OcrConfig(
                                enable_native_pdf_parsing=True,
                                enable_image_quality_scores=True
                            )
                        )
                    )
                    ocr_result = self.client.process_document(request=ocr_request)
                    
                    # Store both outputs if different
                    if ocr_result.document.text != document.text:
                        results['content_ocr'] = ocr_result.document.text
                        results['dual_processed'] = True
                        # Use longer text (usually more complete)
                        if len(ocr_result.document.text) > len(document.text):
                            results['content'] = ocr_result.document.text
                            print(f"    ℹ️  OCR text longer, using OCR output")
                except Exception as e:
                    print(f"    ⚠️  Dual processing failed: {e}")
            
            # Extract entities
            results['extracted_entities'] = self._extract_entities(results['content'])
            results['evidence_classification'] = self._classify_evidence(results['content'], file_path)
            
            print(f"    ✅ Processed: {len(results['content'])} chars, confidence: {results['confidence']:.2f}")
            
        except Exception as e:
            print(f"    ❌ Error: {e}")
            results['content'] = ''
            results['confidence'] = 0.0
            results['page_count'] = 0
            results['error'] = str(e)
        
        return results
    
    def _extract_entities(self, text: str) -> Dict:
        """Extract legal entities from text."""
        
        entities = {
            'people': [],
            'organizations': [],
            'locations': [],
            'dates': [],
            'money_amounts': [],
            'legal_terms': [],
            'case_numbers': [],
            'statutes': []
        }
        
        import re
        
        # Extract dates (multiple formats)
        date_patterns = [
            r'\b\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b',
            r'\b(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]* \d{1,2},? \d{4}\b',
            r'\b\d{1,2} (?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]* \d{4}\b'
        ]
        for pattern in date_patterns:
            entities['dates'].extend(re.findall(pattern, text, re.IGNORECASE))
        
        # Extract money amounts
        money_pattern = r'\$[\d,]+(?:\.\d{2})?'
        entities['money_amounts'] = list(set(re.findall(money_pattern, text)))
        
        # Extract case numbers
        case_patterns = [
            r'\b\d{2}[A-Z]{2,4}\d{5,8}\b',  # Like 24NNCV06082
            r'\bCase No\.\s*[A-Z0-9-]+\b'
        ]
        for pattern in case_patterns:
            entities['case_numbers'].extend(re.findall(pattern, text))
        
        # Legal terms and violations
        legal_keywords = [
            'plaintiff', 'defendant', 'complaint', 'motion', 'demurrer',
            'notice', 'breach', 'violation', 'landlord', 'tenant',
            'unlawful detainer', 'eviction', 'retaliation', 'harassment',
            'habitability', 'quiet enjoyment', 'discovery', 'interrogatories',
            'request for admission', 'request for production'
        ]
        
        text_lower = text.lower()
        for term in legal_keywords:
            if term in text_lower:
                entities['legal_terms'].append(term)
        
        # Extract potential names (simplified)
        # Look for patterns like "FirstName LastName" after specific keywords
        name_contexts = ['Plaintiff', 'Defendant', 'Attorney for', 'Landlord', 'Tenant']
        for context in name_contexts:
            pattern = f'{context}:?\\s+([A-Z][a-z]+ [A-Z][a-z]+)'
            matches = re.findall(pattern, text)
            entities['people'].extend(matches)
        
        # Extract organizations
        org_keywords = ['LLC', 'Inc', 'Corporation', 'Company', 'LP', 'LLP', 'HOA']
        for keyword in org_keywords:
            pattern = f'([A-Z][A-Za-z0-9 &]+\\s+{keyword}\\.?)'
            matches = re.findall(pattern, text)
            entities['organizations'].extend(matches)
        
        # Clean up duplicates
        for key in entities:
            entities[key] = list(set(entities[key]))[:20]  # Limit to 20 items
        
        return entities
    
    def _classify_evidence(self, text: str, file_path: Path) -> Dict:
        """Classify evidence relevance for legal claims."""
        
        classification = {
            'habitability': 0.0,
            'quiet_enjoyment': 0.0,
            'retaliation': 0.0,
            'breach_of_contract': 0.0,
            'harassment': 0.0,
            'evidence_strength': 'supporting',
            'document_category': ''
        }
        
        text_lower = text.lower()
        filename_lower = file_path.name.lower()
        
        # Document categorization
        if 'notice' in filename_lower:
            classification['document_category'] = 'notice'
            classification['evidence_strength'] = 'strong'
        elif 'complaint' in filename_lower:
            classification['document_category'] = 'complaint'
            classification['evidence_strength'] = 'strong'
        elif 'discovery' in filename_lower or 'interrogator' in filename_lower:
            classification['document_category'] = 'discovery'
        elif 'report' in filename_lower or 'inspection' in filename_lower:
            classification['document_category'] = 'inspection'
        
        # Habitability issues
        habitability_keywords = ['mold', 'water damage', 'leak', 'repair', 'maintenance',
                                'inspection', 'hazard', 'unsafe', 'health', 'servpro']
        habitability_score = sum(1 for keyword in habitability_keywords if keyword in text_lower)
        classification['habitability'] = min(habitability_score / 5, 1.0)
        
        # Quiet enjoyment
        quiet_keywords = ['noise', 'disturbance', 'harassment', 'entry without', 
                         'privacy', 'interfere', 'peaceful']
        quiet_score = sum(1 for keyword in quiet_keywords if keyword in text_lower)
        classification['quiet_enjoyment'] = min(quiet_score / 3, 1.0)
        
        # Retaliation
        retaliation_keywords = ['retaliation', 'eviction', 'after complaint', 
                               'response to', 'because', 'punitive']
        retaliation_score = sum(1 for keyword in retaliation_keywords if keyword in text_lower)
        classification['retaliation'] = min(retaliation_score / 3, 1.0)
        
        # Harassment
        if 'harassment' in text_lower or 'harass' in text_lower:
            classification['harassment'] = 0.9
        
        # Determine overall evidence strength
        max_score = max(classification['habitability'], 
                       classification['quiet_enjoyment'],
                       classification['retaliation'])
        
        if max_score > 0.8:
            classification['evidence_strength'] = 'smoking_gun'
        elif max_score > 0.5:
            classification['evidence_strength'] = 'strong'
        
        return classification
    
    def save_to_bigquery(self, results: List[Dict]):
        """Save processing results to BigQuery."""
        
        dataset_id = f"{PROJECT_ID}.stoneman_case"
        table_id = f"{dataset_id}.documents"
        
        # Prepare rows for BigQuery
        rows = []
        for result in results:
            if not result.get('content'):  # Skip failed documents
                continue
                
            row = {
                'document_id': result['document_id'],
                'filename': result['filename'],
                'filepath': result['filepath'],
                'document_type': self._determine_doc_type(result['filename']),
                'content': result.get('content', ''),
                'confidence': float(result.get('confidence', 0.0)),
                'processor_used': result.get('processor_used', 'OCR'),
                'page_count': int(result.get('page_count', 0)),
                'extracted_entities': json.dumps(result.get('extracted_entities', {})),
                'evidence_classification': json.dumps(result.get('evidence_classification', {})),
                'processing_timestamp': datetime.utcnow().isoformat() + 'Z',
                'parties': result.get('extracted_entities', {}).get('people', [])[:10],
                'money_amounts': []
            }
            
            # Extract money amounts as floats
            for amount in result.get('extracted_entities', {}).get('money_amounts', []):
                try:
                    clean_amount = float(amount.replace('$', '').replace(',', ''))
                    row['money_amounts'].append(clean_amount)
                except:
                    pass
            
            rows.append(row)
        
        if not rows:
            print("⚠️  No valid rows to insert to BigQuery")
            return
        
        # Insert rows
        try:
            errors = self.bq_client.insert_rows_json(table_id, rows)
            
            if errors:
                print(f"⚠️  BigQuery insert errors: {errors}")
            else:
                print(f"✅ Inserted {len(rows)} documents to BigQuery")
        except Exception as e:
            print(f"❌ BigQuery error: {e}")
        
        # Save to JSON for backup
        for result in results:
            if result.get('content'):
                json_path = BIGQUERY_STAGING / f"{result['document_id']}.json"
                with open(json_path, 'w') as f:
                    json.dump(result, f, indent=2, default=str)
    
    def _determine_doc_type(self, filename: str) -> str:
        """Determine document type from filename."""
        
        filename_lower = filename.lower()
        
        if 'notice' in filename_lower:
            return 'notice'
        elif 'complaint' in filename_lower:
            return 'complaint'
        elif 'discovery' in filename_lower or 'rfa' in filename_lower or 'rog' in filename_lower:
            return 'discovery'
        elif 'motion' in filename_lower or 'demur' in filename_lower:
            return 'motion'
        elif 'report' in filename_lower or 'inspection' in filename_lower:
            return 'report'
        elif 'response' in filename_lower:
            return 'response'
        else:
            return 'other'
    
    def process_all_documents(self):
        """Process all PDF documents in the directory."""
        
        # Find all PDFs
        pdf_files = list(BASE_DIR.rglob("*.pdf"))
        
        print(f"\n📚 Processing {len(pdf_files)} documents")
        print("=" * 60)
        
        results = []
        low_confidence_files = []
        failed_files = []
        
        # Process each document
        for i, pdf_path in enumerate(pdf_files, 1):
            print(f"\n[{i}/{len(pdf_files)}] Processing: {pdf_path.name}")
            
            try:
                result = self.process_document_simple(pdf_path)
                
                if result.get('content'):
                    results.append(result)
                    
                    # Check confidence
                    if result['confidence'] < MIN_CONFIDENCE:
                        low_confidence_files.append({
                            'file': str(pdf_path),
                            'confidence': result['confidence']
                        })
                        print(f"    ⚠️  Low confidence: {result['confidence']:.2f}")
                    
                    # Save individual result
                    json_path = OUTPUT_DIR / f"{result['document_id']}.json"
                    with open(json_path, 'w') as f:
                        json.dump(result, f, indent=2, default=str)
                else:
                    failed_files.append(str(pdf_path))
                
            except Exception as e:
                print(f"    ❌ Error: {e}")
                failed_files.append(str(pdf_path))
                continue
            
            # Small delay to avoid rate limits
            time.sleep(1)
            
            # Save to BigQuery in batches
            if len(results) % 10 == 0:
                print(f"\n💾 Saving batch of {len(results)} to BigQuery...")
                self.save_to_bigquery(results)
        
        # Final save to BigQuery
        if results:
            print(f"\n💾 Final save of {len(results)} documents to BigQuery...")
            self.save_to_bigquery(results)
        
        # Report summary
        print("\n" + "=" * 60)
        print("📊 PROCESSING SUMMARY")
        print(f"Total documents: {len(pdf_files)}")
        print(f"Successfully processed: {len(results)}")
        print(f"Failed: {len(failed_files)}")
        print(f"Low confidence (<{MIN_CONFIDENCE}): {len(low_confidence_files)}")
        
        if low_confidence_files:
            print("\n⚠️  Low confidence files:")
            for item in low_confidence_files[:5]:
                print(f"  - {Path(item['file']).name}: {item['confidence']:.2f}")
        
        if failed_files:
            print("\n❌ Failed files:")
            for file in failed_files[:5]:
                print(f"  - {Path(file).name}")
        
        # Save processing log
        log_path = OUTPUT_DIR / "processing_log.json"
        with open(log_path, 'w') as f:
            json.dump({
                'timestamp': datetime.utcnow().isoformat(),
                'total_files': len(pdf_files),
                'processed': len(results),
                'failed': failed_files,
                'low_confidence': low_confidence_files,
                'summary': {
                    'avg_confidence': sum(r['confidence'] for r in results) / len(results) if results else 0
                }
            }, f, indent=2)
        
        print(f"\n✅ Processing complete!")
        print(f"📂 Results saved to: {OUTPUT_DIR}")
        print(f"📊 BigQuery dataset: {PROJECT_ID}.stoneman_case")
        print(f"📝 Log: {log_path}")

if __name__ == "__main__":
    print("🚀 GOOGLE DOCUMENT AI - LEGAL DOCUMENT PROCESSING")
    print("=" * 60)
    print("Configuration:")
    print(f"  Project: {PROJECT_ID}")
    print(f"  Location: {LOCATION}")
    print(f"  Source: {BASE_DIR}")
    print(f"  Min Confidence: {MIN_CONFIDENCE}")
    print()
    
    processor = DocumentAIProcessor()
    processor.process_all_documents()