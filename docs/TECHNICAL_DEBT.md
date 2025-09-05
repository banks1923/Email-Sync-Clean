# Technical Debt Report

Generated: 2025-01-05

## Summary
Audit of codebase for shims, bandaids, and technical debt found several issues that need cleanup.

## Critical Issues Found

### 1. sys.path Manipulation (HIGH PRIORITY)
**Location**: Multiple CLI files and MCP servers
**Count**: 20 instances
**Pattern**: `sys.path.insert(0, str(Path(__file__).parent.parent.parent))`

Files affected:
- cli/info.py:12
- cli/process.py:11
- cli/search.py:11
- cli/entity.py:14
- cli/upload.py:13
- cli/timeline.py:11
- cli/legal.py:15
- infrastructure/mcp_servers/search_intelligence_mcp.py:14
- infrastructure/mcp_servers/legal_intelligence_mcp.py:75
- entity/main.py:13
- pdf/main.py:17
- summarization/engine.py:17

**Fix Required**: Convert to proper Python package structure with proper imports.

### 2. TODO Comments for Removed Functions (MEDIUM)
**Location**: infrastructure/mcp_servers/legal_intelligence_mcp.py
**Count**: 11 TODO comments
**Issue**: Functions were removed but TODOs left behind

Examples:
- Line 250: `# TODO: _extract_dates_from_document() was removed`
- Line 273: `# TODO: _identify_timeline_gaps() was removed`
- Line 290: `# TODO: _calculate_document_similarity() was removed`
- Line 492: `# TODO: _extract_themes() was removed`
- Line 497: `# TODO: _detect_anomalies() was removed`

**Fix Required**: Implement these functions properly or remove the TODOs.

### 3. Deprecated Code Still Present (LOW)
**Location**: cli/search.py
**Issue**: Deprecated parameters with warnings instead of removal

```python
# Lines 29-47: Deprecated hybrid and mode parameters still accepted
if hybrid is not True:
    warnings.warn("hybrid parameter is deprecated...")
```

**Fix Required**: Remove deprecated parameters entirely in v3.0.

### 4. Broken Test (HIGH)
**Location**: tests/integration/test_advanced_parsing.py:17
**Issue**: `# FIXME: These functions were refactored - test needs updating`

**Fix Required**: Update or remove the broken test.

### 5. Deprecated CLI Commands (LOW)
**Location**: cli/upload.py
**Issue**: Queue-based processing marked as deprecated but still present

```python
def upload_queue():
    """Process all files in upload queue (deprecated - use direct upload)."""
    print("⚠️  Queue-based processing deprecated")
```

**Fix Required**: Remove deprecated queue processing entirely.

## Positive Findings

### Clean Areas
- No HACK, XXX, BUG, or KLUDGE comments found
- No obvious workarounds or temporary fixes
- Exception hierarchy properly implemented (Task 32)
- RRF hybrid search properly implemented without bandaids

### Recent Cleanup Success
Per CHANGELOG.md:
- Removed sys.path manipulation hacks from quality_score.py (line 586)
- All compatibility shims removed from search_intelligence (line 602)
- Replaced deprecated shim in generate_embeddings.py (line 520)

## Recommendations

### Immediate Actions (This Week)
1. Fix broken test in test_advanced_parsing.py
2. Implement or remove TODO functions in legal_intelligence_mcp.py

### Short Term (This Month)
1. Convert all sys.path manipulations to proper package imports
2. Remove deprecated CLI commands in upload.py
3. Remove deprecated parameters from search.py

### Long Term (Next Quarter)
1. Complete migration to proper Python package structure
2. Remove all v2.0 compatibility code after migration period

## Metrics
- Total sys.path hacks: 20
- Total TODO comments: 12
- Deprecated functions: 3
- Broken tests: 1

## Conclusion
While the codebase has some technical debt, it's manageable and not critical. The recent RRF implementation shows good engineering practices without bandaids. The main issue is improper Python imports which should be addressed systematically.