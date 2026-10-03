<!-- AI-hint: ADR-0028 makes tasks.jsonl at the repo root the only canonical MiOS task list, edited directly; TASKS.md is its rendered documentation plus an operator-overrides block every task tool applies; the retired stores live on as frozen, byte-verified provenance. Supersedes ADR-0026. -->
<!-- AI-related: /usr/share/doc/mios/adr/README.md, /usr/share/doc/mios/adr/0026-global-task-store.md, tasks.jsonl, TASKS.md, /usr/share/mios/mios.toml [tasks.store], /usr/lib/mios/schemas/task-record.schema.json, tools/native/mios-task, automation/98-drift-checks.sh -->
---
adr: 0028
title: One canonical task list, tasks.jsonl, with TASKS.md as its rendered view and operator overrides
status: proposed
date: 2026-10-03
deciders: [operator, ai-pair]
tags: [tasks, backlog, ssot, openai-strict-schema, generated-views, overrides, dev-loop]
laws: [1, 7, 8, 14, 16]
ssot_keys: [tasks.store]
related_ws: [WS-CI, WS-PROCESS]
supersedes: [0026]
superseded_by: []
---

# ADR-0028: One canonical task list, tasks.jsonl, with TASKS.md as its rendered view and operator overrides

## Status

proposed — 2026-10-03. Implements T-1169. The operator's directives, verbatim: "tasks.jsonl is the ONLY
canonical tasks list"; "tasks.md is just documentation(s) and where operator overrides goes". The operator
chose the root path and the MiOS-related-only scope. An agent never flips this record to accepted.

## Context

