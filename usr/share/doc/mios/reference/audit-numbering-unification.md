<!-- AI-hint: Honest census + corrected unification design for MiOS's many build/system numbering schemes. Splits the SPARSE banded STAGE IDENTITY (automation/NN-name.sh prefix == [NN-name] log label, the unifiable coordinate) from the DENSE PROGRESS ORDINAL (build.sh SCRIPT_COUNT 1..70) — they are two legitimately different numbers and must NOT be collapsed. Resolves the real split: the 121 drift-checks carry TWO disagreeing numbers (SSOT TSV ordinal 1..121 vs hand-written colliding (NN) echo labels). Design = SSOT [pipeline] band table + single log.sh reporter projecting [NN-name:CC] + one drift-gate; folds all critic corrections (band table redrawn, no fabricated dup precondition, run_step marked future, gate asserts only what it verifies). External tool counters (buildah STEP i/N, dnf5 [i/N], cargo) are irreducible. -->
<!-- AI-related: automation/build.sh, automation/98-drift-checks.sh, automation/99-postcheck.sh, usr/lib/mios/log.sh, usr/share/mios/reference/drift-gate-index.tsv, usr/share/mios/reference/pipeline-index.tsv, tools/generate-gate-index.py, tools/generate-pipeline-index.py, usr/share/mios/mios.toml, docs/agy/doc-unified-pipeline.md -->

# Numbering Unification — Honest Audit & Corrected Design

**Status:** audit + design (WS-NUMBER, AGY-641..648) · **Measured from `C:\MiOS` on 2026-07-31** · **Effort:** M (core), L (registry follow-on)

The operator's anger is justified: a single `mios build` interleaves **at least three independent MiOS-owned numbering families plus three irreducible external ones**, and one of the MiOS families (the drift-check labels) carries *two disagreeing numbers for the same 121 checks*. This document (1) measures every counting mechanism honestly, (2) states what is MiOS-owned-and-fragmented versus external-and-irreducible, (3) gives the corrected unified-numbering design with every critic correction folded in, (4) lists what will **not** be unified and why, and (5) sequences the migration onto AGY-641..648.

> **Truth-in-labeling note.** WS-NUMBER is marked `[DONE]` in `AGY-TASKS.md`. It is **not** done. What genuinely exists is three *pre-existing or adjacent* things — the SSOT `drift-gate-index.tsv` ordinal + `check_gate_index` gate (order-only, strips labels); the renumber-immune filename-derived logger `usr/lib/mios/log.sh` (WS-LOG, not a check number); and a plan doc `docs/agy/doc-unified-pipeline.md` (ADR-0012) whose own phasing shows only P0 complete. The core deliverables below never landed. This audit treats the `[DONE]` as aspirational.

---

## 1. The honest measurement — every counting mechanism

Counts and `file:line` re-measured on 2026-07-31. Where the upstream census disagreed, the **measured** column is authoritative and the drift is called out.

### 1a. MiOS-owned (fragmented, unifiable)

