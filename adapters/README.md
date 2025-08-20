# Temporary Adapters

This directory contains temporary adapter classes that handle API mismatches between services.

## ⚠️ REMOVAL TARGET: 2025-09-01

These adapters are **technical debt** and should be removed by fixing the underlying services.

## Current Adapters

### 1. EmailThreadAdapter
**Problem:** `gmail/main.py` passes `save_to_db=True` but `EmailThreadProcessor` doesn't accept it.
**Current Fix:** Strip the parameter in the adapter.
**Proper Fix:** Either:
- Update `EmailThreadProcessor` to accept and use `save_to_db`
- Update `gmail/main.py` to stop passing it

### 2. VectorMaintenanceAdapter  
**Problem:** `VectorMaintenance` expects methods like `get_all_content_ids` that `SimpleDB` doesn't provide.
**Current Fix:** Synthesize missing methods using SimpleDB's existing API.
**Proper Fix:** Either:
- Add these methods to SimpleDB
- Refactor VectorMaintenance to use SimpleDB's existing methods

### 3. SchemaAdapter
**Problem:** Code tries to use `source_path` column that may not exist in database.
**Current Fix:** Handle missing columns gracefully, store in metadata if needed.
**Proper Fix:** Run schema migration to add missing columns.

## Usage Example

```python
# Instead of direct usage with mismatches:
processor = EmailThreadProcessor()
processor.process_thread(thread_id, save_to_db=True)  # ERROR!

# Use adapter temporarily:
from adapters import EmailThreadAdapter
processor = EmailThreadAdapter(EmailThreadProcessor())
processor.process_thread(thread_id, save_to_db=True)  # Works!
```

## Migration Plan

1. **Phase 1 (Now):** Use adapters to isolate mismatches
2. **Phase 2 (By 2025-08-01):** Fix underlying service APIs
3. **Phase 3 (By 2025-09-01):** Remove adapters completely

## How to Remove

For each adapter:
1. Fix the underlying mismatch in the services
2. Update all callers to use the fixed API
3. Delete the adapter class
4. Remove from `__init__.py`

## Tracking

Search for adapter usage:
```bash
grep -r "from adapters import" --include="*.py"
grep -r "Adapter(" --include="*.py"
```

Count remaining shims:
```bash
ls -1 adapters/*.py | grep -v __init__ | wc -l
```