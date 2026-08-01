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

```toml
# ----------------------------------------------------------------------------
[pipeline]
# The MiOS build/system numbering SSOT (ADR-0012, doc-unified-pipeline.md).
# TWO axes, deliberately distinct:
#   * stage IDENTITY  NN  -- sparse/banded 0..99; the automation/NN-name.sh prefix
#                           AND the [NN-name] log label (same number by construction).
#                           Becomes the OCI RUN-step ONLY after one-RUN-per-stage (P3).
#   * progress ORDINAL    -- build.sh SCRIPT_COUNT 1..N; the human progress denominator.
#                           NOT equal to the prefix; rendered from ONE variable.
# The 121 drift-checks are NOT a peer axis: they live inside stage 98 and are
# addressed [98-drift-checks:CC], CC = within-stage id from `check_index`.
space = { min = 0, max = 99 }

# Unified NOW (gate-enforced): prefix == log label.
identity_axes = ["script_prefix", "log_label"]
# Future (NOT yet true; requires one-RUN-per-stage, ADR-0012 P3). The gate does
# NOT assert this until P3 lands -- listed to document intent, not current state.
future_axes   = ["oci_run_step"]
# Separate dense axis -- de-duplicated internally, NOT folded into identity.
progress_axis = "script_count"

label_stage = "[{nn}-{name}]"          # e.g. [42-chrony-render]
label_check = "[{nn}-{name}:{cc}]"     # e.g. [98-drift-checks:86]

map         = "usr/share/mios/reference/pipeline-index.tsv"    # NN<TAB>kind<TAB>name<TAB>file<TAB>oneline
check_index = "usr/share/mios/reference/drift-gate-index.tsv"  # CC<TAB>check_fn<TAB>description
check_stage = 98

reporter  = "usr/lib/mios/log.sh"               # mios_step / mios_check_* derive NN + CC at runtime
generator = "tools/generate-pipeline-index.py"  # extends tools/generate-gate-index.py
gate      = "98-drift-checks.sh:check_pipeline_numbering"

# Band allocation -- OPERATOR-DEFINED. CORRECTED so EVERY real prefix falls in a
# band (critic fix: 54, 80, 99 were previously orphaned; band max was 98).
bands = [
  { range = [1, 1],   purpose = "git-overlay" },
  { range = [2, 2],   purpose = "build-context" },
  { range = [5, 7],   purpose = "repos/kernel" },
  { range = [10, 15], purpose = "accounts" },          # 10-15 FULL (6/6)
  { range = [20, 27], purpose = "hardware-universal" },# 20-27 FULL (8/8)
  { range = [33, 54], purpose = "services" },          # widened 53->54 (coderun-sandbox); 33-53 was FULL (21/21)
  { range = [56, 62], purpose = "themes" },
  { range = [65, 80], purpose = "ai/desktop/boot/distribution" }, # widened 79->80 (80-distribution)
  { range = [85, 99], purpose = "finalize/validators" },          # widened 98->99 (99-postcheck)
]

[pipeline.invariants]
prefix_unique       = true   # no two automation/NN-*.sh share a prefix (verified true today)
prefix_in_band      = true   # every NN falls inside a declared bands range
map_in_sync         = true   # `map` == generator(filesystem)
check_dense         = true   # `check_index` ordinals are exactly 1..N, contiguous
check_derived       = true   # NO hand-written (NN) numeric label survives in stage-98 echoes
label_not_stale     = true   # every [NN-drift-checks] literal == this file's real prefix (98)
single_progress     = true   # build.sh chain-count == SCRIPT_COUNT (no independent recount)
# NOTE: there is deliberately NO invariant asserting SCRIPT_COUNT == prefix or
# run_step == stage. Those are FALSE/unbuilt today; the gate must never claim them.

# Irreducibly external -- declared inert so the gate/reporter never renumber/parse.
[pipeline.external]
counters = [
  { tool = "podman/buildah", pattern = "STEP i/N", scope = "outer ~25, nested mios-sys ~19, go-builder 2, rust-builder 4" },
  { tool = "dnf5",           pattern = "[i/N]",     scope = "download ~55 + transaction ~57" },
  { tool = "cargo",          pattern = "Compiling c (i/m)", scope = "rust-builder crate graph" },
]
suppress_hint = "quiet flags only (dnf5 -q, buildah --quiet, cargo -q). Never parse or fold into the MiOS scheme."
```

