Archived on consolidation to lib/ + cli structure.

Purpose:
- Reduce duplication and legacy paths during refactor.
- Preserve code for later review or selective reintroduction.

How archived:
- Paths mirrored under archive/<original_path>.
- No code changes applied during move.

Reinstate policy:
- If you need any archived module, move it back to its original location and add tests.
- Avoid reintroducing prior duplication; prefer lib/ equivalents.

2025-09-04: Legacy CLI scripts relocated to deprecated/ (staging, not final deletion)
- Moved: tools/scripts/search → deprecated/tools/scripts/search
- Moved: tools/scripts/view_search.py → deprecated/tools/scripts/view_search.py
- Moved: tools/scripts/vsearch_modular → deprecated/tools/scripts/vsearch_modular

Replacement:
- Use unified entry: tools/scripts/vsearch
  - Examples:
    - python tools/scripts/vsearch search "query terms"
    - python tools/scripts/vsearch search literal "BATES-00123"
    - python tools/scripts/vsearch admin health --json
