---
description: Run the Dev Loop (verify-hard, two-sided controls, worktree lanes) on an objective
argument-hint: <objective, or "lanes:<path/to/lanes.json>" to orchestrate parallel lanes>
allowed-tools: Read, Edit, Write, Glob, Grep, Bash, Agent
---
Load the `dev-loop` skill (SKILL.md — project `.claude/skills/dev-loop/` or `~/.claude/skills/dev-loop/`) and execute its lifecycle (§1) for this objective:

$ARGUMENTS

Orient first: `AGENTS.md`, the last entry of `.devloop/LEDGER.md`, `TASKS.md`; if the canonical artifacts are missing run `python3 scripts/artifacts.py scaffold` (§3). Flip the task in `.devloop/tasks.jsonl` and append a ledger entry before you stop.
Rules: write the Definition of Done first (§2); both controls before claiming done (§6); explicit-path staging only (§12); end with the `devloop_report` JSON block (§13).
If the objective starts with `lanes:`, you are the L0 host: read `references/harness-adapters.md`, then run `sh scripts/devloop.sh <path>` (or `pwsh scripts/DevLoop.ps1 -Lanes <path>` on Windows) via Bash, wait for it, and report from `.devloop/run-*/report-*.json`. Same-vendor lanes may instead be subagents with `isolation: worktree` (always `git -C <worktree>`).
Current state for orientation: !`git status --short | head -30` and !`git log --oneline -10`
