<!-- AI-hint: ADR-0025 declares the core MiOS profile once in mios.toml [profiles]; every image kind (OCI, WSL2, devcontainer, cloud projection, Codespace) is the root pipeline run under a profile, and the devcontainer Containerfile becomes a rendered thin shim over it. -->
<!-- AI-related: usr/share/mios/mios.toml [profiles] [packages.devcontainer] [build.phases] [variants.entries.mios-dev] [bootstrap.sync], Containerfile, .devcontainer/Containerfile, automation/build.sh, automation/lib/packages.sh, src/mios-rs/mios-build/src/lib.rs, tools/native/mios-resolver, usr/libexec/mios/seed-db-config.py, tools/drift-checks.py -->
---
adr: 0025
title: One pipeline, one core profile - every MiOS image is the same system
status: proposed
date: 2026-09-26
deciders: [operator, ai-pair]
tags: [profiles, devcontainer, cloud, pipeline, ssot, projection, drift-gate, pgvector]
laws: [1, 2, 7, 8, 9, 12, 14, 15, 16]
ssot_keys: [profiles, packages.devcontainer, build.phases, variants.entries, bootstrap.sync]
related_ws: [WS-LANG]
supersedes: []
superseded_by: []
---

# ADR-0025: One pipeline, one core profile - every MiOS image is the same system

## Status

proposed — 2026-09-26. Design only: no lane below is implemented by this
record. Q1, Q3 and Q4 were decided by the operator (see "Operator decisions");
Q2 is still open.

## Context

The operator principle (-dev-loop `AGENTS.md:159-166`): every MiOS image — a
devcontainer, the cloud-session projection, the WSL2 dev machine, a Codespace,
an OCI artifact — is the same full MiOS system built by the one SSOT-driven
pipeline, not a toolchain image with its own package list. Under a storage
limit the same pipeline yields the core first and the rest degrades open.

### What the tree says today (read, with citations)

- **R1. Two image recipes.** The root `Containerfile` builds `FROM ${BASE_IMAGE}`
  (`Containerfile:3`, default `ghcr.io/ublue-os/ucore-hci:stable-nvidia`, the
  same value as `mios.toml:5996` `[image].base`), compiles the native binaries in a
  `rust-builder` stage (`Containerfile:21-40`), runs `automation/build.sh`
  (`Containerfile:107`) and ends `ostree container commit` + `bootc container lint`
  (`Containerfile:133-134`). `.devcontainer/Containerfile` is a separate recipe
  `FROM registry.fedoraproject.org/fedora:44` (`.devcontainer/Containerfile:22`)
  that runs **no** automation stage: it stages a handful of SSOT files
  (`:31-58`), dnf-installs one section (`:62-67`), adds npm globals (`:69`), the
  agent venv (`:71-74`), code-server (`:77-89`), a user (`:91-94`) and helpers
  (`:98-101`).
- **R2. The dev package list is its own list.** `[packages.devcontainer]`
  (`mios.toml:6157-6179`) is documented as "Not a bake section -- no
  automation/NN-*.sh stage installs it into the image" (`mios.toml:6156`).
  Measured by parsing the TOML: of its 72 packages, 37 appear in some bake
  section and 35 appear in none (among them `rust`, `cargo`, `python3.11`,
  `ShellCheck`, `zsh`, `sudo`, `gh`).
- **R3. A third list.** -dev-loop `skills/dev-loop/scripts/env/cloud-fedora-setup.sh:163`
  hand-authors `FEDORA_PACKAGES` (31 names) for the cloud host.
- **R4. The pipeline already has a phase registry.** `[build.phases].list`
  (`mios.toml:11250`) names every stage with `fatal` and `apply_class`
  (`universal` | `containerfile` | `bake-only`); `max_phase_scripts = 77`
  (`mios.toml:11331`). `build.sh` asks `miosd build --list` for the phase order
  and refuses a short list (`automation/build.sh:224-259`), falling back to the
  `[0-9][0-9]-*.sh` glob (`automation/build.sh:272-279`). The Rust type is
  `Phase { ordinal, name, script, fatal, apply_class }`
  (`src/mios-rs/mios-build/src/lib.rs:8-13`).
