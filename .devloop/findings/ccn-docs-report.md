# ccn-docs — do the reference docs' claims hold against the code?

Lane `ccn-docs` ran as a **nested manager**: a lane that is itself a host. It
**dispatched 4 subagents** (read-only, one per file / claim cluster) over
`usr/share/doc/mios/reference/`, then re-verified the load-bearing findings
itself, because two subagent reports contradicted each other (§6).

- Subagents dispatched: **4** — laws.md, ports.md, pipeline.md, drift-gates.md.
- Manager-run checks: events.md (a fifth file, §5), the reconciliation (§6), and
  independent re-runs of the two strongest subagent claims (§7).
- Owned path: this file only. No repo file was modified; `git status --porcelain`
  was empty before and after every probe, including the mutation probe, which
  mutates **in memory** and never writes to the tree.

Headline: the **numbers** in the SSOT-projected docs are true and gated. The
**prose around them** is where the claims break — one doc's provenance anchors
point at code that does not contain the quoted text, one doc renders a column
header it never fills, and one doc calls hardcoded literals "derived".

---

## S1 (subagent 1) — laws.md: the 16-law table and its named enforcers

- **File read:** `usr/share/doc/mios/reference/laws.md` (52 lines); cross-read
  `usr/share/mios/mios.toml`, `automation/98-drift-checks.sh` (4904 lines),
  `automation/99-postcheck.sh` (657 lines), `src/mios-rs/miosd/src/drift/laws.rs`,
  `TASKS.md`.
- **Claim checked:** "This document is derived directly from
  `usr/share/mios/mios.toml`" — 16 laws with id/slug/applies_to/`enforced_by`,
  plus a 13-row root-exception table whose column header reads "Runs as root
  **because**".
- **Command / code line that settles it:**
  `python3 -c "import tomllib,json;d=tomllib.load(open('usr/share/mios/mios.toml','rb'));print(len(d['laws']['laws']))"`
  → `16`, exit 0; full-dict diff matched rows 1–16 verbatim.
  Enforcer definitions found once each in `automation/98-drift-checks.sh`
  (lines 581, 916, 1009, 1046, 1093, 1158, 1181, 1223, 1335, 1984, 3206, 3216)
  and dispatched from `main()` at `98-drift-checks.sh:3744-3787`, with
  `main "$@"` at `98-drift-checks.sh:4904`. The four `99-postcheck.sh:<TOKEN>`
  references resolve to live `die`-gated checks at `99-postcheck.sh:288-650`.
  Law 15's descriptor is refuted by the repo's own `TASKS.md:11384`;
  the Rust validator skips it at `src/mios-rs/miosd/src/drift/laws.rs:96-98`
  (`if file == "process" { continue; }`). Per-unit justifications exist as inline
  TOML comments at `usr/share/mios/mios.toml:2270-2282`.
- **What the evidence showed:** 16/16 rows match the SSOT exactly. Every
  bash enforcer named in `enforced_by` exists **and is actually called** — not
  defined-and-dead — and all four postcheck tokens are unconditional gates.
  Two defects in the prose layer: (a) Law 15's `enforced_by` names its gates by
  **ordinal** ("checks 22+27"); positions 22 and 27 are today
  `check_cephfs_ssot` and `check_bootstrap_sync`, not a "parity" pair, and
  `TASKS.md:11384` records this as knowingly stale ("Left alone deliberately"),
  while `laws.rs` `continue`s on the `process:` scheme so nothing machine-checks
  the string at all; (b) the root-exception table's "Runs as root **because**"
  column prints the identical placeholder "see `[security.privileged_quadlets]`"
  for all 13 rows, discarding the real per-unit reasons the TOML does carry
  (e.g. "Ceph OSD/MON -- uid 0 for block devices") — the doc understates its
  own source.
- **Verdict:** **VERIFIED** for the 16-law table, the enforcer wiring and the
  13-name root list (commands above). **ASSERTED-ONLY** for Law 15's
  `enforced_by` — the ordinal reference is unbacked and contradicted by
  `TASKS.md`, and the one validator that reads the field skips this scheme.

## S2 (subagent 2) — ports.md: 44 allocations, "(pinned)", and the real consumers

