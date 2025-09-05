Refactor Consolidation Tracker (Technical)

Status: In Progress

Details (from consolidation audit)
- Executive Summary
  - Goal: Stabilize semantic search and CLI after consolidation; remove legacy drift; ensure predictable health reporting and failure modes.
  - Current state: Wrapper hell eliminated; single canonical implementation in `lib/search.py`; CLI/MCP call `lib` directly. A few mismatches remain (vector kwargs, MCP tool registration) causing targeted failures.
  - Priority fixes: `lib/search.py` vector kwargs + availability probe, MCP tool registration, `cli/info.py` attributes/stats, coverage/docs cleanup.
- Repo Map (active components)
  - lib: db.py, embeddings.py, vector_store.py, search.py, keyword.py, timeline/
  - cli: __main__.py, admin.py, info.py, search.py, view.py
  - infrastructure/mcp_servers: search_intelligence_mcp.py (legal MCP slated for later)
  - tests: smoke/integration for search/info/health
  - docs: README, VSEARCH guide, health docs
- Acceptance Criteria (success gates)
  - Search CLI returns exit code 0 in TEST_MODE; fail-fast (non-zero) when vector unavailable for hybrid.
  - Health/Info commands show consistent statuses and exit codes (db, vector, embeddings).
  - `lib/search.py`: explicit exceptions; no broad handlers in search surface.
  - MCP: decorators for list/call; friendly error text; tools present.
- Testing Strategy
  - Fast path: TEST_MODE=1 + SKIP_MODEL_LOAD=1; use mocks; avoid external deps.
  - Integration path: real Qdrant locally; embeddings in gated jobs only.
- Fail-Fast Policy
  - Vector: if probe fails, mark unavailable and abort hybrid; do not silently downgrade.
  - Embeddings: mock health in TEST_MODE; log one hint.
  - CLI: invalid args/schema → exit 2; no silent success.
- Logging Policy
  - stdout: human summaries; JSON via `--json`.
  - logs: detailed diagnostics via loguru; stack traces under DEBUG.
- Timeline
  - T0: Land fixes in lib/search, cli/info, MCP; validate with gates.
  - T+1: Add minimal unit tests and smoke for admin health.

Phases
- Phase 1: Stabilize search, CLI info/health, MCP (core paths)
- Phase 2: Docs alignment (README, VSEARCH, health)
- Phase 3: CI smoke (TEST_MODE=1, SKIP_MODEL_LOAD=1)

Dashboards
- Hygiene
  - Broad handlers (search surface): target 0
  - Legacy imports (`search_intelligence`): target 0
- CLI/MCP
  - Info/Health commands: exit 0 in TEST_MODE
  - MCP list/tools: present; search_smart formatting OK
- Search
  - Validation: empty query raises ValidationError
  - Vector offline → VectorStoreError (hybrid)
  - Enrichment errors surfaced as EnrichmentError

Checklists
- Module Inventory (status per module)
  - lib (Keep)
    - [x] lib/exceptions.py — explicit error hierarchy [Keep]
    - [x] lib/search.py — semantic/hybrid/literal + probes [Keep]
    - [x] lib/vector_store.py — Qdrant + mock, health [Keep]
    - [x] lib/embeddings.py — mock + health [Keep]
    - [x] lib/keyword.py — keyword lane, abbreviations [Keep]
    - [ ] lib/pipelines.py — document chunking pipeline review [Consolidate]
    - [ ] lib/timeline/* — error policy + tests [Consolidate]
    - [ ] lib/backup_restore.py — sanity pass, log/error policy [Consolidate]
  - cli (Consolidate)
    - [x] cli/info.py — stats/attributes fixed [Keep]
    - [ ] cli/admin.py — document stable JSON schema + tests [Consolidate]
    - [ ] cli/search.py — ensure errors map to exit codes [Consolidate]
    - [ ] cli/entity.py — route to lib.*, explicit errors [Rebuild]
    - [ ] cli/legal.py — route to lib.*, explicit errors [Rebuild]
    - [ ] cli/process.py — lib vector pipeline, clear errors [Rebuild]
    - [ ] cli/upload.py — DB interactions via SimpleDB only [Consolidate]
    - [ ] cli/timeline.py — route to lib.timeline, tests [Consolidate]
    - [ ] cli/view.py — align with lib.search outputs [Consolidate]
  - MCP (Keep/Consolidate)
    - [x] infrastructure/mcp_servers/search_intelligence_mcp.py — decorators + messages [Keep]
    - [ ] infrastructure/mcp_servers/legal_intelligence_mcp.py — phase rebuild plan [Rebuild]
  - pdf (Rebuild/Consolidate)
    - [ ] pdf/pdf_processor_enhanced.py — explicit errors, SimpleDB use [Rebuild]
    - [ ] pdf/pdf_storage_enhanced.py — explicit errors, DB APIs only [Rebuild]
    - [ ] pdf/wiring.py — logging/health alignment [Consolidate]
    - [ ] pdf/text_only_processor.py — verify integration [Consolidate]
  - gmail (Rebuild)
    - [ ] gmail/main.py — remove broad handlers, lib DB usage [Rebuild]
    - [ ] gmail/oauth.py — explicit errors + retries [Rebuild]
    - [ ] gmail/gmail_api.py — validation + error mapping [Rebuild]
  - entity (Consolidate)
    - [ ] entity/extractors/dependency_parser.py — robust model checks [Consolidate]
    - [ ] entity/processors/* — confirm SimpleDB flows [Consolidate]
  - summarization (Consolidate/Rebuild)
    - [ ] summarization/engine.py — remove broad handlers, tests [Rebuild]
  - tools/scripts (Consolidate)
    - [ ] tools/scripts/cli/service_locator.py — ensure lib.search mapping [Consolidate]
    - [ ] tools/scripts/refactor_gate.sh — keep gates current [Keep]

- Exceptions
  - [x] `lib/exceptions.py`
  - [x] `lib/search.py` raises specific exceptions
  - [x] MCP maps exceptions to friendly messages
  - [ ] CLI search surfaces clear errors (non-zero exit)

- Hygiene
  - [x] Remove broad `except Exception` in search/MCP surface
  - [ ] Sweep `cli/` for broad handlers in search-related commands
  - [ ] Remove `search_intelligence` imports outside `archive/`

- CLI
  - [x] `cli/info.py` attributes and stats fixed
  - [ ] `cli/admin health --json` stable schema documented
  - [ ] Search commands handle VectorStoreError (exit code policy)

- MCP
  - [x] Decorator-based tool registration
  - [x] `search_smart` formatting includes "Smart Search Results"
  - [ ] Add minimal tool args validation (friendly errors)

- Docs
  - [ ] README examples match working commands
  - [ ] VSEARCH guide uses `python -m cli`
  - [ ] Error Reference: new exceptions + meanings

- Tests
  - [ ] Unit tests for `lib.search` exception paths
  - [ ] MCP message assertions (happy path + errors)
  - [ ] Smoke: CLI info/health under TEST_MODE

Test Stubs (to add now)
- [x] `tests/lib/test_search_exceptions.py`: ValidationError on empty query; VectorStoreError on hybrid when vectors unavailable
- [ ] `tests/mcp/test_search_mcp_messages.py`: search_smart includes header; validation/vector errors surface as plain text

Commands (Local Gates)
- Hygiene: `tools/scripts/refactor_gate.sh hygiene`
- CLI/MCP smoke (TEST_MODE=1): `tools/scripts/refactor_gate.sh smoke`

Notes
- Keep scope tight to search/CLI/MCP. Do not chase non-critical drift elsewhere during this refactor.