- **R5. Stages hard-code which sections they install.** e.g. `21-virt.sh`
  installs 16 sections (`automation/21-virt.sh:13-67`), `20-hardware.sh` the GPU
  sections (`:13-33`), `57-gnome.sh:12`, `67-bake-surfer.sh:11` (`ai`).
  `install_packages` skips a section whose `enable=false`
  (`automation/lib/packages.sh:182-187`) — one choke point every stage passes.
- **R6. A section-of-sections precedent exists.** `[packages.dev_overlay].sections`
  (`mios.toml:6186-6197`) is a named list of package sections.
- **R7. The dev variant is partial.** `[variants.entries.mios-dev]`
  (`mios.toml:12207-12215`) targets WSL2 only, `artifacts = ["wsl2"]`,
  `status = "partial"`; no variant names a profile.
- **R8. The mirror.** `.devcontainer/Containerfile` is in
  `[bootstrap.sync].mirror_files` (`mios.toml:11788`), gated by
  `tools/sync-bootstrap.py --check`, and mirrored into -dev-loop under
  `tests/test_devcontainer_mirror.py` (`.devcontainer/Containerfile:1-5`).
- **R9. Seeding.** `check_db_seed_coverage` (`tools/drift-checks.py:3473`) fails
  on any top-level SSOT section missing from `_CANONICAL_SECTIONS`
  (`usr/libexec/mios/seed-db-config.py:14`), except `verbs` and `packages`
  (`tools/drift-checks.py:3505`). There is no `profiles` section today. The seeder
  runs from firstboot and never blocks it (`usr/libexec/mios/mios-ai-firstboot:534-535`,
  `|| true`; `seed-db-config.py:34-36` skips without `psycopg`).
- **R10. Law 9 closure** is `automation/lib/mios_var_closure.py` (referenced ⊆
  emitted), run as `check_var_closure` (`automation/98-drift-checks.sh:1158`).
- **R11. Law 16.** There is no `[templates.containerfile]`; the registered
  types are those under `usr/share/mios/templates/` (no Containerfile type).
- **R12. The cloud budget.** -dev-loop `skills/dev-loop/references/environment.md:278-292`:
  the plain Containerfile path took 3m32s cold (build 208s, of which layer
  export 97s); with the lifecycle prebuild through the Dev Containers CLI the
  whole setup took 452s against a ~5-minute budget.
- **R13. Native tooling present.** `tools/native/` carries `mios-resolver`
  (SSOT → shell/json/install-env emit), `mios-bake-plan`, `mios-drift-runner`,
  `mios-template-compile`/`-conform` and `xtask` (regenerate-and-diff renderer
  for `ARTIFACT-PROMPT.md`).

### What follows from it (inferred, not measured)

- The devcontainer is exactly the "toolchain image with its own package list"
  the principle rules out: a different base (R1), a different list (R2), no
  stage of the pipeline (R1), and a third list for the cloud host (R3).
- Nothing today can say "core": the unit of selection the pipeline has is the
  phase (R4) and the package section (R5), and neither carries a profile.
- Running the full pipeline in the cloud cannot fit (R12): the full bake pulls
  the NVIDIA HCI base, GNOME, virt, GPU, flatpaks and GGUF weights. The size and
  duration of a core-profile bake have **not** been measured.

## Decision

### D1. The core profile is declared once: `mios.toml [profiles]`

A new top-level table. A profile is a named, closed selection over the
pipeline's own units — package sections, phases, services, seeds — and may
extend another. Shape (names illustrative; the lists are filled by lane L1 and
reviewed by the operator):

```toml
[profiles]
default = "full"                       # what an unparameterised build means

[profiles.core]
summary          = "the smallest MiOS that is still MiOS: SSOT, miosd, agent-pipe, the datastore, the verbs"
base             = "fedora-bootc"   # Q1, operator decision
package_sections = ["repos", "base", "containers", "build-toolchain", "utils", "ai", "critical"]
phases           = ["system-files-overlay", "materialize-build-ctx", "repos", "locale-theme",
                    "user", "hostname", "subuid-alloc", "generate-quadlets", "render-quadlets",
                    "render-ports", "services", "mios-dropin-fanout", "tools", "finalize",
                    "cleanup", "ssot-lint", "drift-checks", "postcheck"]
services         = ["miosd", "mios-agent-pipe", "mios-pgvector"]
seeds            = ["config_kv"]
budget_seconds   = 300                 # the cloud wall-clock ceiling (R12)
budget_disk_mb   = "<measured by L6>"

[profiles.dev]
extends          = ["core"]
package_sections = ["devcontainer"]    # the dev userspace, now installed BY a phase
phases           = ["dev-userspace"]   # new NN-dev-userspace.sh: npm CLIs, venv, code-server, agy

[profiles.full]
extends          = ["core"]
all              = true                # every enabled section and every registered phase

[profiles.targets]                     # image kind -> profile; every consumer reads this
oci         = "full"
wsl2        = ["full", "dev"]
devcontainer = "dev"
cloud       = "dev"
codespace   = "dev"
```