- **File read:** `usr/share/doc/mios/reference/ports.md` (56 lines).
- **Claim checked:** "derived directly from `usr/share/mios/mios.toml`" —
  44 Category/Service/Port rows footed "derived from … `[ports.categories]`",
  three annotated `(pinned)`.
- **Command / code line that settles it:** TOML parse + set-diff of
  `[ports]` keys vs `[ports.categories]`-reconstructed `(cat, service, port)`
  triples vs the 44 parsed table rows — all three sets equal, exit 0.
  `(pinned)` is generator-derived, not hand-typed:
  `usr/libexec/mios/mios-manual:987-988` appends the literal `" (pinned)"` while
  iterating `cat["pinned"]`. Gate wiring: `check_manual_generated` at
  `automation/98-drift-checks.sh:4509-4513`, registered in `main()` at
  `automation/98-drift-checks.sh:3847`.
  Consumers: `usr/share/containers/systemd/mios-llm-light.container:18`
  (`--listen 0.0.0.0:${MIOS_PORT_LLM_LIGHT:-8500}`),
  `usr/lib/systemd/system/mios-agent-pipe.service:49`,
  `usr/share/containers/systemd/mios-pgvector.container:19`, with the fallbacks
  generated into `automation/lib/globals.sh:157,170,1981`.
  Live gates: `render-globals.py --check` → "both resolvers match SSOT (2657
  constants)" exit 0; `render-ports.py --check` → "44 ports derive cleanly from
  14 categories" exit 0; `check-port-fallbacks.py` → "1366 file(s) scanned;
  every `MIOS_PORT_*` literal matches `[ports]`" exit 0;
  `check-ports-bound.py` → "44 port(s): 41 referenced by a consumer, 3
  registered unbound" exit 0.
- **What the evidence showed:** Zero rows added, omitted or numerically wrong
  across 44/44. The three `(pinned)` suffixes are exactly the three keys in the
  SSOT `pinned` maps. The documented value is the value a consumer actually
  gets: each bind site reads `MIOS_PORT_<KEY>` with a *generated* fallback that
  a separate gate diffs against `[ports]`, so these are not Law-7 hardcodes.
  `check_manual_generated` covers this file without naming it, because the
  generator scans every tracked Markdown file for a `MIOS-GEN:` marker instead
  of a filename allowlist — no allowlist hole.
- **Verdict:** **VERIFIED** — every sub-claim confirmed by a command run or a
  code line read; no discrepancy found. The cleanest doc of the five.

## S3 (subagent 3) — pipeline.md: 72 phases, the Fatal column, and execution order

- **File read:** `usr/share/doc/mios/reference/pipeline.md` (84 lines);
  cross-read `Containerfile` (132 lines), `automation/build.sh` (450 lines),
  `usr/share/mios/mios.toml`, `CLAUDE.md`, `tools/generate-pipeline-index.py`.
- **Claim checked:** "derived directly from `usr/share/mios/mios.toml`", footed
  "derived from … `[build.phases].list` (72 phases)", each row asserting a
  script filename, a Fatal yes/no and an Applies scope.
- **Command / code line that settles it:**
  `ls automation/ | grep -E '^[0-9]{2}-.*\.sh$' | wc -l` → 72, set-diffed both
  ways against the 72 script names parsed from the table — both difference sets
  empty, exit 0. `[build.phases].list` carries `ordinal`/`name`/`script`/
  `fatal`/`apply_class`; ordinals 06, 14, 33, 97 match the table verbatim.
  Fatal is really implemented: `automation/build.sh:188-213`
  (`NON_FATAL_SCRIPTS=…`), `build.sh:305-309` (`set +e; … SCRIPT_EXIT=${PIPESTATUS[0]}; set -e`),
  `build.sh:321` (non-fatal → warn, does not increment `SCRIPT_FAIL`).
  Order: `Containerfile:100` runs `01-system-files-overlay.sh`, `Containerfile:104`
  delegates to `automation/build.sh`, and `build.sh:394-437` runs
  **99 → 97 → 98**. `CLAUDE.md:89` vs `ls automation/14-*.sh automation/33-*.sh`.
