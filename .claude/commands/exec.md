
Use when: you’re ready to ship but want built-in safety.
Args: task="{unit of work}" --parallel --tests --docs

/gp-exec task="{unit of work}" --parallel --tests --docs

FLOW
- Break into atomic tasks; track in TODO; assign timeboxes.
- Spin up 2 subagents for grunt work (scan deps, GREP usages, surface risks).
- Prefer libraries/utilities; avoid hand-rolled fixes.

QUALITY
- Isolated components; single responsibility; clean interfaces.
- Import hygiene + usage checks (isort/ruff/import-linter/Bowler).
- Tests where changes land; brief docs + Changelog.md entry.

ALERTING
- Significant problem or design fork → ALERT ME with options, tradeoffs, and recommended choice.
- No silent breaking changes. Stop if approval required.