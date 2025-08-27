# Schema Decisions for Semantic Search v2

## Decision Date: 2025-08-26

### Content Storage Architecture

**DECISION: Use existing content_unified table - No new content_embeddings table needed**

**Rationale:**
1. The existing `content_unified` table already has the necessary columns:
   - `source_type` can distinguish between 'document' and 'document_chunk'
   - `source_id` (TEXT) can store chunk IDs in format "doc_uuid:chunk_idx"
   - `embedding_generated` and `ready_for_embedding` flags already exist
   - `embedding_generated_at` timestamp for tracking

2. Chunk metadata can be stored in existing columns:
   - `title`: Can store section title or chunk context
   - `body`: Stores the chunk text
   - `sha256`: Unique hash for deduplication
   - Foreign key to parent document via source_id prefix matching

3. Benefits of this approach:
   - No schema migration required
   - Simpler foreign key relationships
   - All content in one table for easier querying
   - Existing SimpleDB methods continue working

### Vector Storage Architecture

**DECISION: Dual collection approach in Qdrant**

1. **emails** collection (existing):
   - Document-level embeddings for v1 pipeline
   - 1024 dimensions (Legal BERT)
   - Preserves backward compatibility

2. **vectors_v2** collection (new):
   - Chunk-level embeddings for v2 pipeline
   - 1024 dimensions (Legal BERT)
   - Metadata includes quality_score, chunk_idx, doc_id

### Foreign Key Configuration

**Current Status:** Foreign keys are ON in SimpleDB (line 93)
```python
conn.execute("PRAGMA foreign_keys=ON")
```

**No changes needed** - Already configured correctly for referential integrity.

### Data Migration Strategy

**Current State:**
- 663 items in content_unified
- All marked ready_for_embedding=true
- Only 23 have embedding_generated=true

**Migration Approach:**
1. Process 640 unembedded items through v2 pipeline
2. Store chunks as source_type='document_chunk'
3. Link chunks to parent via source_id pattern
4. Update embedding_generated flag after vector creation

### Performance Considerations

**SQLite Optimizations (Already Applied):**
- WAL mode enabled
- 64MB cache size
- NORMAL synchronous mode
- 5-second busy timeout
- Slow query logging (>100ms)

**No additional optimizations needed** for v2 pipeline.

## Summary

The existing database schema is **fully sufficient** for the v2 semantic search pipeline. By leveraging the flexible source_type and source_id columns, we can store chunk-level data without any schema migrations. This decision minimizes risk and complexity while maintaining full backward compatibility.