ADR-0026 merged eleven lists into a generated store, `TASKS.jsonl`, that nobody edited: a task changed in a
live source (`.devloop/tasks.jsonl`, `ROADMAP.md`) and `mios-task migrate` re-merged everything, reading
`-dev-loop`'s backlog and `mios-micro`'s roadmap from sibling checkouts. So MiOS had two task files an agent
could reach for, a third (the dev-loop toolkit's) it depended on, and a store whose check went red whenever
`ROADMAP.md` was regenerated. The dev-loop toolkit now finds a project's task file at `<root>/tasks.jsonl`,
keeps its status dialect, and applies a `TASKS.md` overrides block (JSON lines between
`<!-- overrides:begin -->` and `<!-- overrides:end -->`, under a `# TASKS` banner) on top of it.

## Decision

1. **One list.** `tasks.jsonl` at the repo root is the only canonical MiOS task list. Its path, schema and
   documentation file are declared once, in `mios.toml [tasks.store]`. It is edited directly: by
   `mios-task add/set/claim/release` or by the dev-loop task tools, which resolve the same file. Every line is
   a `mios_task_record` (strict OpenAI `json_schema`), serialized like Python
   `json.dumps(obj, ensure_ascii=False)` with keys in the schema's `required` order, so the toolkit and
   `mios-task` rewrite a record to the same bytes. Statuses are the OpenAI plan words.
2. **TASKS.md is generated.** `mios-task render` writes it from `tasks.jsonl`: `# TASKS`, the overrides
   block, a status summary and one line per task grouped by workstream and epic. No dates, so the render is
   byte-deterministic. Outside the overrides block it is never hand-edited; `mios-task check` fails on any
   difference and names the line.
3. **Operator overrides.** Each line of the block that starts with `{` is `{"id": ..., field: value, ...}`.
   Every task reader (`check`, `render`, `ready/next`, `claim`, and the toolkit's read-only ops) applies the
   fields on top of the record; the last line wins per (id, field). An unknown id, a field the record does
   not have, `id`/`provenance`, or a value the schema refuses fails `check`, naming the TASKS.md line.
   `mios-task overrides fold <id>` moves an override into `tasks.jsonl`.
4. **Retired stores.** `TASKS.jsonl`, `.devloop/tasks.jsonl`, and the lists ADR-0026 absorbed are listed in
   `[tasks.store].retired` and must not exist; a file named like the canonical list (any case) at the root or
   one directory down is a second store. Both fail `check`.
5. **Frozen history, losing no byte.** Every record migrated from a retired list keeps, in
   `provenance.sources`, the verbatim slices it owned (file, kind, offset, length, sha256, and `after`: the
   id of the record owning the slice before it). Concatenated by offset, the slices rebuild each list in
   `[tasks.store].frozen` to the recorded digest (`mios-task source <list>`), so the task gates over the old
   `TASKS.md` and `AGY-TASKS.md` keep running on frozen history. A dropped record leaves a gap whose next
   slice names it; an edited slice fails its digest; `[tasks.store].migrated` counts the carried records.
6. **Scope.** MiOS reads no `-dev-loop` or `mios-micro` file. The operator's classification decisions put
   7 records in the toolkit (they stay in `-dev-loop`) and keep the rest. A MiOS record that only the toolkit
   backlog held (AGY-1692) keeps its toolkit bytes as provenance.

### The migration (one shot, `mios-task migrate-canonical`)

Counted both ways from `TASKS.jsonl` (3491 records) and `.devloop/tasks.jsonl` (115 lines):
store 3491 = kept 3484 + toolkit 7 + devloop-only 0; lane 115 = merged into their store record 115 + lane-only
0; out 3484 lines. Every kept record keeps its id (a second task that reused an id keeps the `#n` form the
store already keyed it by: T-031#2, T-1104#2..T-1107#2) and its status (0 changed: a store record keeps the
store's word, a lane record its lane word). Lane claims are carried as `owner` (lane-b, Codex, claude-code);
the store's free-form "Who" text moves to `provenance.owner_raw`. The 61 `depends_on` edges that formed
cycles move to `related`, each listed in the report, because a cycle cannot be scheduled. Every frozen list
rebuilds byte for byte to the digest the retired store recorded.

## Rationale

- **Edit the list itself.** A generated store that nobody edits needs a second, editable source, which is the
  double-tracking the operator removed. Records with canonical bytes make direct edits safe for both tools.
- **Overrides in the toolkit's format.** One override syntax means the dev-loop tools and `mios-task` see the
  same effective list; a MiOS-only format would make the toolkit ignore the operator.
- **Frozen slices over a separate archive file.** A second file holding history would be a second store to
  keep in step. The slices travel with their records, so dropping a record is detectable and nameable.
- **Rejected:** re-deriving statuses from free prose during the migration (it would change history the
  operator never reviewed); keeping `TASKS.jsonl` as a projection (two files, one stale).

## Consequences

Done when:

1. `mios-task check` exits 0 on the tree: schema, unique ids, resolvable `depends_on`/`epic`, no cycles,
   evidence on every completed record, canonical serialization, no retired or second store, the frozen
   history rebuilds, the migrated count holds, overrides validate, and `TASKS.md` equals its render.
2. `tests/drift-gate-negatives.sh test_task_store` plants a duplicate id, a hand-edited `TASKS.md` task line,
   a dropped record, a retired `.devloop/tasks.jsonl` and an edited frozen slice; each fails naming the plant,
   and a copy of the task files with no sibling checkout beside it passes.
3. The dev-loop toolkit resolves `<root>/tasks.jsonl`, validates it, and reads the overrides block.

Costs:

- `tasks.jsonl` holds the retired lists' text, about 14 MB, smaller than the 28 MB store it replaces.
- The dev-loop toolkit's own `tasks render` also writes `TASKS.md` (in its format, with a date); after it,
  `check_task_store` fails until `mios-task render` runs. Both keep the overrides block verbatim.
- A record the toolkit adds lacks MiOS's extra fields; `mios-task fmt` fills them, and `check` says so.
- `ROADMAP.md` and mios-micro's `ROADMAP.md` stay documents. Their task items were migrated; their later
  edits no longer touch the task list.
