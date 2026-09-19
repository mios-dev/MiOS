# Project Artifacts for Autonomous Development

Harness-neutral written memory. `scripts/artifacts.py scaffold` creates missing files from
`assets/templates/` (never overwrites); `artifacts.py bridges` writes the thin pointer files.
Everything is plain Markdown/JSONL committed to git, so it survives branch switches, context
compaction, and a change of harness or vendor.

## 1. Layout

```
AGENTS.md                      constitution + workflow + gates + conventions (canonical; < 32 KiB — Codex cap)
CLAUDE.md                      "@AGENTS.md" + Claude-only notes           (import, not a copy; symlinks need admin on Windows)
GEMINI.md                      pointer + Gemini/Antigravity-only notes
.agents/rules/00-agents.md     pointer (Antigravity; plural dir is current, .agent/ still read; 12 000 chars/rule cap)
.github/copilot-instructions.md pointer (+ .github/instructions/*.instructions.md with applyTo globs)
.cursor/rules/agents.mdc       pointer (alwaysApply: true)
docs/GOALS.md                  north star + objectives/key results
docs/ROADMAP.md                milestones → tasks → decisions
docs/decisions/NNNN-title.md   MADR 4.0 ADRs (docs/adr/ also fine — match the house convention)
docs/DOD.md                    project Definition of Done
docs/runbooks/                 operational procedures
CHECKLISTS.md                  pre-commit / pre-merge / dependency / release / session-end
CHANGELOG.md                   Keep a Changelog 1.1
TASKS.md                       rendered, human view — do not hand-edit
.devloop/tasks.jsonl           machine source of truth for tasks (beads-style, one JSON object per line)
.devloop/LEDGER.md             handoff notes (newest last)
.devloop/run-*/                orchestrator artefacts: normalized lanes, prompts, worker logs, gate logs, reports, patches
```

Specs, when the project uses them, live where the house framework puts them (`specs/`,
`openspec/`, `.kiro/specs/`, `.specify/`); the skill maps rather than duplicates (§4).

## 2. Fields and vocabularies

**Task** (`tasks.jsonl`, enforced by `artifacts.py tasks validate`)

| field | type | notes |
|---|---|---|
| `id` | `T-001` | unique; used in `Task-Id:` commit trailers and lane `task_id` |
| `type` | task \| epic \| bug | |
| `title` | string | one observable sentence |
| `status` | open \| in_progress \| blocked \| done \| cancelled | `done` requires `verification_evidence` |
| `owner` | string | person or lane id |
| `epic`, `goal` | ids | traceability up to `GOALS.md` |
| `depends_on` | ids | DAG; cycles rejected; `tasks next` lists what is unblocked |
| `acceptance_criteria` | list | EARS (`WHEN <condition> THE SYSTEM SHALL <behaviour>`) or Given/When/Then |
| `verification` | object | `positive_cmd`, `negative_control_cmd`, `negative_expect` — the same three the lane gate runs |
| `verification_evidence` | string | exact commands + outcomes, both controls |
| `links` | list | spec, ADR, PR, commit |

**Goal** (`GOALS.md`): `id` (`G-001`), objective, key results, `status` active \| at_risk \| met \| dropped, owner, linked tasks.

**ADR** (MADR 4.0): front matter `status` proposed \| accepted \| deprecated \| superseded-by, `date`, `decision-makers`, `consulted`, `informed`; sections Context and Problem Statement (Y-statement), Decision Drivers, Considered Options, Decision Outcome → **Confirmation** (the gate that fails if the decision is violated), Consequences, Pros/Cons, More Information. File `NNNN-title-with-dashes.md`. Agents create `proposed`; a human flips to `accepted`.

**Milestone** (`ROADMAP.md`): planned \| in_progress \| blocked \| done \| dropped.

## 3. Tooling (`scripts/artifacts.py`)

```
artifacts.py scaffold [--dry-run]           create missing canonical files
artifacts.py bridges                         create pointer files for every harness
artifacts.py tasks validate | render | next  check, render TASKS.md, list unblocked tasks
artifacts.py tasks add --id T-00N --title … [--epic --goal --depends --ac --positive --negative --expect]
artifacts.py tasks set T-00N done --evidence "…"      (done without evidence is refused)
artifacts.py tasks lane T-00N                emit a lane object (v2 schema) from a task's verification block
artifacts.py adr new "<title>"               next NNNN, status: proposed
adapters.py ledger --status … --objective … --done … --next … --blockers … --unverified …
```

The orchestrators close the loop: a lane with `task_id` commits with a `Task-Id:` trailer, and on
merge the host flips the task to `done` with the report path as evidence and re-renders `TASKS.md`.
Every run appends a ledger entry.

## 4. Mapping harness-native artifacts

| Harness artifact | Canonical file |
|---|---|
| Antigravity Implementation Plan | plan/design doc (spec dir) or an ADR when it records a decision |
| Antigravity Task List | `.devloop/tasks.jsonl` → `TASKS.md` |
| Antigravity Walkthrough | `.devloop/run-*/report-*.json` + `CHANGELOG.md` entry |
| Claude Code plan-mode file | plan/design doc |
| Spec Kit `constitution.md` / `spec.md` / `plan.md` / `tasks.md` | `AGENTS.md`+`GOALS.md` / spec / plan / `tasks.jsonl` |
| OpenSpec `proposal.md` + deltas / `design.md` / `tasks.md` | ADR + spec / plan / `tasks.jsonl` |
| Kiro `requirements.md` (EARS) / `design.md` / `tasks.md` | spec / plan / `tasks.jsonl` |
| Ralph `IMPLEMENTATION_PLAN.md` / `PROMPT.md` | `TASKS.md` + `LEDGER.md` / lane prompt |
| beads `.beads/*.jsonl` | already the same shape; point `tasks.jsonl` at it or keep both in sync via `bd` |

## 5. Session discipline (fresh context, state on disk)

1. **Start**: read `AGENTS.md`, last `LEDGER.md` entry, `TASKS.md` (`tasks next`), `git log -10`.
2. **Work** one task; `tasks set <id> in_progress`.
3. **Before compaction or exit**: commit or park (`git diff > .devloop/run-*/parked.patch`), `tasks set`,
   `adapters.py ledger …`. Never rely on the context window to carry state to the next session.
4. **Conflict with a goal/principle** → RFC (SKILL §5), status `blocked`, ledger entry.

## 6. Sync hygiene

- `AGENTS.md` is the only file with substance; every other contract file is a pointer. Validate
  after edits: size < 32 KiB, no secrets, no harness-specific instructions that contradict it.
- Re-render `TASKS.md` after every `tasks.jsonl` change; CI may diff the render to catch drift
  (`artifacts.py tasks render && git diff --exit-code TASKS.md`).
- `CHANGELOG.md` `[Unreleased]` gets a line for every merged lane that changes behaviour.
- ADRs are never edited after `accepted`; write a new one that supersedes.
