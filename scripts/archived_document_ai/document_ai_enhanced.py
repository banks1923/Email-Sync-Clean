#!/usr/bin/env python3
"""Enhanced Document AI processor with quality control and multiple output
formats.

This script handles:
- Poor quality documents with retry and enhancement
- Multiple output formats (text, JSON, markdown, structured)
- Quality scoring and confidence levels
- Consolidated reports by category
- Legal document specific processing
"""

import os
import json
import sys
from pathlib import Path
from datetime import datetime
from dataclasses import dataclass, asdict
from google.cloud import documentai_v1 as documentai

os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = '/Users/jim/Secrets/modular-command-466820-p2-bc0974cd5852.json'

PROJECT_ID = "modular-command-466820-p2"
LOCATION = "us"

@dataclass
class DocumentResult:
    """
    Structured output for processed documents.
    """
    file_path: str
    file_name: str
    category: str
    process_date: str
    confidence_score: float
    page_count: int
    text: str
    entities: dict[str, list[str]]
    form_fields: dict[str, str]
    warnings: list[str]
    processing_notes: str

class EnhancedDocumentProcessor:
    """
    Enhanced document processor with quality control.
    """
    
    def __init__(self):
        self.client = documentai.DocumentProcessorServiceClient()
        self.processors = {}
        self.results = []
        
    def get_or_create_processor(self, processor_type: str) -> str:
        """
        Get existing processor or create new one.
        """
        if processor_type in self.processors:
            return self.processors[processor_type]
            
        parent = f"projects/{PROJECT_ID}/locations/{LOCATION}"
        
        # Check existing processors
        for processor in self.client.list_processors(parent=parent):
            if processor_type in processor.type_:
                self.processors[processor_type] = processor.name
                return processor.name
        
        # Create new processor
        processor = self.client.create_processor(
            parent=parent,
            processor=documentai.Processor(
                display_name=f"Legal_{processor_type}",
                type_=processor_type
            )
        )
        self.processors[processor_type] = processor.name
        return processor.name
    
    def categorize_document(self, file_path: str) -> str:
        """
        Categorize document based on path and filename.
        """
        path_lower = str(file_path).lower()
        
        # Legal document categories
        categories = {
            'notice': ['notice', '60 day', '3 day', 'quit'],
            'complaint': ['complaint', 'summons', 'motion'],
            'lease': ['lease', 'rental', 'agreement'],
            'report': ['report', 'inspection', 'lab results'],
            'correspondence': ['email', 're:', 'letter'],
            'evidence': ['photo', 'image', 'screenshot'],
            'legal_filing': ['unlawful detainer', 'ud', 'judgment'],
            'disclosure': ['disclosure', 'ab1482', 'addendum']
        }
        
        for category, keywords in categories.items():
            if any(kw in path_lower for kw in keywords):
                return category
                
        return 'uncategorized'
    
    def assess_quality(self, document) -> tuple[float, list[str]]:
        """
        Assess document quality and return confidence score with warnings.
        """
        warnings = []
        confidence = 1.0
        
        if not document.text:
            warnings.append("No text extracted")
            return 0.0, warnings
        
        text_len = len(document.text.strip())
        
        # Check for quality issues
        if text_len < 100:
            warnings.append(f"Very little text extracted ({text_len} chars)")
            confidence *= 0.5
            
        # Check for OCR artifacts
        garbage_chars = sum(1 for c in document.text if c in '□■▪▫◆◇○●')
        if garbage_chars > len(document.text) * 0.1:
            warnings.append(f"High garbage character ratio ({garbage_chars} chars)")
            confidence *= 0.7
            
        # Check for broken text patterns
        if '�' in document.text:
            warnings.append("Contains encoding errors")
            confidence *= 0.8
            
        # Check readability (words vs noise)
        words = document.text.split()
        avg_word_len = sum(len(w) for w in words) / len(words) if words else 0
        if avg_word_len > 15 or avg_word_len < 2:
            warnings.append(f"Unusual word length average: {avg_word_len:.1f}")
            confidence *= 0.8
            
        return confidence, warnings
    
    def process_with_retry(self, file_path: str, max_attempts: int = 2) -> DocumentResult | None:
        """
        Process document with retry logic for poor quality.
        """
        file_path = Path(file_path)
        category = self.categorize_document(file_path)
        
        # Try different processors based on document type
        processor_sequence = []
        if category in ['form', 'lease', 'disclosure']:
            processor_sequence = ["FORM_PARSER_PROCESSOR", "OCR_PROCESSOR"]
        else:
            processor_sequence = ["OCR_PROCESSOR", "FORM_PARSER_PROCESSOR"]
        
        best_result = None
        best_confidence = 0.0
        
        for processor_type in processor_sequence[:max_attempts]:
            try:
                print(f"  Trying {processor_type}...")
                
                # Read file
                with open(file_path, 'rb') as f:
                    content = f.read()
                
                # Determine MIME type
                mime_type = 'application/pdf'
                if file_path.suffix.lower() in ['.png', '.jpg', '.jpeg']:
                    mime_type = 'image/' + file_path.suffix[1:].lower()
                
                # Process document
                processor_name = self.get_or_create_processor(processor_type)
                request = documentai.ProcessRequest(
                    name=processor_name,
                    raw_document=documentai.RawDocument(
                        content=content,
                        mime_type=mime_type
                    )
                )
                
                result = self.client.process_document(request=request)
                document = result.document
                
                # Assess quality
                confidence, warnings = self.assess_quality(document)
                
                # Extract entities
                entities = {}
                if document.entities:
                    for entity in document.entities:
                        entity_type = entity.type_ or 'unknown'
                        if entity_type not in entities:
                            entities[entity_type] = []
                        entities[entity_type].append(entity.mention_text)
                
                # Extract form fields
                form_fields = {}
                if processor_type == "FORM_PARSER_PROCESSOR" and document.pages:
                    for page in document.pages:
                        for field in page.form_fields:
                            field_name = self._get_text(field.field_name, document)
                            field_value = self._get_text(field.field_value, document)
                            if field_name and field_value:
                                form_fields[field_name] = field_value
                
                # Create result
                doc_result = DocumentResult(
                    file_path=str(file_path),
                    file_name=file_path.name,
                    category=category,
                    process_date=datetime.now().isoformat(),
                    confidence_score=confidence,
                    page_count=len(document.pages) if document.pages else 1,
                    text=document.text or "",
                    entities=entities,
                    form_fields=form_fields,
                    warnings=warnings,
                    processing_notes=f"Processed with {processor_type}"
                )
                
                # Keep best result
                if confidence > best_confidence:
                    best_result = doc_result
                    best_confidence = confidence
                    
                # If confidence is good enough, stop trying
                if confidence > 0.8:
                    break
                    
            except Exception as e:
                print(f"    Error with {processor_type}: {e}")
                continue
        
        if best_result:
            self.results.append(best_result)
            
        return best_result
    
    def _get_text(self, element, document) -> str:
        """
        Extract text from document element.
        """
        if not element.text_anchor:
            return ""
        text = ""
        for segment in element.text_anchor.text_segments:
            start = segment.start_index if segment.start_index else 0
            end = segment.end_index
            text += document.text[start:end]
        return text.strip()
    
    def save_results(self, output_dir: Path, format: str = "all"):
        """
        Save results in various formats.
        """
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Group by category
        by_category = {}
        for result in self.results:
            if result.category not in by_category:
                by_category[result.category] = []
            by_category[result.category].append(result)
        
        # Save individual text files
        if format in ["text", "all"]:
            text_dir = output_dir / "text_files"
            text_dir.mkdir(exist_ok=True)
            for result in self.results:
                output_file = text_dir / f"{Path(result.file_name).stem}.txt"
                with open(output_file, 'w', encoding='utf-8') as f:
                    f.write(f"File: {result.file_name}\n")
                    f.write(f"Category: {result.category}\n")
                    f.write(f"Confidence: {result.confidence_score:.2f}\n")
                    if result.warnings:
                        f.write(f"Warnings: {', '.join(result.warnings)}\n")
                    f.write("-" * 50 + "\n")
                    f.write(result.text)
        
        # Save JSON structured data
        if format in ["json", "all"]:
            json_file = output_dir / "document_analysis.json"
            with open(json_file, 'w', encoding='utf-8') as f:
                json.dump([asdict(r) for r in self.results], f, indent=2)
        
        # Save markdown report
        if format in ["markdown", "all"]:
            md_file = output_dir / "document_report.md"
            with open(md_file, 'w', encoding='utf-8') as f:
                f.write("# Document Processing Report\n\n")
                f.write(f"**Processed**: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n")
                f.write(f"**Total Documents**: {len(self.results)}\n\n")
                
                # Summary by category
                f.write("## Summary by Category\n\n")
                for category, docs in by_category.items():
                    f.write(f"### {category.replace('_', ' ').title()} ({len(docs)} documents)\n\n")
                    for doc in docs:
                        f.write(f"- **{doc.file_name}** (Confidence: {doc.confidence_score:.2f})\n")
                        if doc.warnings:
                            f.write(f"  - ⚠️ {', '.join(doc.warnings)}\n")
                        if doc.entities:
                            f.write(f"  - Entities: {', '.join(doc.entities.keys())}\n")
                    f.write("\n")
                
                # Low confidence documents
                low_conf = [r for r in self.results if r.confidence_score < 0.7]
                if low_conf:
                    f.write("## ⚠️ Low Confidence Documents\n\n")
                    for doc in low_conf:
                        f.write(f"- {doc.file_name}: {', '.join(doc.warnings)}\n")
        
        # Save consolidated text by category
        if format in ["consolidated", "all"]:
            consolidated_dir = output_dir / "consolidated"
            consolidated_dir.mkdir(exist_ok=True)
            
            for category, docs in by_category.items():
                category_file = consolidated_dir / f"{category}.txt"
                with open(category_file, 'w', encoding='utf-8') as f:
                    f.write(f"# {category.replace('_', ' ').upper()} DOCUMENTS\n")
                    f.write(f"# Total: {len(docs)} documents\n")
                    f.write("=" * 70 + "\n\n")
                    
                    for doc in docs:
                        f.write(f"\n{'='*70}\n")
                        f.write(f"DOCUMENT: {doc.file_name}\n")
                        f.write(f"Processed: {doc.process_date}\n")
                        f.write(f"Confidence: {doc.confidence_score:.2f}\n")
                        f.write("=" * 70 + "\n\n")
                        f.write(doc.text)
                        f.write("\n\n")
        
        print(f"\n✅ Results saved to {output_dir}")
        print(f"   - Text files: {output_dir}/text_files/")
        print(f"   - JSON data: {output_dir}/document_analysis.json")
        print(f"   - Markdown report: {output_dir}/document_report.md")
        print(f"   - Consolidated by category: {output_dir}/consolidated/")

