_This document outlines the development principles and implementation details for the CLI tools._

# CLI Modular Architecture

Modular CLI implementation following clean architecture principles.

## Architecture Principles

### Hard Limits
- **File Size**: Maximum 450 lines per file
- **Function Size**: Maximum 30 lines per function
- **Handler Independence**: Each handler focuses on one command category
- **Single Responsibility**: Each file has one clear purpose

### Anti-Patterns (NEVER DO)
- **No Monolithic Functions**: Break down large command handlers
- **No Direct Service Imports**: Use service locator pattern instead
- **No Complex Routing**: Simple command → handler mapping
- **No Shared State**: Each handler operates independently

### Good Patterns
- **Simple Handlers**: Command args → Service locator → Service call → Display results
- **Service Locator**: Use `get_locator().get_*_service()` for service access
- **Focused Modules**: Each handler handles related commands only
- **Clear Names**: `search_handler.py` not `SearchCommandProcessor`

## Module Structure

### Core Entry Point
- **cli_main.py** (186 lines) - Main CLI with argument parsing and routing

### Service Discovery
- **service_locator.py** (70 lines) - Service access layer for CLI handlers
- **../shared/service_registry.py** (232 lines) - Centralized service registration and health monitoring

### Handler Modules
- **search_handler.py** (184 lines) - Search operations: `search`, `multi-search` (uses service locator)
- **process_handler.py** (81 lines) - Processing operations: `process`, `embed` (uses service locator)
- **upload_handler.py** (147 lines) - Upload operations: `upload`, `process-uploads`, `process-pdf-uploads`
- **info_handler.py** (288 lines) - Information display: `info`, `pdf-stats`, `transcription-stats`
- **transcription_handler.py** (46 lines) - Transcription operations: `transcribe`
- **timeline_handler.py** (72 lines) - Timeline operations: `timeline`
- ~~**notes_handler.py**~~ - **REMOVED** - Notes migrated to document pipeline

## Usage

```bash
# Direct usage via modular CLI
python3 scripts/cli/cli_main.py search "query"

# Via convenience wrapper (recommended)
scripts/vsearch_modular search "query"
```

## Benefits

- **Maintainability**: Each command category under 200 lines
- **Testability**: Individual handlers easily tested with service injection
- **Extensibility**: New commands added by creating new handlers
- **Clean Separation**: Search logic separate from upload logic
- **Service Discovery**: Centralized service management with health monitoring
- **Loose Coupling**: Handlers don't directly import service classes
- **Architecture Compliance**: All files under 250-line limit

## Service Discovery Pattern

### Usage in Handlers
```python
from scripts.cli.service_locator import get_locator

def search_emails(query, limit=5):
    locator = get_locator()
    vector_service = locator.get_vector_service()
    search_service = locator.get_search_service()
    # Use services normally...
```

### Available Services
- `get_vector_service()` - Legal BERT semantic search
- `get_search_service()` - Hybrid keyword/semantic search
- `get_gmail_service()` - Gmail API integration
- `get_pdf_service()` - PDF processing and storage
- `get_transcription_service()` - Audio transcription
- `get_entity_service()` - Named entity recognition
- `get_timeline_service()` - Chronological content timeline
- ~~`get_notes_service()`~~ - **REMOVED** - Use document pipeline for notes

### Health Monitoring
```python
locator = get_locator()
if locator.is_service_healthy('vector'):
    vector_service = locator.get_vector_service()
else:
    print("Vector service unavailable")
```

## Migration Strategy

1. **Phase 1**: Split monolithic CLI into focused handler modules ✅
2. **Phase 2**: Implement service discovery pattern ✅
3. **Phase 3**: Update all handlers to use service locator (in progress)
4. **Phase 4**: Update main vsearch script to delegate to modular CLI
5. **Phase 5**: Deprecate monolithic CLI once stability confirmed

The modular CLI with service discovery maintains full backward compatibility while providing a clean, maintainable architecture for future development.