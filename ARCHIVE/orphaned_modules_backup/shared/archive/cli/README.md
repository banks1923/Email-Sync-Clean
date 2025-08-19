# Archived CLI Components

This directory contains CLI components that have been archived due to being orphaned or replaced by better implementations.

## Archived Files

### `dedup_handler.py` (Archived: 2025-08-19)

**Reason**: Orphaned CLI handler - not integrated into current CLI architecture

**Original Location**: `tools/cli/dedup_handler.py`

**Status**: Functionally replaced by search intelligence system

**Functions Provided**:
- `find_duplicates_command()` - Batch duplicate detection with rich display
- `compare_documents_command()` - Two-document similarity comparison  
- `deduplicate_database_command()` - Database cleanup with dry-run mode
- `build_duplicate_index_command()` - Index building for duplicate detection

**Replacement**: Use `vsearch intelligence duplicates` command instead

**Code Quality**: Well-structured (336 lines), good error handling, rich console output

**Integration Evidence**:
- No active imports found in codebase
- Not referenced in CLI routing (`cli_main.py`, `vsearch` script)
- Functionality superseded by `intelligence_handler.py:duplicates_command()`

**Valuable Patterns**:
- Rich console display patterns
- Good error handling with user confirmations
- Dry-run mode implementation
- Progress tracking with Rich library

## Archive Policy

Files are archived rather than deleted when:
1. They contain valuable code patterns for future reference
2. They represent working implementations that might inform future development
3. They are well-structured but made obsolete by architectural changes
4. They have no active dependencies but could provide learning value

## Recovery

To recover archived components:
1. Review the replacement implementation first
2. Extract valuable patterns rather than wholesale restoration
3. Ensure integration with current architecture
4. Update imports and dependencies as needed