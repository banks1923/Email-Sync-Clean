/gp-core task="{short goal}" --strict --notify --two-agents

GUARDRAILS
- Build it right, build it once. If you "build it fast," explicitly mark DEBT and plan the real fix.
- ALERT ME on significant problems/unknowns. Do not pick a solution silently.
- USE LIBRARIES: GREP first; prefer proven libs/tools (e.g., isort/ruff/import-linter/Bowler) over hand edits.
- Isolated components with clear interfaces; single responsibility.

EXECUTION
- Always: TODO + Atomic tasks; keep steps small and traceable.
- Pre-plan recon: run two subagents on low-complexity investigation in parallel; validate assumptions before proposing the plan.
- Organize code: no monster files; module per concern.
- Record: update Changelog.md; add docstrings/notes.

STOP RULES
- Any design conflict, breaking change, or redesign → STOP and request explicit approval.
- If time-boxed bandaid is unavoidable → label DEBT, scope impact, propose remediation window.