# Entity Service

spaCy-powered named entity recognition with 18 entity types.

## Architecture Principles

### Hard Limits
- **File Size**: Target 450 lines for new files; existing working files guided by functionality
- **Function Size**: Maximum 30 lines per function
- **Service Independence**: No imports from other services
- **Single Responsibility**: Each file has one clear purpose

### Anti-Patterns (NEVER DO)
- **No Singletons**: Direct instantiation is fine
- **No Factories**: Use if/else for 2-3 choices
- **No Abstract Base Classes**: Unless Python stdlib requires it
- **No Dependency Injection**: Just import and use
- **No Manager of Managers**: One level of management max
- **No Complex Patterns**: This is a hobby project for ONE user

### Good Patterns
- **Simple Functions**: Input → Process → Output
- **Direct Imports**: `from module import function`
- **Flat Structure**: Avoid deep nesting
- **Clear Names**: `extract_entities()` not `EntityExtractionFactory`

## Status
Production-ready Phase 1 with sub-second processing.

## Quick Commands

```bash
# Extract entities
scripts/vsearch extract-entities "John from Apple called about the Q1 meeting"

# Search by entity
scripts/vsearch search-entities --type PERSON --value "John"

# Service stats
scripts/vsearch entity-stats
```

## Architecture

- **EntityService** (`main.py`) - Main service interface
- **EntityExtractor** (`entity_extractor.py`) - spaCy NER pipeline
- **EntityDatabase** (`entity_database.py`) - SQLite entity storage
- **EntitySearcher** (`entity_searcher.py`) - Entity-based search

## Entity Types (18)

PERSON, ORG, GPE, DATE, TIME, MONEY, PERCENT, PRODUCT, EVENT,
FAC, LOC, NORP, WORK_OF_ART, LAW, LANGUAGE, QUANTITY, ORDINAL, CARDINAL

## API

```python
from src.app.core.services.entity import EntityService

service = EntityService()

# Extract entities
entities = service.extract_entities("text content")

# Search by entity
results = service.search_by_entity("PERSON", "John Smith")

# Get entity stats
stats = service.get_entity_statistics()
```

## Database Schema

- `entity_content_mapping` table links entities to content
- Full-text search indexing for performance

## Testing

```bash
pytest tests/entity_service/
```
EOF < /dev/null