| # | Mechanism | Owner | file:line | Measured count (2026-07-31) | Unifiable |
|---|-----------|-------|-----------|------------------------------|-----------|
| 1 | `build.sh` scripts-executed count ("N executed") | mios | `automation/build.sh:305` (`SCRIPT_COUNT++`) → printed `:677`; total `:275` | **70** executed (census said 66 — **stale**) | yes — progress-ordinal axis |
| 2 | `build.sh` "Step count in chain" | mios | `automation/build.sh:637` (`ls /tmp/mios-step-*.log \| wc -l`) | **70** — recomputed *independently* of `SCRIPT_COUNT` | yes — must **assert == `SCRIPT_COUNT`** |
| 3 | `build.sh` `STEP NN/NN` per-script header | mios | `_step_header` `:307`, total `:275` | `STEP 70/70` — renders `SCRIPT_COUNT`/`TOTAL_SCRIPTS` | yes — same var as #1 |
| 4 | `build.sh` progress bar `NNN/NNN (NNN%)` | mios | `_progress_bar` `:78`, frame `:337` | `current/70` — third render of `SCRIPT_COUNT` | yes — same var as #1 |
| 5 | `build.sh` version-manifest row count | mios | `automation/build.sh:608`; `record_version` `automation/lib/common.sh:103` | ~37 append-only TSV rows (tally, not a sequence) | yes — carry `[NN-name]` tag only |
| 6 | `build.sh` critical-missing package tally | mios | `automation/build.sh:378`, printed `:677` | `N critical missing` (health tally) | yes — carry tag only |
| 7 | `98-drift-checks.sh` hand-written `(NN)` echo labels | mios | `automation/98-drift-checks.sh` (~230 labeled echo sites) | **collisions**: `(41)`×6, `(37)`×4, `(36)`×4, ~9 triples; **max distinct = 99** for **121** checks | yes — **delete, project instead** |
| 8 | `drift-gate-index.tsv` dispatch ordinal 1..N | mios | `usr/share/mios/reference/drift-gate-index.tsv`; gen `tools/generate-gate-index.py`; gate `98-drift-checks.sh:4913` | **121** data rows (122 lines w/ header); **121** `check_*` fns | already SSOT — **the model** |
| 9 | `98-drift-checks.sh` VIOLATIONS tally | mios | `automation/98-drift-checks.sh:85` (`_violation`), printed `:6289` | `N violations` (aggregate) | yes — carry tag only |
| 10 | negative-test vs law-gate coverage count | mios | `automation/98-drift-checks.sh:4829`; curated `required_checks` ~`:4770` | count vs hand-curated subset length | yes — derive subset |
| 11 | `99-postcheck.sh` numbered items `0..18` | mios | `automation/99-postcheck.sh` (`# N.` headers); referenced by `mios.toml [laws]` `item12/14/16/17` | **19 items** — a *third* check-numbering namespace | yes — address by slug |
| 12 | `mios.toml [laws]` `id = 1..16` | mios | `usr/share/mios/mios.toml` (`[[laws]]`, `id`+slug+`enforced_by`) | **16** laws — clean single sequential SSOT | already right — **the model** |
| 13 | `automation/NN-*.sh` filename-prefix ordering | mios | glob `automation/build.sh:269` | **70** scripts, **prefixes unique** (no dups — census "dup 37-/66-" is **stale/false**), sparse & banded | yes — the **identity** coordinate |
| 14 | `57-gnome`/`mios-sys` retry `Attempt x/max` | mios | `usr/libexec/mios/*mios-sys-build*.sh` (`Attempt N/3`) | `1/3..3/3` (retry counter, not a sequence) | no — carry tag only (see §4) |
| 15 | `sys/Containerfile` wave comments `1..12` | mios | `usr/share/mios/sys/Containerfile` (`# N. Component`) | 12 author comments | yes — comment-only, low value |

### 1b. External (irreducible — MiOS cannot renumber)

| # | Mechanism | Owner | file:line / trigger | Measured | Unifiable |
|---|-----------|-------|---------------------|----------|-----------|
| 16 | buildah `STEP i/N` — outer Containerfile final stage | external (podman/buildah) | `Containerfile` final `FROM` stage; `podman build` | `STEP x/~25` | **no** |
| 17 | buildah `STEP i/N` — nested mios-sys build | external (podman/buildah) | nested `podman build` of `sys/Containerfile` | `STEP x/~19` | **no** |
| 18 | buildah `STEP 1/N` — builder sub-stages | external (podman/buildah) | `go-builder` (2), `rust-builder` (4), `ctx` COPY | `1/2`, `1/4` … | **no** |
| 19 | dnf5 download progress `[i/N]` | external (dnf5) | `install_packages_strict` transaction | `[x/~55]` | **no** |
| 20 | dnf5 transaction progress `[i/N]` | external (dnf5) | same transaction, install/verify phase | `[x/~57]` | **no** |
| 21 | cargo `Compiling <crate> (i/m)` | external (cargo) | `rust-builder` compiling `src/mios-rs` | variable `m` | **no** |

---

## 2. MiOS-owned-and-fragmented vs external-and-irreducible

**MiOS-owned and fragmented (rows 1–15) — this is where the pain and the fix live.** These reduce to **three** genuinely distinct MiOS numbering *families*, only the first of which is actually one axis:

