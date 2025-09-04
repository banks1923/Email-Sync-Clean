# Entity Extraction Integration Documentation

## Overview

The unified entity extraction system processes all content types (emails, PDFs, documents) through a single pipeline with quality filtering and proper source attribution.

## Architecture

### Components

- **UnifiedEntityProcessor** (`shared/unified_entity_processor.py`) - Core extraction pipeline
- **EntityHandler** (`tools/scripts/cli/entity_handler.py`) - CLI interface
- **Quality Filters** - OCR garbage detection and removal
- **Database Integration** - Full entity-to-content attribution

### Data Flow

```
Content Unified Table → Entity Extractor → Quality Filter → Entity Content Mapping → Consolidated Entities
```

## Database Schema

### Entity Content Mapping Table
```sql
entity_content_mapping (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    content_id TEXT NOT NULL,           -- Links to content_unified.id
    entity_text TEXT NOT NULL,          -- The actual entity text (was entity_value)
    entity_type TEXT NOT NULL,          -- Entity type (PERSON, ORG, etc.)
    entity_label TEXT NOT NULL,         -- Entity label from NER
    start_char INTEGER NOT NULL,        -- Start position in text
    end_char INTEGER NOT NULL,          -- End position in text
    confidence REAL,                    -- Confidence score
    normalized_form TEXT,               -- Normalized version of entity
    processed_time TEXT DEFAULT CURRENT_TIMESTAMP,
    entity_id TEXT,                     -- Unique entity identifier
    aliases TEXT,                       -- Entity aliases
    frequency INTEGER DEFAULT 1,        -- Occurrence frequency
    last_seen DATETIME DEFAULT CURRENT_TIMESTAMP,
    extractor_type TEXT DEFAULT 'spacy', -- Extraction method
    role_type TEXT                      -- Role/relationship type
)
```

### Supported Entity Types

- **PERSON** - Names and individuals
- **ORG** - Organizations and companies
- **DATE** - Specific dates and date ranges
- **TIME** - Times and temporal expressions
- **MONEY** - Currency amounts and financial terms
- **STATUTE** - Legal references and statutes
- **COURT** - Court-related entities
- **CARDINAL** - Numbers (filtered for quality)
- **GPE** - Geopolitical entities (locations)
- **LEGAL_CONCEPT** - Legal terms and concepts

## Usage

### CLI Commands

```bash
# Extract entities from unified content (missing only)
tools/scripts/vsearch extract-entities --missing-only --limit 100

# Check entity processing status
tools/scripts/vsearch entity-status

# Search content by entity (searches entity_text column)
tools/scripts/vsearch search-entities --entity-type PERSON --entity-value "Smith"
```

### Python API

```python
from shared.unified_entity_processor import UnifiedEntityProcessor

processor = UnifiedEntityProcessor()

# Process entities from all content
result = processor.process_content_entities(max_content=100)

# Process only missing entities
result = processor.process_missing_entities_only(max_content=50)

# Get processing status
status = processor.get_processing_status()
```

## Quality Controls

### Content Filtering

The system automatically excludes low-quality content:

- **OCR Garbage Detection**: Skip content with >3% symbol density
- **Minimum Length**: Require at least 20 characters
- **Symbol Pattern Detection**: Filter out corrupted PDF content

### Entity Filtering

Extracted entities are filtered for quality:

```python
# Filters applied:
- Length < 2 characters (too short)
- Single digit numbers (OCR noise)
- >30% symbol content (OCR garbage)  
- >100 characters (OCR errors)
- >50% punctuation (malformed)
```

### Examples of Filtered Content

**Excluded (OCR Garbage):**
- "Bp CO ag BS ZR"
- "= & EERE BESS" 
- "Ssesee 753 256 o2s5se"
- Single digits: "1", "2", "3"

**Included (High Quality):**
- "N. Stoneman Ave"
- "Stoneman Staff"
- "March 17th, March 18th and March 19th, 2025"
- "518 N. Stoneman Ave., Alhambra CA 91801"

## Search Capabilities

