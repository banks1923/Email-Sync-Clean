# Standalone Legal Document Boilerplate Removal Tool

A complete, self-contained tool for processing legal documents with OCR and intelligent boilerplate removal. This tool extracts text from PDF legal documents and automatically removes repetitive boilerplate language while preserving important legal content.

## What It Does

The tool is specifically designed for legal discovery documents (like those you showed me) and can automatically detect and remove:

- **Standard legal objections** ("burdensome, oppressive, and harassing...")
- **Discovery response boilerplate** ("After diligent search and reasonable inquiry...")
- **Case citations** (Sav-On Drugs references, CCP sections, etc.)
- **Procedural language** (repeated reservation clauses)
- **Cross-document repetitive content** using similarity analysis

## Quick Start

### 1. Install Dependencies

```bash
# Install Python packages
pip install -r standalone_requirements.txt

# Install system dependencies
# Ubuntu/Debian:
sudo apt-get install tesseract-ocr tesseract-ocr-eng poppler-utils

# macOS:
brew install tesseract poppler

# Optional: Install spaCy model for better text processing
python -m spacy download en_core_web_sm
```

### 2. Test the System

```bash
# Test with sample legal text
python standalone_boilerplate_remover.py --test

# Check if all dependencies are working
python standalone_boilerplate_remover.py --check-deps
```

### 3. Process Your Documents

```bash
# Process single document
python standalone_boilerplate_remover.py your_legal_document.pdf

# Process with output directory
python standalone_boilerplate_remover.py document.pdf --output ./cleaned/

# Process multiple documents (with cross-document analysis)
python standalone_boilerplate_remover.py doc1.pdf doc2.pdf doc3.pdf --output ./batch/

# Adjust settings
python standalone_boilerplate_remover.py document.pdf --confidence 0.8 --mode summary
```

## Output Files

For each processed document, the tool creates:

- `{filename}_cleaned.txt` - Document with boilerplate removed
- `{filename}_original_ocr.txt` - Raw OCR output
- `{filename}_report.json` - Processing statistics and detected patterns
- `batch_processing_report.json` - Summary for multiple documents

## Configuration Options

- `--confidence 0.7` - Confidence threshold (0.0-1.0) for removing boilerplate
- `--similarity 0.85` - Similarity threshold for cross-document detection
- `--mode placeholder` - Replacement mode:
  - `placeholder`: Replace with `[STANDARD OBJECTIONS REMOVED]` tags
  - `summary`: Replace with brief summaries
  - `remove`: Complete removal
- `--dpi 300` - OCR resolution (higher = better quality, slower processing)

## Example Results

**Before (Original):**
```
Responding Party objects to this request on the grounds that it is burdensome, 
oppressive, and harassing in its entirety. Responding Party objects that this 
request calls for documents already in the Propounding Party's possession. 
Responding Party does not have an obligation to obtain information that is 
equally available to the Propounding Party. (CCP § 2030.220(c).) Responding 
Party is not required to prepare the Plaintiff's case. (Sav-On Drugs, Inc. v. 
Superior Court of Los Angeles County (1975) 15 Cal. 3d 1, 5.).

Subject to these objections but without waiving, Responding Party responds as follows:
After diligent search and reasonable inquiry, Responding Party identifies and 
produces the following documents: DEF 000001-DEF 000046.
```

**After (Cleaned):**
```
[STANDARD OBJECTIONS REMOVED]

[STANDARD DISCOVERY RESPONSE REMOVED]
DEF 000001-DEF 000046.
```

## Technical Details

### OCR Processing
- Uses Tesseract 4.0+ with legal document optimization
- Configurable DPI for quality vs. speed trade-offs
- Page-by-page processing with error recovery
- Character whitelist optimized for legal text

### Boilerplate Detection
- **Pattern-based**: Regex patterns for common legal boilerplate
- **Similarity-based**: TF-IDF analysis to find repetitive content across documents
- **Cross-document**: Analyzes multiple documents together for better detection
- **Preservation rules**: Never removes case numbers, party names, dates, or monetary amounts

### Safety Features
- Content preservation rules protect important information
- Confidence thresholds prevent over-aggressive removal
- Multiple replacement modes for different use cases
- Comprehensive logging and reporting

## Dependencies

### Required
- Python 3.8+
- pytesseract, pdf2image, Pillow (OCR)
- Tesseract OCR system binary
- poppler-utils (PDF processing)

### Optional but Recommended
- scikit-learn, numpy (similarity detection)
- spaCy + English model (better text processing)

## Troubleshooting

### Common Issues

1. **"Tesseract not found"**
   - Ensure Tesseract is installed and in PATH
   - On Windows, you may need to set the path explicitly

2. **"pdf2image conversion failed"**
   - Install poppler-utils
   - Check PDF file permissions

3. **"Poor OCR accuracy"**
   - Increase DPI (`--dpi 600`)
   - Ensure PDF quality is good
   - Check if document is already searchable (might not need OCR)

4. **"Too aggressive boilerplate removal"**
   - Lower confidence threshold (`--confidence 0.5`)
   - Use `--mode placeholder` instead of `remove`

### Performance Tips

- Use `--dpi 300` for good balance of quality and speed
- Process multiple related documents together for better boilerplate detection
- Use SSD storage for faster image processing

## Integration

This standalone tool uses the same boilerplate removal components as your main project but doesn't depend on the existing infrastructure. You can later integrate the cleaned results back into your legal intelligence system.

The tool creates JSON reports that include:
- Processing statistics
- Detected boilerplate patterns
- Removed segment details
- Configuration used

## License

Uses the same license as your main project.