Rules: a profile's resolved set is the union over its `extends` closure; every
name must resolve (a section in `[packages]`, a phase in `[build.phases].list`,
a unit/Quadlet in the tree, a seed the seeder knows); `core` must be a subset of
every other profile. `[variants.entries.<v>]` gains `profile = "<name>"`
(`mios-dev` → `["full","dev"]`) so R7 stops being a separate notion.
`[packages.devcontainer]` survives as a section but its header comment (R2)
inverts: it is now installed by the `dev-userspace` phase. `[packages.dev_overlay]`
(R6) is the natural `full`-minus-desktop overlay and is left alone by this ADR.

### D2. Every image kind is the root pipeline run under a profile

- **One selector, `MIOS_PROFILE`.** Emitted by the resolver (Law 9 — one
  canonical name, referenced ⊆ emitted), defaulting to `[profiles].default`.
- **Phase selection** happens in Rust: `mios-build` filters `Phase` by the
  resolved profile and `miosd build --list --profile <p>` prints only those
  phases; `build.sh` already consumes that list and refuses a short one (R4), so
  it needs one flag, not new logic.
- **Package selection** happens at the one choke point (R5):
  `install_packages*` skip a section outside the resolved set, logging
  `outside profile <p>`, exactly as they skip `enable=false` today. Stages keep
  their hard-coded section names; the profile decides which are live. A
  `_strict` install of an out-of-profile section is a skip, not a failure.
- **Root Containerfile:** `ARG MIOS_PROFILE` (default from SSOT through the
  existing arg projection) passed into `build.sh`; `ARG BASE_IMAGE` resolved from
  `[profiles.<p>].base`. The final instruction stays `RUN bootc container lint`
  (Law 4) for every profile.
- **`.devcontainer/Containerfile` becomes a rendered thin shim** (Law 8): the
  SSOT-staging step it has today (clone-if-not-a-checkout, R1 `:31-58`),
  widened to stage the whole overlay, then the same `build.sh` under
  `MIOS_PROFILE=dev`, then the container-only tail (dev user, `CMD`). It carries
  no package list and no install logic. It is emitted by a Rust renderer from a
  new `usr/share/mios/templates/containerfile` declared in
  `[templates.containerfile]` (Law 16, R11), and guarded by a regenerate-and-diff
  gate `check_devcontainer_projection`. Its bytes are still mirrored (R8), so the
  mirrors change in the same assignment (Law 15). Alternative in Q2.
- **WSL2 / MiOS-DEV** is the OCI image built with `targets.wsl2`; the WSL
  artifact is a format of that image, as today.

### D3. The cloud projection: core first, the rest degrades open

- **Prefer pull over build.** CI publishes the `dev`-profile image as an OCI tag
  of the same image ref (`[image].ref` + a profile suffix); the cloud setup pulls
  it and falls back to a cold `dev` build only when the pull fails. A pull
  removes the 97 s layer export and the dnf time measured in R12. (Q3.)
- **What is core is fatal, what is beyond core is not.** Core phases keep their
  `fatal` bit. Beyond-core components are applied after the container is up by a
  post-start extender under `budget_seconds`/`budget_disk_mb`, each step
  non-fatal, stopping at the first budget breach. What was skipped is written to
  `/usr/share/mios/profile-manifest.json` at bake time (Law 1, no `/var` mkdir —
  Law 2) and to the datastore at runtime, never inferred.
- **Degrades open (Law 12):** model weights (`model-prep`), the heavy lanes, GPU
  stages, GNOME/desktop, virt, flatpaks, k3s/Ceph. With no weights baked the AI
  plane still starts and reports its lanes unavailable through `/v1/models`
  rather than failing boot; `MIOS_AI_ENDPOINT` is unchanged (Law 5).