### 3.3 Single reporter — `[NN-name]` stage tag + `[NN-name:CC]` check tag

`usr/lib/mios/log.sh` already derives `[NN-name]` from the **caller's own filename** (renumber-immune); adopted by ~65 files. It fixes the 230 stale `[38-*]` labels the instant `98-drift-checks.sh` sources it. We **extend** it with a check sub-reporter that derives `CC` from `drift-gate-index.tsv` by the **calling `check_` function's name** — never hand-typed:

```sh
# Append to usr/lib/mios/log.sh -- the CHECK sub-reporter (ADR-0012 label_check).
# NN comes from mios_tag (caller filename, renumber-immune). CC is looked up from
# the SSOT map by the calling check_ function's NAME, so the (NN) echo labels and
# the TSV ordinals can never disagree again. Migration is mechanical: replace each
#   echo "[98-drift-checks]   (80) msg"   ->   mios_check_ok "msg"
MIOS_CHECK_INDEX="${MIOS_CHECK_INDEX:-/usr/share/mios/reference/drift-gate-index.tsv}"
declare -gA _MIOS_CHECK_ID=()
_mios_load_check_index() {
    [ "${#_MIOS_CHECK_ID[@]}" -gt 0 ] && return 0
    [ -r "$MIOS_CHECK_INDEX" ] || return 1
    local ord fn _rest
    while IFS=$'\t' read -r ord fn _rest; do
        case "$ord" in ''|'#'*) continue ;; esac
        _MIOS_CHECK_ID["$fn"]="$ord"
    done < "$MIOS_CHECK_INDEX"
}
mios_check_id() {                 # CC for nearest check_ fn on the call stack
    _mios_load_check_index || { printf '??'; return; }
    local fn="${1:-}" i
    if [ -z "$fn" ]; then
        for (( i=1; i<${#FUNCNAME[@]}; i++ )); do
            case "${FUNCNAME[i]}" in check_*) fn="${FUNCNAME[i]}"; break ;; esac
        done
    fi
    printf '%s' "${_MIOS_CHECK_ID[$fn]:-??}"
}
mios_check_ok()  { printf '[%s:%s] OK %s\n'  "$(mios_tag)" "$(mios_check_id)" "$*"; }
mios_check_err() { printf '[%s:%s] ERR %s\n' "$(mios_tag)" "$(mios_check_id)" "$*" >&2; }
mios_check_skip(){ printf '[%s:%s] SKIP %s\n' "$(mios_tag)" "$(mios_check_id)" "$*"; }
```

Result: `check_gate_index` now emits `[98-drift-checks:86] OK gate index in sync …` — the `86` fully SSOT-projected, the `(80)` deleted, the stale `38` gone.

### 3.4 The drift-gate — `check_pipeline_numbering()` (AGY-642)

New check in `98-drift-checks.sh`, registered in `main()` (its own `CC` auto-assigned by the TSV, so it dog-foods `mios_check_ok`). It asserts **only what it can verify** — complementing `check_gate_index` (`:4913`), which validates order/description only and *strips* the `(NN)` prefix:

- **(A) prefix uniqueness + range** — no two `automation/NN-*.sh` share a prefix; `0 ≤ NN ≤ 99`. *Passes today* (no dups). There is **no** "renumber the dupes" precondition — that was fabricated.
- **(B) map in sync** — `pipeline-index.tsv == generate-pipeline-index.py(filesystem)`.
- **(C) check ids dense** — `drift-gate-index.tsv` ordinals are exactly `1..N`, contiguous (no gap/dup).
- **(D) check ids derived** *(the AGY-642 done-when)* — any surviving literal `(NN)` numeric label after a `[NN-name]` in a stage-98 echo is a violation; an injected second `(41)` now fails the build because all literal check numbers are forbidden.
- **(E) label not stale** — any `[NN-drift-checks]` literal whose `NN != 98` fails (kills the 230 stale `38`s at the source, not just at runtime).
- **(F) single progress count** — `build.sh` must not re-count the chain via `ls /tmp/mios-step-*.log | wc -l`; it must derive from / assert `== $SCRIPT_COUNT`.
- **(G) band conformance** — every prefix falls inside a declared `[[pipeline.bands]]` range (against the **corrected** table; reds if the table is ever left incomplete).

