#!/usr/bin/env python3
"""
Enhanced Document AI processor with comprehensive fixes for 95-100% ingestion success.
Implements: pre-screening, PDF splitting, coverage metrics, stage->merge pattern, and operational guardrails.
"""

import os
import json
import hashlib
import logging
import time
import sqlite3
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, asdict
from concurrent.futures import ThreadPoolExecutor, as_completed

from google.cloud import documentai_v1 as documentai
from google.cloud import bigquery
from google.api_core.client_options import ClientOptions
from google.api_core import exceptions as api_exceptions
from google.api_core import retry
from pypdf import PdfReader, PdfWriter

# ============= CONFIGURATION =============
# Environment variables
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

# Processing limits and configuration
PAGE_HARD_CAP = 30          # Document AI hard limit in imageless mode
IMAGELESS_CAP = 15          # Limit for imageless mode
CHUNK_SIZE = 5              # Very small chunks to ensure processing success
SIZE_LIMIT_MB = 40          # File size limit in MB
BATCH_SIZE = 10             # BigQuery batch size
MIN_CONFIDENCE = 0.7        # Minimum confidence threshold
EXCERPT_LENGTH = 20000      # Characters to store in BQ
MAX_RETRIES = 5             # Max retry attempts
INITIAL_BACKOFF = 2         # Initial backoff in seconds

# Add Contract Parser for discovery documents
CONTRACT_PROCESSOR_ID = os.getenv(
    'CONTRACT_PROCESSOR_ID',
    ''  # Will skip if not configured
)

# BigQuery configuration
BQ_DATASET = f"{PROJECT_ID}.stoneman_case"
BQ_TARGET = f"{BQ_DATASET}.documents"
BQ_STAGE = f"{BQ_DATASET}.documents_stage"

# Paths - scan all subdirectories for PDFs
BASE_DIR = Path("data/Stoneman_dispute")  # Root directory to scan
OUTPUT_DIR = Path("data/Stoneman_dispute/processed")
CHUNKS_DIR = Path("data/Stoneman_dispute/chunks")
FULL_TEXT_DIR = Path("data/Stoneman_dispute/full_text")
STATE_DB = Path("data/Stoneman_dispute/processing_state.db")
MANIFESTS_DIR = Path("data/Stoneman_dispute/manifests")

# Logging setup
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('processing.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


@dataclass
class ProcessingState:
    """Track document processing state for resume support."""
    doc_id: str
    filename: str
    status: str  # pending, processing, success, failed
    chunks: List[str] = None
    attempts: int = 0
    last_error: str = ""
    created_at: datetime = None
    updated_at: datetime = None
    
    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.utcnow()
        if self.updated_at is None:
            self.updated_at = datetime.utcnow()
        if self.chunks is None:
            self.chunks = []


class StateManager:
    """Manage processing state for resume support."""
    
    def __init__(self, db_path: Path = STATE_DB):
        """Initialize state database."""
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()
    
    def _init_db(self):
        """Initialize state database."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS processing_state (
                    doc_id TEXT PRIMARY KEY,
                    filename TEXT NOT NULL,
                    status TEXT NOT NULL,
                    chunks TEXT,
                    attempts INTEGER DEFAULT 0,
                    last_error TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            conn.commit()
    
    def get_state(self, doc_id: str) -> Optional[ProcessingState]:
        """Get processing state for a document."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                "SELECT * FROM processing_state WHERE doc_id = ?",
                (doc_id,)
            )
            row = cursor.fetchone()
            if row:
                return ProcessingState(
                    doc_id=row[0],
                    filename=row[1],
                    status=row[2],
                    chunks=json.loads(row[3]) if row[3] else [],
                    attempts=row[4],
                    last_error=row[5] or "",
                    created_at=datetime.fromisoformat(row[6]) if row[6] else None,
                    updated_at=datetime.fromisoformat(row[7]) if row[7] else None
                )
        return None
    
    def update_state(self, state: ProcessingState):
        """Update processing state."""
        state.updated_at = datetime.utcnow()
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT OR REPLACE INTO processing_state 
                (doc_id, filename, status, chunks, attempts, last_error, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                state.doc_id,
                state.filename,
                state.status,
                json.dumps(state.chunks) if state.chunks else None,
                state.attempts,
                state.last_error,
                state.created_at.isoformat() if state.created_at else None,
                state.updated_at.isoformat()
            ))
            conn.commit()
    
    def get_pending_and_failed(self) -> List[ProcessingState]:
        """Get documents that need processing."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                SELECT * FROM processing_state 
                WHERE status IN ('pending', 'failed') 
                AND attempts < ?
                ORDER BY attempts ASC, updated_at ASC
            """, (MAX_RETRIES,))
            
            states = []
            for row in cursor:
                states.append(ProcessingState(
                    doc_id=row[0],
                    filename=row[1],
                    status=row[2],
                    chunks=json.loads(row[3]) if row[3] else [],
                    attempts=row[4],
                    last_error=row[5] or "",
                    created_at=datetime.fromisoformat(row[6]) if row[6] else None,
                    updated_at=datetime.fromisoformat(row[7]) if row[7] else None
                ))
            return states


