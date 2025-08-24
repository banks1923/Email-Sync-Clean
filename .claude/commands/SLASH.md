Overview
	1.	/gp-core — full general-purpose guardrails
	2.	/gp-strict — zero-drift, approval-first
	3.	/gp-exec — execution flow with parallel subagents
	4.	/gp-lean — minimal, fast, still safe

⸻

Details

1) /gp-core

Use when: default for any task/thread.
Args: task="{short goal}" --strict --notify --two-agents

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

Why: Balanced coverage; reduces drift and tech debt while keeping velocity.

⸻

2) /gp-strict

Use when: PR gates, risky refactors, production-adjacent work.
Args: scope="{repo|service}" --block --no-bandaids

/gp-strict scope="{repo|service}" --block --no-bandaids

PASS ONLY IF
- Assumptions investigated (2 subagents used) and results cited.
- Libraries leveraged; imports and usages auto-managed (isort/ruff/import-linter/Bowler).
- Tasks are atomic; TODO present; changelog + docs updated.
- Modules are isolated; no oversized files.

INSTANT FAIL
- Bandaid fix without DEBT ticket + remediation plan.
- Silent solution choice on significant issues (must ALERT ME).
- Needless complexity where a library exists.
- Redesign/breaking change without explicit approval.

ACTION
- On FAIL → stop, report options (2–3), impacts, and a recommended path.

Why: Enforces “no drift, no debt” with explicit approval gates.

⸻

3) /gp-exec

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

Why: Execution template that bakes in investigation, parallelism, and alerts.

⸻

4) /gp-lean

Use when: small tasks, quick iterations, still guarded.
Args: task="{small goal}" --notify

/gp-lean task="{small goal}" --notify

RULES
- No bandaids. If forced by time, mark DEBT + follow-up step.
- Always TODO + atomic steps.
- Use libraries first; GREP usages; avoid import thrash.

LIGHT CHECKS
- One small module per concern; no monster files.
- Minimal docstrings + Changelog.md touch.
- Alert on any significant ambiguity; do not decide for the user.

PARALLEL
- If investigation needed, run 2 small subagent probes before proposing the plan.

Why: Minimal overhead while preserving the core protections.

⸻

Recap
	•	Delivered 4 general-purpose slash commands that encode: build-right (no bandaids), explicit alerts/approvals, heavy library reuse, 2-subagent investigation, atomic TODO workflow, and modular/isolated design.

Recommendations
	•	Default to /gp-core on new threads.
	•	Gate risky work with /gp-strict --block.
	•	Use /gp-exec --parallel --tests --docs during implementation.
	•	For tiny fixes, /gp-lean --notify keeps speed without drift.