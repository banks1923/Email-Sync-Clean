# Task #8 ULTRATHINK Design: Enhanced Entity Extraction System

## Deep Analysis: Legal Entity Extraction & Knowledge Graphs

### Core Requirements Analysis

**Primary Goal**: Transform basic spaCy extractor into comprehensive legal entity extraction system with relationship mapping and knowledge graph capabilities.

**Key Enhancements Needed**:
1. Legal domain entity patterns (case numbers, legal concepts, roles)
2. Entity relationship mapping for knowledge graphs
3. Advanced deduplication with fuzzy matching
4. Search service integration
5. Content cross-referencing

---

## Architecture Design

### 1. Enhanced Entity Extraction Pipeline

#### Legal Entity Types (New)
```python
LEGAL_ENTITIES = {
    "CASE_NUMBER": r"(?i)\b(?:case|matter|docket)\s*(?:no\.?|number)?\s*[:\-]?\s*([A-Z0-9\-\/]+)",
    "COURT": r"(?i)\b(?:court|tribunal|commission)\s+(?:of\s+)?([A-Z][A-Za-z\s]+)",
    "LEGAL_ROLE": ["attorney", "lawyer", "counsel", "judge", "client", "plaintiff", "defendant"],
    "LEGAL_CONCEPT": ["contract", "agreement", "settlement", "verdict", "ruling", "motion"],
    "STATUTE": r"(?i)\b(?:usc|cfr|\d+\s+u\.?s\.?c\.?|\d+\s+cfr)\s+§?\s*(\d+(?:\([a-z0-9]+\))*)",
}
```

#### Enhanced Extractor Architecture
```
entity/
├── extractors/
│   ├── base_extractor.py          # Existing
│   ├── spacy_extractor.py         # Enhanced with legal patterns
│   ├── legal_extractor.py         # NEW: Legal-specific extraction
│   ├── relationship_extractor.py  # NEW: Extract entity relationships
│   └── extractor_factory.py      # Enhanced factory
├── processors/
│   ├── entity_normalizer.py      # NEW: Advanced deduplication
│   ├── relationship_mapper.py    # NEW: Build knowledge graphs
│   └── knowledge_graph.py        # NEW: Graph operations
├── storage/
│   ├── entity_storage.py         # Enhanced schema
│   └── relationship_storage.py   # NEW: Relationship tables
└── search/
    └── entity_search.py          # NEW: Entity-based search
```

### 2. Database Schema Enhancement

#### Entity Relationships Table
```sql
CREATE TABLE entity_relationships (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source_entity_id INTEGER,
    target_entity_id INTEGER,
    relationship_type TEXT,  -- "knows", "works_for", "represents", "mentioned_with"
    confidence REAL,
    source_message_id TEXT,
    extraction_date DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (source_entity_id) REFERENCES entities(id),
    FOREIGN KEY (target_entity_id) REFERENCES entities(id)
);
```

#### Enhanced Entities Table
```sql
ALTER TABLE email_entities ADD COLUMN entity_id TEXT;  -- Unique entity identifier
ALTER TABLE email_entities ADD COLUMN aliases TEXT;    -- JSON array of known aliases
ALTER TABLE email_entities ADD COLUMN frequency INTEGER DEFAULT 1;
ALTER TABLE email_entities ADD COLUMN last_seen DATETIME;
```

### 3. Legal Pattern Enhancement

#### Legal Entity Patterns
- **Case Numbers**: Pattern matching for legal case formats
- **Court Names**: Recognition of court hierarchies and jurisdictions
- **Legal Roles**: Context-aware role identification
- **Statutes/Citations**: Legal citation parsing
- **Contract Terms**: Legal concept extraction

#### Implementation Strategy
```python
class LegalExtractor(BaseExtractor):
    def __init__(self):
        self.legal_patterns = self._load_legal_patterns()
        self.role_context_analyzer = RoleContextAnalyzer()

    def extract_legal_entities(self, text, context):
        # Use regex + spaCy + contextual analysis
        # Return legal-specific entities with high confidence
```

### 4. Relationship Mapping System