class PDFSplitter:
    """Handle PDF splitting for large documents."""
    
    @staticmethod
    def get_pdf_info(path: Path) -> Tuple[int, float]:
        """Get PDF page count and file size in MB."""
        size_mb = path.stat().st_size / (1024 * 1024)
        try:
            reader = PdfReader(str(path))
            pages = len(reader.pages)
        except Exception as e:
            logger.error(f"Error reading PDF {path}: {e}")
            pages = 0
        return pages, size_mb
    
    @staticmethod
    def calculate_hash(content: bytes) -> str:
        """Calculate SHA256 hash of content."""
        return hashlib.sha256(content).hexdigest()
    
    @classmethod
    def split_pdf(cls, path: Path, chunk_size: int = CHUNK_SIZE) -> List[Path]:
        """Split PDF into compliant chunks."""
        CHUNKS_DIR.mkdir(parents=True, exist_ok=True)
        
        try:
            reader = PdfReader(str(path))
            total_pages = len(reader.pages)
            
            if total_pages <= chunk_size:
                return [path]  # No need to split
            
            # Calculate original document hash
            with open(path, 'rb') as f:
                original_hash = cls.calculate_hash(f.read())
            
            chunks = []
            for start in range(0, total_pages, chunk_size):
                end = min(start + chunk_size, total_pages)
                
                # Create chunk
                writer = PdfWriter()
                for i in range(start, end):
                    writer.add_page(reader.pages[i])
                
                # Generate chunk ID
                chunk_info = f"{original_hash}_{start+1}-{end}"
                chunk_id = cls.calculate_hash(chunk_info.encode())[:16]
                
                # Save chunk
                chunk_path = CHUNKS_DIR / f"{path.stem}__pp_{start+1}-{end}__{chunk_id}.pdf"
                with open(chunk_path, 'wb') as f:
                    writer.write(f)
                
                chunks.append(chunk_path)
                logger.info(f"Created chunk: {chunk_path.name} (pages {start+1}-{end})")
            
            # Create manifest
            manifest = {
                "original_doc_id": original_hash,
                "original_filename": path.name,
                "total_pages": total_pages,
                "chunks": [
                    {
                        "chunk_id": cls.calculate_hash(open(c, 'rb').read()),
                        "filename": c.name,
                        "page_range": c.stem.split("__pp_")[1].split("__")[0]
                    }
                    for c in chunks
                ]
            }
            
            MANIFESTS_DIR.mkdir(parents=True, exist_ok=True)
            manifest_path = MANIFESTS_DIR / f"{original_hash}_manifest.json"
            with open(manifest_path, 'w') as f:
                json.dump(manifest, f, indent=2)
            
            logger.info(f"Split {path.name} into {len(chunks)} chunks")
            return chunks
            
        except Exception as e:
            logger.error(f"Error splitting PDF {path}: {e}")
            return [path]  # Return original on error
    
    @classmethod
    def route_pdf(cls, path: Path, imageless: bool = False) -> List[Path]:
        """Route PDF based on size/page limits."""
        pages, size_mb = cls.get_pdf_info(path)
        
        # The actual API limit is 15 pages in normal mode, not 30!
        # Split if document exceeds 15 pages (or less with our chunk size)
        actual_limit = 15  # Real API limit in normal mode
        
        if pages > actual_limit or size_mb > SIZE_LIMIT_MB:
            logger.info(f"📂 Splitting {path.name}: {pages} pages, {size_mb:.1f}MB")
            return cls.split_pdf(path, chunk_size=CHUNK_SIZE)
        
        return [path]


