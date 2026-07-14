<!-- AI-hint: Two orthogonal gates — BAKE (is it in the image?) vs ACTIVATION (does it start on THIS blade?) — give one universal image many roles with no image variants; read before touching the bound-image bake or blade role gating. -->
<!-- AI-related: usr/share/mios/mios.toml [build.bake] + [blade], Containerfile bake RUNs, usr/libexec/mios/mios-bake-group, usr/libexec/mios/role-apply, automation/41-mios-dropin-fanout.sh, usr/share/mios/dropins/, /etc/mios/blade.d/ -->
---
adr: 0001
title: Two-gate bake / activation model
status: accepted
date: 2026-07-12
deciders: [operator, ai-pair]
tags: [build, bake, activation, blade, systemd, topology, universal-image]
laws: [3, 6, 7, 8, 12]
ssot_keys: [build.bake, build.bake.core, build.bake_groups, build.bake_group, blade, blade.archetypes, blade.requires]
related_ws: [WS-BAKEGATE, WS-BLADE]
supersedes: []
superseded_by: []
---

# ADR-0001: Two-gate bake / activation model

## Status
Accepted — 2026-07-12.

## Context

MiOS ships **one** OCI/bootc image (`ghcr.io/mios-dev/mios:latest`,
`FROM ghcr.io/ublue-os/ucore-hci:stable-nvidia`) that must deploy anywhere,
fully-featured, for sovereignty: a laptop, a GPU workstation, a headless
controller, an edge endpoint — all the *same bytes*. MiOS is simultaneously an
immutable Fedora workstation and a local, self-hosted, OpenAI-compatible agentic
AI OS, so that single image carries a heavy fleet: two GPU inference engines
(vLLM ~25 GB, SGLang ~22 GB), the always-on `llama.cpp`/`llama-swap` light lane,
a Postgres+pgvector agent datastore, the agent-pipe gateway plane, k3s, Ceph,
Forgejo + runner, a Guacamole remote-access stack, Matchbox/PXE, AdGuard,
CrowdSec, code-server, observability, and more.

Two forces collide:

- **Universal image, deploys everywhere fully-featured.** The operator's
  sovereignty requirement forbids per-role image variants ("compute image",
  "endpoint image", …). Variants fragment the upgrade/rollback story and
  re-introduce exactly the drift that immutable-image OSes exist to kill.
- **Don't run everything everywhere.** A DNS-only edge endpoint must not spin up
  vLLM (~25 GB, VRAM it does not have); a controller must not start a desktop
  session. Running the whole fleet on every box is wrong on VRAM, boot time, and
  role grounds.

