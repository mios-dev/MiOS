---
name: goal
description: Define an engineering goal with explicit stopping conditions, decompose it into tasks, and drive it to done through the dev loop (`/goal dev OBJECTIVE`), or evaluate whether the current goal's stopping conditions hold (`/goal eval`). Use when the user names an outcome to reach rather than a single change.
argument-hint: "[dev|eval|status] OBJECTIVE"
allowed-tools: Read, Grep, Glob, Bash, Agent, Skill
---
# /goal — goal-driven autonomous engineering

_Paths: `${CLAUDE_SKILL_DIR}/../dev-loop/scripts/` resolves in Claude Code; in other harnesses use `<skills dir>/dev-loop/scripts/` (the shims in `shims/<harness>/` already do)._

Goal state lives on disk (`.devloop/goal_state.json`, `docs/GOALS.md`, `.devloop/tasks.jsonl`); never in the context window. Operating procedure: the `dev-loop` skill.

Route on the first word of `$ARGUMENTS`:

- **dev <objective>** — full loop:
  1. `python3 ${CLAUDE_SKILL_DIR}/../dev-loop/scripts/goal.py init "<objective>" --stop "<shell expression that must succeed>"` — stopping condition = the project gate command(s) + `git status --porcelain` empty. Add non-goals (blast-radius boundary) and acceptance criteria in EARS form.
  2. Decompose into tasks: `python3 ${CLAUDE_SKILL_DIR}/../dev-loop/scripts/artifacts.py tasks add --id T-0NN --title … --ac "WHEN … THE SYSTEM SHALL …" --positive … --negative … --expect …`; render `TASKS.md`.
  3. Run the dev loop per task (`/dev-loop <task>`), or for independent tasks generate lanes (`artifacts.py tasks lane T-0NN`) and run them in parallel through the `dev-loop` skill's orchestrator. Same-vendor lanes may be `dev-loop:lane-worker` subagents (worktree-isolated).
  4. After every iteration: `python3 ${CLAUDE_SKILL_DIR}/../dev-loop/scripts/goal.py eval`. Continue while it reports NOT met and the stop conditions in SKILL §12 (same failure set twice, budget, blocker) have not triggered.
  5. Finish with `/dev-loop:review` then `/dev-loop:ship`; append a ledger entry.
- **eval** — `python3 ${CLAUDE_SKILL_DIR}/../dev-loop/scripts/goal.py eval`; report which criteria fail and what the next iteration does.
- **status** (default) — `python3 ${CLAUDE_SKILL_DIR}/../dev-loop/scripts/goal.py status` + `artifacts.py tasks next`.

Rules: a goal is met only when positive AND negative controls hold (SKILL §6); a task that conflicts with `docs/GOALS.md` or `AGENTS.md` is escalated, not executed; end with the `devloop_report` JSON block.