class EnhancedDocumentAIProcessor:
    """Enhanced Document AI processor with all production fixes."""
    
    def __init__(self):
        """Initialize processor with fixed IDs."""
        
        # Validate processor IDs
        if not FORM_PROCESSOR_ID or not OCR_PROCESSOR_ID:
            raise RuntimeError(
                "Missing processor IDs. Set FORM_PROCESSOR_ID and OCR_PROCESSOR_ID environment variables."
            )
        
        # Initialize clients
        self.client = documentai.DocumentProcessorServiceClient(
            client_options=ClientOptions(api_endpoint=f"{LOCATION}-documentai.googleapis.com")
        )
        self.bq_client = bigquery.Client()
        
        # Store processor IDs
        self.form_parser = FORM_PROCESSOR_ID
        self.ocr_processor = OCR_PROCESSOR_ID
        
        # State manager
        self.state_manager = StateManager()
        
        # Create directories
        for directory in [OUTPUT_DIR, CHUNKS_DIR, FULL_TEXT_DIR, MANIFESTS_DIR]:
            directory.mkdir(parents=True, exist_ok=True)
        
        # Initialize BigQuery
        self._ensure_bigquery_tables()
        
        # Batch buffer for rolling saves
        self.batch_buffer = []
        
        logger.info("✅ Enhanced Document AI processor initialized")
    
    def _ensure_bigquery_tables(self):
        """Create BigQuery dataset and tables with proper schema."""
        
        # Create dataset
        dataset = bigquery.Dataset(BQ_DATASET)
        dataset.location = "US"
        dataset.description = "Stoneman legal case document analysis"
        
        try:
            self.bq_client.create_dataset(dataset, exists_ok=True)
            logger.info(f"Dataset ready: {BQ_DATASET}")
        except Exception as e:
            logger.error(f"Dataset creation error: {e}")
        
        # Production schema
        schema = [
            bigquery.SchemaField("document_id", "STRING", mode="REQUIRED"),
            bigquery.SchemaField("filename", "STRING", mode="REQUIRED"),
            bigquery.SchemaField("filepath", "STRING"),
            bigquery.SchemaField("document_type", "STRING"),
            bigquery.SchemaField("processor_used", "STRING"),
            bigquery.SchemaField("processing_timestamp", "TIMESTAMP", mode="REQUIRED"),
            bigquery.SchemaField("page_count", "INTEGER"),
            bigquery.SchemaField("confidence", "FLOAT64"),
            bigquery.SchemaField("coverage", "FLOAT64"),  # New: coverage metric
            bigquery.SchemaField("excerpt", "STRING"),
            bigquery.SchemaField("entities", "STRING"),  # JSON as STRING
            bigquery.SchemaField("evidence", "STRING"),  # JSON as STRING
            bigquery.SchemaField("parties", "STRING", mode="REPEATED"),
            bigquery.SchemaField("money_amounts", "FLOAT64", mode="REPEATED"),
            bigquery.SchemaField("full_text_uri", "STRING"),
            bigquery.SchemaField("chunk_info", "STRING"),  # Chunk metadata if split
            bigquery.SchemaField("processing_metrics", "STRING"),  # JSON metrics
        ]
        
        # Create both tables
        for table_id in [BQ_TARGET, BQ_STAGE]:
            table = bigquery.Table(table_id, schema=schema)
            try:
                self.bq_client.create_table(table, exists_ok=True)
                logger.info(f"Table ready: {table_id}")
            except Exception as e:
                logger.error(f"Table creation error for {table_id}: {e}")
    
    def calculate_coverage(self, text: str, page_count: int) -> float:
        """Calculate text coverage metric."""
        if page_count <= 0:
            return 0.0
        return len(text) / page_count
    
    def choose_best_output(self, primary: Dict, fallback: Dict) -> Dict:
        """Choose output based on coverage and quality."""
        pages = primary.get('page_count', 1)
        
        primary_coverage = self.calculate_coverage(
            primary.get('content', ''), pages
        )
        fallback_coverage = self.calculate_coverage(
            fallback.get('content', ''), pages
        )
        
        # Require 5% better coverage to switch
        if fallback_coverage > primary_coverage * 1.05:
            logger.info(f"Using fallback (coverage: {fallback_coverage:.0f} vs {primary_coverage:.0f})")
            fallback['coverage'] = fallback_coverage
            return fallback
        
        primary['coverage'] = primary_coverage
        return primary
    
    @retry.Retry(
        predicate=retry.if_exception_type(api_exceptions.ResourceExhausted),
        initial=INITIAL_BACKOFF,
        maximum=60,
        multiplier=2,
        deadline=300
    )
    def process_document_chunk(self, file_path: Path, is_chunk: bool = False) -> Dict:
        """Process a single document or chunk with comprehensive error handling."""
        
        start_time = time.time()
        
        # Read file
        with open(file_path, 'rb') as f:
            content = f.read()
        
        # Calculate hash
        doc_hash = hashlib.sha256(content).hexdigest()
        
        # Determine processor type
        processor_type = self.determine_processor_type(file_path)
        
        logger.info(f"Processing: {file_path.name} [{processor_type}]")
        
        # Prepare document
        raw_document = documentai.RawDocument(
            content=content,
            mime_type='application/pdf'
        )
        
        # Enhanced process options for legal documents
        # Note: Some fields may not be available in all API versions
        ocr_config_params = {
            'enable_native_pdf_parsing': True,
            'enable_image_quality_scores': True,
            'compute_style_info': True,  # Preserve bold/italic emphasis
        }
        
        # Try to add additional fields if supported
        try:
            # Test if enable_symbol is supported
            test_config = documentai.OcrConfig(enable_symbol=True)
            ocr_config_params['enable_symbol'] = True  # Preserve legal symbols (§, ¶)
        except:
            pass
        
        ocr_config = documentai.OcrConfig(**ocr_config_params)
        
        # Try to add advanced options if available
        try:
            if hasattr(documentai.OcrConfig, 'AdvancedOcrOptions'):
                ocr_config.advanced_ocr_options = documentai.OcrConfig.AdvancedOcrOptions(
                    enable_handwriting=True,  # For signatures/notes
                    enable_selection_marks=True,  # For checkboxes in forms
                    hints=['legal_document']  # Help with legal terminology
                )
            elif hasattr(ocr_config, 'enable_handwriting'):
                # Direct attributes in some API versions
                ocr_config.enable_handwriting = True
                ocr_config.enable_selection_marks = True
                ocr_config.hints = ['legal_document']
        except Exception as e:
            logger.debug(f"Advanced OCR options not available: {e}")
        
        process_options = documentai.ProcessOptions(
            ocr_config=ocr_config
        )
        
        results = {
            'document_id': doc_hash,
            'filename': file_path.name,
            'filepath': str(file_path),
            'processing_timestamp': datetime.utcnow().isoformat() + 'Z',
            'processor_used': processor_type,
            'is_chunk': is_chunk
        }
        
        try:
            # Select processor
            processor_name = self.form_parser if processor_type == 'FORM_PARSER' else self.ocr_processor
            
            # Process with primary processor
            request = documentai.ProcessRequest(
                name=processor_name,
                raw_document=raw_document,
                process_options=process_options
            )
            
            result = self.client.process_document(request=request)
            document = result.document
            
            # Extract primary results
            primary_result = {
                'content': document.text,
                'page_count': len(document.pages) if document.pages else 1,
                'confidence': self._calculate_confidence(document),
                'processor': processor_type
            }
            
            # ALWAYS run dual processing (both FORM_PARSER and OCR)
            ocr_result = None
            try:
                # Use opposite processor for dual processing
                second_processor = self.ocr_processor if processor_type == 'FORM_PARSER' else self.form_parser
                ocr_request = documentai.ProcessRequest(
                    name=second_processor,
                    raw_document=raw_document,
                    process_options=process_options
                )
                ocr_doc = self.client.process_document(request=ocr_request)
                
                ocr_result = {
                    'content': ocr_doc.document.text,
                    'page_count': len(ocr_doc.document.pages) if ocr_doc.document.pages else 1,
                    'confidence': self._calculate_confidence(ocr_doc.document),
                    'processor': 'OCR' if processor_type == 'FORM_PARSER' else 'FORM_PARSER'
                }
            except Exception as e:
                logger.warning(f"Dual processing failed: {e}")
            
            # Triple processing for discovery documents
            contract_result = None
            if CONTRACT_PROCESSOR_ID and self._is_discovery_document(file_path):
                try:
                    contract_request = documentai.ProcessRequest(
                        name=CONTRACT_PROCESSOR_ID,
                        raw_document=raw_document,
                        process_options=process_options
                    )
                    contract_doc = self.client.process_document(request=contract_request)
                    
                    contract_result = {
                        'content': contract_doc.document.text,
                        'page_count': len(contract_doc.document.pages) if contract_doc.document.pages else 1,
                        'confidence': self._calculate_confidence(contract_doc.document),
                        'processor': 'CONTRACT_PARSER'
                    }
                except Exception as e:
                    logger.warning(f"Contract parser processing failed: {e}")
            
            # Choose best output from all available results
            all_results = [primary_result]
            if ocr_result:
                all_results.append(ocr_result)
            if contract_result:
                all_results.append(contract_result)
            
            # Choose best based on confidence AND coverage
            best = self.choose_best_from_multiple(all_results)
            
            # Set processor_used field based on processing
            if len(all_results) == 3:
                results['processor_used'] = 'TRIPLE'  # All three processors
            elif len(all_results) == 2:
                results['processor_used'] = 'DUAL'  # Two processors
            else:
                results['processor_used'] = best['processor']  # Single processor
            
            # Update results with best output
            results.update(best)
            
            # Extract entities and evidence
            results['extracted_entities'] = self._extract_entities(results['content'])
            results['evidence_classification'] = self._classify_evidence(results['content'], file_path)
            
            # Log metrics
            processing_time = time.time() - start_time
            results['processing_metrics'] = {
                'latency_ms': processing_time * 1000,
                'text_length': len(results['content']),
                'coverage': results.get('coverage', 0),
                'success': True
            }
            
            logger.info(
                f"✅ Processed: {len(results['content'])} chars, "
                f"confidence: {results['confidence']:.2f}, "
                f"coverage: {results.get('coverage', 0):.0f} chars/page"
            )
            
        except Exception as e:
            logger.error(f"❌ Processing error: {e}")
            results['content'] = ''
            results['confidence'] = 0.0
            results['coverage'] = 0.0
            results['error'] = str(e)
            results['processing_metrics'] = {
                'latency_ms': (time.time() - start_time) * 1000,
                'success': False,
                'error': str(e)
            }
        
        return results
    
    def _calculate_confidence(self, document) -> float:
        """Calculate document confidence score."""
        confidence_scores = []
        
        if document.pages:
            for page in document.pages:
                if hasattr(page, 'image_quality_scores') and page.image_quality_scores:
                    if hasattr(page.image_quality_scores, 'quality_score'):
                        confidence_scores.append(page.image_quality_scores.quality_score)
        
        return sum(confidence_scores) / len(confidence_scores) if confidence_scores else 0.85
    
    def determine_processor_type(self, file_path: Path) -> str:
        """Determine processor type from filename."""
        filename_lower = file_path.name.lower()
        
        form_patterns = [
            '3 day notice', '3-day', 'unlawful detainer', 'complaint',
            'motion', 'demur', 'judgment', 'summons', 'discovery',
            'interrogator', 'rfa', 'rfp', 'rog', 'request for'
        ]
        
        for pattern in form_patterns:
            if pattern in filename_lower:
                return 'FORM_PARSER'
        
        return 'OCR'
    
    def _is_discovery_document(self, file_path: Path) -> bool:
        """Check if document is a discovery document needing Contract Parser."""
        filename_lower = file_path.name.lower()
        discovery_patterns = ['discovery', 'rfa', 'rog', 'rfp', 'interrogator', 'request for']
        return any(pattern in filename_lower for pattern in discovery_patterns)
    
    def choose_best_from_multiple(self, results: List[Dict]) -> Dict:
        """Choose best result from multiple processors."""
        if not results:
            return {}
        
        # Calculate coverage for each
        for result in results:
            result['coverage'] = self.calculate_coverage(result['content'], result['page_count'])
        
        # Score each result
        best_score = -1
        best_result = results[0]
        
        for result in results:
            # Score = confidence * 0.4 + normalized_coverage * 0.6
            normalized_coverage = min(result['coverage'] / 1000, 1.0)  # Normalize to 0-1
            score = result['confidence'] * 0.4 + normalized_coverage * 0.6
            
            if score > best_score:
                best_score = score
                best_result = result
        
        logger.info(f"Selected {best_result['processor']} with score {best_score:.3f}")
        return best_result
    
    def _extract_entities(self, text: str) -> Dict:
        """Extract legal entities from text with enhanced patterns."""
        if not text:
            return {}
        
        import re
        
        entities = {
            'people': [],
            'organizations': [],
            'dates': [],
            'money_amounts': [],
            'legal_terms': [],
            'case_numbers': [],
            'legal_citations': [],
            'violations': [],
            'addresses': [],
            'statutes': []
        }
        
        # Extract dates with more patterns
        date_patterns = [
            r'\b\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b',
            r'\b(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]* \d{1,2},? \d{4}\b',
            r'\b\d{1,2}\s+(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{4}\b'
        ]
        for pattern in date_patterns:
            entities['dates'].extend(re.findall(pattern, text, re.IGNORECASE))
        
        # Extract money amounts
        money_pattern = r'\$[\d,]+(?:\.\d{2})?'
        money_matches = re.findall(money_pattern, text)
        entities['money_amounts'] = list(set(money_matches))
        
        # Extract case numbers
        case_patterns = [
            r'\b\d{2}[A-Z]{2,4}\d{5,8}\b',  # Standard case format
            r'Case No\.?\s*[:\s]?\s*([A-Z0-9-]+)',  # Case No: format
            r'\b[A-Z]{2,4}-\d{2}-\d{4,8}\b'  # Alternative format
        ]
        for pattern in case_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            if matches and isinstance(matches[0], tuple):
                entities['case_numbers'].extend([m[0] for m in matches])
            else:
                entities['case_numbers'].extend(matches)
        
        # Extract legal citations and statutes
        citation_patterns = [
            r'\b\d+\s+[A-Z]\.?[A-Za-z]+\.?\s+\d+\b',  # e.g., 42 USC 1983
            r'§\s*\d+(?:\.\d+)?',  # Section symbols
            r'\bCal\.\s+Civ\.\s+Code\s+§?\s*\d+',  # California Civil Code
            r'\b[A-Z]{2,}\s+§\s*\d+(?:\.\d+)?'  # State code sections
        ]
        for pattern in citation_patterns:
            entities['legal_citations'].extend(re.findall(pattern, text))
        
        # Enhanced legal terms
        legal_keywords = [
            'plaintiff', 'defendant', 'petitioner', 'respondent',
            'complaint', 'motion', 'demurrer', 'discovery',
            'unlawful detainer', 'eviction', 'retaliation', 'retaliatory',
            'habitability', 'quiet enjoyment', 'breach', 'damages',
            'injunction', 'restraining order', 'settlement',
            'deposition', 'interrogatories', 'request for admission',
            'request for production', 'subpoena', 'summons',
            'judgment', 'verdict', 'order', 'decree'
        ]
        
        text_lower = text.lower()
        for term in legal_keywords:
            if term.lower() in text_lower:
                entities['legal_terms'].append(term)
        
        # Extract violations
        violation_patterns = [
            r'violation of (?:Cal\.?\s+)?(?:Civ\.?\s+)?Code\s+§?\s*\d+',
            r'breach of (?:the )?(?:implied )?warranty of habitability',
            r'retaliatory eviction',
            r'constructive eviction',
            r'breach of covenant of quiet enjoyment',
            r'negligence', r'gross negligence',
            r'intentional infliction of emotional distress',
            r'violation of (?:tenant|renter)\'?s? rights'
        ]
        for pattern in violation_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            entities['violations'].extend(matches)
        
        # Enhanced name extraction
        name_patterns = [
            r'\b(?:Mr\.|Ms\.|Mrs\.|Dr\.)\s+[A-Z][a-z]+(?:\s+[A-Z]\.?)?(?:\s+[A-Z][a-z]+)?',
            r'\b[A-Z][a-z]+\s+[A-Z][a-z]+\s+(?:v\.?|vs\.?)\s+[A-Z][a-z]+(?:\s+[A-Z][a-z]+)?',
            r'(?:Plaintiff|Defendant|Petitioner|Respondent)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)',
        ]
        
        for pattern in name_patterns:
            matches = re.findall(pattern, text)
            if matches and isinstance(matches[0], tuple):
                entities['people'].extend([m[0] for m in matches])
            else:
                entities['people'].extend(matches)
        
        # Extract organizations
        org_patterns = [
            r'\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\s+(?:LLC|Inc|Corp|Corporation|Company|LLP|LP|Partnership)\b',
            r'\b(?:Department of|Board of|Office of|Bureau of)\s+[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*',
            r'\b[A-Z][a-z]+\s+(?:Property|Properties|Management|Realty|Real Estate|Holdings)\b'
        ]
        
        for pattern in org_patterns:
            entities['organizations'].extend(re.findall(pattern, text))
        
        # Extract addresses  
        address_pattern = r'\b\d+\s+[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\s+(?:St|Street|Ave|Avenue|Blvd|Boulevard|Rd|Road|Dr|Drive|Ct|Court|Pl|Place|Way|Lane|Ln)\b'
        entities['addresses'].extend(re.findall(address_pattern, text))
        
        # Remove duplicates and clean up
        for key in entities:
            if isinstance(entities[key], list):
                # Remove duplicates while preserving order
                seen = set()
                unique = []
                for item in entities[key]:
                    if item not in seen:
                        seen.add(item)
                        unique.append(item)
                entities[key] = unique[:10] if key == 'people' else unique  # Limit people to 10
        
        return entities
    
    def _classify_evidence(self, text: str, file_path: Path) -> Dict:
        """Classify document evidence relevance with detailed scoring."""
        if not text:
            return {}
        
        text_lower = text.lower()
        
        # Initialize comprehensive evidence classification
        evidence = {
            'document_class': self._determine_doc_type(file_path.name),
            'habitability_score': 0.0,
            'retaliation_score': 0.0,
            'quiet_enjoyment_score': 0.0,
            'harassment_score': 0.0,
            'violation_indicators': [],
            'evidence_strength': 'unknown',
            'key_phrases': []
        }
        
        # Habitability scoring with weighted keywords
        habitability_keywords = {
            'critical': ['mold', 'toxic', 'black mold', 'health hazard', 'uninhabitable', 'dangerous condition'],
            'high': ['leak', 'water damage', 'flooding', 'sewage', 'infestation', 'rodent', 'pest'],
            'medium': ['repair', 'maintenance', 'broken', 'damaged', 'defective', 'malfunction'],
            'low': ['inspection', 'report', 'complaint', 'request']
        }
        
        hab_score = 0.0
        for level, keywords in habitability_keywords.items():
            for keyword in keywords:
                if keyword in text_lower:
                    if level == 'critical':
                        hab_score = max(hab_score, 0.95)
                        evidence['key_phrases'].append(f"CRITICAL: {keyword}")
                    elif level == 'high':
                        hab_score = max(hab_score, 0.8)
                        evidence['key_phrases'].append(f"HIGH: {keyword}")
                    elif level == 'medium':
                        hab_score = max(hab_score, 0.6)
                    else:
                        hab_score = max(hab_score, 0.4)
        
        evidence['habitability_score'] = hab_score
        
        # Retaliation scoring with temporal analysis
        retaliation_keywords = {
            'critical': ['retaliation', 'retaliatory', 'punitive', 'revenge', 'discriminatory'],
            'high': ['eviction', 'terminate', '3 day notice', '3-day notice', '60 day notice', 'quit', 'vacate'],
            'medium': ['complaint', 'report', 'health department', 'code enforcement', 'housing authority'],
            'temporal': ['after', 'following', 'in response to', 'because', 'result of', 'due to']
        }
        
        ret_score = 0.0
        has_temporal = False
        has_complaint = False
        
        for level, keywords in retaliation_keywords.items():
            for keyword in keywords:
                if keyword in text_lower:
                    if level == 'critical':
                        ret_score = max(ret_score, 0.95)
                        evidence['key_phrases'].append(f"RETALIATION: {keyword}")
                    elif level == 'high':
                        ret_score = max(ret_score, 0.7)
                    elif level == 'medium':
                        ret_score = max(ret_score, 0.5)
                        has_complaint = True
                    elif level == 'temporal':
                        has_temporal = True
        
        # Boost score if temporal relationship found with complaint
        if has_temporal and has_complaint:
            ret_score = max(ret_score, 0.85)
            evidence['key_phrases'].append("TEMPORAL RETALIATION PATTERN")
        
        evidence['retaliation_score'] = ret_score
        
        # Quiet enjoyment and harassment scoring
        quiet_keywords = {
            'high': ['harassment', 'intimidation', 'threat', 'coercion', 'hostile', 'abuse'],
            'medium': ['disturb', 'noise', 'peaceful', 'quiet enjoyment', 'privacy', 'interfere'],
            'low': ['entry', 'access', 'notice to enter', 'inspection']
        }
        
        quiet_score = 0.0
        for level, keywords in quiet_keywords.items():
            for keyword in keywords:
                if keyword in text_lower:
                    if level == 'high':
                        quiet_score = max(quiet_score, 0.9)
                        evidence['key_phrases'].append(f"HARASSMENT: {keyword}")
                    elif level == 'medium':
                        quiet_score = max(quiet_score, 0.6)
                    else:
                        quiet_score = max(quiet_score, 0.4)
        
        evidence['quiet_enjoyment_score'] = quiet_score
        evidence['harassment_score'] = quiet_score  # Same scoring for both
        
        # Determine overall evidence strength
        max_score = max(hab_score, ret_score, quiet_score)
        if max_score >= 0.9:
            evidence['evidence_strength'] = 'smoking_gun'
        elif max_score >= 0.7:
            evidence['evidence_strength'] = 'strong'
        elif max_score >= 0.5:
            evidence['evidence_strength'] = 'supporting'
        else:
            evidence['evidence_strength'] = 'weak'
        
        # Add violation indicators for scores above threshold
        if hab_score >= 0.5:
            evidence['violation_indicators'].append('habitability')
        if ret_score >= 0.5:
            evidence['violation_indicators'].append('retaliation')
        if quiet_score >= 0.5:
            evidence['violation_indicators'].append('quiet_enjoyment')
        
        return evidence
    
    def shape_bq_row(self, result: Dict) -> Dict:
        """Shape result into BigQuery row with proper types."""
        
        # Save full text to file
        full_text_path = FULL_TEXT_DIR / f"{result['document_id']}.txt"
        with open(full_text_path, 'w', encoding='utf-8') as f:
            f.write(result.get('content', ''))
        
        # Extract excerpt
        content = result.get('content', '')
        excerpt = content[:EXCERPT_LENGTH]
        
        # Extract entities
        entities = result.get('extracted_entities', {})
        evidence = result.get('evidence_classification', {})
        
        # Extract parties (people)
        parties = entities.get('people', [])[:10]
        
        # Extract money amounts as floats
        money_amounts = []
        for amount in entities.get('money_amounts', []):
            try:
                clean = float(amount.replace('$', '').replace(',', ''))
                money_amounts.append(clean)
            except:
                pass
        
        # Determine document type
        filename = result.get('filename', '')
        doc_type = self._determine_doc_type(filename)
        
        # Build row
        return {
            'document_id': result['document_id'],
            'filename': filename,
            'filepath': result.get('filepath', ''),
            'document_type': doc_type,
            'processor_used': result.get('processor_used', 'OCR'),
            'processing_timestamp': result.get('processing_timestamp'),
            'page_count': int(result.get('page_count', 0)),
            'confidence': float(result.get('confidence', 0.0)),
            'coverage': float(result.get('coverage', 0.0)),
            'excerpt': excerpt,
            'entities': json.dumps(entities),
            'evidence': json.dumps(evidence),
            'parties': parties,
            'money_amounts': money_amounts,
            'full_text_uri': str(full_text_path),
            'chunk_info': json.dumps(result.get('chunk_info', {})) if result.get('is_chunk') else None,
            'processing_metrics': json.dumps(result.get('processing_metrics', {}))
        }
    
    def _determine_doc_type(self, filename: str) -> str:
        """Determine document type from filename."""
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
        elif 'email' in filename_lower:
            return 'email'
        elif 'text' in filename_lower or 'sms' in filename_lower:
            return 'text_message'
        else:
            return 'other'
    
    def flush_batch_to_bq(self, force=False):
        """Flush batch buffer to BigQuery using stage->merge pattern."""
        
        # Only flush if we have a full batch or forced
        if not force and len(self.batch_buffer) < BATCH_SIZE:
            return
        
        if not self.batch_buffer:
            return
        
        rows = [self.shape_bq_row(r) for r in self.batch_buffer if r.get('content')]
        
        if not rows:
            logger.warning("No valid rows to flush")
            self.batch_buffer.clear()
            return
        
        try:
            # Insert to staging table
            errors = self.bq_client.insert_rows_json(BQ_STAGE, rows)
            if errors:
                logger.error(f"BigQuery stage insert errors: {errors}")
                return
            
            # Merge from staging to target
            merge_query = f"""
            MERGE `{BQ_TARGET}` T
            USING `{BQ_STAGE}` S
            ON T.document_id = S.document_id
            WHEN MATCHED THEN UPDATE SET
                filename = S.filename,
                filepath = S.filepath,
                document_type = S.document_type,
                processor_used = S.processor_used,
                processing_timestamp = S.processing_timestamp,
                page_count = S.page_count,
                confidence = S.confidence,
                coverage = S.coverage,
                excerpt = S.excerpt,
                entities = S.entities,
                evidence = S.evidence,
                parties = S.parties,
                money_amounts = S.money_amounts,
                full_text_uri = S.full_text_uri,
                chunk_info = S.chunk_info,
                processing_metrics = S.processing_metrics
            WHEN NOT MATCHED THEN INSERT ROW
            """
            
            job = self.bq_client.query(merge_query)
            job.result()  # Wait for merge
            
            # Clear staging table
            clear_query = f"DELETE FROM `{BQ_STAGE}` WHERE TRUE"
            self.bq_client.query(clear_query).result()
            
            logger.info(f"✅ Merged {len(rows)} documents to BigQuery")
            
            # Clear buffer after successful save
            self.batch_buffer.clear()
            
        except Exception as e:
            logger.error(f"BigQuery flush error: {e}")
    
    def process_document_with_splitting(self, file_path: Path) -> List[Dict]:
        """Process document with automatic splitting if needed."""
        
        # Check if we need to split
        chunks = PDFSplitter.route_pdf(file_path)
        
        results = []
        for chunk_path in chunks:
            is_chunk = chunk_path != file_path
            
            # Process chunk
            result = self.process_document_chunk(chunk_path, is_chunk=is_chunk)
            
            if is_chunk and result.get('content'):
                # Add chunk info
                result['chunk_info'] = {
                    'original_file': file_path.name,
                    'chunk_file': chunk_path.name,
                    'page_range': chunk_path.stem.split("__pp_")[1].split("__")[0] if "__pp_" in chunk_path.stem else ""
                }
            
            results.append(result)
            
            # Add to batch buffer
            if result.get('content'):
                self.batch_buffer.append(result)
                
                # Flush if batch is full
                if len(self.batch_buffer) >= BATCH_SIZE:
                    self.flush_batch_to_bq()
        
        return results
    
    def process_all_documents(self):
        """Process all documents with resume support and proper batching."""
        
        # Find all PDFs across all subdirectories, excluding processed and chunks
        pdf_files = []
        for root, dirs, files in os.walk(BASE_DIR):
            # Skip processed and chunks directories
            if 'processed' in root or 'chunks' in root:
                continue
            for file in files:
                if file.lower().endswith('.pdf'):
                    pdf_files.append(Path(root) / file)
        
        logger.info(f"📚 Found {len(pdf_files)} PDF documents across all subdirectories")
        
        # Initialize or update state for all documents
        for pdf_path in pdf_files:
            with open(pdf_path, 'rb') as f:
                doc_hash = hashlib.sha256(f.read()).hexdigest()
            
            existing_state = self.state_manager.get_state(doc_hash)
            if not existing_state:
                state = ProcessingState(
                    doc_id=doc_hash,
                    filename=pdf_path.name,
                    status='pending'
                )
                self.state_manager.update_state(state)
        
        # Get documents to process
        to_process = self.state_manager.get_pending_and_failed()
        
        logger.info(f"📋 Processing queue: {len(to_process)} documents")
        
        successful = []
        failed = []
        
        for i, state in enumerate(to_process, 1):
            # Find the actual file
            pdf_path = None
            for p in pdf_files:
                if p.name == state.filename:
                    pdf_path = p
                    break
            
            if not pdf_path:
                logger.error(f"File not found: {state.filename}")
                continue
            
            print(f"\n[{i}/{len(to_process)}] Processing: {pdf_path.name}")
            print(f"  Attempt: {state.attempts + 1}/{MAX_RETRIES}")
            
            # Update state to processing
            state.status = 'processing'
            state.attempts += 1
            self.state_manager.update_state(state)
            
            try:
                # Process with splitting if needed
                results = self.process_document_with_splitting(pdf_path)
                
                if any(r.get('content') for r in results):
                    successful.extend(results)
                    state.status = 'success'
                    state.chunks = [r['filename'] for r in results]
                else:
                    state.status = 'failed'
                    state.last_error = 'No content extracted'
                    failed.append(pdf_path.name)
                
            except Exception as e:
                logger.error(f"Failed to process {pdf_path.name}: {e}")
                state.status = 'failed'
                state.last_error = str(e)
                failed.append(pdf_path.name)
            
            # Update state
            self.state_manager.update_state(state)
            
            # Rate limiting with exponential backoff on errors
            if state.status == 'failed':
                backoff = min(INITIAL_BACKOFF * (2 ** (state.attempts - 1)), 60)
                logger.info(f"Backing off for {backoff} seconds...")
                time.sleep(backoff)
            else:
                time.sleep(0.5)  # Normal rate limiting
        
        # Final batch flush with force flag
        if self.batch_buffer:
            logger.info(f"💾 Flushing final batch of {len(self.batch_buffer)} documents...")
            self.flush_batch_to_bq(force=True)  # Force flush remaining items
        
        # Generate summary
        self._generate_summary(successful, failed, pdf_files)
    
    def _generate_summary(self, successful: List[Dict], failed: List[str], all_files: List[Path]):
        """Generate processing summary with detailed metrics."""
        
        print("\n" + "=" * 60)
        print("📊 PROCESSING SUMMARY")
        print(f"Total files: {len(all_files)}")
        print(f"Successfully processed: {len(successful)}")
        print(f"Failed: {len(failed)}")
        
        if successful:
            avg_confidence = sum(r['confidence'] for r in successful) / len(successful)
            avg_coverage = sum(r.get('coverage', 0) for r in successful) / len(successful)
            total_chunks = sum(1 for r in successful if r.get('is_chunk'))
            
            print(f"\n📈 Metrics:")
            print(f"  Average confidence: {avg_confidence:.2%}")
            print(f"  Average coverage: {avg_coverage:.0f} chars/page")
            print(f"  Documents split into chunks: {total_chunks}")
        
        if failed:
            print(f"\n❌ Failed documents:")
            for name in failed[:10]:
                print(f"  - {name}")
        
        # Save detailed log
        log_path = OUTPUT_DIR / f"processing_summary_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(log_path, 'w') as f:
            json.dump({
                'timestamp': datetime.utcnow().isoformat(),
                'configuration': {
                    'project_id': PROJECT_ID,
                    'processors': {
                        'form': FORM_PROCESSOR_ID,
                        'ocr': OCR_PROCESSOR_ID
                    },
                    'limits': {
                        'page_cap': PAGE_HARD_CAP,
                        'chunk_size': CHUNK_SIZE,
                        'size_limit_mb': SIZE_LIMIT_MB
                    }
                },
                'summary': {
                    'total_files': len(all_files),
                    'successful': len(successful),
                    'failed': len(failed),
                    'chunks_created': sum(1 for r in successful if r.get('is_chunk')),
                    'avg_confidence': sum(r['confidence'] for r in successful) / len(successful) if successful else 0,
                    'avg_coverage': sum(r.get('coverage', 0) for r in successful) / len(successful) if successful else 0
                },
                'failed_files': failed
            }, f, indent=2, default=str)
        
        print(f"\n✅ Processing complete!")
        print(f"📂 Results: {OUTPUT_DIR}")
        print(f"📄 Full text: {FULL_TEXT_DIR}")
        print(f"📦 Chunks: {CHUNKS_DIR}")
        print(f"📊 BigQuery: {BQ_TARGET}")
        print(f"📝 Summary: {log_path}")
        print(f"💾 State DB: {STATE_DB}")


def main():
    """Main entry point."""
    print("🚀 ENHANCED DOCUMENT AI PROCESSOR")
    print("=" * 60)
    print(f"Configuration:")
    print(f"  Project: {PROJECT_ID}")
    print(f"  Location: {LOCATION}")
    print(f"  Source: {BASE_DIR}")
    print(f"  Page limit: {PAGE_HARD_CAP}")
    print(f"  Chunk size: {CHUNK_SIZE}")
    print(f"  Size limit: {SIZE_LIMIT_MB}MB")
    print(f"  Batch size: {BATCH_SIZE}")
    print()
    
    try:
        processor = EnhancedDocumentAIProcessor()
        processor.process_all_documents()
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        raise


if __name__ == "__main__":
    main()