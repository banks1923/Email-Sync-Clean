_This document outlines the development principles and implementation details for the Shared services._

# Shared Components

Minimal shared utilities - only truly shared components remain here.

## Philosophy

Following the "Simple > Complex" principle, this directory now contains only 3 files that are genuinely shared across multiple services.

## Current Structure (3 files only)

### SimpleDB (`simple_db.py`)
The core database interface used by 13+ modules across the system.

```python
from shared.simple_db import SimpleDB

db = SimpleDB()
content_id = db.add_content("transcript", title, content, metadata)
results = db.search_content("query", limit=10)

# High-performance batch operations
stats = db.batch_insert(
    table_name="emails",
    columns=["id", "subject", "body"],
    data_list=[...],
    batch_size=1000
)
```

**Features:**
- Direct SQLite operations (no ORM)
- Batch operations (~2000+ records/second)
- Auto-generation of UUIDs, word counts
- Progress callbacks for long operations
- Used by: search, pdf, transcription, mcp_server, scripts, tests

### ServiceInterfaces (`service_interfaces.py`)
Common interface definitions for services.

```python
from shared.service_interfaces import IService

class PDFService(IService):
    # Implements standard service interface
```

**Used by:**
- PDFService (implements IService)
- Test suites for interface compliance

### Package Init (`__init__.py`)
Simple package initialization - exports only the shared components.

## Moved Components

Service-specific utilities have been moved to their respective services:

### Moved to `gmail/`:
- `validators.py` → `gmail/validators.py` (EmailValidator, DateValidator, InputSanitizer)

### Moved to `pdf/`:
- `database_error_recovery.py` → `pdf/database_error_recovery.py`
- `database_health_monitor.py` → `pdf/database_health_monitor.py`

### Archived (in `shared/archive/`):
Unused or deprecated components preserved for reference:
- `config_manager.py` - Not actively used
- `memory_monitor.py` - Not actively used
- `response_standardizer.py` - Not actively used
- `db_connection.py` - Only used in deployment scripts
- `database_tables.py` - Replaced by SimpleDB
- `database_schema.py` - Replaced by SimpleDB
- `database_indexes.py` - Replaced by SimpleDB
- `database_fts.py` - Replaced by SimpleDB
- `env_loader.py` - Not actively used

## Import Changes

### Old (Don't use):
```python
from shared.validators import EmailValidator
from shared.database_error_recovery import DatabaseErrorRecovery
```

### New (Use these):
```python
from gmail.validators import EmailValidator  # Gmail-specific
from pdf.database_error_recovery import DatabaseErrorRecovery  # PDF-specific
from shared.simple_db import SimpleDB  # Still in shared (used everywhere)
```

## Testing

```bash
# Test shared components
python3 -c "
from shared import SimpleDB, IService
db = SimpleDB()
print('✓ Shared components working')
"

# Test moved components
python3 -c "
from gmail.validators import EmailValidator
from pdf.database_error_recovery import DatabaseErrorRecovery
print('✓ Moved components working')
"
```

## Results

- **Before**: 15 Python files, 3,176 lines
- **After**: 3 Python files, ~450 lines active
- **Reduction**: 80% fewer files, 86% less code
- **Benefit**: Cleaner architecture, better organization