- **What the evidence showed:** 72/72 script names match on-disk one-to-one in
  both directions — nothing the pipeline runs is missing from the table, and no
  table row names a script that does not exist. The Fatal column is functional,
  not decorative: the 23 `fatal=false` phases are membership-identical to
  `NON_FATAL_SCRIPTS`, which is tolerated-and-warned under an explicit
  `set +e`/`PIPESTATUS` capture. Two real findings: (a) the table's ascending
  97/98/99 tail implies an order the build does not use — `build.sh` runs
  `99-postcheck.sh` **before** `97-ssot-lint.sh` and `98-drift-checks.sh`, and
  the doc gives no hint of it; (b) `CLAUDE.md:89` claims quadlet generation is
  `automation/14-generate-quadlets.sh`, but on disk 14 is
  `14-podman-machine-compat.sh` and generation is `33-generate-quadlets.sh`
  exactly as this doc says — **the doc is right and the contract file is stale**.
  `NON_FATAL_SCRIPTS` also carries one dead entry, `37-aichat.sh`, matching no
  on-disk script.
- **Verdict:** **VERIFIED** for the 72-row table, the SSOT field parity and the
  Fatal mechanics. The subagent additionally returned ASSERTED-ONLY on "derived
  directly / gated", claiming no generator or diff gate exists for this file —
  **I overrode that**: it is wrong, see §6. The undocumented 99→97→98 order
  stands as a genuine documentation gap (subagent-reported; see §7 for what I
  did and did not re-run).

## S4 (subagent 4) — drift-gates.md: the `mios-src` provenance claim is false

- **File read:** `usr/share/doc/mios/reference/drift-gates.md` (24 lines);
  cross-read `tools/check-unit-projection.py`,
  `usr/libexec/mios/test_mios_manual.py`, `usr/lib/mios/mios_comments.py`,
  `usr/libexec/mios/mios-manual`, `src/mios-rs/mios-gate/src/doc_refs.rs`.
- **Claim checked:** the AI-hint's provenance guarantee — "Prose harvested out
  of source comments by `mios-manual harvest`; **each passage carries the
  mios-src anchor that proves which comment it came from**" — behind anchors
  `mios-src:24fe6d8ba72a from tools/check-unit-projection.py:144-150` and
  `mios-src:dfb3a7090eeb from usr/libexec/mios/test_mios_manual.py:4-8`.
- **Command / code line that settles it:**
  `sed -n '144,150p' tools/check-unit-projection.py` → a `tomllib.load` /
  `except OSError` block inside `main()`, **not** the "Hygiene alone cannot
  see…" passage. `sed -n '4,8p' usr/libexec/mios/test_mios_manual.py` →
  `import os/sys/unittest` + `ROOT = …`, **not** the "Unit test suite for the
  mios_comments classifier…" passage. `grep -rn "Hygiene alone cannot see" .`
  excluding the doc → no matches, exit 1; `git log --all -p` over both files
  finds the prose in none of the reachable commits. The hash itself is
  legitimate and re-derivable — `usr/lib/mios/mios_comments.py:472,478`
  (whitespace-normalized lowercase SHA-256, first 12 hex) reproduces both hashes
  from the doc's own text. Neither hash appears in the harvest ledger
  `usr/share/mios/reference/manual-corpus.tsv` (17,696 rows), `grep -c` → 0,
  exit 1. Gate scope: `check_comment_landing`
  (`automation/98-drift-checks.sh:4516-4520`) → `mios-manual landing --check`,
  whose predicate (`tools/drift-checks.py:4444`) iterates **ledger rows** and
  asks whether the doc contains `mios-src:<sha12>`;
  `src/mios-rs/mios-gate/src/doc_refs.rs` contains zero occurrences of
  `mios-src` (`grep -c` → 0, exit 1) and parses only `AI-related:`/`AI-doc:`
  headers and Markdown links.
- **What the evidence showed:** Both cited files exist, but neither cited line
  range contains the quoted prose — and this is not off-by-a-few-lines drift:
  the text is absent from those files' entire current contents and from every
  reachable commit. Re-deriving the hash proves only that the doc is
  self-consistent with itself, which is a textbook Self-Certifying Predicate:
  the subject's own text satisfies the test. The landing gate runs in the wrong
  direction — ledger-row → doc — so a doc anchor absent from the ledger (both of
  these) is invisible to it, and nothing anywhere validates a `mios-src` anchor
  against the source it names. Secondary: `mios-manual` has a real `harvest`
  subcommand but is mode `-rw-r--r--`, so the AI-hint's backticked
  `mios-manual harvest` is not directly runnable.
