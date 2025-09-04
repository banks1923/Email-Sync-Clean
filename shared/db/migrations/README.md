# Database Migration System

This directory contains the formal database migration system for the Email Sync project, implemented to prevent schema drift and maintain data integrity.

## ⚠️ IMPORTANT: Table Migration Complete (2025-08-21)

**The system has been fully migrated from `content` table to `content_unified` table.**
- Old `content` table has been **DROPPED**
- Migration `001_add_content_columns.sql` is now **OBSOLETE** (references dropped table)
- All production code uses `content_unified` exclusively

## Overview

The migration system provides:
- ✅ **Formal migration tracking** with checksums and timestamps
- ✅ **Schema version validation** to prevent drift
- ✅ **Rollback procedures** for safe recovery
- ✅ **Automated verification** in CI/deployment pipeline
- ✅ **Data integrity protection** with constraints

## File Structure

```
migrations/
├── README.md                           # This file
├── migrate.py                          # Migration runner script
├── 001_add_content_columns.sql        # Initial schema columns
├── V002_fix_sha256_truncation.sql     # Data integrity fix (retroactive)
├── V003_add_documents_constraints.sql # Schema constraints (retroactive)
└── rollback/                          # Rollback procedures
    ├── README.md                      # Rollback documentation
    ├── R002_revert_sha256_fix.sql     # Rollback V002
    └── R003_remove_constraints.sql    # Rollback V003
```

## Migration History

### Applied Migrations

| Version | File | Description | Status | Date Applied |
|---------|------|-------------|--------|-------------|
| V001 | `001_add_content_columns.sql` | Add missing PDF pipeline columns | ✅ Applied | 2025-08-20 |
| V002 | `V002_fix_sha256_truncation.sql` | Fix SHA256 truncation in content_unified | ✅ Applied | 2025-08-20 |
| V003 | `V003_add_documents_constraints.sql` | Add unique constraints to documents table | ✅ Applied | 2025-08-20 |

### Migration Impact Summary

- **V001**: Added essential columns for PDF processing pipeline
- **V002**: Fixed critical data integrity issue with SHA256 hashes (prevented orphaned records)
- **V003**: Added constraints to prevent future duplicate documents

## Usage

### Running Migrations

```bash
# Check for pending migrations (safe)
python3 migrations/migrate.py --dry-run

# Apply all pending migrations
python3 migrations/migrate.py

# Specify different database
python3 migrations/migrate.py --db-path test/emails.db
```

### Verifying Migration Status

```bash
# Check schema version and integrity
python3 scripts/verify_pipeline.py

# JSON output for CI
python3 scripts/verify_pipeline.py --json

# Check specific migration tracking
sqlite3 data/emails.db "SELECT * FROM schema_version ORDER BY version;"
sqlite3 data/emails.db "SELECT * FROM migrations ORDER BY filename;"
```

## Migration Safety

### Before Migration
1. **Always backup the database**:
   ```bash
   timestamp=$(date +%Y%m%d_%H%M%S)
   cp data/emails.db data/emails.db.backup.$timestamp
   ```

2. **Test in dry-run mode**:
   ```bash
   python3 migrations/migrate.py --dry-run
   ```

3. **Verify current state**:
   ```bash
   python3 scripts/verify_pipeline.py
   ```

### During Migration
- Migration runner uses transactions for atomicity
- Checksums prevent corrupted migration files
- Detailed logging shows each step
- Automatic rollback on failure

### After Migration
- Schema integrity validation runs automatically
- Constraint validation tests execute
- Full pipeline verification confirms functionality

## Schema Validation

The migration system includes comprehensive validation:

### Preflight Checks
- Database file existence and accessibility
- Schema version consistency
- Required table presence
- Essential column verification
- Index and constraint validation

### Schema Integrity Tests
- V002 validation: No orphaned content records
- V002 validation: All source_ids are full 64-char SHA256 hashes  
- V003 validation: Unique constraints prevent duplicates
- Migration tracking consistency between tables

### Constraint Validation
- Tests actual constraint functionality
- Validates expected failures occur
- Confirms legitimate operations still work
- Verifies multi-chunk document support

## Error Handling

### Exit Codes
- `0`: Success - all operations completed
- `1`: Migration failure - database unchanged
- `2`: Configuration error - check database path
- `3`: Schema validation failure - manual intervention needed

### Common Issues

