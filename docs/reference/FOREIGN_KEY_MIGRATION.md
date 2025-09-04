# Foreign Key Migration Documentation

**Date**: 2025-08-26  
**Status**: ✅ COMPLETED  
**Impact**: Critical data integrity improvement

## Summary

Successfully implemented referential integrity in the database through conditional foreign key constraints. This ensures data consistency for legal evidence while properly handling email summaries.

## Problem Discovered

- 362 "orphaned" records in `content_unified` table
- Actually a mix of:
  - 182 email summaries (SHA256 hashes)
  - 180 Gmail ID records from older imports
- All incorrectly stored as `source_type='email_message'`
- No actual FK constraints despite `PRAGMA foreign_keys=ON`

## Solution Implemented

### 1. Data Model Update
- Created new `source_type='email_summary'` for non-message content
- Migrated all 362 orphaned records to proper type
- Preserved all data while fixing integrity issues

### 2. Foreign Key Implementation
- Added conditional FK enforcement via triggers
- Only applies to `source_type='email_message'` records
- Email summaries exempt from FK constraints
- CASCADE DELETE enabled for automatic cleanup

### 3. Schema Changes

```sql
-- Updated CHECK constraint
CHECK(source_type IN ('email', 'email_message', 'email_summary', 'document', 'document_chunk'))

-- Conditional FK trigger
CREATE TRIGGER enforce_email_message_fk
BEFORE INSERT ON content_unified
WHEN NEW.source_type = 'email_message'
BEGIN
    SELECT RAISE(ABORT, 'Foreign key violation')
    WHERE NOT EXISTS (
        SELECT 1 FROM individual_messages 
        WHERE message_hash = NEW.source_id
    );
END
```

## Current State

| Source Type | Count | FK Required | Description |
|------------|-------|-------------|-------------|
| email_message | 302 | ✅ Yes | Actual email messages with valid hashes |
| email_summary | 362 | ❌ No | Summaries and Gmail ID records |
| Total | 664 | - | All data preserved |

## Benefits

1. **Data Integrity**: Can't create orphaned email_message records
2. **Legal Compliance**: Audit trail preserved for evidence
3. **Safe Deletions**: CASCADE ensures no broken references
4. **Performance**: Minimal impact (triggers only on INSERT/UPDATE)
5. **Backward Compatible**: Email summaries continue to work

## Migration Tool

`scripts/enable_foreign_keys_comprehensive.py`

Features:
- Dry-run mode for safety
- Automatic backup creation
- Rollback on failure
- Comprehensive validation
- Force mode for automation

## Usage

```bash
# Check what would happen
python3 scripts/enable_foreign_keys_comprehensive.py --dry-run

# Apply migration
python3 scripts/enable_foreign_keys_comprehensive.py --force

# Verify enforcement
python3 scripts/test_foreign_keys.py
```

## Testing

The system now enforces:
- ✅ Blocks invalid email_message references
- ✅ Allows email_summary without FK
- ✅ CASCADE deletes work properly
- ✅ Performance unchanged

## Important Notes

1. **SimpleDB Configuration**: Foreign keys enabled in `_configure_connection()`
2. **Per-Connection Setting**: Must be enabled for each connection
3. **Triggers vs Constraints**: Using triggers for conditional enforcement
4. **Email Summaries**: 362 records now properly categorized

## Future Considerations

1. Consider separate `email_summaries` table for better organization
2. Monitor performance with FK enforcement
3. Add metrics for constraint violations
4. Consider adding FK for document-related tables

## Rollback Plan

If issues arise:
```bash
# Restore from backup
cp data/system_data/emails.backup_*.db data/system_data/emails.db

# Or disable FK enforcement temporarily
sqlite3 data/system_data/emails.db "PRAGMA foreign_keys=OFF"
```

## Verification Commands

```bash
# Check FK status
sqlite3 data/system_data/emails.db "PRAGMA foreign_keys"

# View records by type
sqlite3 data/system_data/emails.db "SELECT source_type, COUNT(*) FROM content_unified GROUP BY source_type"

# Test enforcement
python3 scripts/test_foreign_keys.py
```

## Related Files

- `/scripts/enable_foreign_keys_comprehensive.py` - Migration script
- `/scripts/test_foreign_keys.py` - Verification script
- `/shared/simple_db.py` - Database connection configuration
- `/CHANGELOG.md` - Migration history
- `/CLAUDE.md` - Development documentation update