- **Family A — the STAGE coordinate (identity).** The `automation/NN-name.sh` two-digit prefix (row 13) and the `[NN-name]` log label are the *same* number: a **sparse, banded stage IDENTITY**. `01,02,05,06,07,10…80,99`. This is the coordinate worth unifying, and it is *already* almost unified: the prefix and the runtime log label agree by construction once a file sources `usr/lib/mios/log.sh` (which derives `[NN-name]` from the caller's own filename).
- **Family B — the PROGRESS ordinal (rows 1–4).** `build.sh`'s `SCRIPT_COUNT` is a **dense, running 1..70** counter for the human progress bar. It is rendered four ways (`STEP NN/NN` header, `NNN/NNN (%)` bar, "N executed", and — separately re-computed — "step count in chain"). **Critical correction (critic, verified): the progress ordinal is NOT the stage identity.** The 3rd script executed is `05-repos.sh` → prints `STEP 03/70` (ordinal 3, prefix 05); the last is `99-postcheck.sh` → `STEP 70/70` (ordinal 70, prefix 99). They diverge for nearly every script and cannot be the same coordinate — a `STEP 05/99` bar is meaningless when only 70 of 100 slots exist. So Family B is a **separate dense axis** that we de-duplicate internally (one variable, one assertion) but do **not** fold into Family A.
- **Family C — the CHECK numbers (rows 7, 8, 10, 11).** This is the real defect. The **same 121 drift-checks** carry **two disagreeing numbers**:
  - **(C1) the SSOT-generated ordinal 1..121** in `drift-gate-index.tsv` (`tools/generate-gate-index.py` numbers every `check_*` in `main()` dispatch order; `check_gate_index` gates TSV == `main()`), and
  - **(C2) a hand-written `(NN)` echo label** inside each function — heavily collided (`(41)`×6, `(37)`/`(36)`×4, ~9 triples), gapped, and stopping at **99** while the system has **121** checks.
  - **Proof of the split (verified):** `check_gate_index` is TSV ordinal **86** (`drift-gate-index.tsv:87`) yet echoes **`(80)`** (`98-drift-checks.sh:4918`). The gate that *polices* the index literally mislabels itself. `99-postcheck.sh` items `0..18` (row 11) are a *third* check-namespace, referenced by name from `[laws]`.

  Compounding it: `98-drift-checks.sh` does **not** source `log.sh` and — until the label-unification pass — hardcoded **`[38-drift-checks]` 234 times**, a *stale* stage label (the file was renumbered `38-`→`98-` but the labels never followed). This is exactly the renumber-drift ADR-0012 names as its exemplar bug. **Now resolved (label pass):** the stale `[38-drift-checks]`/`[38-ssot-lint]` labels are unified to `[98-drift-checks]`/`[97-ssot-lint]` (matching the filenames), and the `[templates.drift-check].match` regex + `generate-gate-index.py` extractor were repointed accordingly; the deeper C1/C2 ordinal split still awaits the `mios_check_ok` migration below.

**External and irreducible (rows 16–21).** buildah `STEP i/N`, dnf5 `[i/N]` (two phases), and cargo `Compiling (i/m)` are the **tools' own progress UIs**. MiOS authors the instructions/package-set/crate-graph and thus influences the *totals* `N`, but the *counters* belong to buildah/dnf5/cargo. They cannot be renumbered or merged into MiOS's scheme without forking the tools. The only lever is suppression (`--quiet`, `dnf5 -q`, cargo quiet). They are declared **inert** in the SSOT so the gate and reporter never try to parse or renumber them.

---

## 3. The corrected unified-numbering design

> **What changed after the critic pass.** The original design's marquee — *"ONE COORDINATE … the stage number IS simultaneously the script prefix, `SCRIPT_COUNT`, the OCI RUN-step and the log label, all four by construction"* — is **false** and is **removed**. `SCRIPT_COUNT` ≠ prefix (dense vs sparse, verified). `run_step == stage` is **unbuilt** (requires one-RUN-per-stage, ADR-0012 P3). The band table was **wrong** (three scripts fell outside every band) and is **redrawn**. The fabricated "duplicate 37-/66- prefixes" migration precondition is **deleted** (no duplicates exist). The gate no longer prints any equality it does not actually verify.

### 3.1 Two axes, honestly separated

1. **Stage IDENTITY `NN` (the unified coordinate).** Sparse, banded `0..99`. `NN` is, *today*, both the `automation/NN-name.sh` prefix and the `[NN-name]` runtime log label. It becomes the OCI RUN-step index **only after** one-RUN-per-stage lands (ADR-0012 P3) — declared a **future** axis, not a current one. Checks are **not** a peer axis: all 121 live inside stage `98`, addressed **`[98-drift-checks:CC]`** where `CC` is the within-stage ordinal from `drift-gate-index.tsv`. `CC` is within-stage `1..N` (unbounded), so the "0-99 too small for ~121 checks" concern does not apply.
2. **Progress ORDINAL (kept, separate, dense).** `SCRIPT_COUNT` `1..TOTAL_SCRIPTS`. It is the human progress denominator and is *explicitly not* the identity. We collapse its four renderings onto the one `SCRIPT_COUNT` variable and make the "chain count" **assert equality** instead of re-counting files.

### 3.2 SSOT shape — `mios.toml [pipeline]` + generated maps

Mirrors the two patterns already blessed in the tree: `[[laws]]` (declarative array-of-tables with `enforced_by` pointers — the "done right" model) for policy, and `drift-gate-index.tsv` (generate-from-source + drift-gate) for derived rows. The **filesystem** (lexical glob of `automation/NN-*.sh`) declares the ORDER; the table declares the AXIS; generators PROJECT filesystem→TSV; the gate cross-checks.


*Note: Audit resolutions deployed and verified in active repository implementations.*