- **Never degraded:** the SSOT overlay, `miosd`, the verbs, agent-pipe and the
  datastore (how it runs without systemd is Q4).

### D4. Rust versus Python, and who hosts what

| Piece | Language | Where |
|---|---|---|
| profile resolution, `extends` closure, `MIOS_PROFILE` emit | Rust | `tools/native/mios-resolver` |
| phase filter, `build --list --profile` | Rust | `src/mios-rs/mios-build`, `src/mios-rs/miosd` |
| devcontainer Containerfile renderer + `--check` | Rust | new `tools/native/mios-containerfile-render` (or an `xtask` subcommand, R13) |
| profile integrity + projection gates | Rust runner, Python body where the peers are Python | `tools/drift-checks.py`, wired in `automation/98-drift-checks.sh` |
| section skip at install time | bash glue (thin, Law 14) | `automation/lib/packages.sh` |
| profile seeding, runtime profile state | Python (AI plane) | `usr/libexec/mios/seed-db-config.py` |
| capability report (what is present / degraded) | Python | agent-pipe, read from the profile manifest |

`miosd` hosts the build and the profile query (`miosd profile show`); agent-pipe
hosts the runtime capability view the agents see.

### D5. Database seeding for the core profile

- `profiles` joins `_CANONICAL_SECTIONS` (R9); it is seeded into `config_kv` like
  every other section, in every profile — config is small, so core seeds **all**
  SSOT sections, keeping `check_db_seed_coverage` unchanged and profile-blind.
- `[profiles.<p>].seeds` names only the heavy, optional seeds (knowledge corpus,
  skills catalogue, model registry) a profile adds on top.
- The profile manifest (D3) is seeded as the runtime record of which profile
  this image is and what degraded, so agents query it instead of probing.

### D6. Gates

- **Law 9:** `MIOS_PROFILE` added to the resolver's emitted set;
  `check_var_closure` proves every consumer's reference is emitted.
- **`check_db_seed_coverage`:** red until `profiles` is in `_CANONICAL_SECTIONS`.
- **New `check_profile_integrity`:** every name in every profile resolves;
  `extends` is acyclic; `core` ⊆ every profile; every `[profiles.targets]` value
  and every `variants.entries.*.profile` is a declared profile; `[build.phases]`
  `max_phase_scripts` still bounds the phase count.
- **New `check_devcontainer_projection`** (Law 8): re-render and diff
  `.devcontainer/Containerfile`; a hand edit fails.
- **`check_template_conformance`** covers the new `containerfile` type (Law 16).
- **Law 15 mirrors:** `tools/sync-bootstrap.py --check` (mios-bootstrap) and
  -dev-loop `tests/test_devcontainer_mirror.py` stay byte-identical gates; -dev-loop's
  `FEDORA_PACKAGES` (R3) is replaced by the pulled `dev` image or by the SSOT
  resolution, and a -dev-loop test fails if a literal package list reappears.
- Every new gate gets a negative in `tests/drift-gate-negatives.sh`.

### D7. Lane plan (not implemented in this round)

Ownership is exclusive; `mios.toml` has exactly one owner. Order:
L1 → (L2, L3, L5 in parallel) → L4 → (L6, L7).

