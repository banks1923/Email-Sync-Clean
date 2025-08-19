# External ID Conventions

This document defines the `external_id` conventions for all content types in the Email Sync system. These IDs are used in the business key constraint `UNIQUE(source_type, external_id)` to prevent duplicates and enable idempotent operations.

## Overview

After schema migration, all content uses:
- **Primary Key**: `id` (deterministic UUID5 generated from business key)
- **Business Key**: `(source_type, external_id)` for deduplication
- **Deterministic UUID Generation**: `uuid5(DNS_NAMESPACE, f"{source_type}:{external_id}")`

## UUID Namespace

All deterministic UUIDs MUST use this namespace:
```
UUID_NAMESPACE = UUID('6ba7b810-9dad-11d1-80b4-00c04fd430c8')  # DNS namespace
```

## Content Type Conventions

### Emails (`source_type = "email"`)

**External ID**: Gmail message ID (e.g., `"178a1b2c3d4e5f6g"`)
- **Source**: `message['id']` from Gmail API
- **Format**: Alphanumeric string, typically 16 characters
- **Uniqueness**: Guaranteed unique by Gmail
- **Example**: `external_id = "178a1b2c3d4e5f6g"`
- **Full Business Key**: `("email", "178a1b2c3d4e5f6g")`

**Deterministic UUID Generation**:
```python
content_id = str(uuid5(UUID_NAMESPACE, "email:178a1b2c3d4e5f6g"))
# Results in: "a1b2c3d4-e5f6-5789-abcd-ef0123456789" (deterministic)
```

### PDFs (`source_type = "pdf"`)

**External ID**: SHA-256 hash of file content
- **Source**: `hashlib.sha256(file_content).hexdigest()`
- **Format**: 64-character hexadecimal string
- **Uniqueness**: Guaranteed by cryptographic hash
- **Example**: `external_id = "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"`
- **Full Business Key**: `("pdf", "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855")`

**Deterministic UUID Generation**:
```python
file_hash = hashlib.sha256(pdf_content).hexdigest()
content_id = str(uuid5(UUID_NAMESPACE, f"pdf:{file_hash}"))
```

### Audio Transcripts (`source_type = "transcript"`)

**External ID**: SHA-256 hash of original audio file
- **Source**: `hashlib.sha256(audio_file_content).hexdigest()`
- **Format**: 64-character hexadecimal string
- **Uniqueness**: Guaranteed by cryptographic hash of source audio
- **Example**: `external_id = "d2d2d2d2d2d2d2d2d2d2d2d2d2d2d2d2d2d2d2d2d2d2d2d2d2d2d2d2d2d2d2d2"`
- **Full Business Key**: `("transcript", "d2d2d2d2d2d2d2d2d2d2d2d2d2d2d2d2d2d2d2d2d2d2d2d2d2d2d2d2d2d2d2d2")`

**Special Cases**:
- **OpenAI Whisper**: Include model version in business key for different transcription models
- **Multiple Transcripts**: For same audio with different models, use `f"transcript-{model}:{file_hash}"`

### Email Attachments (`source_type = "attachment"`)

**External ID**: Gmail attachment ID + parent message ID
- **Source**: `f"{attachment_id}@{parent_message_id}"`
- **Format**: `"{attachment_id}@{message_id}"`
- **Uniqueness**: Gmail attachment IDs are unique within a message
- **Example**: `external_id = "ANGjdJ8wGTDtMjX4b5c@178a1b2c3d4e5f6g"`
- **Full Business Key**: `("attachment", "ANGjdJ8wGTDtMjX4b5c@178a1b2c3d4e5f6g")`

**Parent Relationship**:
- Use `parent_content_id` to link to parent email
- Parent content_id = UUID5 of parent email business key

### Notes (`source_type = "note"`)

**External ID**: Timestamp + title hash for user-created notes
- **Source**: `f"{timestamp}_{title_hash}"`
- **Format**: `"{ISO8601_timestamp}_{sha256_first_8_chars}"`
- **Example**: `external_id = "20241201T143000Z_a1b2c3d4"`
- **Full Business Key**: `("note", "20241201T143000Z_a1b2c3d4")`

### Web Content (`source_type = "web"`)

**External ID**: URL hash (for scraped content)
- **Source**: `hashlib.sha256(canonical_url.encode()).hexdigest()`
- **Format**: 64-character hexadecimal string
- **Uniqueness**: One record per unique URL
- **Example**: `external_id = "f5f5f5f5f5f5f5f5f5f5f5f5f5f5f5f5f5f5f5f5f5f5f5f5f5f5f5f5f5f5f5f5"`

