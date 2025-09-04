# Codemod Tools

This directory contains LibCST-based code transformation tools.

## Archived Migrations

Completed migrations have been archived to `archive_completed_2025-09-04/`:

- `centralize_config.py` - Centralized configuration paths (applied 2025-08-25)
- `consolidate_search.py` - Consolidated search functionality (applied 2025-08-25)
- `migrate_src_imports.py` - Migrated src/ imports to infrastructure/ (applied 2025-09-04)
- `replace_content_id_sql.py` - Updated SQL for TEXT-based IDs (applied 2025-08-26)
- `test_single_transform.py` - Test harness for transformations

These scripts were one-time migrations that have already been successfully applied to the codebase.

## Active Tools

Currently no active migration tools. New codemods should be placed in this directory.