def main():
    """
    Process documents with enhanced options.
    """
    if len(sys.argv) < 2:
        print("Usage: python3 scripts/document_ai_enhanced.py <directory> [output_dir] [format]")
        print("Formats: text, json, markdown, consolidated, all (default: all)")
        return
    
    input_dir = Path(sys.argv[1])
    output_dir = Path(sys.argv[2]) if len(sys.argv) > 2 else Path("./extracted_documents")
    output_format = sys.argv[3] if len(sys.argv) > 3 else "all"
    
    if not input_dir.exists():
        print(f"❌ Directory not found: {input_dir}")
        return
    
    # Find all PDFs and images
    files = list(input_dir.rglob("*.pdf"))
    files.extend(input_dir.rglob("*.png"))
    files.extend(input_dir.rglob("*.jpg"))
    
    if not files:
        print(f"❌ No documents found in {input_dir}")
        return
    
    print(f"📚 Found {len(files)} documents to process")
    print("=" * 60)
    
    processor = EnhancedDocumentProcessor()
    
    # Process each file
    for i, file_path in enumerate(files, 1):
        print(f"\n[{i}/{len(files)}] Processing: {file_path.name}")
        result = processor.process_with_retry(file_path)
        
        if result:
            status = "✅" if result.confidence_score > 0.7 else "⚠️"
            print(f"  {status} Confidence: {result.confidence_score:.2f}")
            if result.warnings:
                print(f"  ⚠️ {', '.join(result.warnings)}")
    
    # Save results
    processor.save_results(output_dir, output_format)
    
    # Print summary
    print("\n" + "=" * 60)
    print("📊 Processing Summary:")
    high_conf = sum(1 for r in processor.results if r.confidence_score > 0.7)
    low_conf = len(processor.results) - high_conf
    print(f"  ✅ High confidence: {high_conf}")
    print(f"  ⚠️ Low confidence: {low_conf}")
    print(f"  📁 Total processed: {len(processor.results)}")

if __name__ == "__main__":
    main()