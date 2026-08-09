<!-- AI-hint: doc-unified-pipeline.md — The Unified MiOS Pipeline (ADR-0012). git=$ROOT unification (doc-git-root-unification.md) · **North star:** one number, one pipeline, curated shared templates, terse logs, offline-self-buildable, zero twin-drift.
     AI-related: usr/share/mios/mios.toml, docs/adr/, AGY-TASKS.md -->
# doc-unified-pipeline.md — The Unified MiOS Pipeline (ADR-0012)

**Status:** accepted (2026-07-25) · **Supersedes fragments of:** ADR-0011 (language/template), the
git=$ROOT unification (doc-git-root-unification.md) · **North star:** one number, one pipeline,
curated shared templates, terse logs, offline-self-buildable, zero twin-drift.

## 1. Problem — scattered scripts + colliding counters cause rippling bugs

MiOS accreted **several independent numbering systems** that do not reconcile, and **duplicated
implementations** ("twins") that silently drift:

| Counter today | Source | Problem |
|---|---|---|
| stage index `NN` | `automation/NN-name.sh` filename (01–98) | the real order; SSOT |
| output label `[38-*]` | hardcoded string in each script's echoes | STALE after renumber (was 38, script is now 98) |
| buildah `STEP N/M` | Containerfile instruction count | unrelated to stage `NN` |
| `build.sh` `STEP N` | in-loop counter | a THIRD count, unrelated to `NN` |
| drift-check number | `tools/generate-gate-index.py` | a FOURTH namespace |

Exemplar bug (2026-07-25): the stage renumber moved `15-render-quadlets.sh → 34`, the sweep updated
bash `97-ssot-lint.sh`, but the **Rust twin** `tools/native/mios-ssot-lint` (a hand-port of the bash)
still opened `15-…` → `FATAL not-found` → diverged from bash → `check_ssot_lint_equivalence` (79)
red-baked the pipeline at 1m18s. Two hand-maintained ports of one logic drifted on a rename.

## 2. Decision — the Unified Pipeline

**D1 — ONE canonical number.** The automation **stage index `NN`** is the single global coordinate.
It IS simultaneously: the OCI layer index, the buildah `STEP`, the log label, and a check's
stage-context. "What is 42?" resolves, from anywhere, to `42-chrony-render` via the registry (D5).

**D2 — one RUN per stage → `STEP N == stage N == OCI layer N`.** The generated Containerfile emits one
`RUN` per numbered stage (not one monolithic loop), so buildah's step counter, the OCI layer, and the
stage index are the same number. Bonus (research wnmoyvhwj): cache granularity — a change in stage 42
invalidates only layers ≥ 42, not the whole build.

**D3 — curated globally-accessible templates.** Shared functions live in `usr/lib/mios/*.sh` (and
`.py`), sourced by every stage/tool. First cornerstone: `usr/lib/mios/log.sh`. These are the MiOS-AI
**tools/skills/recipes** surface: one curated place an agent (or a script) calls, never a re-implementation.

**D4 — labels derive from the filename at runtime.** `mios_log` computes `[NN-name]` from the caller's
own `$0`/`BASH_SOURCE`, so the number is always the stage's real position — **renumber-immune, self-
identifying, terse.** No hardcoded `[38-*]` to drift.

**D5 — one global registry.** `usr/share/mios/reference/pipeline-index.tsv` (generated, extends the
gate-index + names-registry) maps every number → `(kind, name, file, oneline)`. Resolvable from any
log line, tool, or MiOS-AI query. Drift-gated.

**D6 — terse technical logging.** Format `[NN-name] <SEV> <msg>`, `SEV ∈ {OK,WARN,ERR,SKIP,STEP}` (STEP
omitted for plain info). No prose, no ellipses, no emoji, no "Preparing…/…complete/Backing off N s".
`retry 5s` not "Backing off 5 seconds before retry…".

**D7 — offline self-build (self-hosting).** An OS built from its own tree MUST ship its own toolchain.
Rust/cargo, cmake, go, node are provided in a **toolchain-bearing build layer** (`mios-build`);
`91-strip-build-toolchain` strips it **only** from the slim runtime variant. The dev substrate
(podman-MiOS-DEV) provisions the same toolchain so `cargo build` (hence the equivalence gate) runs
offline, locally. MiOS rebuilds MiOS with no network.

**D8 — no twins.** A behavior has ONE source. Where a compiled twin is justified (perf, e.g. the Rust
ssot-lint), it is **generated from** the canonical source or both derive from a shared spec, and an
equivalence gate (check 79 pattern) fails the build on any drift. No hand-kept parallel ports.

## 3. Numbering scheme

```
stage    NN-name.sh              NN ∈ [01,98], lexical-glob order == run order == OCI layer == STEP
label    [NN-name]               derived at runtime from the caller filename (D4)
check    [NN-name:CC]            CC = stable check id within its owning stage (e.g. drift-checks:79)
registry pipeline-index.tsv      NN \t kind \t name \t file \t oneline   (generated, D5)
```

Bands (git-overlay first, then by importance/stability — already landed in the renumber):
`01 overlay · 02 ctx · 05–07 repos/kernel · 10–15 accounts · 20–27 hardware(universal) ·
33–53 services · 56–62 themes · 65–79 AI/desktop/boot · 85–98 finalize/validators`.

## 4. Phased execution (each phase = its own verified bake)

- **P0 ✅** ssot Rust-twin 15→34 (unblock) — commit 09b46786.
- **P1** `usr/lib/mios/log.sh` template + `mios_log` family; drift-gate check "stages source the shared
  logger, no ad-hoc `[NN-` hardcodes"; convert `automation/*.sh` + `usr/libexec/mios/*.sh` echoes.
- **P2** `pipeline-index.tsv` registry generator + resolver `mios-index <N>`; drift-gate.
- **P3** Containerfile-per-stage (D2): `build.sh`/`generate-build-scripts.py` emit one `RUN` per stage;
  `STEP==stage==layer`. Biggest structural change — full bake validation.
- **P4** `mios-build` toolchain layer (rust/cargo/cmake/go/node) + dev-VM provisioning (D7).
- **P5** mios-sys Containerfile core-first + `--mount=type=cache` (dnf/pip/pnpm/go) + multi-stage extraction.
- **P6** kill remaining twins (D8): generate Rust ssot-lint from bash (or shared spec); dedup the two
  `build-mios.ps1`; fold the 3 overlay mechanisms onto `mios-apply` + `root-merge.sh`.

## 5. Constraints (MUST NOT break)

- ssot-lint **bash == Rust byte-identical** (check 79): any log-wording change touches BOTH in lockstep
  until P6 generates one from the other.
- Drift-gate-asserted output strings and the negatives suite (`98-drift-checks.sh`).
- SSOT projection headers `# DO NOT EDIT -- run automation/NN-*.sh` must match their renderer's emit.
- `.gitattributes eol=lf`; never `git add -A` (shared tree); explicit-path staging.
