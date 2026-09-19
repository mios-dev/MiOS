---
name: triage
description: Phantom-failure and flakiness triage for a failing command - separates deterministic bugs from flaky tests and environment/path/cache artefacts by repeated isolated runs, produces a minimal repro script and a TRIAGE_INCIDENT record. Use when a test or build fails, especially "passes locally, fails in CI" or intermittent failures.
argument-hint: "FAILING-COMMAND [--runs N]"
context: fork
agent: dev-loop:triage
allowed-tools: Read, Grep, Glob, Bash
---
# /triage — before you touch code (SKILL §9)

_Paths: `${CLAUDE_SKILL_DIR}/../dev-loop/scripts/` resolves in Claude Code; in other harnesses use `<skills dir>/dev-loop/scripts/` (the shims in `shims/<harness>/` already do)._

Command under test: `$ARGUMENTS`.

1. Walk the phantom runbook in order: path mismatch → stale artefact → worktree `.git` file → earliest root failure → manifest/projection sync.
2. `python3 ${CLAUDE_SKILL_DIR}/../dev-loop/scripts/triage.py "<cmd>" --runs 3` → classification (deterministic | flaky | phantom), repro script, `.devloop/triage_*.json`; record in `docs/` from `templates/TRIAGE_INCIDENT.md`.
3. Flaky is a defect, not noise: find the shared state / order dependence / port collision; never "fix" by retrying or pinning order (§6).
4. Return: classification, root cause hypothesis with evidence, the repro command, and the phantoms dismissed. No fixes in this skill — hand the repro to `/dev-loop`.
