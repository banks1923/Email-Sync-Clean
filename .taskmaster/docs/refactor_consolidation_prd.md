# Refactor Consolidation PRD (Technical, Test-Driven)

## Objective
Unify code under `lib/` + `cli/` with explicit exceptions, predictable health checks, and deterministic behavior. Remove legacy drift, ensure consistent imports, and maintain a single source of truth for search/DB/vector logic.

## Scope
- lib: `db.py`, `embeddings.py`, `vector_store.py`, `search.py`, `keyword.py`
- CLI: `admin.py`, `info.py`, `search.py`, `view.py`
- MCP: `infrastructure/mcp_servers/search_intelligence_mcp.py`
- Docs: README, VSEARCH guide, health docs
- Tests: smoke + targeted unit tests for search, CLI health/info, MCP

## Non-Goals
- New search features (query expansion, reranking)
- Full repo-wide exception cleanup outside search/CLI/MCP surface

## Workstreams
1) Exceptions: Introduce `lib/exceptions.py` and migrate search/CLI/MCP to explicit errors.
2) Search: Stabilize `semantic_search`, `hybrid_search`, `vector_store_available`.
3) CLI: Fix info/health outputs, remove stale imports, align exit codes.
4) MCP: Decorator API, error mapping, result formatting.
5) Docs: Align examples and commands to current structure.
6) Tests: Add focused tests + repo hygiene checks.

## Acceptance Criteria (Definition of Done)
- Imports reference `lib.*` (no `search_intelligence` paths) in active code.
- No broad `except Exception` in `lib/`, `cli/`, `infrastructure/mcp_servers/` (search-related only).
- `TEST_MODE=1`:
  - `python -m cli admin info` prints stats, exits 0
  - `python -m cli admin health --json` returns JSON, exits 0
- Search:
  - `hybrid_search` raises `VectorStoreError` when vector store is unavailable
  - `semantic_search("")` raises `ValidationError`
  - `find_literal()` uses parameterized SQL and returns results
- MCP:
  - `list_tools` includes search tools
  - `search_smart` returns friendly text and surfaces validation/vector errors as messages

## Test Plan (Gates)
1) Hygiene
   - `rg -n "except Exception" lib/ cli/ infrastructure/mcp_servers/` → 0
   - `rg -n "search_intelligence" -g '!archive/**'` → 0
2) CLI (TEST_MODE=1)
   - `python -m cli admin info` → exit 0
   - `python -m cli admin health --json` → exit 0; has db/vector/embeddings keys
3) Search unit
   - `semantic_search("")` → raises `ValidationError`
   - vector offline → `hybrid_search()` raises `VectorStoreError`
   - DB path errors → `EnrichmentError`
4) MCP
   - `search_smart("query", limit=3)` → header contains "Smart Search Results"
   - invalid query → friendly message with error context

## Milestones
- Phase 1: Stabilize search + MCP + CLI info/health (tests green)
- Phase 2: Docs alignment and examples validated
- Phase 3: CI smoke with `TEST_MODE=1` (no network/model downloads)

## Risks & Mitigations
- Inconsistent imports → add hygiene check gate
- Hidden DB schema mismatches → use SimpleDB helpers only
- Vector availability flakiness → strict probe + TEST_MODE bypass

