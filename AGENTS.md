# Repository Guidelines

## Project Structure & Module Organization
- Core modules live at the repo root: `shared/` (DB, utilities), `gmail/` (Gmail ingest), `pdf/` (PDF pipeline), `entity/`, `search_intelligence/`, `embeddings/`, `vector_store/`, etc. Supporting code in `utilities/`, `infrastructure/`, and `scripts/`.
- Additional helpers in `src/` (e.g., `src/chunker`, `src/quality`).
- Tests in `tests/` with patterns `test_*.py`; sample paths: `tests/test_shared_*.py`.
- Assets/data: `data/`, `logs/`, `qdrant_data/` (vector DB), `htmlcov/` (coverage).

## Build, Test, and Development Commands
- `make setup`: Install deps, install Qdrant, run a quick sanity check.
- `make test`: Run fast tests (excludes `-m slow`).
- `make test-all`: Full suite with all markers.
- `make format`: Apply `black`, `isort`, and `docformatter`.
- `make lint`: Run `flake8`, `ruff`, and `mypy` checks.
- `make fix`: Autofix via `ruff` and `autoflake`, then format.
- Runtime ops: `make search QUERY="contract terms"`, `make upload FILE="doc.pdf"`, `make sync`, `make status`.

## Coding Style & Naming Conventions
- Python 3.8–3.11 targeted. Use 4-space indents, 100-char lines.
- Format with `black`; imports via `isort` (black profile). Lint with `ruff` and `flake8`.
- Type-check with `mypy` (strict by default; selective relaxations in `.config/mypy.ini`).
- Naming: `snake_case` for functions/vars, `CapWords` for classes, `UPPER_SNAKE_CASE` for constants. Prefer Google-style docstrings.

## Testing Guidelines
- Framework: `pytest`. Run with `make test` or `pytest -c .config/pytest.ini`.
- Markers include `unit`, `integration`, `slow`, `requires_models`, etc. Example: `pytest -m "unit and not slow"`.
- Coverage outputs to `htmlcov/`; thresholds configured in `pyproject.toml`. Avoid regressions.

## Commit & Pull Request Guidelines
- Commits: imperative mood; prefer scopes (e.g., `feat:`, `fix:`, `docs:`) when clear. Group related changes.
- PRs: concise description, rationale, and screenshots/log snippets when UI/ops change. Link issues. Note test coverage and markers touched.

## Security & Configuration Tips
- Do not commit secrets. Use `.env`/`.envrc` and local credentials (e.g., `credentials.json`).
- Ensure vector DB available: `make setup` then `make status` (Qdrant runs at `localhost:6333`).
- Large/derived data (`qdrant_data/`, `logs/`, `htmlcov/`) stays untracked.
