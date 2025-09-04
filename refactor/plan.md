# One-Shot Refactor Plan (No Shims)

Objective: Flatten and consolidate to a simple, maintainable structure that matches PROJECT_PHILOSOPHY. Remove duplicates and legacy dirs. Single disruptive change with import rewrites and immediate deletions.

## Target Structure (Opinionated)

- services/
  - gmail/
  - pdf/
  - entity/
  - search_intelligence/
- lib/
  - db.py                 # SimpleDB, direct SQLite helpers
  - migrations/           # SQL + minimal runners
  - backup_restore.py     # Admin DB ops
  - embeddings.py         # get_embedding_service, encode, helpers
  - embeddings_batch.py   # Optional batch utilities
  - vector_store.py       # Qdrant ops (store/search/health)
  - search.py             # query/similar/index/reindex (coordinates db + vectors)
  - pipelines.py          # semantic_pipeline + chunk_pipeline
  - timeline/             # timeline modules (kept as a dir to avoid forced merge)
- cli/
  - __main__.py           # Entry: python -m cli
  - db.py
  - embed.py
  - search.py
  - index.py
  - admin.py
- infrastructure/         # as-is
- scripts/                # admin-only: monitoring/, recovery/
- tests/
- docs/
- data/

## Phases

1) Prep
- Branch + tag `pre-consolidation`.
- Add `lib/` and `cli/` scaffolds.
- Land mapping + consolidation tool (dry run).

2) Move
- DB: `shared/db/simple_db.py` → `lib/db.py`; `shared/db/migrations/**` → `lib/migrations/**`; `scripts/database/*` → `lib/backup_restore.py` (merge focused functions only).
- Embeddings/Vector: `utilities/embeddings/*` → `lib/embeddings.py`, `lib/embeddings_batch.py`; `utilities/vector_store/__init__.py` → `lib/vector_store.py`.
- Search: `search_intelligence/basic_search.py` (+ CLI search code) → `lib/search.py`.
- Pipelines: `utilities/semantic_pipeline.py`, `utilities/chunk_pipeline.py` → `lib/pipelines.py`.
- Timeline: `utilities/timeline/**` → `lib/timeline/**`.
- CLI: `tools/scripts/cli/**` → `cli/*.py`; delete `tools/scripts/vsearch`.

3) Imports
- Rewrite imports to the new `lib.*` modules across the repo.

4) Deletions
- Remove `utilities/`, `shared/` (processors, ingestion, db), `tools/` CLI and duplicates, `scripts/data/generate_*embeddings.py`.

5) Validate
- Smoke: gmail/pdf/entity/search_intelligence.
- Run tests and `rg` audit for old import paths.

6) Docs
- Update README and examples (`python -m cli ...`).

## Risks & Guardrails
- Big-bang change: freeze merges; tag allows hard rollback.
- Stop-the-line if any old imports remain after rewrite.
- Keep functions under 35 lines as touched; defer splitting huge modules until after structure lands.