**The specific failure that forced this decision:** prior build work *conflated*
"in the image" with "runs here." The Containerfile's bound-image bake was a single
`RUN` that scraped every Quadlet's `Image=` and pulled all ~20 sidecars + both
CUDA whales into one layer → one `buildah commit` whose transient scratch spike
overran disk-constrained runners (`exit 125` / "io: read/write on closed pipe"
while storing the layer — buildah writes ~2–3× the layer diff to temp during
commit; containers/podman#22342). Meanwhile role selection was *imperative* —
`usr/libexec/mios/role-apply` called `systemctl start` — and covered only
desktop-vs-headless, never gating the ~25 heavy services per machine. A sidecar
audit then flagged code-server, the Guacamole stack, and Matchbox/PXE as
"a-la-carte candidates" that "bloat compute/endpoint images that never run them"
— but the operator's ground truth is that those are **core** (always present).
Both positions are right, on *different axes*, and the conflation was hiding it.

MiOS already ships ~80% of the native machinery to do this correctly: static
kargs via `usr/lib/bootc/kargs.d/*.toml`, mutually-exclusive role `.target`
units, and a `ConditionVirtualization=` drop-in fan-out
(`automation/41-mios-dropin-fanout.sh` applying `usr/share/mios/dropins/*.conf`
across ~60 units). The gap was a clean conceptual split and an SSOT to hang it on.

## Decision

Separate the two questions into **two orthogonal gates**, each with its own SSOT
surface and its own native mechanism.

| Gate | Question it answers | SSOT surface | Mechanism |
|---|---|---|---|
| **BAKE gate** | *Is this content present in the image at all?* | `mios.toml [build.bake]` | Containerfile RUN consumes a projected bake plan |
| **ACTIVATION gate** | *Does this baked unit START on THIS machine?* | `mios.toml [blade]` | systemd `Condition*` drop-ins keyed on `/etc/mios/blade.d/<cap>` markers |

**BAKE gate — decides presence.**
- `[build.bake].core` is a fixed, SSOT-independent allow-list of members baked
  into **every** published image **regardless of any enable flag**. *Core
  overrides SSOT*: no `enable=false` anywhere can remove a core member from the
  bake. The heavy GPU serving **engines** (vLLM, SGLang) are core as *images*;
  their **model weights** are the a-la-carte payload (empty `bake_model` string ⇒
  zero weight bytes).
- Everything not in `core` is **à-la-carte**: baked **iff** the owning service's
  SSOT enable resolves true through the vendor < host < user cascade. Today the
  à-la-carte tier is essentially just model weights plus future optional
  apps/datasets, because the operator classified nearly every current sidecar as
  core.
- "Core overrides SSOT" is implemented as **one branch in one generator** (a
  bake-plan projection, Law 8), not smeared across the Containerfile.

**ACTIVATION gate — decides whether a baked unit starts here.**
- `[blade]` names this host's role. `[blade.archetypes]` expand a named archetype
  (`hybrid`/`compute`/`endpoint`/`controller`/`headless`) into a set of
  capability labels; `[blade.requires]` maps each gated service to the capability
  it needs (a k8s-style `nodeSelector` table). A service with no entry is
  ungated core-of-core and starts everywhere.
- Activation is gated by **systemd itself, declaratively.** `role-apply` is
  demoted from actor to resolver: it materializes marker files
  `/etc/mios/blade.d/<capability>` (empty files) for the resolved role and writes
  `/run/mios/blade.env`. Each gated unit gets a generated drop-in
  `.../<unit>.d/10-blade-<cap>.conf` containing a single
  `ConditionPathExists=/etc/mios/blade.d/<cap>`. A failed `Condition*` is a
  **clean skip**, not a failure — visible in `systemctl status` as
  "condition failed → skipped," greenboot-checkable, zero CPU/VRAM/boot cost.

**One universal image, many roles, NO image variants.** The vLLM image (~25 GB)
is baked on every blade; on a `controller` blade the `gpu-serving` marker is
absent, systemd condition-skips the unit, and **zero VRAM is touched**. Identical
image, different running set. This is the whole design.

Keep both gates independent and defense-in-depth: the coarse karg
`mios.blade=<type>` (via `kargs.d`) and an optional `ConditionHost=` from
`[blade].hostname_glob` complement the marker files. Vendor default is the
fully-capable `hybrid` superset, so an un-specialized image "just runs
everything" — degrade-open, matching today's behavior.

## Rationale

- **Law 8 (SSOT-PROJECTION) + Law 7 (NO-HARDCODE).** Classification and
  "core overrides SSOT" live in a projected, drift-gated bake plan, not in
  Containerfile `sed`/`${VAR:-default}` scraping. The Containerfile consumes a
  plan; it never re-parses Quadlets. A hand-edited plan, or a whale that fell out
  of `core`, fails the build.
- **Law 3 (BOUND-IMAGES) + Law 12 (BAKE-NOT-FETCH).** Bake membership is
  explicit and every core image ships *with* the host; the à-la-carte tier
  degrades open (firstboot/OCI-artifact fallback) and never blocks boot on egress.
- **Law 6 (UNPRIVILEGED-QUADLETS) untouched.** Activation gating is a per-unit
  drop-in; each unit keeps its `User=`/`Group=`/`Delegate=yes` and any documented
  root exception verbatim. Consolidation is presence-side only.
- **Upstream precedent for "one image, specialized at deploy time by a token":**
  Fedora CoreOS `ignition.platform.id` (a kernel-cmdline token consumed via
  `ConditionKernelCommandLine=`); k3s (one binary, server vs agent by config, not
  by a different image); Kubernetes node labels + `nodeSelector` (the exact mental
  model — a blade advertises capability labels, each service's
  `ConditionPathExists` is its `nodeSelector`). We adopt Universal Blue's `ujust`
  *ergonomics* (a single `mios blade set <type>` verb) while **rejecting** its
  multi-published-image model.

## Alternatives considered

- **Trim "wasteful" sidecars out of the image (the audit's proposal).**
  Rejected: it re-frames an *activation* concern as a *bake* concern. code-server,
  Guacamole, and Matchbox are baked on every blade but started only on their blade
  type; dropping them from the image would break the "deploy anywhere
  fully-featured" sovereignty requirement. The "waste" becomes dormant,
  condition-skipped units costing zero runtime.
- **Per-role published image variants (compute/endpoint/controller images).**
  Rejected by the operator: fragments upgrade/rollback, multiplies the build
  matrix, and re-introduces drift. One image, role by flag.
- **systemd-sysext/confext as the role mechanism.** Rejected as the *primary*
  mechanism: sysext delivers *different `/usr` content per role*, which is
  de-facto image variants. Kept in the toolbox for one narrow optional use:
  dropping the `/etc/mios/blade.d/*` marker set as an atomic, reversible `/etc`
  overlay if blade role ever needs to be hot-swappable.
- **A per-service `bake = "core"|"ssot"|"off"` verb in `[image.sidecars]`.**
  Rejected: `[image.sidecars]` is a flat scalar table; a per-key sub-field is
  awkward and invents a parallel toggle to keep in sync with the enable flags MiOS
  already has. One `core` allow-list expresses "fixed SSOT-independent set" in a
  single auditable place and composes with existing `[ai.vllm].enable`-style gates.
- **Imperative role activation via `systemctl start` (status quo).** Rejected:
  brittle, invisible to greenboot, and unable to express "baked but dormant" per
  unit. Declarative `Condition*` is robust across boots and is already the pattern
  MiOS uses for the virtualization fan-out.

## Consequences

Positive:
- One image, many roles, zero variants. A baked-but-dormant heavy engine costs
  disk only, never runtime.
- Classification becomes one auditable SSOT list; "core overrides SSOT" is one
  drift-gated branch.
- Day-2 re-role without a rebuild: `mios blade add-capability gpu-serving` =
  `touch` a marker + `daemon-reload` + `start`.

Negative / honest costs:
- The published image is *intentionally large* (~65–90 GB uncompressed on-disk;
  engines ≈ 73%). Any runner that *bakes* needs ≳ 2× the committed image free
  (300 GB floor for the container image; 707 GB once bootc-image-builder doubles
  it per artifact). Standard CI cannot bake it — see ADR-0004 (capacity gate) and
  ADR-0002 (MiOS-Sys shrinks the bake so a standard runner eventually can).
- The `[blade]` axis must be kept orthogonal to the existing fleet-dispatch axis
  (`[blades.*]`/`[nodes.*]`, which the agent-pipe uses to fan out across machines).
  Reconciliation: `[blade]` (singular) = this host's OS role; `[blades.*]`
  (plural) = fleet machine topology + VRAM budget. Both natively enforce
  "heavy lane only on GPU blades" — Axis A never *starts* the engine off a GPU
  blade; Axis B never *routes* to an engine that isn't answering.

Status — **DONE vs PLANNED:**
- **DONE (Phase 0):** the sharded bake. The single monolithic bake `RUN` is
  replaced by one `RUN` per group, heavy-first, each calling
  `usr/libexec/mios/mios-bake-group <group>`; groups + tokens live in
  `mios.toml [build].bake_groups` / `[build].bake_group.<name>`. This fixes the
  `exit 125` commit-fit crash today and drops no core. (`Containerfile:180–190`,
  `usr/libexec/mios/mios-bake-group`, `mios.toml:8453–8475`.)
- **PLANNED (WS-BAKEGATE):** the `[build.bake]` `core`/à-la-carte projection
  (`tools/generate-bake-plan.py` + `automation/16-bake-plan.sh` after
  `15-render-quadlets.sh`), the `.image` Quadlets for the whales
  (`mios-llm-heavy.image` / `mios-llm-heavy-alt.image`), symlinking `*.image` into
  `bound-images.d`, and the regenerate-and-diff drift-check asserting both whales
  ∈ `core` and every core member fully-qualified.
- **PLANNED (WS-BLADE):** `[blade]`/`[blade.archetypes]`/`[blade.requires]`,
  `role-apply` demotion to marker-writer, the generated `blade-<cap>.conf`
  drop-ins, `mios-{compute,endpoint,controller}.target`, the `mios blade` verb,
  and the greenboot check asserting resolved capabilities match the markers.

## Implementation

Current tree (DONE):
- `C:\MiOS\Containerfile` — five per-group `mios-bake-group` RUNs
  (`vllm`, `sglang`, `ai`, `infra`, `extra`), heavy-first, each with
  `--mount=type=cache,target=/var/tmp/mios-bakescratch`; no `--squash`;
  `ostree container commit` + `bootc container lint` stay last (Law 4).
- `C:\MiOS\usr\libexec\mios\mios-bake-group` — reads `mios.toml [build]` group
  config, classifies each bound Quadlet by substring token, pulls into
  `/usr/lib/containers/storage` with an inner `storage.conf` (`use_hard_links`,
  `convert_images`, `enable_partial_images`), TMPDIR on the big disk, ×3 retry,
  fails LOUD. Also records resolved digests to the SBOM (see ADR-0003).
- `C:\MiOS\usr\share\mios\mios.toml [build]` — `bake_groups`,
  `bake_group.{vllm,sglang,ai,infra,extra}`.

Planned files (WS-BAKEGATE / WS-BLADE), cross-referencing ADR-0002 (the bake
groups evolve toward two *built* images `mios-sys`/`mios-cuda`) and ADR-0003
(digests are SBOM, not hardcoded):
- `usr/share/mios/mios.toml` — add `[build.bake]` (`core`, `groups`,
  `group_members.*`) and `[blade]` (`type`, `capabilities`, `hostname_glob`),
  `[blade.archetypes]`, `[blade.requires]`; fold `[profile].role/features` into
  `[blade]` as a one-release alias.
- `tools/generate-bake-plan.py` + `automation/16-bake-plan.sh` — project the plan
  to `/usr/lib/mios/bake/plan.d/NN-<group>.list` via the shared resolver
  `usr/lib/mios/mios_toml.py`.
- `usr/share/containers/systemd/mios-llm-heavy.image`, `mios-llm-heavy-alt.image`;
  extend `automation/08-system-files-overlay.sh` (~L178) to symlink `*.image`.
- `usr/libexec/mios/role-apply` — resolve `type`→capabilities, write
  `/etc/mios/blade.d/*` + `/run/mios/blade.env`; drop the imperative
  `systemctl start` side-cars.
- `usr/share/mios/dropins/blade-<cap>.conf` + gate entries generated into
  `automation/41-mios-dropin-fanout.sh` from `[blade.requires]` (Law-8 generator +
  drift-check).
- New drift-check in `automation/38-drift-checks.sh` (regenerate-and-diff the plan;
  assert whales ∈ core, full qualification, `referenced ⊆ emitted`).

Deploy-time role selection degrades open to the `hybrid` superset across every
channel: ISO/USB (`kargs.d/05-mios-blade.toml`), fleet PXE/Matchbox
(Butane/Ignition `kernel_arguments`), cloud/hypervisor (Afterburn/cloud-init →
`role.conf`), day-2 (`mios blade set <type>`), and `role-apply` autodetect.

## References

- bootc — logically-bound images: <https://bootc.dev/bootc/logically-bound-images.html>
- bootc ↔ systemd relationship particles: <https://bootc.dev/bootc/relationship-particles.html>
- `.image` vs `.container` Quadlets (podman-systemd.unit / quadlet).
- systemd.unit(5) `Condition*` (a failed condition is a clean skip):
  <https://www.freedesktop.org/software/systemd/man/latest/systemd.unit.html>
- Fedora CoreOS `ignition.platform.id` / platform specialization:
  <https://docs.fedoraproject.org/en-US/fedora-coreos/platforms/>
- K3s server/agent configuration: <https://docs.k3s.io/installation/configuration>
- Kubernetes `nodeSelector` / node labels:
  <https://kubernetes.io/docs/concepts/scheduling-eviction/assign-pod-node/>
- Universal Blue / `ujust` ergonomics: <https://universal-blue.org/>
- containers/podman#22342 (buildah commit transient-space `exit 125`).
- MADR / ADR: <https://adr.github.io/madr/>
- Sibling ADRs: ADR-0002 (MiOS-Sys shrinks the core bake), ADR-0003 (SBOM digests),
  ADR-0004 (CI capacity gate), ADR-0006 (the AI front door that lives in the AI-core group).