- **Verdict:** **ASSERTED-ONLY** — and worse than unbacked: the central
  provenance claim is **false**. The anchors prove nothing, and no gate in the
  tree would notice if they drifted further.

## S5 (manager-run, not a subagent) — events.md calls hardcoded literals "derived"

- **File read:** `usr/share/doc/mios/reference/events.md` (24 lines);
  `usr/libexec/mios/mios-manual:1175-1199`;
  `usr/share/mios/postgres/schema-init.sql`.
- **Claim checked:** "This document is derived directly from system event
  definitions and schema files", footed "derived from event schema definitions
  (**12 event(s)**)".
- **Command / code line that settles it:** `_derive_events` at
  `usr/libexec/mios/mios-manual:1179-1186` holds **six event tuples as literals
  in the generator body**, then `mios-manual:1191` scrapes the SQL with
  `re.finditer(r"['\"]([a-z0-9_\-\.:]+)['\"]\s*,\s*--\s*(.+)", text)`.
  That regex matches any quoted string followed by `,` and a `--` comment, which
  is why `usr/share/mios/postgres/schema-init.sql:80`
  (`source text DEFAULT 'agent', -- agent | operator`) and
  `schema-init.sql:645` (`state text DEFAULT 'assigned', -- assigned | completed | stalled`)
  surface in the table as the "event kinds" `agent` and `assigned`, with enum
  alternation strings as their descriptions.
- **What the evidence showed:** 6 of the 12 rows are not event kinds at all —
  `agent`, `assigned`, `global`, `pending`, `user`, `warm` are **column default
  values**, and their Description column is the column's enum comment
  (`agent | operator`, `assigned | completed | stalled`,
  `global | agent:<name> | conversation:<id>`). The remaining 6 real rows are
  hardcoded literals inside the generator, so no part of the table is actually
  derived from "event definitions": half is invented by the generator and half
  is scraped by a regex that measures the wrong property. The "(12 event(s))"
  count is `len(set(events))` — internally consistent, semantically 50% wrong.
  The projection gate cannot catch this, because it compares the doc to the same
  generator's output (§7 Self-Comparison): the file is byte-perfect and the
  content is still false.
- **Verdict:** **ASSERTED-ONLY** — "derived directly from system event
  definitions and schema files" is refuted by the generator's own source; the
  doc documents a regex accident as an event schema.

## §6 — Reconciling two subagents that contradicted each other

S2 reported an active gate (`check_manual_generated` → `mios-manual render
--check`) covering every `MIOS-GEN:` marker. S3 reported, for the same marker
convention, that **no** generator or diff gate exists for its file. Both cannot
be true, so I settled it myself rather than taking either at face value.

S3 was wrong, and its mistake is instructive: it searched `tools/`,
`automation/` and `src/mios-rs/` for `MIOS-GEN:` and concluded absence. The
generator lives at `usr/libexec/mios/mios-manual` — outside all three paths. An
absence proved by a search whose scope excludes the answer is the same
"Empty-Set Pass" defect class this lane is auditing.

Evidence I ran myself:

- `grep -n "_derive_" usr/libexec/mios/mios-manual` → 11 derivers, including
  `_derive_pipeline` at line 1021 and `"pipeline": _derive_pipeline` in the
  `DERIVERS` dispatch at line 1226.
- `usr/libexec/mios/mios-manual:1266-1278` — `cmd_render` iterates
  `_tracked_markdown(root, …)` and skips only files without `MIOS-GEN:`, so
  scope is every tracked Markdown file, not an allowlist.
- `git ls-files --error-unmatch` on `pipeline.md` and `events.md` → exit 0, both
  tracked, therefore both in scope.
- `MIOS_ROOT="$PWD" python3 usr/libexec/mios/mios-manual --root "$PWD" render --check`
  → `derived sections up to date (35 markers)`, exit 0.
- An in-memory parity+mutation probe (scratchpad, writes nothing to the repo)
  that re-derives each section and compares it to the committed interior:

