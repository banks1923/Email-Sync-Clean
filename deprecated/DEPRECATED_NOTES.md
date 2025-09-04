This directory contains isolated, not-yet-evaluated or retired scripts.

Intent:
- Stage items away from production paths without implying safe deletion.
- Review for porting, replacement, or final archival/removal.

2025-09-04 moved items (replaced by unified CLI):
- tools/scripts/search → deprecated/tools/scripts/search
- tools/scripts/view_search.py → deprecated/tools/scripts/view_search.py
- tools/scripts/vsearch_modular → deprecated/tools/scripts/vsearch_modular

Replacement commands:
- Use unified entry: `python tools/scripts/vsearch <subcommand>`
  - `search "query"`
  - `search literal "BATES-00123"`
  - `admin health --json`

