# Semantic Search v2 Migration Checklist

## Pre-Migration Verification ✅

### Dependencies (Completed 2025-08-26)
- [x] Install whoosh==2.7.4 for BM25 indexing
- [x] Install sentencepiece==0.1.99 for fallback tokenization
- [x] Install boilerpy3==1.0.6 for OCR preprocessing
- [x] Verify scikit-learn>=1.5.0 installed (found 1.7.1)
- [x] Verify existing: tiktoken, spacy, numpy, scipy
- [x] Update requirements.txt with new dependencies

### Infrastructure (Completed 2025-08-26)
- [x] Verify Qdrant is running (localhost:6333)
- [x] Create vectors_v2 collection (1024D, COSINE)
- [x] Verify existing emails collection intact
- [x] Confirm SQLite foreign keys enabled
- [x] Document schema decisions (no new tables needed)

## Scripts Requiring v2 Compatibility Updates

### Priority 1: Core Pipeline Scripts
- [ ] `utilities/semantic_pipeline.py` - Add chunking integration
- [ ] `infrastructure/pipelines/service_orchestrator.py` - Add v2 operations
- [ ] `tools/scripts/vsearch` - Add --pipeline flag for v1/v2 selection

### Priority 2: Embedding & Vector Scripts
- [ ] `tools/scripts/process_embeddings.py` - Support chunk processing
- [ ] `tools/scripts/sync_vector_store.py` - Sync to vectors_v2
- [ ] `utilities/embeddings/embedding_service.py` - Batch chunk embeddings
- [ ] `utilities/vector_store/vector_store.py` - Dual collection support

### Priority 3: Search & Intelligence Scripts
- [ ] `search_intelligence/main.py` - RRF aggregation logic
- [ ] `tools/scripts/cli/search_handler.py` - v2 search routing
- [ ] `scripts/verify_semantic_wiring.py` - Test v2 pipeline

### Priority 4: Monitoring & Testing
- [ ] `tools/scripts/cli/info_handler.py` - Show v2 statistics
- [ ] `tools/scripts/check_qdrant_documents.py` - Check vectors_v2
- [ ] `tests/test_semantic_pipeline_comprehensive.py` - v2 test cases

## Migration Execution Steps

### Phase 1: Component Implementation (Tasks 22-25)
1. [ ] Implement DocumentChunker (Task 22)
2. [ ] Implement ChunkQualityScorer (Task 23)
3. [ ] Verify schema compatibility (Task 24) ✅ 
4. [ ] Integrate pipeline components (Task 25)

### Phase 2: Search Enhancement (Tasks 26-27)
1. [ ] Implement RRF aggregation (Task 26)
2. [ ] Add feature flags & routing (Task 27)

### Phase 3: Data Migration (Task 28)
1. [ ] Run batch_reembed.py on 640 unembedded items
2. [ ] Monitor progress with checkpointing
3. [ ] Verify chunk quality scores

### Phase 4: Testing & Validation (Tasks 29-30)
1. [ ] Create gold standard queries
2. [ ] Run A/B comparisons
3. [ ] Monitor performance metrics

## Rollback Plan

### Quick Rollback (Feature Flags)
```bash
# Instant revert to v1
export SEARCH_PIPELINE=v1
tools/scripts/vsearch search "query"  # Uses v1
```

### Data Rollback
1. Vectors: Single collection strategy. If needed, recreate `vectors_v2` (1024D, COSINE) and re-embed.
2. Database: Chunks are additive in `content_unified`; original data untouched
3. Code: Git revert to previous commit

## Testing Procedures

### Smoke Tests (After Each Phase)
```bash
# Test v1 still works
tools/scripts/vsearch search "lease" --pipeline v1

# Test v2 pipeline
tools/scripts/vsearch search "lease" --pipeline v2

# Compare results
tools/scripts/vsearch compare "lease"
```

### Integration Tests
```bash
# Full pipeline test
python3 scripts/verify_pipeline.py

# Semantic wiring test
python3 scripts/verify_semantic_wiring.py

# Performance test
python3 tests/test_semantic_pipeline_comprehensive.py
```

## Success Metrics

### Technical Metrics
- [ ] 640 items successfully embedded
- [ ] p95 search latency < 200ms
- [ ] Quality score filtering working (≥0.35)
- [ ] RRF improving relevance scores

### Functional Metrics
- [ ] v1 pipeline still operational
- [ ] v2 pipeline processing chunks
- [ ] Feature flags switching correctly
- [ ] No data loss or corruption

## Notes

- All changes are **additive** - v1 continues working throughout
- Use existing project patterns (SimpleDB, CLI tools, loguru)
- No new frameworks or abstractions needed
- Focus on incremental, testable improvements

## Status

**Current Phase:** Pre-Migration ✅
**Next Step:** Implement DocumentChunker (Task 22)
**Blockers:** None

---

Last Updated: 2025-08-26
Updated By: Task 21 Implementation