Closing line — **honest**, asserts only the above:
```
mios_check_ok "pipeline numbering: prefix==log-label unified; check ids dense 1..N & SSOT-derived; single progress count"
```
It does **not** say `script==stage==RUN-step==label`, because the gate does not (and today cannot) verify that.

---

## 4. What will NOT be unified — and why

1. **buildah `STEP i/N` (rows 16–18)** — buildah's per-stage instruction counter. MiOS sets `N` (instruction count) but not the counter. Not renumberable without forking buildah. *Lever: `--quiet`.* (Note: real `STEP == stage == layer` alignment for MiOS's **own** stages comes from ADR-0012 P3 **one-RUN-per-stage** — a MiOS Containerfile-emission change — **not** a claim to renumber buildah. That is future work and is not asserted by the gate.)
2. **dnf5 `[i/55]` download + `[i/57]` transaction (rows 19–20)** — two distinct dnf5-internal phase counters. MiOS owns the package **set** via `[packages.*]`, not the counters. *Lever: `dnf5 -q`.*
3. **cargo `Compiling (i/m)` (row 21)** — upstream toolchain counter; `m` depends on the resolved dependency graph. *Lever: cargo quiet.*
4. **`SCRIPT_COUNT` progress ordinal is NOT folded into the stage identity.** Deliberately kept as its own dense axis (§3.1). Forcing it onto the sparse banded prefix is the exact non-1:1 collapse that burned the operator. We de-duplicate its four renderings and assert the chain-count equality — nothing more.
5. **MiOS-owned QUANTITIES, not sequence namespaces** — retry `Attempt x/3` (row 14), version-manifest rows (row 5), "N critical missing" (row 6), "N VIOLATIONS" (row 9), negative-test coverage (row 10). They keep their own `x/total` meaning; they **must** carry the unified `[NN-name]` tag via the reporter but are **not** put on the `0..99` axis.
6. **`run_step == stage` (OCI RUN-step)** — **not unified now.** Requires one-RUN-per-stage (P3); until then all 70 scripts run inside a single buildah `RUN`, so buildah's `STEP x/25` is unrelated to the 70 MiOS steps. Declared a `future_axis`; the gate never asserts it.

**Band-headroom caveat (operator, decide before adding stages):** the operator bands are near-exhausted — **services `33-53` was 21/21 FULL** (the corrected band widens it to `33-54` to absorb `54-bake-coderun-sandbox`, leaving essentially zero interior headroom), **hardware `20-27` is 8/8 FULL**, **accounts `10-15` is 6/6 FULL**. Because `STEP==stage==layer` (P3) needs unique in-band prefixes, inserting any new service forces a cross-band renumber that the band gate will then fight. Widen the bands (or accept renumbers) *before* the next service lands.

---

## 5. Sequenced migration → AGY-641..648

Ordered so each step is independently shippable and the gate is added **after** the thing it polices is clean (so day-0 stays green). Preconditions fold in the critic must-fixes.

**P0 — preconditions (critic must-fix, no behavior change).**
- Correct the census everywhere downstream: **70** scripts (not 66), **121** checks / **121** TSV rows, **230** stale `[38-*]` labels. Drop the fabricated "duplicate 37-/66- prefixes" narrative.
- Land the **corrected band table** (§3.2) so every real prefix (incl. 54, 80, 99) is in a band *before* gate assertion (G) exists.

**AGY-641 — `build.sh` single progress count.** Change `automation/build.sh:637` from `ls /tmp/mios-step-*.log | wc -l` to print/assert `$SCRIPT_COUNT`. This de-duplicates Family B onto one variable and kills the "66"=="66" (now "70"=="70") coincidence. *Files:* `automation/build.sh`.

**AGY-645 — single reporter (check sub-axis).** Add `mios_check_ok/err/skip` + `mios_check_id` to `usr/lib/mios/log.sh` (§3.3), projecting `CC` from `drift-gate-index.tsv`. *Files:* `usr/lib/mios/log.sh`.

