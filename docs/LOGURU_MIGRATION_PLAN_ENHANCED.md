# Loguru Migration Plan - Enhanced Implementation Guide v2

## Executive Summary
Migration from Python standard logging to loguru for improved debugging experience, especially beneficial for rookie developers.

**Revised Estimates Based on 1OrchestratorAgent1 Review:**
- **Total Time**: 5-7 hours (revised from 4-6)
- **Files Affected**: 67 files (corrected from 61)
- **Log Statements**: 424 occurrences (corrected from 399)
- **Critical Files**: SimpleDB has 29 log statements and is central to system

## CRITICAL PRIORITY: SimpleDB Migration

### Why SimpleDB First?
- Central to entire system (all services depend on it)
- 29 log statements - significant presence
- Any issues here affect everything
- Good test case for migration approach

## Phase 0: Pre-Migration Safety (30 minutes)

### 0.1 Create Safety Checkpoint
```bash
# Create feature branch
git checkout -b feature/loguru-migration

# Tag current state for easy rollback
git tag pre-loguru-migration

# Create backup of critical files
cp shared/simple_db.py shared/simple_db.py.backup
cp shared/logging_config.py shared/logging_config.py.backup
```

### 0.2 Performance Baseline
```python
# Create benchmark script: tools/scripts/benchmark_logging.py
import time
import logging
from loguru import logger as loguru_logger

def benchmark_standard_logging(iterations=10000):
    """Benchmark standard logging performance."""
    logger = logging.getLogger(__name__)
    start = time.perf_counter()
    for i in range(iterations):
        logger.info(f"Test message {i}")
    return time.perf_counter() - start

def benchmark_loguru(iterations=10000):
    """Benchmark loguru performance."""
    loguru_logger.remove()
    loguru_logger.add("benchmark.log", level="INFO")
    start = time.perf_counter()
    for i in range(iterations):
        loguru_logger.info(f"Test message {i}")
    return time.perf_counter() - start

if __name__ == "__main__":
    std_time = benchmark_standard_logging()
    loguru_time = benchmark_loguru()
    print(f"Standard logging: {std_time:.3f}s")
    print(f"Loguru: {loguru_time:.3f}s")
    print(f"Difference: {((loguru_time - std_time) / std_time * 100):.1f}%")
```

## Phase 1: Enhanced Configuration Module (45 minutes)

