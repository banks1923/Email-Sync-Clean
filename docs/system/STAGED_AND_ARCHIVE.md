Staged vs Archive Strategy

Definitions
- Staged: Temporary home for code pending evaluation/migration to `lib/` or `cli/`.
  - Expectation: Actively reviewed and incrementally pulled into the new interface.
  - Lifetime: Short; contents decrease over time.
- Archive: Deprecated code kept for reference only; not intended to be executed.
  - Expectation: May be removed externally later; no migrations planned.

Process
1) Move not-yet-migrated modules into `staged/` in their current form.
2) Pull working pieces into `lib/` in small, verified steps (with tests/docs updated).
3) Move truly deprecated items to `archive/` for historical reference.

Guidelines
- Avoid wrappers/shims; update callers to the `lib/` surface instead.
- Keep diffs surgical; do not rename broadly or change APIs unnecessarily.
- Update CHANGELOG and docs for each migration wave.

Status (2025-09-04)
- `deprecated/` folder will be folded into `archive/`.
- First wave to populate `staged/`: any remaining legacy helpers under `shared/`, `utilities/`, selective parts of `infrastructure/` not yet ported.
