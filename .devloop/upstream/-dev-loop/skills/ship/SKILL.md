---
name: ship
description: Safe trunk-based shipping of a lane or feature branch - pre-flight gates, --no-ff merge with abort-on-conflict, worktree and branch cleanup, CHANGELOG entry, optional tag. Use only after /review passed; ship is user-invoked, never auto-triggered.
argument-hint: "SOURCE_BRANCH [--target main] [--tag vX.Y.Z]"
disable-model-invocation: true
allowed-tools: Read, Bash
---
# /ship — trunk-based merge (SKILL §12)

_Paths: `${CLAUDE_SKILL_DIR}/../dev-loop/scripts/` resolves in Claude Code; in other harnesses use `<skills dir>/dev-loop/scripts/` (the shims in `shims/<harness>/` already do)._

Args: `$ARGUMENTS`.

1. Pre-flight: base tree clean (`git status --porcelain` empty); `/dev-loop:review` verdict PASSED for this branch; both controls recorded in the task (`artifacts.py tasks validate`); `CHECKLISTS.md` pre-merge items ticked.
2. `python3 ${CLAUDE_SKILL_DIR}/../dev-loop/scripts/ship.py <source> [--target main] [--tag vX.Y.Z]` — runs the gates, merges `--no-ff`, aborts and keeps the branch + worktree on conflict, prunes on success, appends `CHANGELOG.md` (`[Unreleased]`).
3. Tagging, pushing, publishing are irreversible: confirm with the operator unless standing authorisation exists in `AGENTS.md`.
4. Close the task (`artifacts.py tasks set T-0NN done --evidence …`), re-render `TASKS.md`, append a ledger entry, report.