### 1.1 Production-Safe loguru_config.py
```python
"""
Centralized loguru configuration for Email Sync system.
Production-safe with environment detection and sensitive data filtering.
"""

import os
import sys
import re
from pathlib import Path
from typing import Optional
from loguru import logger

# Patterns for sensitive data
SENSITIVE_PATTERNS = [
    r'password["\']?\s*[:=]\s*["\']?[\w\S]+',
    r'token["\']?\s*[:=]\s*["\']?[\w\S]+',
    r'api_key["\']?\s*[:=]\s*["\']?[\w\S]+',
    r'secret["\']?\s*[:=]\s*["\']?[\w\S]+',
    r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',  # Email
]

def filter_sensitive(record):
    """Filter sensitive data from log messages."""
    message = record["message"]
    for pattern in SENSITIVE_PATTERNS:
        message = re.sub(pattern, "***REDACTED***", message, flags=re.IGNORECASE)
    record["message"] = message
    return record

def setup_logging(
    service_name: str = "email_sync",
    log_level: Optional[str] = None,
    log_dir: str = "logs",
    enable_rotation: bool = True,
    enable_json: bool = False,
    use_loguru: bool = None  # Toggle for gradual migration
):
    """
    Configure loguru for the application with production safety.
    
    Environment Variables:
    - LOG_LEVEL: Set logging level (DEBUG, INFO, WARNING, ERROR)
    - ENVIRONMENT: Set to 'production' for production safety
    - USE_LOGURU: Set to 'false' to use standard logging (migration toggle)
    """
    # Check if we should use loguru (for gradual migration)
    if use_loguru is None:
        use_loguru = os.getenv("USE_LOGURU", "true").lower() != "false"
    
    if not use_loguru:
        # Fall back to standard logging for safety
        import logging
        logging.basicConfig(
            level=log_level or os.getenv("LOG_LEVEL", "INFO"),
            format='%(asctime)s | %(levelname)-8s | %(name)s:%(funcName)s:%(lineno)d - %(message)s'
        )
        return logging.getLogger(service_name)
    
    # Remove default handler
    logger.remove()
    
    # Detect environment
    is_production = os.getenv("ENVIRONMENT", "").lower() == "production"
    
    # Get log level from environment or parameter
    level = log_level or os.getenv("LOG_LEVEL", "INFO" if is_production else "DEBUG")
    
    # Create logs directory
    Path(log_dir).mkdir(exist_ok=True)
    
    # Console handler with color (disabled in production)
    console_format = (
        "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
        "<level>{level: <8}</level> | "
        "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - "
        "<level>{message}</level>"
    )
    
    logger.add(
        sys.stderr,
        format=console_format,
        level=level,
        colorize=not is_production,  # No colors in production
        filter=filter_sensitive if is_production else None
    )
    
    # File handler with rotation
    if enable_rotation:
        file_format = (
            "{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | "
            "{name}:{function}:{line} - {message}"
        )
        
        logger.add(
            f"{log_dir}/{service_name}_{{time:YYYY-MM-DD}}.log",
            rotation="500 MB",
            retention="10 days" if is_production else "30 days",
            compression="zip",
            format=file_format,
            level=level,
            backtrace=True,
            diagnose=not is_production,  # CRITICAL: Disable in production
            filter=filter_sensitive if is_production else None
        )
    
    # JSON handler for structured logging (useful for log aggregation)
    if enable_json:
        logger.add(
            f"{log_dir}/{service_name}_json.log",
            format="{message}",
            serialize=True,
            rotation="1 GB",
            retention="30 days" if is_production else "7 days",
            level=level,
            filter=filter_sensitive if is_production else None
        )
    
    # Error-only file for critical issues
    if is_production:
        logger.add(
            f"{log_dir}/{service_name}_errors.log",
            level="ERROR",
            rotation="100 MB",
            retention="90 days",
            backtrace=True,
            diagnose=False,
            filter=filter_sensitive
        )
    
    # Add context binding for service
    return logger.bind(service=service_name)

# Backward compatibility
def get_logger(name: str = __name__):
    """Get a logger instance (backward compatibility)."""
    return logger.bind(module=name)
```

## Phase 2: Enhanced Migration Script (45 minutes)