## Implementation Guidelines

### 1. UPSERT Operations

Always use the `upsert_content()` method for idempotent operations:

```python
content_id = db.upsert_content(
    source_type="email",
    external_id=message_id,
    content_type="email",
    title=subject,
    content=body,
    metadata=metadata_dict
)
```

### 2. Deterministic ID Generation

Never generate random UUIDs. Always use deterministic generation:

```python
from uuid import UUID, uuid5

UUID_NAMESPACE = UUID('6ba7b810-9dad-11d1-80b4-00c04fd430c8')

def generate_content_id(source_type: str, external_id: str) -> str:
    """Generate deterministic content ID from business key."""
    return str(uuid5(UUID_NAMESPACE, f"{source_type}:{external_id}"))
```

### 3. External ID Validation

Implement validation for each content type:

```python
def validate_external_id(source_type: str, external_id: str) -> bool:
    """Validate external_id format for given source_type."""
    if source_type == "email":
        return bool(re.match(r'^[a-zA-Z0-9]{10,20}$', external_id))
    elif source_type == "pdf":
        return len(external_id) == 64 and all(c in '0123456789abcdef' for c in external_id)
    elif source_type == "transcript":
        return len(external_id) == 64 and all(c in '0123456789abcdef' for c in external_id)
    elif source_type == "attachment":
        return '@' in external_id and len(external_id.split('@')) == 2
    elif source_type == "note":
        return '_' in external_id and len(external_id) > 20
    elif source_type == "web":
        return len(external_id) == 64 and all(c in '0123456789abcdef' for c in external_id)
    return False
```

## Migration Compatibility

### Existing Content

During migration, existing content without business keys gets:
- `source_type = NULL` (will be backfilled)
- `external_id = NULL` (will be backfilled)
- Deterministic IDs generated when business keys are assigned

### Backfill Strategy

1. **Emails**: Use existing `message_id` from emails table
2. **PDFs**: Calculate SHA-256 from stored content or file path
3. **Transcripts**: Use file hash or generate from source audio
4. **Legacy Content**: Generate external_id from existing data patterns

## Database Schema

### Business Key Constraint

```sql
CREATE UNIQUE INDEX content_uniq_business 
ON content(source_type, external_id)
WHERE source_type IS NOT NULL AND external_id IS NOT NULL;
```

### Content Table Schema

```sql
CREATE TABLE content (
    id TEXT PRIMARY KEY,                    -- Deterministic UUID5
    source_type TEXT,                       -- Content source type
    external_id TEXT,                       -- External identifier
    parent_content_id TEXT,                 -- For hierarchical content
    type TEXT NOT NULL,                     -- Content type (legacy)
    title TEXT,
    content TEXT NOT NULL,
    metadata TEXT DEFAULT '{}',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP,
    content_hash TEXT,                      -- SHA-256 of content
    char_count INTEGER DEFAULT 0,
    FOREIGN KEY(parent_content_id) REFERENCES content(id)
);
```

## Error Handling

### Duplicate Detection

The business key constraint will prevent duplicates:
```sql
-- This will succeed the first time
INSERT INTO content (id, source_type, external_id, ...) 
VALUES (?, ?, ?, ...);

-- This will trigger UNIQUE constraint violation the second time
-- Use UPSERT instead:
INSERT INTO content (...) VALUES (...)
ON CONFLICT(source_type, external_id) DO UPDATE SET
    updated_at = CURRENT_TIMESTAMP,
    content = excluded.content;
```

### Validation Errors

- **Invalid external_id format**: Reject at application layer
- **Missing business key**: Allow NULL values for legacy compatibility
- **UUID collision**: Impossible with deterministic generation

## Best Practices

1. **Always use UPSERT**: Never use raw INSERT for content
2. **Validate inputs**: Check external_id format before database operations
3. **Log business keys**: Include source_type:external_id in all logging
4. **Consistent casing**: Use lowercase for source_type values
5. **Document mappings**: When adding new content types, document the external_id convention

## Testing

### Unit Tests Required

- External ID generation for each content type
- UPSERT idempotency (run twice, get same result)
- Business key uniqueness constraint
- Deterministic UUID generation
- External ID validation

### Integration Tests

- Migration of existing content to business keys
- Cross-service content sharing using deterministic IDs
- Qdrant vector synchronization with deterministic IDs

---

**Remember**: These conventions are enforced by the business key constraint and enable idempotent operations across the entire system. Changes to these conventions require database migration.