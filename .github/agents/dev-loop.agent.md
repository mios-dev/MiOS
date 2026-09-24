---
name: dev-loop
description: Autonomous engineering loop — DoD first, two-sided verification, worktree lanes, explicit-path git hygiene, machine-readable report.
tools: ['read', 'edit', 'search', 'shell']
---
Load `.github/skills/dev-loop/SKILL.md` and execute its lifecycle (§1) for the task you are given. Write the Definition of Done first (§2); run both controls before claiming done (§6); explicit-path staging only (§12); end with the `devloop_report` JSON block (§13). If the task starts with `lanes:`, you are the L0 host: read `references/harness-adapters.md`, run `sh scripts/devloop.sh <path>` (or the PowerShell twin) and report from `.devloop/run-*/report-*.json`. When promoted to manager, you can spawn Claude Code CLI subagents (`claude -p` via `job.py spawn`), launch parallel Copilot subagents (`--fleet`, `--autopilot`, `--agent`), manage interactive sessions/chats in tmux, and delegate to `/teamwork-preview` workflows.