### 2.1 Robust Migration Script with Dry-Run
```python
#!/usr/bin/env python3
"""
Enhanced migration script from standard logging to loguru.
Includes dry-run mode, backup creation, and error handling.
"""

import os
import re
import shutil
from pathlib import Path
from typing import List, Tuple
import argparse

class LoguruMigrator:
    def __init__(self, dry_run: bool = False, backup: bool = True):
        self.dry_run = dry_run
        self.backup = backup
        self.files_processed = 0
        self.files_skipped = 0
        self.errors = []
        
    def migrate_file(self, filepath: Path) -> Tuple[bool, str]:
        """Migrate a single file from logging to loguru."""
        try:
            # Create backup if requested
            if self.backup and not self.dry_run:
                backup_path = filepath.with_suffix(filepath.suffix + '.backup')
                shutil.copy2(filepath, backup_path)
            
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()
            
            original_content = content
            
            # Skip if already using loguru
            if 'from loguru import logger' in content:
                return False, "Already using loguru"
            
            # Replace imports
            content = re.sub(
                r'^import logging$',
                'from loguru import logger',
                content,
                flags=re.MULTILINE
            )
            
            content = re.sub(
                r'^from logging import .*$',
                'from loguru import logger',
                content,
                flags=re.MULTILINE
            )
            
            # Handle getLogger patterns
            patterns = [
                (r'self\.logger = logging\.getLogger\(__name__\)', 
                 '# Logger is now imported globally from loguru'),
                (r'logger = logging\.getLogger\(__name__\)', 
                 '# Logger is now imported globally from loguru'),
                (r'(\w+) = logging\.getLogger\([^)]*\)', 
                 r'# \1 is now the global logger from loguru'),
            ]
            
            for pattern, replacement in patterns:
                content = re.sub(pattern, replacement, content)
            
            # Convert self.logger to logger
            content = re.sub(r'self\.logger\.', 'logger.', content)
            
            # Convert error with exc_info to exception
            content = re.sub(
                r'logger\.error\((.*?),\s*exc_info=True\)',
                r'logger.exception(\1)',
                content,
                flags=re.DOTALL
            )
            
            # Remove basicConfig calls
            content = re.sub(
                r'logging\.basicConfig\([^)]+\)',
                '# Logging config moved to shared/loguru_config.py',
                content,
                flags=re.DOTALL
            )
            
            # Handle logging.DEBUG, INFO, etc. constants
            content = re.sub(r'logging\.(DEBUG|INFO|WARNING|ERROR|CRITICAL)', r'"\1"', content)
            
            # Special case for setup_service_logging imports
            content = re.sub(
                r'from shared\.logging_config import setup_service_logging',
                'from shared.loguru_config import setup_logging',
                content
            )
            
            # Special case for setup_service_logging calls
            content = re.sub(
                r'setup_service_logging\(',
                'setup_logging(',
                content
            )
            
            # Check if changes were made
            if content == original_content:
                return False, "No changes needed"
            
            # Write changes if not dry-run
            if not self.dry_run:
                with open(filepath, 'w', encoding='utf-8') as f:
                    f.write(content)
            
            return True, "Successfully migrated"
            
        except Exception as e:
            return False, f"Error: {str(e)}"
    
    def find_python_files(self, root_dir: Path, exclude_dirs: List[str] = None) -> List[Path]:
        """Find all Python files that need migration."""
        exclude_dirs = exclude_dirs or ['.venv', 'venv', '__pycache__', '.git', 'migrations']
        python_files = []
        
        for file in root_dir.rglob('*.py'):
            # Skip excluded directories
            if any(excluded in file.parts for excluded in exclude_dirs):
                continue
            
            # Check if file uses logging
            try:
                with open(file, 'r', encoding='utf-8') as f:
                    content = f.read()
                    if 'logging' in content and 'loguru' not in content:
                        python_files.append(file)
            except Exception:
                pass
        
        return python_files
    
    def migrate_project(self, root_dir: str, pilot_mode: bool = False):
        """Migrate entire project with optional pilot mode."""
        root_path = Path(root_dir)
        
        # Find files to migrate
        files = self.find_python_files(root_path)
        
        # Sort files by priority (SimpleDB first, then core services)
        priority_files = []
        other_files = []
        
        for file in files:
            if 'simple_db.py' in file.name:
                priority_files.insert(0, file)  # SimpleDB goes first
            elif any(s in str(file) for s in ['gmail/main', 'pdf/main', 'entity/main']):
                priority_files.append(file)
            else:
                other_files.append(file)
        
        all_files = priority_files + other_files
        
        # Pilot mode: only process first 5 files
        if pilot_mode:
            all_files = all_files[:5]
            print(f"PILOT MODE: Processing only {len(all_files)} files")
        
        print(f"Found {len(all_files)} files to migrate")
        if self.dry_run:
            print("DRY RUN MODE - No files will be modified")
        
        # Process files
        for i, file in enumerate(all_files, 1):
            rel_path = file.relative_to(root_path)
            success, message = self.migrate_file(file)
            
            status = "✓" if success else "○"
            print(f"[{i}/{len(all_files)}] {status} {rel_path}: {message}")
            
            if success:
                self.files_processed += 1
            else:
                self.files_skipped += 1
                if "Error" in message:
                    self.errors.append((rel_path, message))
        
        # Print summary
        print("\n" + "="*60)
        print("Migration Summary:")
        print(f"  Files processed: {self.files_processed}")
        print(f"  Files skipped: {self.files_skipped}")
        
        if self.errors:
            print(f"\nErrors encountered:")
            for file, error in self.errors:
                print(f"  - {file}: {error}")
        
        if self.dry_run:
            print("\nDRY RUN COMPLETE - No files were modified")
            print("Run without --dry-run to apply changes")

def main():
    parser = argparse.ArgumentParser(description='Migrate from standard logging to loguru')
    parser.add_argument('--dry-run', action='store_true', help='Preview changes without modifying files')
    parser.add_argument('--no-backup', action='store_true', help='Skip creating backup files')
    parser.add_argument('--pilot', action='store_true', help='Pilot mode: migrate only 5 files')
    parser.add_argument('--path', default='.', help='Project root path')
    
    args = parser.parse_args()
    
    migrator = LoguruMigrator(
        dry_run=args.dry_run,
        backup=not args.no_backup
    )
    
    migrator.migrate_project(args.path, pilot_mode=args.pilot)

if __name__ == "__main__":
    main()
```

