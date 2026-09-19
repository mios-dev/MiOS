# /dev-loop
Load the `dev-loop` skill (`.cursor/skills/dev-loop/SKILL.md`) and execute its lifecycle (§1) for the objective given with this command.

Orient first: `AGENTS.md`, the last entry of `.devloop/LEDGER.md`, `TASKS.md`; if the canonical artifacts are missing run `python3 scripts/artifacts.py scaffold` (§3). Flip the task in `.devloop/tasks.jsonl` and append a ledger entry before you stop.
Write the Definition of Done first (§2); run both controls before claiming done (§6); explicit-path staging only (§12); end with the `devloop_report` JSON block (§13).
If the objective starts with `lanes:`, you are the L0 host: read `references/harness-adapters.md`, run `sh scripts/devloop.sh <path>` (or `pwsh scripts/DevLoop.ps1 -Lanes <path>`) in the terminal, and report from `.devloop/run-*/report-*.json`.
