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