| marker | derived == committed | mutation would be caught | interior lines |
|---|---|---|---|
| `laws` | true | true | 21 |
| `ports` | true | true | 49 |
| `pipeline` | true | true | 77 |
| `events` | true | true | 17 |

So pipeline.md **is** mechanically derived and **is** gated; S3's sub-claim 5 is
struck. Its other findings (72/72 script parity, functional Fatal column, the
99→97→98 order, the stale `CLAUDE.md:89`) are unaffected.

## §7 — Evidence strength: what I re-ran vs. what is subagent-only

Independently re-run by me (manager), with the commands above:

- The four-marker derive-parity + mutation probe, and `render --check` (exit 0).
- `check_manual_generated` body and `main()` registration (`98-drift-checks.sh:4509-4513`, `:3847`).
- `_derive_events` body; both bogus rows traced to `schema-init.sql:80,:645`.
- Both `mios-src` cited line ranges read directly; prose absent tree-wide
  (`grep` exit 1); both hashes absent from the 17,696-row ledger (`grep -c` → 0).
- `tools/drift-checks.py:4444` — the landing predicate's direction.
- `src/mios-rs/mios-gate/src/doc_refs.rs` — zero `mios-src` occurrences (`grep -c` → 0, exit 1).
- `TASKS.md:11384` verbatim; `laws.rs:96-98` `if file == "process" { continue; }`.

**Subagent-reported, NOT re-run by me** — carry these as unverified:

- S1: the 16-row field-by-field TOML diff; the per-enforcer definition/dispatch
  line numbers; the 13-name root-list ordering.
- S2: the three consumer bind sites; the four live gate script runs and their
  printed counts.
- S3: `automation/build.sh:188-213/305-309/321` Fatal mechanics; the 72-vs-72
  set diff; the **99→97→98 execution order**; the dead `37-aichat.sh` entry.
- S4: the `git log --all -p` history sweep; the sha12 re-derivation; the
  `-rw-r--r--` mode note.

## §8 — Verdict summary

| # | File (`usr/share/doc/mios/reference/`) | Claim cluster | Verdict |
|---|---|---|---|
| S1 | `laws.md` | 16-law table + named enforcers | VERIFIED (table, enforcers) / ASSERTED-ONLY (Law 15 "checks 22+27"; empty "because" column) |
| S2 | `ports.md` | 44 allocations, `(pinned)`, consumers | VERIFIED |
| S3 | `pipeline.md` | 72 phases, Fatal column, order | VERIFIED (table, Fatal) / gap: undocumented 99→97→98; `CLAUDE.md:89` stale |
| S4 | `drift-gates.md` | `mios-src` anchors "prove" provenance | ASSERTED-ONLY — claim is false; ungated |
| S5 | `events.md` | "derived from event definitions" | ASSERTED-ONLY — 6/12 rows are SQL column defaults; 6 are generator literals |

The pattern across all five: **the SSOT-projected tables are trustworthy and
gated; the sentences that describe their provenance are not.** Three of the five
docs make a provenance claim (`derived directly from…`, `the anchor proves…`)
that no gate tests, and in two cases the claim is materially false — while every
one of those files passes `render --check` byte-for-byte, because the only gate
compares each doc to the same generator that produced it.

## §9 — Controls for this lane's own deliverable

- **Positive control** — asserts this file is non-empty, carries ≥3 `## `
  sections, contains a verdict token, and names a file under
  `usr/share/doc/mios/reference/`. Run and passed, exit 0.
- **Negative control** — replaces this report with a sectionless, verdictless
  stub carrying this lane's planted sentinel, asserts the plant landed, then
  asserts the gate refuses it; restores the report via `trap … EXIT INT TERM`.
  Run; exited 1 with the sentinel line, and `git status --porcelain` plus a
  `sha256sum` of this file both matched their pre-control values afterwards.
  The sentinel token itself is deliberately **not** written into this report:
  the control's plant-landed assertion is `grep -q <sentinel> <this file>`, so a
  copy of the token living in the prose would let that assertion pass even if
  the plant never wrote — a Self-Certifying Predicate (§7) in the control that
  is supposed to prove the gate can fail. Both controls were re-run after this
  token was removed.
- No `git add` / `commit` / `push` / generator run was performed by this lane.
  The only file written is this report.