### Entity-Based Search

Find all content containing specific entities:

```sql
SELECT DISTINCT cu.title, cu.source_type
FROM content_unified cu
JOIN entity_content_mapping ecm ON cu.id = ecm.content_id
WHERE ecm.entity_text LIKE '%Stoneman%'
```

### Cross-Document Analysis

Identify entities appearing across multiple documents:

```sql
SELECT 
    e1.entity_text,
    COUNT(DISTINCT e1.content_id) as document_count,
    GROUP_CONCAT(DISTINCT cu.title) as documents
FROM entity_content_mapping e1
JOIN content_unified cu ON e1.content_id = cu.id
GROUP BY e1.entity_text
HAVING document_count > 1
ORDER BY document_count DESC
```

## Performance Metrics

### Current Statistics
- **Processing Rate**: ~275 entities/second
- **Quality Score**: 95.3% (after filtering)
- **Entity Coverage**: Cross-document attribution for legal case entities
- **Content Types**: Emails, PDFs, documents, uploads

### Processing Results
```
Total entities: 719 (after quality filtering)
Quality entities (>2 chars): 685 (95.3%)
Garbage removed: 99 entities (12.1% improvement)
```

## Integration Points

### MCP Server Integration

Entity extraction is available through MCP servers:

```javascript
// Legal Intelligence MCP
legal_extract_entities({
    content: "Legal document text...",
    case_id: "optional-case-id"
})
```

### Search Intelligence Integration

Entities enhance search capabilities:

```python
from search_intelligence import get_search_intelligence_service

search = get_search_intelligence_service()

# Entity-enhanced search
results = search.search_with_entities("contract dispute", entity_types=["PERSON", "ORG"])
```

### Knowledge Graph Integration

Entities can be used for relationship analysis through the entity service:

```python
from entity.main import EntityService

entity_service = EntityService()

# Get entity relationships
relationships = entity_service.get_entity_relationships(content_id)
```

## Troubleshooting

### Common Issues

**1. No Entities Extracted**
- Check content quality (may be filtered for OCR garbage)
- Verify entity service initialization
- Ensure content length >20 characters

**2. Low Quality Entities**
- Review source documents for OCR corruption
- Check symbol density in source content
- Verify quality filters are active

**3. Missing Entity Mappings**
- Run entity extraction: `extract-entities --missing-only`
- Check database connections
- Verify content_unified table has data

### Diagnostic Commands

```bash
# Check entity processing status
python3 tools/scripts/cli/entity_handler.py entity-status

# Analyze entity quality
python3 scripts/clean_entity_extraction.py

# Show entity proof and connections
python3 scripts/show_entity_proof.py
```

## Configuration

### Quality Thresholds

Adjustable in `shared/unified_entity_processor.py`:

```python
# Content quality filter (symbol density)
SYMBOL_THRESHOLD = 3.0  # Skip content with >3% symbols

# Entity quality filters
MIN_ENTITY_LENGTH = 2
MAX_ENTITY_LENGTH = 100
MAX_SYMBOL_RATIO = 0.3
MAX_PUNCT_RATIO = 0.5
```

### Processing Limits

```python
# Batch processing settings
DEFAULT_BATCH_SIZE = 50
DEFAULT_MAX_CONTENT = None  # No limit
```

## Future Enhancements

### Planned Features
1. **Entity Disambiguation** - Resolve entity variants (e.g., "N. Stoneman Ave" vs "Stoneman Ave")
2. **Confidence Scoring** - Machine learning-based quality assessment
3. **Entity Relationships** - Extract relationships between entities
4. **Custom Entity Types** - Domain-specific entity categories
5. **Real-time Processing** - Process entities as content is added

### Performance Optimizations
1. **Caching** - Cache entity extraction results
2. **Parallel Processing** - Multi-threaded entity extraction
3. **Incremental Updates** - Process only changed content
4. **Smart Filtering** - ML-based OCR garbage detection

---

*Last Updated: 2025-08-22*
*Quality Score: 95.3% entities*
*Processing Coverage: All unified content types*