| Lane | owned_paths | Positive control | Negative control (must fail, naming the plant) |
|---|---|---|---|
| **L1 ssot-profiles** | `usr/share/mios/mios.toml`, `usr/libexec/mios/seed-db-config.py`, `usr/share/mios/templates/containerfile` | `python3 tools/drift-checks.py db-seed-coverage` exits 0 with `[profiles]` present; `just drift-gate` green | drop `'profiles'` from `_CANONICAL_SECTIONS` on a copy → fails `Section 'profiles' is not handled by seed-db-config.py` |
| **L2 native-profile** | `tools/native/mios-resolver/**`, `src/mios-rs/mios-build/**`, `src/mios-rs/miosd/src/**` | `cargo test -p mios-build`; `miosd build --list --profile core` prints exactly `[profiles.core].phases` in ordinal order | a copy of `mios.toml` with `DEVLOOP-PLANTED-phase` in `core.phases` → `miosd` exits non-zero naming `DEVLOOP-PLANTED-phase` |
| **L3 bake-glue** | `automation/build.sh`, `automation/lib/packages.sh`, `Containerfile`, `tests/test-profile-packages.sh` | with a stub `DNF_BIN`, `MIOS_PROFILE=core install_packages gaming` logs `outside profile core` and calls dnf 0 times; `bash -n` clean | a core list naming `DEVLOOP-PLANTED-section` → `get_packages_strict` fails naming it |
| **L4 devcontainer-render** | `.devcontainer/Containerfile`, `tools/native/mios-containerfile-render/**`, `tools/sync-generated.sh` | renderer `--check` exits 0; `bash tools/sync-generated.sh` reaches a fixed point; the rendered image's RPM set ⊇ `dev` profile set | append `# DEVLOOP-PLANTED-hand-edit` to `.devcontainer/Containerfile` → `check_devcontainer_projection` fails naming the file |
| **L5 gates** | `tools/drift-checks.py`, `automation/98-drift-checks.sh`, `tests/drift-gate-negatives.sh` | `just drift-gate` and `bash tests/run-suites.sh lint` green | `core` extending a profile that omits a core phase → `check_profile_integrity` fails `core is not a subset of DEVLOOP-PLANTED-profile` |
| **L6 cloud-degrade** | `.devcontainer/post-start.sh`, `usr/libexec/mios/mios-profile-extend`, agent-pipe capability module + its `test_mios_*.py` | cold cloud setup ≤ `budget_seconds` with the core verified present; manifest lists what degraded | `budget_seconds = 1` → extender stops after core, exits 0, and the manifest names every skipped component (a missing name fails the test) |
| **L7 mirrors** | mios-bootstrap `.devcontainer/Containerfile`; -dev-loop `.devcontainer/Containerfile`, `skills/dev-loop/scripts/env/cloud-fedora-setup.sh`, `tests/test_devcontainer_mirror.py` | `tools/sync-bootstrap.py --check` and -dev-loop `validate.sh` green, bytes identical | a one-byte change in the bootstrap copy → `sync-bootstrap.py --check` fails naming `.devcontainer/Containerfile`; a literal `FEDORA_PACKAGES=` list → the -dev-loop test fails naming it |

## Rationale

- Declaring the profile over units the pipeline already has (phases, sections)
  adds one table and no second pipeline; the alternative — a `core` Containerfile
  with its own list — is the defect R1–R3 describe, moved.
- Filtering at `miosd build --list` and at `install_packages` touches two choke
  points instead of seventy stage scripts, and both already refuse loudly (R4) or
  log a skip (R5).
- A rendered shim keeps the mirror gate (R8) meaningful: the mirrored bytes are a
  projection of SSOT, so a drift is a regenerate, not a merge.
- Seeding every section in every profile keeps `check_db_seed_coverage` a
  single, profile-blind rule instead of a matrix.

## Consequences

- The devcontainer stops being Fedora-44-plus-a-list and becomes MiOS on the
  core base: some of the 35 packages found in no bake section (R2) move into
  `[packages.devcontainer]` as the `dev-userspace` phase's list, the rest are
  expected from the base image — **unverified** until L4 compares RPM sets.
- A core-profile bake's size and time are **unmeasured**; D3's budget is a
  target, and L6 is where it is proven or the design is revised.
- `[packages.devcontainer]`, `FEDORA_PACKAGES` and the hand-authored
  devcontainer recipe are retired as independent lists; they survive only as
  projections.
- Every stage that assumes a desktop, GPU or systemd must tolerate being
  skipped by profile; `fatal = true` phases outside core are skipped, never run
  and failed.

### Operator decisions

- **Q1 core base image — decided: `fedora-bootc`.** Small and bootc-lintable, so
  Law 4's final `bootc container lint` holds for every profile with no waiver.
- **Q3 cloud delivery — decided: pull a CI-published `dev` tag, cold build as
  fallback.**
- **Q4 datastore without systemd — decided: `postgresql-server` + `pgvector`
  from RPM under a small supervisor** in the container image kinds; the
  `mios-pgvector` Quadlet stays the datastore where systemd runs.
- **Q2 devcontainer shape — open:** rendered thin shim (recommended, keeps the
  mirror model) · `devcontainer.json` builds the root `Containerfile` with
  `args.MIOS_PROFILE=dev` (no second file; mirrors then carry the JSON).