#### Migration File Corruption
```bash
# Symptoms: checksum mismatch
# Solution: Restore migration file from git
git checkout migrations/V00X_filename.sql
python3 migrations/migrate.py --dry-run
```

#### Schema Drift Detection  
```bash
# Symptoms: preflight test fails with "missing constraint"
# Solution: Apply missing migrations
python3 migrations/migrate.py
python3 scripts/verify_pipeline.py
```

#### Database Lock Errors
```bash
# Symptoms: "database is locked"
# Solution: Stop all applications using database
pkill -f "python.*email"
pkill -f qdrant
python3 migrations/migrate.py
```

## Development Guidelines

### Creating New Migrations

1. **Use sequential naming**: `V004_description.sql`
2. **Include comprehensive comments**: Purpose, prerequisites, validation
3. **Add rollback procedure**: Create corresponding `R004_rollback.sql`
4. **Test thoroughly**: Test on copy of production data
5. **Update expected schema version**: Modify `verify_pipeline.py`

### Migration File Template

```sql
-- Migration V00X: Brief description
-- Date: YYYY-MM-DD
-- Purpose: Detailed explanation of changes
-- Prerequisites: List required previous migrations
-- Impact: Describe effects on system behavior

-- Problem Analysis:
-- Explain what issue this fixes or feature this adds

-- Solution:
-- Describe the approach taken

-- Migration Commands:
-- SQL commands go here

-- Verification Queries:
-- Queries to validate the migration worked
-- Expected results described

-- Migration Success Criteria:
-- List of conditions that indicate success

-- Rollback Information:
-- Reference to rollback procedure file
```

### Testing Migrations

```bash
# 1. Create test database
cp data/emails.db test_migration.db

# 2. Test migration
python3 migrations/migrate.py --db-path test_migration.db --dry-run
python3 migrations/migrate.py --db-path test_migration.db

# 3. Validate results
python3 scripts/verify_pipeline.py --json | grep -E "(PASS|FAIL)"

# 4. Test rollback procedure  
sqlite3 test_migration.db < migrations/rollback/R00X_rollback.sql
```

## Integration with CI/CD

### Pre-deployment Validation
```bash
# Validate current schema state
python3 scripts/verify_pipeline.py --json --strict

# Check for pending migrations
python3 migrations/migrate.py --dry-run | grep "pending"
```

### Deployment Pipeline
```bash
# 1. Create pre-deployment backup
backup_db_before_deployment.sh

# 2. Apply migrations
python3 migrations/migrate.py

# 3. Verify system integrity
python3 scripts/verify_pipeline.py --json --strict

# 4. Start services
start_email_sync_services.sh
```

### Health Monitoring
```bash
# Continuous schema validation
python3 scripts/verify_pipeline.py --json | jq '.tests.schema_integrity.status'

# Migration consistency check
python3 scripts/verify_pipeline.py --json | jq '.tests.preflight.details.schema_version'
```

## Troubleshooting

### Schema Version Mismatch
If the schema validation fails:

1. Check current version:
   ```bash
   sqlite3 data/emails.db "SELECT MAX(version) FROM schema_version;"
   ```

2. Check expected version in `verify_pipeline.py`:
   ```python
   expected_version = 3  # Should match current maximum
   ```

3. Apply missing migrations:
   ```bash
   python3 migrations/migrate.py
   ```

### Constraint Failures
If unique constraints are failing:

1. Check for duplicate data:
   ```bash
   sqlite3 data/emails.db "
   SELECT sha256, chunk_index, COUNT(*) 
   FROM documents 
   GROUP BY sha256, chunk_index 
   HAVING COUNT(*) > 1;"
   ```

2. Resolve duplicates before applying constraints
3. Re-run migration

### Rollback Recovery
For emergency rollback to known-good state:

1. Stop all services
2. Restore from backup:
   ```bash
   cp data/emails.db.backup.TIMESTAMP data/emails.db
   ```
3. Reset schema version:
   ```bash
   sqlite3 data/emails.db "DELETE FROM schema_version WHERE version > X;"
   ```
4. Re-apply migrations as needed

## Support

- **Documentation**: See `CLAUDE.md` for project guidelines
- **Pipeline Issues**: Run `make diag-wiring` for comprehensive diagnostics  
- **Emergency Procedures**: See `migrations/rollback/README.md`
- **Schema Questions**: Check `shared/simple_db.py` for database implementation