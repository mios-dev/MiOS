---
description: Run the Dev Loop (verify-hard, two-sided controls, worktree lanes) on an objective
argument-hint: <objective, or lanes:<path/to/lanes.json>>
---
Load the `dev-loop` skill (`.agents/skills/dev-loop/SKILL.md` or `~/.agents/skills/dev-loop/SKILL.md`; also invocable as `$dev-loop`) and execute its lifecycle (§1) for this objective:

$ARGUMENTS

Orient first: `AGENTS.md`, the last entry of `.devloop/LEDGER.md`, `TASKS.md`; if the canonical artifacts are missing run `python3 scripts/artifacts.py scaffold` (§3). Flip the task in `.devloop/tasks.jsonl` and append a ledger entry before you stop.
Write the Definition of Done first (§2); run both controls before claiming done (§6); explicit-path staging only (§12) — note `.git/` is read-only under `workspace-write`, so when you are a lane the host commits; end with the `devloop_report` JSON block (§13).
If the objective starts with `lanes:`, you are the L0 host: read `references/harness-adapters.md`, run `sh scripts/devloop.sh <path>` (or `pwsh scripts/DevLoop.ps1 -Lanes <path>`), and report from `.devloop/run-*/report-*.json`.