#### Entity Co-occurrence Analysis
```python
class RelationshipMapper:
    def extract_relationships(self, entities, text, message_id):
        # Analyze entity co-occurrence in sentences
        # Determine relationship types based on:
        # - Proximity in text
        # - Connecting words/phrases
        # - Legal context clues
        # - Email header information
```

#### Knowledge Graph Construction
- **Entity Nodes**: People, organizations, legal concepts
- **Relationship Edges**: Weighted connections with confidence scores
- **Temporal Awareness**: Track relationship changes over time
- **Legal Context**: Case-specific relationship subgraphs

### 5. Advanced Deduplication

#### Fuzzy Matching Strategy
```python
class EntityNormalizer:
    def deduplicate_entities(self, entities):
        # 1. Exact match on normalized form
        # 2. Fuzzy string matching (Levenshtein distance)
        # 3. Alias detection ("John Smith" vs "J. Smith")
        # 4. Role-based consolidation ("John Smith, Attorney")
        # 5. Cross-document entity linking
```

#### Deduplication Techniques
- **String similarity**: Jaro-Winkler, Levenshtein
- **Name parsing**: First/last name component matching
- **Context similarity**: Role and organization matching
- **Email signature analysis**: Extract consistent identities

### 6. Search Integration

#### Entity-Based Query Enhancement
```python
class EntitySearch:
    def search_by_entity(self, entity_type, entity_value):
        # Find all content containing this entity
        # Include relationship-connected entities
        # Rank by entity frequency and confidence

    def find_entity_connections(self, entity_id):
        # Traverse knowledge graph
        # Find all related entities
        # Return connection paths and strengths
```

---

## Implementation Plan

### Phase 1: Legal Pattern Enhancement (Core)
1. **LegalExtractor**: Regex patterns for legal entities
2. **Enhanced SpacyExtractor**: Legal model integration
3. **Legal entity types**: Case numbers, courts, roles

### Phase 2: Relationship Mapping (Knowledge Graph)
1. **RelationshipExtractor**: Co-occurrence analysis
2. **RelationshipMapper**: Graph construction
3. **Database schema**: Relationship tables

### Phase 3: Advanced Deduplication
1. **EntityNormalizer**: Fuzzy matching implementation
2. **Alias management**: Name variant handling
3. **Cross-document linking**: Entity consolidation

### Phase 4: Search Integration
1. **EntitySearch**: Entity-based queries
2. **Search service integration**: Entity filters
3. **Knowledge graph queries**: Relationship traversal

---

## Technical Considerations

### Performance Optimization
- **Batch processing**: Handle multiple documents efficiently
- **Caching**: Cache compiled regex patterns and models
- **Indexing**: Optimize database queries with proper indexes
- **Memory management**: Stream processing for large documents

### Error Handling
- **Model failures**: Graceful degradation if spaCy models unavailable
- **Pattern matching errors**: Continue processing on regex failures
- **Database consistency**: Transaction-based relationship updates
- **Confidence thresholds**: Filter low-confidence extractions

### CLAUDE.md Compliance
- **File size limit**: Keep each file under 450 lines
- **Function complexity**: Max 30 lines per function
- **Flat architecture**: Avoid deep inheritance hierarchies
- **Simple patterns**: Direct implementations, no over-engineering

---

## Expected Outcomes

### Entity Extraction Improvements
- **Legal accuracy**: 85%+ accuracy on legal document entity extraction
- **Relationship detection**: Identify 70%+ of entity relationships
- **Deduplication**: 90%+ accuracy in entity consolidation
- **Performance**: Process 1000+ documents/minute

### Knowledge Graph Capabilities
- **Entity connections**: Map people-organization-case relationships
- **Temporal tracking**: Show relationship evolution over time
- **Search enhancement**: Entity-based content discovery
- **Legal insights**: Case participant identification and analysis

### Integration Benefits
- **Enhanced search**: Find content by entity relationships
- **Legal analysis**: Case timeline and participant mapping
- **Document clustering**: Group by shared entities
- **Intelligence gathering**: Identify patterns across cases

This ULTRATHINK design provides a comprehensive roadmap for transforming the basic entity service into a powerful legal entity extraction and knowledge graph system while maintaining CLAUDE.md architectural principles.