**AGY-643 — renumber-immune stage label.** `source usr/lib/mios/log.sh` in `automation/98-drift-checks.sh`; this alone fixes the 230 stale `[38-*]` → `[98-drift-checks]` at runtime. *Files:* `automation/98-drift-checks.sh`.

**AGY-647 — migrate the check numbers.** Mechanically replace the ~230 hand-labeled echo sites (`echo "[98-drift-checks]   (80) msg"`) with `mios_check_ok "msg"` — deleting every hand-written `(NN)`. Resolves the C1/C2 split permanently (`check_gate_index` will emit `:86`, never `(80)`). *Files:* `automation/98-drift-checks.sh`.

**AGY-644 — pipeline-index registry + generator.** Add `tools/generate-pipeline-index.py` (extends `generate-gate-index.py`) projecting `automation/` → `usr/share/mios/reference/pipeline-index.tsv`; make `generate-gate-index.py`/`check_gate_index` **fail on gap/dup** in `CC` instead of silently stripping. *Honest scope:* this is the larger structural piece; `STEP==stage==layer` (P3 one-RUN-per-stage) remains a follow-on and is **not** part of this step. *Files:* `tools/generate-pipeline-index.py`, `tools/generate-gate-index.py`, `usr/share/mios/reference/pipeline-index.tsv`.

**AGY-642 — the numbering gate.** Add `check_pipeline_numbering()` (§3.4) to `98-drift-checks.sh`; register in `main()`. Assertions A–G; closing message asserts only the verified invariants. Add the negatives that prove it fires (inject a second `(41)`; a stale `[37-drift-checks]`; a `ls|wc` recount; an out-of-band prefix). *Files:* `automation/98-drift-checks.sh`, `tests/drift-gate-negatives.sh`.

**AGY-648 — fold the third namespace.** Address `99-postcheck.sh` items as stage-context `[99-postcheck]` and reference them from `mios.toml [laws]` by **slug**, not by the private `0..18` number. *Files:* `automation/99-postcheck.sh`, `usr/share/mios/mios.toml`.

**AGY-646 — documentation.** This report + update `docs/agy/doc-unified-pipeline.md` (ADR-0012) to the **corrected** framing: identity-vs-progress split; `run_step` marked P3-future; band table redrawn; gate asserts only what it verifies. Update `AGY-TASKS.md` to reflect real status (P0–P2 landed; P3 one-RUN-per-stage aspirational). *Files:* `docs/agy/doc-unified-pipeline.md`, this file, `AGY-TASKS.md`.

**Deferred (genuinely bigger, out of AGY-641..648 core):** ADR-0012 **P3 one-RUN-per-stage** so the OCI RUN-step literally equals the stage — the only path to a true `STEP == stage == layer`, and the only thing that would make `future_axes = ["oci_run_step"]` real. Until then it stays declared-future and unasserted.

---

### Appendix — verification log (2026-07-31, from `C:\MiOS`)

- `ls automation/[0-9][0-9]-*.sh | wc -l` → **70**; `uniq -d` on prefixes → **none** (no duplicate prefixes).
- `drift-gate-index.tsv` → **122** lines = header + **121** rows; `grep -c 'check_.*()'` in `98-drift-checks.sh` → **121**.
- `grep -c '\[98-drift-checks\]'` → **230**; `98-drift-checks.sh` sources `log.sh` → **no**.
- `drift-gate-index.tsv:87` = `86  check_gate_index …`; `98-drift-checks.sh:4918` echoes `(80)` → **split confirmed**.
- `(NN)` label histogram: `(41)`×6, `(37)`×4, `(36)`×4, plus `(87)/(79)/(75)/(61)/(47)/(46)/(44)/(30)`×3; **max distinct label = 99** for 121 checks.
- Out-of-band under the *original* bands: `54-bake-coderun-sandbox`, `80-distribution`, `99-postcheck` → **corrected** in §3.2.
- Band fullness: services `33-53` **21/21**, hardware `20-27` **8/8**, accounts `10-15` **6/6**.
- `build.sh:637` → `ls /tmp/mios-step-*.log 2>/dev/null | wc -l` (independent recount, confirmed); `SCRIPT_COUNT` is dense `1..70` incremented at `:305`, printed `STEP $SCRIPT_COUNT/$TOTAL_SCRIPTS` at `:307`.
