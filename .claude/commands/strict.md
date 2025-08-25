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