## Phase 3: Staged Migration Plan (3-4 hours)

### Stage 1: Critical Infrastructure (1 hour)
**Priority Order:**
1. `shared/simple_db.py` - CRITICAL (29 log statements)
2. `shared/logging_config.py` - Create compatibility wrapper
3. `shared/health_check.py`
4. `shared/error_handler.py`
5. `shared/retry_helper.py`

### Stage 2: Core Services (1 hour)
**Main Service Files:**
1. `gmail/main.py` + `gmail/gmail_api.py` + `gmail/storage.py`
2. `pdf/main.py` + all `pdf/ocr/*.py` files
3. `entity/main.py` + all `entity/extractors/*.py`
4. `transcription/main.py` + `transcription/providers/whisper_provider.py`

### Stage 3: Intelligence Services (30 minutes)
1. `search_intelligence/main.py` + related files
2. `legal_intelligence/main.py`
3. `knowledge_graph/main.py` + all knowledge_graph files
4. `summarization/engine.py`

### Stage 4: Infrastructure & Utilities (30 minutes)
1. `infrastructure/pipelines/*.py` (especially orchestrator.py with 29 statements)
2. `infrastructure/documents/*.py`
3. `utilities/embeddings/embedding_service.py`
4. `utilities/vector_store/__init__.py`
5. `utilities/notes/main.py`
6. `utilities/timeline/main.py`

### Stage 5: Scripts & Tests (30 minutes)
1. `tools/scripts/*.py`
2. Test files that use logging

## Phase 4: Testing Strategy (1-2 hours)

### 4.1 Unit Test Compatibility
```python
# Create test helper: tests/loguru_test_helper.py
"""Helper for testing with loguru."""

from unittest.mock import MagicMock
from loguru import logger

def mock_logger():
    """Create a mock logger for testing."""
    mock = MagicMock()
    # Preserve logger interface
    mock.info = MagicMock()
    mock.debug = MagicMock()
    mock.warning = MagicMock()
    mock.error = MagicMock()
    mock.exception = MagicMock()
    mock.bind = MagicMock(return_value=mock)
    mock.contextualize = MagicMock(return_value=mock)
    return mock

# Monkey-patch for tests
def patch_loguru_for_tests():
    """Patch loguru for test compatibility."""
    import sys
    from io import StringIO
    
    # Capture logs in tests
    logger.remove()
    log_capture = StringIO()
    logger.add(log_capture, format="{message}")
    return log_capture
```

### 4.2 Performance Testing
```bash
# Before migration
python tools/scripts/benchmark_logging.py > benchmark_before.txt

# After migration
python tools/scripts/benchmark_logging.py > benchmark_after.txt

# Compare
diff benchmark_before.txt benchmark_after.txt
```

### 4.3 Integration Testing Checklist
- [ ] SimpleDB operations log correctly
- [ ] Gmail sync shows proper debug output
- [ ] PDF processing logs OCR progress
- [ ] Entity extraction logs found entities
- [ ] Search operations log query expansion
- [ ] Error handling shows full tracebacks
- [ ] Log files rotate at 500MB
- [ ] Old logs compress to .zip
- [ ] Sensitive data is redacted in production mode

## Phase 5: Rollback Strategy

### Immediate Rollback (< 5 minutes)
```bash
# Quick revert using git
git checkout pre-loguru-migration

# Or revert the feature branch
git checkout main
git branch -D feature/loguru-migration
```

