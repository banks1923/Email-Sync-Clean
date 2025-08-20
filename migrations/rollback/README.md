# Migration Rollback Procedures

This directory contains rollback procedures for Email Sync database migrations.

## Important Warning

**Always create a database backup before applying migrations or rollbacks:**

```bash
timestamp=$(date +%Y%m%d_%H%M%S)
cp data/emails.db data/emails.db.backup.$timestamp
```

## Available Rollbacks

### R002_revert_sha256_fix.sql
- **Reverts**: V002 SHA256 truncation fix
- **Risk Level**: HIGH - Requires backup restore
- **Data Impact**: Restores broken document->content relationships
- **Procedure**: Must restore from database backup

### R003_remove_constraints.sql  
- **Reverts**: V003 unique constraints on documents table
- **Risk Level**: LOW - Safe SQL rollback
- **Data Impact**: No data loss, removes duplicate prevention
- **Procedure**: Execute SQL commands directly

## Rollback Usage

### General Process

1. **Stop applications**:
   ```bash
   # Stop any running processes using the database
   pkill -f "python.*gmail"
   pkill -f "python.*pdf"  
   pkill -f qdrant
   ```

2. **Create current backup**:
   ```bash
   timestamp=$(date +%Y%m%d_%H%M%S)
   cp data/emails.db data/emails.db.backup.before_rollback.$timestamp
   ```

3. **Execute rollback**:
   - For backup-based rollbacks (R002): Follow backup restoration procedure
   - For SQL rollbacks (R003): Execute SQL commands

4. **Verify rollback**:
   ```bash
   python3 scripts/verify_pipeline.py
   ```

5. **Restart applications**:
   ```bash
   make full-run  # or your normal startup procedure
   ```

### Specific Rollback Procedures

#### Rolling back V002 (SHA256 Fix)

```bash
# 1. Identify pre-V002 backup
ls -la data/*.backup* | grep -v constraints

# 2. Restore backup (replace TIMESTAMP with actual)
cp data/emails.db.backup.TIMESTAMP data/emails.db

# 3. Update schema version
sqlite3 data/emails.db "DELETE FROM schema_version WHERE version = 2;"

# 4. Verify rollback
python3 scripts/verify_pipeline.py  # Should show broken chains
```

#### Rolling back V003 (Constraints)

```bash
# 1. Execute rollback SQL
sqlite3 data/emails.db < migrations/rollback/R003_remove_constraints.sql

# 2. Verify constraints removed
sqlite3 data/emails.db ".indexes documents"  # Should not show unique constraint

# 3. Test duplicate insertion (should succeed)
sqlite3 data/emails.db "INSERT INTO documents (chunk_id, sha256, chunk_index) VALUES ('test1', 'abc123', 0);"
sqlite3 data/emails.db "INSERT INTO documents (chunk_id, sha256, chunk_index) VALUES ('test2', 'abc123', 0);"  # Should work
sqlite3 data/emails.db "DELETE FROM documents WHERE chunk_id LIKE 'test%';"  # Cleanup
```

## Recovery After Rollback

### After R002 Rollback (Restore SHA256 Fix)
```bash
# Re-apply migration
python3 migrations/migrate.py

# Verify fix
python3 scripts/verify_pipeline.py  # Should pass all tests
```

### After R003 Rollback (Restore Constraints)
```bash
# Check for duplicates first
sqlite3 data/emails.db "SELECT sha256, chunk_index, COUNT(*) FROM documents GROUP BY sha256, chunk_index HAVING COUNT(*) > 1;"

# Remove any duplicates found, then re-apply
python3 migrations/migrate.py

# Verify constraints
python3 scripts/add_documents_constraints.py  # Should show constraints exist
```

## Emergency Procedures

### Complete System Reset
If multiple rollbacks are needed or the system is in an inconsistent state:

```bash
# 1. Find oldest known-good backup
ls -la data/*.backup* | head -5

# 2. Restore to known-good state
cp data/emails.db.backup.EARLIEST data/emails.db

# 3. Reset schema version
sqlite3 data/emails.db "DELETE FROM schema_version WHERE version > 1;"

# 4. Re-apply migrations from scratch
python3 migrations/migrate.py

# 5. Full system verification
python3 scripts/verify_pipeline.py
make diag-wiring
```

### Backup Recovery
```bash
# List all available backups with details
ls -la data/*.backup* | awk '{print $6, $7, $8, $9}' | sort

# Check backup integrity before restore
sqlite3 data/emails.db.backup.TIMESTAMP "PRAGMA integrity_check;"

# Verify backup content
sqlite3 data/emails.db.backup.TIMESTAMP "SELECT COUNT(*) FROM documents;"
```

## Troubleshooting

### Common Issues

1. **Permission Errors**: Ensure proper file ownership
   ```bash
   chown $USER:$USER data/emails.db*
   ```

2. **Lock Errors**: Ensure no processes are using database
   ```bash
   lsof data/emails.db
   ```

3. **Corruption**: Check database integrity
   ```bash
   sqlite3 data/emails.db "PRAGMA integrity_check;"
   ```

### Validation Commands

```bash
# Check current schema version
sqlite3 data/emails.db "SELECT * FROM schema_version ORDER BY version;"

# Check migration table
sqlite3 data/emails.db "SELECT * FROM migrations ORDER BY filename;"

# Verify table structures
sqlite3 data/emails.db ".schema documents"
sqlite3 data/emails.db ".schema content_unified"

# Check data integrity
python3 scripts/verify_pipeline.py
```

## Contact and Support

- Review project documentation: `CLAUDE.md`
- Check pipeline status: `make diag-wiring`
- Run full verification: `python3 scripts/verify_pipeline.py --json`