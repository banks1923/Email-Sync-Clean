_This document outlines the development principles and implementation details for the Gmail service._

# Gmail Service

Gmail API integration for email synchronization with streaming batch operations.

## Architecture Principles

### Hard Limits
- **File Size**: Target 450 lines for new files; existing working files guided by functionality
- **Function Size**: Maximum 30 lines per function
- **Service Independence**: No imports from other services
- **Single Responsibility**: Each file has one clear purpose

### Anti-Patterns (NEVER DO)
- **No Singletons**: Direct instantiation is fine
- **No Factories**: Use if/else for 2-3 choices
- **No Abstract Base Classes**: Unless Python stdlib requires it
- **No Dependency Injection**: Just import and use
- **No Manager of Managers**: One level of management max
- **No Complex Patterns**: This is a hobby project for ONE user

### Good Patterns
- **Simple Functions**: Input → Process → Output
- **Direct Imports**: `from module import function`
- **Flat Structure**: Avoid deep nesting
- **Clear Names**: `get_email()` not `EmailRetrievalManager`

## Quick Commands

```bash
# Sync emails (uses streaming batch)
scripts/vsearch sync-gmail

# Check sync status
scripts/vsearch gmail-stats
```

## Architecture

- **GmailService** (`main.py`) - Main service interface with streaming sync and **advanced email parsing**
- **GmailAuth** (`auth.py`) - OAuth2 authentication
- **GmailAPI** (`api.py`) - Gmail API wrapper
- **EmailStorage** (`storage.py`) - SQLite storage with batch operations
- **Advanced Parsing Modules** (2025-08-22):
  - `shared/email_parser.py` - Individual message extraction from email threads
  - `shared/thread_manager.py` - Thread reconstruction and timeline analysis
  - `shared/email_cleaner.py` - HTML cleaning and content normalization

## Sync Modes

### Advanced Email Parsing (Default - Recommended) 
**NEW (2025-08-22)**: Individual message extraction from email threads
```python
# Extract individual messages from threads with legal evidence preservation
result = service._process_threads_advanced(threads_grouped)
```
- **Features**: Extracts individual quoted messages from email threads
- **Legal Evidence**: Preserves harassment signatures for evidence (e.g., "Stoneman Staff")
- **Thread Reconstruction**: Maintains relationships for chronological timeline analysis
- **Pattern Detection**: Automated detection of ignored messages and harassment patterns
- **Deduplication**: SHA256 includes sender/date for evidence preservation

### Streaming Batch (Legacy - Still Available)
**Legacy (2025-08-15)**: Reliable sync for large email volumes
```python
# Process in 50-email chunks, save immediately
result = service.sync_emails(max_results=500, batch_mode=True)
```
- **Performance**: ~50 emails/minute
- **Reliability**: Saves progress even if interrupted
- **Memory**: Low memory usage (50 emails at a time)
- **Use for**: Basic sync without advanced parsing

### Incremental Sync
```python
# Uses Gmail History API for efficient updates
result = service.sync_incremental(max_results=500)
```
- **Falls back** to full sync if no history available
- **Efficient** for regular updates
- **Tracks** last sync state

### Single Email Mode
```python
# One-by-one processing for small batches
result = service.sync_emails(max_results=50, batch_mode=False)
```
- **Use for**: Small batches (<50 emails), debugging
- **Note**: Not deprecated - valid for smaller syncs

## Configuration

### Sender Filters
Configured in `gmail/config.py`:
```python
self.preferred_senders = [
    "jenbarreda@yahoo.com",
    "518stoneman@gmail.com",
    "sally@lotuspropertyservices.net",
    "grace@lotuspropertyservices.net",
    "gaildcalhoun@gmail.com",
    # ... other legal contacts
]
```

### Gmail API Setup
1. Get credentials from Google Cloud Console
2. Save as `.config/credentials.json`
3. Run initial auth flow

## API Examples

```python
from gmail.main import GmailService

service = GmailService()

# Streaming sync with sender filters (default)
result = service.sync_emails(use_config=True, max_results=500, batch_mode=True)

# Incremental sync (recommended for regular updates)
result = service.sync_incremental(max_results=500)

# Manual query
result = service.sync_emails(
    query="from:specific@email.com",
    max_results=100,
    batch_mode=True
)

# Check results
if result['success']:
    print(f"Synced {result['processed']} emails")
    print(f"Duplicates: {result['duplicates']}")
```

## Database Schema

### emails table
```sql
CREATE TABLE emails (
    id INTEGER PRIMARY KEY,
    message_id TEXT UNIQUE NOT NULL,
    subject TEXT NOT NULL,
    sender TEXT NOT NULL,
    recipient_to TEXT,
    content TEXT,
    datetime_utc DATETIME,
    content_hash TEXT UNIQUE,  -- SHA-256 for deduplication
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
```

### sync_state table
```sql
CREATE TABLE sync_state (
    account_email TEXT PRIMARY KEY,
    last_history_id TEXT,
    last_sync_time DATETIME,
    sync_status TEXT DEFAULT 'idle',
    messages_processed INTEGER DEFAULT 0,
    -- ... additional tracking fields
);
```

## Performance Characteristics

- **Streaming Sync**: ~50 emails/minute, reliable for 500+ emails
- **Memory Usage**: <50MB (processes 50 emails at a time)
- **Deduplication**: SHA-256 content hashing prevents duplicates
- **Error Handling**: Continues processing if individual emails fail

## Troubleshooting

### Common Issues

1. **"file_cache is only supported with oauth2client<4.0.0"**
   - Warning only, sync continues normally

2. **Timeout on large syncs**
   - Fixed with streaming batch mode (50 emails/chunk)
   - Use `batch_mode=True` (default)

3. **No emails synced**
   - Check sender filters in `config.py`
   - Verify Gmail API permissions
   - Check logs in `logs/gmail_service_YYYYMMDD.log`

### Logs
```bash
# View sync logs
tail -f logs/gmail_service_$(date +%Y%m%d).log

# Check for errors
grep -i error logs/gmail_service_*.log
```

## Testing

```bash
# Test small sync
python3 -c "
from gmail.main import GmailService
service = GmailService()
result = service.sync_emails(max_results=10, batch_mode=True)
print(result)
"

# Unit tests
pytest tests/gmail/
```

## Recent Changes

### 2025-08-22: Advanced Email Parsing Integration 🧵
- **MAJOR FEATURE**: Individual message extraction from email threads
- **Added**: QuotedMessage dataclass for structured message representation
- **Added**: ThreadService for conversation grouping and timeline reconstruction
- **Added**: Legal evidence preservation (harassment signature detection)
- **Added**: `_process_threads_advanced()` method for thread processing
- **Integration**: Full integration with shared parsing modules
- **Testing**: Comprehensive test suite with real data validation
- **Result**: 3 individual messages extracted, 2 harassment signatures detected

### 2025-08-15: Streaming Batch Sync
- **Fixed**: Timeout issues with large email volumes
- **Added**: Streaming batch mode (50 emails/chunk)
- **Improved**: Reliability for 500+ email syncs
- **Performance**: ~2x faster, uses 90% less memory