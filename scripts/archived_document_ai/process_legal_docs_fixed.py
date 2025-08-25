#!/usr/bin/env python3
"""
Process legal documents with Google Document AI - Production-ready version.
Implements all critical fixes for correctness, reliability, and maintainability.
"""

import os
import json
import hashlib
import logging
from pathlib import Path
from datetime import datetime
import time
from dataclasses import dataclass

from google.cloud import documentai_v1 as documentai
from google.cloud import bigquery
from google.api_core.client_options import ClientOptions
from google.api_core import exceptions as api_exceptions
from google.api_core import retry

# ============= CONFIGURATION =============
# Set these as environment variables or update here
GOOGLE_APPLICATION_CREDENTIALS = os.getenv(
    'GOOGLE_APPLICATION_CREDENTIALS',
    '/Users/jim/Secrets/modular-command-466820-p2-bc0974cd5852.json'
)
os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = GOOGLE_APPLICATION_CREDENTIALS

PROJECT_ID = os.getenv('GCP_PROJECT_ID', 'modular-command-466820-p2')
LOCATION = os.getenv('DOCAI_LOCATION', 'us')

# Processor IDs - MUST be set!
FORM_PROCESSOR_ID = os.getenv(
    'FORM_PROCESSOR_ID',
    'projects/1098140055345/locations/us/processors/29975d02da9ab3a2'
)
OCR_PROCESSOR_ID = os.getenv(
    'OCR_PROCESSOR_ID', 
    'projects/1098140055345/locations/us/processors/8fadbc185616d041'
)

# BigQuery configuration
BQ_DATASET = f"{PROJECT_ID}.stoneman_case"
BQ_TARGET = f"{BQ_DATASET}.documents"
BQ_STAGE = f"{BQ_DATASET}.documents_stage"

# Processing configuration
STORE_FULL_TEXT_IN_BQ = False  # Store only excerpt in BQ to avoid row size limits
EXCERPT_LENGTH = 5000  # Characters to store in BQ
BATCH_SIZE = 10
MIN_CONFIDENCE = 0.7
DUAL_PROCESS = True
MAX_RETRIES = 3
RETRY_DELAY = 2  # seconds

# Paths
BASE_DIR = Path("data/Stoneman_dispute/pdfs_raw")
OUTPUT_DIR = Path("data/Stoneman_dispute/processed")
BIGQUERY_STAGING = Path("data/Stoneman_dispute/bigquery_staging")
LOW_CONFIDENCE_DIR = Path("data/Stoneman_dispute/low_confidence")
FULL_TEXT_DIR = Path("data/Stoneman_dispute/full_text")  # Store full text here

# Logging setup
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@dataclass
class ProcessingMetrics:
    """
    Track processing metrics for logging.
    """
    doc_id: str
    filename: str
    processor: str
    start_time: float
    end_time: float = 0
    text_length: int = 0
    page_count: int = 0
    confidence: float = 0
    success: bool = False
    error: str = ""
    
    @property
    def latency_ms(self) -> float:
        return (self.end_time - self.start_time) * 1000 if self.end_time else 0


