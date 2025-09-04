# SQL Query Patterns - v2 Schema Reference

**CRITICAL**: The `emails` and `email_entities` tables NO LONGER EXIST. Any reference will cause immediate failure.

## Core Tables (v2 Schema)

### Primary Tables
- `individual_messages` - Deduplicated email messages (keyed by message_hash)
- `content_unified` - All content with source_type='email_message' for emails
- `entity_content_mapping` - Entities linked to content via content_id

### Key Relationships
```
individual_messages.message_hash <-> content_unified.source_id (when source_type='email_message')
content_unified.source_id <-> entity_content_mapping.content_id
```

## Canonical Query Patterns

### 1. List Recent Emails
```sql
SELECT 
    im.message_hash,
    im.subject,
    im.sender_email,
    im.date_sent,
    cu.created_at,
    cu.quality_score
FROM individual_messages im
JOIN content_unified cu ON cu.source_id = im.message_hash
WHERE cu.source_type = 'email_message'
ORDER BY im.date_sent DESC
LIMIT 50;
```

### 2. Search Emails by Content
```sql
SELECT 
    im.*,
    cu.substantive_text
FROM individual_messages im
JOIN content_unified cu ON cu.source_id = im.message_hash
WHERE cu.source_type = 'email_message'
  AND (im.subject LIKE ? OR cu.substantive_text LIKE ?)
ORDER BY im.date_sent DESC;
```

### 3. Get Email with Entities
```sql
SELECT 
    im.message_hash,
    im.subject,
    ecm.entity_type,
    ecm.entity_text,
    ecm.confidence
FROM individual_messages im
JOIN content_unified cu ON cu.source_id = im.message_hash
LEFT JOIN entity_content_mapping ecm ON ecm.content_id = cu.source_id
WHERE cu.source_type = 'email_message'
  AND im.message_hash = ?;
```

### 4. Find Emails by Legacy Message ID
```sql
-- Legacy message_id is preserved in individual_messages
SELECT 
    im.*,
    cu.body
FROM individual_messages im
JOIN content_unified cu ON cu.source_id = im.message_hash
WHERE im.message_id = ?  -- Legacy Gmail message ID
  AND cu.source_type = 'email_message';
```

### 5. Thread Analysis
```sql
SELECT 
    im.thread_id,
    COUNT(*) as message_count,
    MIN(im.date_sent) as thread_start,
    MAX(im.date_sent) as thread_end
FROM individual_messages im
JOIN content_unified cu ON cu.source_id = im.message_hash
WHERE cu.source_type = 'email_message'
GROUP BY im.thread_id
HAVING COUNT(*) > 1
ORDER BY thread_end DESC;
```

### 6. Emails Ready for Embedding
```sql
SELECT 
    cu.source_id as message_hash,
    cu.substantive_text,
    im.subject
FROM content_unified cu
JOIN individual_messages im ON im.message_hash = cu.source_id
WHERE cu.source_type = 'email_message'
  AND cu.ready_for_embedding = 1
  AND cu.source_id NOT IN (
    SELECT content_id FROM vector_index WHERE collection = 'emails'
  );
```

### 7. Email Deduplication Check
```sql
-- Find duplicate content across different email IDs
SELECT 
    cu.sha256,
    COUNT(*) as occurrences,
    GROUP_CONCAT(im.message_id) as message_ids
FROM content_unified cu
JOIN individual_messages im ON im.message_hash = cu.source_id
WHERE cu.source_type = 'email_message'
GROUP BY cu.sha256
HAVING COUNT(*) > 1;
```

## Migration Helpers

### Convert Legacy Code

**OLD (BROKEN):**
```sql
SELECT * FROM emails WHERE message_id = ?
```

**NEW (CORRECT):**
```sql
SELECT im.*, cu.body
FROM individual_messages im
JOIN content_unified cu ON cu.source_id = im.message_hash
WHERE im.message_id = ?
  AND cu.source_type = 'email_message'
```

**OLD (BROKEN):**
```sql
SELECT * FROM email_entities WHERE message_id = ?
```

**NEW (CORRECT):**
```sql
SELECT ecm.*
FROM entity_content_mapping ecm
JOIN individual_messages im ON im.message_hash = ecm.content_id
WHERE im.message_id = ?
```

## Python Code Patterns

### SimpleDB Usage
```python
from shared.simple_db import SimpleDB

db = SimpleDB()

# Get emails with content
emails = db.fetch("""
    SELECT im.*, cu.substantive_text
    FROM individual_messages im
    JOIN content_unified cu ON cu.source_id = im.message_hash
    WHERE cu.source_type = 'email_message'
    ORDER BY im.date_sent DESC
    LIMIT 10
""")

# Add new email (use add_email_message helper)
message_hash = db.add_email_message(
    sender="user@example.com",
    recipients=["recipient@example.com"],
    subject="Test",
    body="Content",
    date_sent="2024-01-01T12:00:00Z",
    message_id="gmail_message_id_123"
)
```

### Entity Extraction
```python
# Store entities for an email
db.execute("""
    INSERT INTO entity_content_mapping (
        content_id, entity_type, entity_text, 
        start_char, end_char, confidence
    ) VALUES (?, ?, ?, ?, ?, ?)
""", (message_hash, "PERSON", "John Doe", 0, 8, 0.95))
```

## Testing Queries

### Verify No Legacy Tables
```sql
-- This should return 0
SELECT COUNT(*) FROM sqlite_master 
WHERE type='table' AND name IN ('emails', 'email_entities');
```

### Check Data Integrity
```sql
-- No orphaned content_unified records
SELECT COUNT(*) as orphans
FROM content_unified cu
LEFT JOIN individual_messages im ON cu.source_id = im.message_hash
WHERE cu.source_type = 'email_message' 
  AND im.message_hash IS NULL;
```

### Foreign Key Validation
```sql
-- Should fail with FK error
INSERT INTO content_unified (source_type, source_id, title, body, sha256)
VALUES ('email_message', 'fake_hash_xxx', 'Test', 'Test', 'test_sha');
```

## Common Mistakes to Avoid

1. **❌ NEVER**: Reference `emails` table - it doesn't exist
2. **❌ NEVER**: Use `email_messages` (plural) - correct is `email_message`
3. **❌ NEVER**: Join on `message_id` for content - use `message_hash`
4. **❌ NEVER**: Store entities with old `message_id` FK - use `content_id`
5. **✅ ALWAYS**: Include `source_type = 'email_message'` when querying emails
6. **✅ ALWAYS**: Join through `content_unified` for email content
7. **✅ ALWAYS**: Use `message_hash` as the primary key for deduplication

## Performance Indexes

These indexes are already created:
```sql
CREATE INDEX idx_content_unified_source ON content_unified(source_type, source_id);
CREATE INDEX idx_individual_messages_thread ON individual_messages(thread_id);
CREATE INDEX idx_ecm_content ON entity_content_mapping(content_id);
```

## Troubleshooting

### "no such table: emails"
- Use the query patterns above
- The table was permanently deleted

### "FOREIGN KEY constraint failed"
- Ensure message_hash exists in individual_messages first
- Check source_type is exactly 'email_message'

### Finding legacy references
```bash
# Find files still using old tables
grep -r "FROM emails\|email_entities" --include="*.py" .
```

---

**Remember**: Every query is explicit. No views, no adapters, no ORM. The SQL you write is exactly what runs.