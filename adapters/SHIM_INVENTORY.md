# Shim Inventory - Current State

Generated: 2025-08-19

## Identified Shims (Now Isolated in adapters/)

### 1. ✅ EmailThreadProcessor Parameter Mismatch
**Location:** `gmail/main.py:413`
**Issue:** Passes `save_to_db=True` but `EmailThreadProcessor.process_thread()` doesn't accept it
**Adapter:** `EmailThreadAdapter` 
**Fix Required:** 
- Option A: Add `save_to_db` parameter to `EmailThreadProcessor.process_thread()`
- Option B: Remove `save_to_db=True` from `gmail/main.py` call

### 2. ✅ VectorMaintenance API Mismatch  
**Location:** `utilities/maintenance/vector_maintenance.py:45-60`
**Issue:** Expects `get_all_content_ids()` method that SimpleDB doesn't provide
**Adapter:** `VectorMaintenanceAdapter`
**Fix Required:**
- Option A: Add `get_all_content_ids()` to SimpleDB
- Option B: Refactor VectorMaintenance to use SimpleDB's existing methods

### 3. ✅ Schema Column Mismatches
**Detected Columns Missing:**
- `source_path` 
- `vector_processed`
- `word_count`

**Adapter:** `SchemaAdapter`
**Fix Required:** Add migration to create missing columns in content table

## Usage Locations

### Current Adapter Usage
```python
# gmail/main.py:411-416
from adapters import EmailThreadAdapter
adapted_processor = EmailThreadAdapter(self.thread_processor)
result = adapted_processor.process_thread(
    thread_id=thread_id,
    include_metadata=True,
    save_to_db=True  # This param is the mismatch
)

# utilities/maintenance/vector_maintenance.py:38-39  
from adapters import VectorMaintenanceAdapter
self.db = VectorMaintenanceAdapter(SimpleDB())
```

## Metrics

- **Total Shims Found:** 3
- **Shims Isolated:** 3 (100%)
- **Files with Adapters:** 2
- **Target Removal:** 2025-09-01

## Next Steps

1. **Immediate:** ✅ All shims now isolated in adapters/
2. **By 2025-08-01:** Fix underlying service APIs
3. **By 2025-09-01:** Remove all adapters

## Verification Commands

```bash
# Check adapter usage
grep -r "from adapters import" --include="*.py"

# Find remaining inline shims (should be 0)
grep -r "save_to_db" --include="*.py" | grep -v adapters/

# Check for missing SimpleDB methods
grep -r "get_all_content_ids" --include="*.py" | grep -v adapters/
```

## Technical Debt Score

**Current:** 🟡 Medium (3 shims, but all isolated)
**Target:** 🟢 Low (0 shims by 2025-09-01)