### Gradual Rollback (if issues in production)
```bash
# Use environment variable to disable loguru
export USE_LOGURU=false

# This uses the compatibility layer in loguru_config.py
# Falls back to standard logging without code changes
```

### File-Level Rollback
```bash
# Restore individual files from backups
for file in $(find . -name "*.py.backup"); do
    original="${file%.backup}"
    mv "$file" "$original"
done
```

## Phase 6: Documentation Updates (30 minutes)

### 6.1 Update CLAUDE.md
Add section about logging:
```markdown
## Logging System

The Email Sync system uses **loguru** for superior logging capabilities:

### Benefits for Developers
- **Simpler API**: Just `from loguru import logger` and use `logger.info()`
- **Better Debugging**: Automatic exception catching with full stack traces
- **Structured Logging**: Built-in JSON serialization for log analysis
- **Automatic Rotation**: Logs rotate at 500MB, compress to .zip
- **Context Tracking**: Use `logger.bind()` to add context to all subsequent logs
- **Thread-Safe**: No configuration needed for concurrent operations

### Configuration
- Main config: `shared/loguru_config.py`
- Environment variables:
  - `LOG_LEVEL`: DEBUG, INFO, WARNING, ERROR
  - `ENVIRONMENT`: Set to 'production' for production safety
  - `USE_LOGURU`: Set to 'false' to use standard logging (migration fallback)

### For Rookie Developers
Instead of complex logging setup:
```python
# OLD WAY (confusing)
import logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
logger.info("Message")

# NEW WAY (simple)
from loguru import logger
logger.info("Message")
```

### Debugging Tips
1. **See all variables in errors**: Loguru shows local variables in tracebacks
2. **Track request flow**: Use `with logger.contextualize(request_id=id):`
3. **Filter logs**: Use `logger.bind(subsystem="gmail")` for filtering
4. **Pretty print objects**: Loguru automatically formats complex objects
```

## Success Metrics

### Quantitative
- [ ] All 67 files migrated
- [ ] All 424 log statements converted
- [ ] All tests pass (100% success rate)
- [ ] Performance within 10% of original
- [ ] Zero runtime errors from logging

### Qualitative
- [ ] Cleaner, more readable log output
- [ ] Better exception tracebacks
- [ ] Easier debugging for new developers
- [ ] Consistent logging across all services
- [ ] Production-safe configuration

## Execution Timeline

### Day 1 (3-4 hours)
1. **Hour 1**: Setup and pilot migration (5 files)
2. **Hour 2**: Migrate critical infrastructure (SimpleDB + shared)
3. **Hour 3**: Migrate core services
4. **Hour 4**: Testing and validation

### Day 2 (2-3 hours)
1. **Hour 1**: Migrate remaining services
2. **Hour 2**: Complete testing suite
3. **Hour 3**: Documentation and final review

## Final Checklist

### Pre-Migration
- [ ] Create feature branch
- [ ] Tag current state
- [ ] Run benchmark tests
- [ ] Backup critical files

### During Migration
- [ ] Run migration script with --dry-run first
- [ ] Migrate SimpleDB first and test thoroughly
- [ ] Use --pilot mode for initial 5 files
- [ ] Test after each stage
- [ ] Keep detailed notes of any issues

### Post-Migration
- [ ] Run full test suite
- [ ] Compare performance benchmarks
- [ ] Test log rotation manually
- [ ] Verify production safety features
- [ ] Update all documentation
- [ ] Create PR with detailed description
- [ ] Have team review changes

## Notes from 1OrchestratorAgent1 Review

Key points addressed:
1. ✅ Corrected file count (67 not 61)
2. ✅ Corrected log statement count (424 not 399)
3. ✅ SimpleDB prioritized as critical
4. ✅ Added missing files (knowledge_graph, summarization)
5. ✅ Enhanced rollback strategy with environment toggle
6. ✅ Added production safety (diagnose=False, sensitive data filtering)
7. ✅ Included performance benchmarking
8. ✅ Created staged migration approach
9. ✅ Added dry-run and pilot modes to migration script
10. ✅ Time estimate revised to 5-7 hours