class DocumentAIProcessor:
    """Process documents with Google Document AI - Production version."""
    
    def __init__(self):
        """
        Initialize with pre-existing processor IDs.
        """
        
        # Validate processor IDs
        if not FORM_PROCESSOR_ID or not OCR_PROCESSOR_ID:
            raise RuntimeError(
                "Missing processor IDs. Set FORM_PROCESSOR_ID and OCR_PROCESSOR_ID "
                "environment variables or update the script configuration."
            )
        
        # Initialize clients
        self.client = documentai.DocumentProcessorServiceClient(
            client_options=ClientOptions(api_endpoint=f"{LOCATION}-documentai.googleapis.com")
        )
        self.bq_client = bigquery.Client()
        
        # Store processor IDs
        self.form_parser = FORM_PROCESSOR_ID
        self.ocr_processor = OCR_PROCESSOR_ID
        
        # Create output directories
        for directory in [OUTPUT_DIR, BIGQUERY_STAGING, LOW_CONFIDENCE_DIR, FULL_TEXT_DIR]:
            directory.mkdir(parents=True, exist_ok=True)
        
        # Ensure BigQuery tables exist
        self._ensure_bigquery_tables()
        
        logger.info(f"✅ Initialized Document AI processors")
        logger.info(f"   Form Parser: {self.form_parser}")
        logger.info(f"   OCR Processor: {self.ocr_processor}")
    
    def _ensure_bigquery_tables(self):
        """
        Ensure BigQuery dataset and tables exist.
        """
        
        # Create dataset if needed
        dataset = bigquery.Dataset(BQ_DATASET)
        dataset.location = "US"
        dataset.description = "Stoneman legal case document analysis"
        
        try:
            self.bq_client.create_dataset(dataset, exists_ok=True)
            logger.info(f"Dataset ready: {BQ_DATASET}")
        except Exception as e:
            logger.error(f"Dataset creation error: {e}")
        
        # Define schema for both target and staging tables
        schema = [
            bigquery.SchemaField("document_id", "STRING", mode="REQUIRED"),
            bigquery.SchemaField("filename", "STRING", mode="REQUIRED"),
            bigquery.SchemaField("filepath", "STRING"),
            bigquery.SchemaField("full_text_path", "STRING"),  # Path to full text file
            bigquery.SchemaField("document_type", "STRING"),
            bigquery.SchemaField("content", "STRING"),  # Excerpt only
            bigquery.SchemaField("content_length", "INTEGER"),  # Full text length
            bigquery.SchemaField("confidence", "FLOAT64"),
            bigquery.SchemaField("processor_used", "STRING"),
            bigquery.SchemaField("dual_processed", "BOOLEAN"),
            bigquery.SchemaField("page_count", "INTEGER"),
            bigquery.SchemaField("extracted_entities", "JSON"),
            bigquery.SchemaField("evidence_classification", "JSON"),
            bigquery.SchemaField("processing_timestamp", "TIMESTAMP", mode="REQUIRED"),
            bigquery.SchemaField("processing_metrics", "JSON"),
            bigquery.SchemaField("parties", "STRING", mode="REPEATED"),
            bigquery.SchemaField("money_amounts", "FLOAT64", mode="REPEATED"),
        ]
        
        # Create both tables
        for table_id in [BQ_TARGET, BQ_STAGE]:
            table = bigquery.Table(table_id, schema=schema)
            try:
                self.bq_client.create_table(table, exists_ok=True)
                logger.info(f"Table ready: {table_id}")
            except Exception as e:
                logger.error(f"Table creation error for {table_id}: {e}")
    
    def determine_processor_type(self, file_path: Path) -> str:
        """
        Determine which processor to use based on filename patterns.
        """
        
        filename_lower = file_path.name.lower()
        
        # FORM_PARSER for structured legal forms
        form_patterns = ['3 day notice', '3-day', 'unlawful detainer', 'complaint', 
                        'motion', 'demur', 'judgment', 'summons', 'discovery',
                        'interrogator', 'rfa', 'rfp', 'rog', 'request for']
        
        for pattern in form_patterns:
            if pattern in filename_lower:
                return 'FORM_PARSER'
        
        # Default to OCR for narrative documents
        return 'OCR'
    
    @retry.Retry(predicate=retry.if_exception_type(api_exceptions.ResourceExhausted))
    def process_document(self, file_path: Path) -> dict:
        """
        Process a single document with retry logic.
        """
        
        processor_type = self.determine_processor_type(file_path)
        metrics = ProcessingMetrics(
            doc_id="",
            filename=file_path.name,
            processor=processor_type,
            start_time=time.time()
        )
        
        logger.info(f"Processing: {file_path.name} [Processor: {processor_type}]")
        
        # Read file
        with open(file_path, 'rb') as f:
            content = f.read()
        
        # Calculate document hash
        doc_hash = hashlib.sha256(content).hexdigest()
        metrics.doc_id = doc_hash
        
        # Prepare the document
        raw_document = documentai.RawDocument(
            content=content,
            mime_type='application/pdf'
        )
        
        # Configure OCR settings with page limits
        process_options = documentai.ProcessOptions(
            ocr_config=documentai.OcrConfig(
                enable_native_pdf_parsing=True,
                enable_image_quality_scores=True
            ),
            # Process first 30 pages (API limit)
            individual_page_selector=documentai.ProcessOptions.IndividualPageSelector(
                pages=list(range(1, 31))  # Pages 1-30
            )
        )
        
        results = {
            'document_id': doc_hash,
            'filename': file_path.name,
            'filepath': str(file_path),
            'processing_timestamp': datetime.utcnow().isoformat() + 'Z',
            'processor_used': processor_type,
            'dual_processed': False
        }
        
        try:
            # Select processor
            processor_name = self.form_parser if processor_type == 'FORM_PARSER' else self.ocr_processor
            
            # Process document
            request = documentai.ProcessRequest(
                name=processor_name,
                raw_document=raw_document,
                process_options=process_options
            )
            
            result = self.client.process_document(request=request)
            document = result.document
            
            # Extract results
            results['content'] = document.text
            results['page_count'] = len(document.pages) if document.pages else 1
            
            # Calculate confidence
            confidence_scores = []
            if document.pages:
                for page in document.pages:
                    # Try different confidence score locations
                    if hasattr(page, 'image_quality_scores') and page.image_quality_scores:
                        if hasattr(page.image_quality_scores, 'quality_score'):
                            confidence_scores.append(page.image_quality_scores.quality_score)
            
            results['confidence'] = sum(confidence_scores) / len(confidence_scores) if confidence_scores else 0.85
            
            # Dual processing if configured
            if DUAL_PROCESS and processor_type == 'FORM_PARSER':
                logger.info(f"  Running dual processing with OCR...")
                try:
                    ocr_request = documentai.ProcessRequest(
                        name=self.ocr_processor,
                        raw_document=raw_document,
                        process_options=process_options
                    )
                    ocr_result = self.client.process_document(request=ocr_request)
                    
                    # Compare and potentially use OCR result
                    if len(ocr_result.document.text) > len(document.text) * 1.2:
                        results['content'] = ocr_result.document.text
                        results['dual_processed'] = True
                        logger.info(f"  Using OCR output (20% more text)")
                except Exception as e:
                    logger.warning(f"  Dual processing failed: {e}")
            
            # Extract entities
            results['extracted_entities'] = self._extract_entities(results['content'])
            results['evidence_classification'] = self._classify_evidence(results['content'], file_path)
            
            # Update metrics
            metrics.text_length = len(results['content'])
            metrics.page_count = results['page_count']
            metrics.confidence = results['confidence']
            metrics.success = True
            
            logger.info(f"  ✅ Processed: {metrics.text_length} chars, "
                       f"confidence: {metrics.confidence:.2f}, "
                       f"pages: {metrics.page_count}")
            
        except Exception as e:
            logger.error(f"  ❌ Error: {e}")
            results['content'] = ''
            results['confidence'] = 0.0
            results['error'] = str(e)
            metrics.success = False
            metrics.error = str(e)
        
        # Record metrics
        metrics.end_time = time.time()
        results['processing_metrics'] = {
            'latency_ms': metrics.latency_ms,
            'success': metrics.success,
            'error': metrics.error
        }
        
        return results
    
    def _extract_entities(self, text: str) -> dict:
        """
        Extract legal entities from text.
        """
        
        if not text:
            return {}
        
        entities = {
            'people': [],
            'organizations': [],
            'dates': [],
            'money_amounts': [],
            'legal_terms': [],
            'case_numbers': []
        }
        
        import re
        
        # Extract dates
        date_patterns = [
            r'\b\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b',
            r'\b(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]* \d{1,2},? \d{4}\b'
        ]
        for pattern in date_patterns:
            entities['dates'].extend(re.findall(pattern, text, re.IGNORECASE))
        
        # Extract money
        money_pattern = r'\$[\d,]+(?:\.\d{2})?'
        entities['money_amounts'] = list(set(re.findall(money_pattern, text)))
        
        # Extract case numbers
        case_pattern = r'\b\d{2}[A-Z]{2,4}\d{5,8}\b'
        entities['case_numbers'] = re.findall(case_pattern, text)
        
        # Legal terms
        legal_keywords = [
            'plaintiff', 'defendant', 'complaint', 'motion',
            'unlawful detainer', 'eviction', 'retaliation',
            'habitability', 'quiet enjoyment'
        ]
        
        text_lower = text.lower()
        for term in legal_keywords:
            if term in text_lower:
                entities['legal_terms'].append(term)
        
        # Clean duplicates
        for key in entities:
            entities[key] = list(set(entities[key]))[:20]
        
        return entities
    
    def _classify_evidence(self, text: str, file_path: Path) -> dict:
        """
        Classify evidence relevance.
        """
        
        if not text:
            return {}
        
        classification = {
            'habitability': 0.0,
            'quiet_enjoyment': 0.0,
            'retaliation': 0.0,
            'evidence_strength': 'supporting'
        }
        
        text_lower = text.lower()
        
        # Score based on keywords
        if any(word in text_lower for word in ['mold', 'leak', 'repair', 'hazard']):
            classification['habitability'] = 0.9
        
        if any(word in text_lower for word in ['eviction', 'retaliation', 'complaint']):
            classification['retaliation'] = 0.8
        
        # Evidence strength
        if 'notice' in file_path.name.lower():
            classification['evidence_strength'] = 'strong'
        
        return classification
    
    def save_to_bigquery(self, batch: list[dict]):
        """
        Save batch to BigQuery using stage+merge pattern.
        """
        
        if not batch:
            return
        
        rows = []
        for result in batch:
            if not result.get('content'):
                continue
            
            # Save full text to file
            full_text_path = FULL_TEXT_DIR / f"{result['document_id']}.txt"
            with open(full_text_path, 'w', encoding='utf-8') as f:
                f.write(result['content'])
            
            # Extract money amounts as floats
            money_amounts = []
            for amount in result.get('extracted_entities', {}).get('money_amounts', []):
                try:
                    clean = float(amount.replace('$', '').replace(',', ''))
                    money_amounts.append(clean)
                except:
                    pass
            
            # Prepare row with excerpt only
            row = {
                'document_id': result['document_id'],
                'filename': result['filename'],
                'filepath': result.get('filepath', ''),
                'full_text_path': str(full_text_path),
                'document_type': self._determine_doc_type(result['filename']),
                'content': result['content'][:EXCERPT_LENGTH] if STORE_FULL_TEXT_IN_BQ else result['content'][:EXCERPT_LENGTH],
                'content_length': len(result['content']),
                'confidence': float(result.get('confidence', 0.0)),
                'processor_used': result.get('processor_used', 'OCR'),
                'dual_processed': result.get('dual_processed', False),
                'page_count': int(result.get('page_count', 0)),
                'extracted_entities': json.dumps(result.get('extracted_entities', {})),
                'evidence_classification': json.dumps(result.get('evidence_classification', {})),
                'processing_timestamp': result.get('processing_timestamp', datetime.utcnow().isoformat() + 'Z'),
                'processing_metrics': json.dumps(result.get('processing_metrics', {})),
                'parties': result.get('extracted_entities', {}).get('people', [])[:10],
                'money_amounts': money_amounts
            }
            rows.append(row)
        
        if not rows:
            logger.warning("No valid rows to insert")
            return
        
        try:
            # Insert to staging table
            errors = self.bq_client.insert_rows_json(BQ_STAGE, rows)
            if errors:
                logger.error(f"BigQuery stage insert errors: {errors}")
                return
            
            # Merge from staging to target (idempotent upsert)
            merge_query = f"""
            MERGE `{BQ_TARGET}` T
            USING `{BQ_STAGE}` S
            ON T.document_id = S.document_id
            WHEN MATCHED THEN UPDATE SET
                filename = S.filename,
                filepath = S.filepath,
                full_text_path = S.full_text_path,
                document_type = S.document_type,
                content = S.content,
                content_length = S.content_length,
                confidence = S.confidence,
                processor_used = S.processor_used,
                dual_processed = S.dual_processed,
                page_count = S.page_count,
                extracted_entities = S.extracted_entities,
                evidence_classification = S.evidence_classification,
                processing_timestamp = S.processing_timestamp,
                processing_metrics = S.processing_metrics,
                parties = S.parties,
                money_amounts = S.money_amounts
            WHEN NOT MATCHED THEN INSERT ROW
            """
            
            job = self.bq_client.query(merge_query)
            job.result()  # Wait for merge to complete
            
            # Clear staging table
            clear_query = f"DELETE FROM `{BQ_STAGE}` WHERE TRUE"
            self.bq_client.query(clear_query).result()
            
            logger.info(f"✅ Merged {len(rows)} documents to BigQuery")
            
        except Exception as e:
            logger.error(f"BigQuery error: {e}")
    
    def _determine_doc_type(self, filename: str) -> str:
        """
        Determine document type from filename.
        """
        
        filename_lower = filename.lower()
        
        if 'notice' in filename_lower:
            return 'notice'
        elif 'complaint' in filename_lower:
            return 'complaint'
        elif any(x in filename_lower for x in ['discovery', 'rfa', 'rog', 'rfp']):
            return 'discovery'
        elif 'motion' in filename_lower or 'demur' in filename_lower:
            return 'motion'
        elif 'report' in filename_lower:
            return 'report'
        else:
            return 'other'
    
    def process_all_documents(self):
        """
        Process all PDF documents with proper batching.
        """
        
        # Find all PDFs
        pdf_files = list(BASE_DIR.rglob("*.pdf"))
        
        logger.info(f"📚 Processing {len(pdf_files)} documents")
        print("=" * 60)
        
        results = []  # All results for summary
        batch = []    # Current batch for BigQuery
        low_confidence_files = []
        failed_files = []
        
        # Process each document
        for i, pdf_path in enumerate(pdf_files, 1):
            print(f"\n[{i}/{len(pdf_files)}] {pdf_path.name}")
            
            try:
                result = self.process_document(pdf_path)
                
                if result.get('content'):
                    results.append(result)
                    batch.append(result)
                    
                    # Check confidence
                    if result['confidence'] < MIN_CONFIDENCE:
                        low_confidence_files.append({
                            'file': str(pdf_path),
                            'confidence': result['confidence']
                        })
                        # Copy to low confidence directory
                        low_conf_path = LOW_CONFIDENCE_DIR / pdf_path.name
                        if not low_conf_path.exists():
                            import shutil
                            shutil.copy2(pdf_path, low_conf_path)
                    
                    # Save individual result JSON
                    json_path = OUTPUT_DIR / f"{result['document_id']}.json"
                    with open(json_path, 'w') as f:
                        json.dump(result, f, indent=2, default=str)
                    
                    # Batch save to BigQuery
                    if len(batch) >= BATCH_SIZE:
                        logger.info(f"💾 Saving batch of {len(batch)} to BigQuery...")
                        self.save_to_bigquery(batch)
                        batch.clear()  # Clear batch after saving
                else:
                    failed_files.append(str(pdf_path))
                
            except Exception as e:
                logger.error(f"Failed to process {pdf_path.name}: {e}")
                failed_files.append(str(pdf_path))
                continue
            
            # Rate limiting
            time.sleep(0.5)
        
        # Save final batch
        if batch:
            logger.info(f"💾 Saving final batch of {len(batch)} to BigQuery...")
            self.save_to_bigquery(batch)
        
        # Generate summary report
        self._generate_summary(results, low_confidence_files, failed_files, pdf_files)
    
    def _generate_summary(self, results, low_confidence_files, failed_files, pdf_files):
        """
        Generate and save processing summary.
        """
        
        print("\n" + "=" * 60)
        print("📊 PROCESSING SUMMARY")
        print(f"Total documents: {len(pdf_files)}")
        print(f"Successfully processed: {len(results)}")
        print(f"Failed: {len(failed_files)}")
        print(f"Low confidence (<{MIN_CONFIDENCE}): {len(low_confidence_files)}")
        
        if low_confidence_files:
            print(f"\n⚠️  Low confidence files moved to: {LOW_CONFIDENCE_DIR}")
            for item in low_confidence_files[:5]:
                print(f"  - {Path(item['file']).name}: {item['confidence']:.2f}")
        
        # Save comprehensive log
        log_path = OUTPUT_DIR / "processing_log.json"
        with open(log_path, 'w') as f:
            json.dump({
                'timestamp': datetime.utcnow().isoformat(),
                'configuration': {
                    'project_id': PROJECT_ID,
                    'processors': {
                        'form': FORM_PROCESSOR_ID,
                        'ocr': OCR_PROCESSOR_ID
                    },
                    'batch_size': BATCH_SIZE,
                    'dual_process': DUAL_PROCESS
                },
                'summary': {
                    'total_files': len(pdf_files),
                    'processed': len(results),
                    'failed': len(failed_files),
                    'low_confidence': len(low_confidence_files),
                    'avg_confidence': sum(r['confidence'] for r in results) / len(results) if results else 0
                },
                'failed_files': failed_files,
                'low_confidence_files': low_confidence_files
            }, f, indent=2)
        
        print(f"\n✅ Processing complete!")
        print(f"📂 Results: {OUTPUT_DIR}")
        print(f"📄 Full text: {FULL_TEXT_DIR}")
        print(f"⚠️  Low confidence: {LOW_CONFIDENCE_DIR}")
        print(f"📊 BigQuery: {BQ_TARGET}")
        print(f"📝 Log: {log_path}")


if __name__ == "__main__":
    print("🚀 GOOGLE DOCUMENT AI - PRODUCTION PROCESSING")
    print("=" * 60)
    print(f"Configuration:")
    print(f"  Project: {PROJECT_ID}")
    print(f"  Location: {LOCATION}")
    print(f"  Source: {BASE_DIR}")
    print(f"  Batch Size: {BATCH_SIZE}")
    print(f"  Dual Processing: {DUAL_PROCESS}")
    print(f"  Store Full Text in BQ: {STORE_FULL_TEXT_IN_BQ}")
    print()
    
    try:
        processor = DocumentAIProcessor()
        processor.process_all_documents()
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        raise