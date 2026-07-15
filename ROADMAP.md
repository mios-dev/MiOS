# MiOS -- Master Roadmap (SINGULAR monolith)

> The one canonical roadmap. Absorbs all former top-level `*-PLAN-*.md` + `concepts/*` planning docs. Workstreams map to `T-*` in TASKS.md.

<!-- ROADMAP_ROLLUP_START -->
### Workstream Status Rollup
- **Done**: 0
- **Active**: 4
- **Proposed**: 4
- **Blocked**: 0
<!-- ROADMAP_ROLLUP_END -->

<!-- ROADMAP_INDEX_START -->
### Workstream Index

**OS-Image & Build**
- `WS-BAKEGATE` — Two-gate model: [build.bake] core allow-list + projected bake-plan (active)
- `WS-BLADE` — Universal-core + blade-type ACTIVATION gate (one image, role by flag) (proposed)
- `WS-MIOSSYS` — MiOS-Sys shared-base consolidation of the sidecar fleet (proposed)
- `WS-SBOM` — SBOM-not-hardcode: digests/hashes are build-time provenance, never SSOT literals (active)
- `WS-DOCS` — Planning-docs refactor: ADR system + generated index (active)

**AI-Plane & Orchestration**
- `WS-DEPRED` — AI-plane dependency reduction (Hermes→agent-pipe collapse + sidecar consolidations) (proposed)

**Deployment & Sovereignty**
- `WS-MDRIVE` — Sovereign "run off M:" deployment (Hyper-V Gen 2 .vhdx + Ceph OSD on M:) (proposed)

**Storage & Data**
(no workstreams)

**Security & Identity**
(no workstreams)

**Desktop & UX**
(no workstreams)

**Fleet & Federation**
- `WS-RELTOP` — Release topology: GitHub ≡ Forgejo equal publishers; PUBLISH capacity gate (active)
<!-- ROADMAP_INDEX_END -->

<!-- ROADMAP_TOC_START -->
## Table of Contents
- [OS-Image & Build](#os-image-build)
- [AI-Plane & Orchestration](#ai-plane-orchestration)
- [Deployment & Sovereignty](#deployment-sovereignty)
- [Storage & Data](#storage-data)
- [Security & Identity](#security-identity)
- [Desktop & UX](#desktop-ux)
- [Fleet & Federation](#fleet-federation)
<!-- ROADMAP_TOC_END -->

---

# OS-Image & Build

## WS-BAKEGATE — Two-gate model: `[build.bake]` core allow-list + projected bake-plan (Phase 0 sharded bake ✅)
<!--
id: WS-BAKEGATE
title: Two-gate model: [build.bake] core allow-list + projected bake-plan
theme: OS-Image & Build
status: active
priority: P1
laws: [3, 7, 8, 12]
ssot_keys: ["build.bake.core", "build.bake.groups", "build.bake.group_members"]
adr: [1]
deps: []
acceptance: |
  just drift-gate validates plan.d/*.list; the check fails if a whale leaves core,
  a core member is not fully-qualified, or referenced not in emitted.
-->

**Phase 0 (sharded bake) ✅ DONE this session** — the monolithic `RUN` that pulled ~20 sidecars + both CUDA whales into one `buildah commit` overran disk-constrained runners (`exit 125` / "io: read/write on closed pipe"). Fixed by sharding into one `RUN` per group, heavy-first: `usr/libexec/mios/mios-bake-group` (new; reads `[build].bake_groups`, writes an inner `storage.conf` with `use_hard_links`/`convert_images`/`enable_partial_images`, pulls with `--tmpdir` scratch + ×3 retry, fails LOUD, and records each resolved digest to the SBOM — see WS-SBOM), `usr/share/mios/mios.toml [build].bake_groups` (L8470-8475: `["vllm","sglang","ai","infra","extra"]` — whales first while the store is emptiest), and `Containerfile` L181-190 (five per-group `RUN`s, each `--mount=type=cache,target=/var/tmp/mios-bakescratch`; `ostree container commit` + `bootc container lint` stay last; **never `--squash`**). This moves layer boundaries only, not membership — every image is still baked.

### BAKE-01 — `[build.bake]` core allow-list + `generate-bake-plan.py` projection + drift-check + `.image` whales  **[P1]**
- **What:** Add a dedicated `[build.bake]` SSOT section (a `core` allow-list — the fixed, SSOT-independent membership baked into every image; `groups`/`group_members.*` for shard order) adjacent to `[build]`. Add generator `tools/generate-bake-plan.py` invoked by new numbered step `automation/16-bake-plan.sh` (after `15-render-quadlets.sh`, so `Image=` values are concrete): read `mios.toml` through the shared `usr/lib/mios/mios_toml.py` resolver, resolve each bound Quadlet's fully-qualified `Image=`, emit CORE members **unconditionally** (this one branch is where "core overrides SSOT" is literally implemented) and à-la-carte members **iff** their enable gate resolves true, into ordered `/usr/lib/mios/bake/plan.d/NN-<group>.list`. Encode "engine baked, service disabled" natively with `.image` Quadlets for the whales (`usr/share/containers/systemd/mios-llm-heavy.image` + `mios-llm-heavy-alt.image`), symlinked into `/usr/lib/bootc/bound-images.d/` by extending `automation/08-system-files-overlay.sh` (~L178) to also glob `*.image`. Have `mios-bake-group` consume `plan.d/` (swap out its interim static group tokens).
- **Why:** Phase 0 fixed the crash but the Containerfile still `sed`-scrapes Quadlets and the gate is all-or-nothing (against Law 7 NO-HARDCODE + Law 8 SSOT-PROJECTION). A single `core` list expresses "core is fixed; everything else is enable-gated" in one auditable place and composes with the enable flags MiOS already has, instead of inventing a parallel per-service toggle. `.image` Quadlets are bootc's native encoding of pull-only-no-service (the whales are CORE-baked but VRAM-gated off).
- **Files:** `usr/share/mios/mios.toml` (`[build.bake]`; digest-free `vllm`/`sglang`/`hermes` entries in `[image.sidecars]`), `tools/generate-bake-plan.py` (new), `automation/16-bake-plan.sh` (new), `automation/08-system-files-overlay.sh` (~L178), `automation/38-drift-checks.sh` (new check), `usr/share/containers/systemd/mios-llm-heavy.image` + `mios-llm-heavy-alt.image` (new), `usr/libexec/mios/mios-bake-group`, the `just iso`/BIB path (`--bound-images=stored`).
- **Accept:** `just drift-gate` regenerates `plan.d/*.list` and diffs clean; the check FAILS if a whale falls out of `core`, if a core member is not fully-qualified (no `localhost/`, no short-name), or if `referenced ⊄ emitted`; the Containerfile carries no inline Quadlet `sed`-scraping; a build with all whales in `core` and empty `bake_model` bakes engines-only.
- **Deps:** Phase 0 (done). Interlocks with WS-MIOSSYS (the bake groups collapse toward `sys`/`cuda` built images) and WS-SBOM (digest-free SSOT).


## WS-BLADE — Universal-core + blade-type ACTIVATION gate (one image, role by flag)
<!--
id: WS-BLADE
title: Universal-core + blade-type ACTIVATION gate (one image, role by flag)
theme: OS-Image & Build
status: proposed
priority: P1
laws: [3, 8]
ssot_keys: ["blade.type", "blade.archetypes", "blade.requires"]
adr: [1]
deps: [WS-BAKEGATE]
acceptance: |
  one universal image specializes into roles cleanly by cmdline token + markers.
-->

### BLADE-01 — `[blade]` archetypes + capability→unit map + declarative `Condition*` activation + deploy-time selection  **[P1]**
- **What:** Add a `[blade]` SSOT: `type` (named archetype: `hybrid`/`compute`/`endpoint`/`controller`/`headless`), `[blade.archetypes]` (each expands to a k8s-style capability label set), and `[blade.requires]` (the "nodeSelector" table mapping each CORE service unit → required capability; a service with no entry is ungated core-of-core that starts everywhere). Demote `usr/libexec/mios/role-apply` from imperative actor (it currently calls `systemctl start`) to a **marker-writing resolver** — expand `type`→capabilities and materialize `/etc/mios/blade.d/<cap>` marker files + `/run/mios/blade.env`; keep autodetect. Generate one `usr/share/mios/dropins/blade-<cap>.conf` per capability (a single `ConditionPathExists=/etc/mios/blade.d/<cap>`) from `[blade.requires]` (Law 8 generator + drift-check) and wire the `automation/41-mios-dropin-fanout.sh` gate table. Deploy-time selection per channel: karg `mios.blade=<type>` (from a generated `usr/lib/bootc/kargs.d/05-mios-blade.toml`) for ISO/bare-metal, Butane/Ignition `kernel_arguments`/marker drops for PXE/Matchbox, Afterburn/cloud-init for hypervisor, `mios blade set|add-capability|status` verb for day-2 (marker `touch` + `daemon-reload`, no reboot). Fold `[profile].role/features` into `[blade]` (thin alias one release, then retire); add `mios-{compute,endpoint,controller}.target` mirroring the existing `Conflicts=`/`AllowIsolate=` pattern; a greenboot check asserts resolved capabilities match the markers.
- **Why:** The sidecar audit flagged code-server, the Guacamole stack, and Matchbox/PXE as "bloat that never runs" — but the operator classifies them CORE. Both are right on different axes: baked on every blade (BAKE gate = core), started only on their blade type (ACTIVATION gate = marker present). A failed `Condition*` is a *clean skip*, not a failure, so a `controller` blade bakes the ~25 GB vLLM image and leaves it condition-skipped at **zero VRAM/boot cost** — identical image, different running set, no variants. Marker files (over raw per-unit kargs) give capability granularity + day-2 mutability without reboot + admin-tier `/etc/mios` override.
- **Files:** `usr/share/mios/mios.toml` (`[blade]`/`[blade.archetypes]`/`[blade.requires]`), `usr/libexec/mios/role-apply`, `usr/share/mios/dropins/blade-<cap>.conf` (generated), `automation/41-mios-dropin-fanout.sh`, `usr/lib/bootc/kargs.d/05-mios-blade.toml` (generated), `usr/lib/systemd/system/mios-{compute,endpoint,controller}.target`, `usr/lib/greenboot/check/required.d/10-mios-role.sh`, the `mios blade` verb.
- **Accept:** one universal image; on a `controller` blade `systemctl status mios-llm-heavy.service` reports condition-skipped with zero VRAM touched, while a `gpu-serving` blade starts it; `mios blade add-capability gpu-serving` lights the unit hot (no reboot); the drop-in generator is drift-gated; `[blades.*]`/`[nodes.*]` fleet-dispatch (Axis B) stays orthogonal to `[blade]` OS-activation (Axis A).
- **Deps:** none hard; complements WS-BAKEGATE (activation vs bake orthogonality) and WS-MIOSSYS (activation `Condition*` unchanged by consolidation).


## WS-MIOSSYS — MiOS-Sys shared-base consolidation of the sidecar fleet
<!--
id: WS-MIOSSYS
title: MiOS-Sys shared-base consolidation of the sidecar fleet
theme: OS-Image & Build
status: proposed
priority: P1
laws: [3, 6, 8]
ssot_keys: ["image.sys", "image.cuda", "image.sidecars"]
adr: [2]
deps: [WS-BAKEGATE]
acceptance: |
  collapses container fleet base OS, reducing size down to ~25GB.
-->

### MIOSSYS-01 — Two shared-base images (`mios-sys` + `mios-cuda`) collapse ~18 sidecars via Model A  **[P1]**
- **What:** Replace the ~18-image sidecar fleet (which today shares **zero** base-OS blobs → ~60 GB store) with **two images of one base lineage, both `FROM ${BASE_IMAGE}` (ucore-hci:stable-nvidia)**: `localhost/mios-sys` (CUDA-free glibc base for the Go/Python/Node/native services, ~6-8 GB) and `localhost/mios-cuda` (the shared CUDA/torch/flashinfer L2 whale + sibling `vllm-venv`/`sglang-venv` + `llama-server`, ~15-18 GB). Consolidate via **Model A** (one IMAGE, many CONTAINERS — distinct Quadlets, shared `Image=`, per-service `Exec=`; each keeps its own `User=`/`Group=`/`Delegate=yes` + `Condition*` activation, only the image collapses — the pattern MiOS already ships as `localhost/mios-crawl4ai-slim` etc.). New builder `automation/57-mios-sys-build.sh` (mirrors `52-56-bake-*.sh` + the venv/checksum molds) building into `/usr/lib/containers/storage` with `--layers`; generated `usr/share/mios/sys/Containerfile` + `usr/share/mios/cuda/Containerfile`; `[image.sys]`/`[image.cuda]` SSOT blocks; `MIOS_SYS_IMAGE`/`MIOS_CUDA_IMAGE` threaded through `userenv.sh` + **both** allowlists in `automation/15-render-quadlets.sh` (envsubst arg-string L73 + bash-fallback loop ~L87-127) + asserted in `38-ssot-lint.sh`. The per-member Quadlet delta is a **pure SSOT edit** (repoint `Image=`, add the previously-implicit `Exec=`); the `[build].bake_groups` collapse toward `["sys","cuda","extra"]`. Migration in Waves: **Wave 0** wiring; **Wave 1** Go/static-binary tier (socat[RPM]/adguard/matchbox/forgejo/jaeger/crowdsec — biggest win, lowest risk); **Wave 2** interpreted+native (searxng/open-webui/code-server/valkey/guacd, fold crawl4ai+firecrawl onto shared layers) + k3s/forgejo-runner binaries (privileged activation UNCHANGED); **Wave 3** `mios-cuda` (the ~12-13 GB CUDA/torch byte win) + the DB tier (postgres+pgvector one instance, resolve the PG17-pgvector packaging gap) behind a data-plane smoke test.
- **Why:** The exit-125 root cause is a *big store*, not build-logic; collapsing 18×base → 2×base (and 2.5× duplicated CUDA/torch → one L2) takes the store ~60 GB → ~25 GB — half the win from de-duplicating the vLLM/SGLang whale alone. This makes GitHub-runner-fits-the-bake TRUE (the enabler of WS-RELTOP equality), and simplifies Law 3 (bootc dedups to one/two image IDs). `bootc rollback` reverts OS + baked binaries + Quadlets atomically. The honest lever is single-base-within-the-store (ostree host `/usr` and containers-storage do NOT blob-share), not `additionalimagestores` against host `/usr`.
- **Files:** `usr/share/mios/mios.toml` (`[image.sys]`/`[image.cuda]`/`[image.sidecars]` sys+cuda refs; `[build].bake_groups`→`sys`/`cuda`/`extra`), `automation/57-mios-sys-build.sh` (new), `usr/share/mios/sys/Containerfile` + `usr/share/mios/cuda/Containerfile` (generated), `automation/15-render-quadlets.sh` (both allowlists), `automation/38-ssot-lint.sh`, `automation/14-generate-quadlets.sh`, `usr/libexec/mios/mios-bake-group` (retire the now-superseded `use_hard_links` path), `Containerfile` L181-190, the ~18 `usr/share/containers/systemd/*.container` members.
- **Accept:** the bound-image store drops to ~25 GB (conservative ~27-30) with the largest single commit capped at the ~12 GB CUDA/torch group; `just drift-gate` (`generate-pod-quadlets.py --check`) validates the regenerated `Image=`/`Exec=`; every `User=`/`Group=`/root-exception is byte-identical (Law 6 untouched); a WSL blade still won't start pxe-hub even though its binary is now baked (activation orthogonality holds).
- **Deps:** Locked operator decisions — newest-packages-globally tagged-at-build; ALL core components consolidate; k3s binary consolidated (clustering/HA-compatible, privileged activation unchanged) and Pacemaker/corosync HA is CORE; on-CVE/on-release rebuild cadence (Renovate bumps `MIOS_<X>_VERSION` keys under checksum/GPG verify); Ceph = **KEEP-SEPARATE** (cephadm container-only); `mios-cuda` bake-scope (every blade vs GPU-blade-gated) deferred to Wave 3. Complements WS-BAKEGATE Phase 0 (sharding kept as the free 2× safety margin).


## WS-SBOM — SBOM-not-hardcode: digests/hashes are build-time provenance, never SSOT literals
<!--
id: WS-SBOM
title: SBOM-not-hardcode: digests/hashes are build-time provenance, never SSOT literals
theme: OS-Image & Build
status: active
priority: P2
laws: [7, 8]
ssot_keys: ["image.sidecars"]
adr: [3]
deps: [WS-MIOSSYS]
acceptance: |
  no hand-pinned digests remain in mios.toml; build resolves and records to SBOM.
-->

**✅ DONE this session (for images):** SSOT (`mios.toml`) refs now carry the TAG intent only (`:latest` = "track newest globally", or a bare version) — a hand-written `@sha256:…` is a hardcode (Law 7). ALL 12 hand-pinned `@sha256` digests were stripped from `mios.toml` (verified: 0 remaining); the 27 rendered Quadlets were regenerated digest-free (verified: 0 `@sha256` in `usr/share/containers/systemd/`; the digest-drift gate is green); and `usr/libexec/mios/mios-bake-group` now resolves each `:latest` at pull time and records `<image>\t<digest>\t<group>` to `/usr/share/mios/artifacts/sbom/bound-images.tsv` (L173-178) — reproducibility comes from the SBOM + baked OCI manifest, not from SSOT digests. This **reverses** the older "pin `@sha256` in `[image.sidecars]` for reproducible builds" convention.

### SBOM-01 — Extend build-time provenance beyond images (model checksums, package version-hashes)  **[P2]**
- **What:** Apply the same principle to every remaining hand-maintained hash literal: model checksums in `automation/38-llamacpp-prep.sh`, package version-hashes, and the per-app upstream `checksums.txt`/`.asc` verification that WS-MIOSSYS's Wave fetchers introduce — resolved/verified at build and recorded to the SBOM (`automation/90-generate-sbom.sh`), never hand-pinned in `mios.toml`, Quadlets, or scripts.
- **Why:** A hand-pinned hash duplicates SBOM data, can drift from resolved reality, and is a Law-7 hardcode; the SBOM is the single provenance record. Applies beyond images — llama.cpp model checksums, package version-hashes, etc.
- **Files:** `automation/38-llamacpp-prep.sh`, `automation/90-generate-sbom.sh`, the WS-MIOSSYS `automation/NN-*.sh` app fetchers, `usr/share/mios/mios.toml` (version-intent keys only).
- **Accept:** no hand-maintained `@sha256`/checksum literal remains in `mios.toml` or scripts for a runtime-pinned artifact; each resolved hash appears in the SBOM; the digest/checksum drift-checks validate build-resolved values.
- **Deps:** images DONE; interlocks with WS-MIOSSYS (digest-lock the floating `:latest` sources as part of Wave 0) and WS-RELTOP (newest-packages, tagged at build).


## WS-DOCS — Planning-docs refactor: ADR system + lean thematic roadmap + generated index
<!--
id: WS-DOCS
title: Planning-docs refactor: ADR system + generated index
theme: OS-Image & Build
status: active
priority: P1
laws: [7, 8]
ssot_keys: ["meta.mios_version"]
adr: [7]
deps: []
acceptance: |
  every workstream backed by an ADR; generated indexes pass drift checks.
-->
*The meta-workstream that solidifies this whole refactor into cohesive, AI-agent-native docs matching upstream patterns — [MADR](https://adr.github.io/madr/) ADRs · k8s-KEP-style workstream metadata · [Diátaxis](https://diataxis.fr/) doc quadrants · [Keep a Changelog](https://keepachangelog.com/) + SemVer history · `llms.txt`/`AGENTS.md` agent-context. Goal: a future agent starts a workstream from ONE self-contained file, spending tokens on the task not on re-deriving context. Governs the doc tree only; seeds no runtime change. Backing decisions: every WS-* above is now recorded in `usr/share/doc/mios/adr/` (ADR-0001..0006).*

### DOCS-01 — ADR system (`usr/share/doc/mios/adr/`)  **✅ DONE this session**
- **What:** Immutable, numbered, MADR-format Architecture Decision Records, **baked into the image** so a deployed MiOS carries its own *why* (no external wiki). Index + process spec in `adr/README.md` (format, `proposed→accepted→superseded` lifecycle, append-only/never-rewrite rule, the record table, the 13-laws reference). Six foundational ADRs: **0001** two-gate bake/activation · **0002** MiOS-Sys consolidation · **0003** SBOM-not-hardcode · **0004** GitHub≡Forgejo topology · **0005** sovereign run-off-M: · **0006** OpenAI-API-only AI contract. Each frontmatter carries `laws[]`/`ssot_keys[]`/`related_ws[]` cross-linking it to the workstream it seeds.
- **Files:** `usr/share/doc/mios/adr/README.md` + `0001..0006-*.md`.
- **Accept:** every Part-21 WS-* is backed by an accepted ADR (0001→BAKEGATE/BLADE · 0002→MIOSSYS · 0003→SBOM · 0004→RELTOP · 0005→MDRIVE · 0006→DEPRED). **✅ met.**

### DOCS-02 — WS metadata schema + `roadmap-index.py` generator + drift-check  **[P1]**
- **What:** Give every `WS-*` machine-parseable frontmatter (`id, title, theme, status, priority, laws[], ssot_keys[], adr[], deps[], acceptance`) — KEP-style. Add `tools/roadmap-index.py` that regenerates the top Part/WS index + a status rollup (proposed/active/blocked/done counts) + the Table-of-Contents **from that frontmatter** (fixes the hand-truncated ToC that stops at Part 12), plus a drift-check (`automation/38-drift-checks.sh check_roadmap_index`) that fails if the index is stale or a WS cites a non-existent ADR/law/`ssot_key`. Law-8 SSOT-PROJECTION applied to the planning docs themselves.
- **Files:** `ROADMAP.md` (per-WS frontmatter), `TASKS.md`, new `tools/roadmap-index.py`, `automation/38-drift-checks.sh`.
- **Accept:** `just drift-gate` regenerates the index byte-identically; a WS with a bad `adr:`/`laws:` ref fails the gate; the ToC lists all Parts.
- **Deps:** DOCS-01.

### DOCS-03 — Lean thematic `ROADMAP.md`; archive Parts 1–20 losslessly  **[P1]**
- **What:** Split the 2,900-line monolith. Keep `ROADMAP.md` as the **current, forward-looking** roadmap grouped by **theme/pillar** (the MiOS "SIGs": OS-Image & Build · AI-Plane & Orchestration · Deployment & Sovereignty · Storage & Data · Security & Identity · Desktop & UX · Fleet & Federation), listing only `proposed/active/blocked` WS. Move the historical/absorbed Parts 1–20 (and every `done` WS) losslessly to `usr/share/doc/mios/roadmap/history/` (dated). Part 21's WS become the seed of the new active roadmap under their themes.
- **Files:** `ROADMAP.md`, `usr/share/doc/mios/roadmap/history/*.md`, `CHANGELOG.md`.
- **Accept:** `ROADMAP.md` is theme-grouped + active-only (~≤600 lines); every archived Part is retrievable under `history/`; the generator's WS rollup total is conserved (nothing lost).
- **Deps:** DOCS-02.

### DOCS-04 — Status-lifecycle retag (honest done-vs-gated) + cross-ref backfill  **[P2]**
- **What:** Re-tag every WS to the lifecycle with the 2026-06-22 honesty rule formalized: **`done` = active AND live-fired**, never "built-but-gated" (those become `blocked`/`active`). Backfill each WS's `laws[]`/`ssot_keys[]`/`adr[]` so the cross-reference graph (WS↔T↔ADR↔Law↔SSOT-key) is complete + drift-checkable.
- **Files:** `ROADMAP.md`, `TASKS.md`.
- **Accept:** no WS tagged `done` that is gated-off/never-fired; every `done` claim carries a live-evidence line; the cross-ref drift-check (DOCS-02) passes.
- **Deps:** DOCS-02.

### DOCS-05 — Diátaxis reorg of `/usr/share/doc/mios` + `CHANGELOG.md` + agent-context refresh  **[P2]**
- **What:** Align the whole doc tree to **Diátaxis** quadrants — *tutorial* (day-0/first-boot), *how-to* (`guides/`), *reference* (`api.md`, `mios.toml`, the ports/laws registries), *explanation* (`concepts/`, `adr/`, `roadmap/`). Add a top-level `CHANGELOG.md` (Keep a Changelog + SemVer) fed from `bootc`-version bumps. Refresh `llms.txt` + `AGENTS.md` so an arriving agent is routed in ≤3 hops: current roadmap → ADR index → SSOT → the 13 laws.
- **Files:** `usr/share/doc/mios/**`, `CHANGELOG.md`, `llms.txt`, `AGENTS.md`.
- **Accept:** each doc sits in exactly one Diátaxis quadrant; `llms.txt` resolves an agent to the current-state entry points in ≤3 hops.
- **Deps:** DOCS-03.

---

## Appendix: Absorbed sources (2026-07-10 consolidation)

ROADMAP.md + TASKS.md are now the **singular** planning SSOT. Folded in:
- **9 top-level `*-PLAN-*.md`** (2026-06-14/15) → **Part 17 / T-167–T-177**. Originals archived under `usr/share/doc/mios/archive/absorbed-plans-2026-06/`.
- **~28 `usr/share/doc/mios/concepts/*` docs** → **Part 18 / T-200–T-241** (actionable deltas); the ~24 pure-reference/architecture docs are kept in place and cross-referenced from their Part.
- Live dGPU heavy-lane diagnosis → **Part 19 / T-178**.
- Retired the old `combine_roadmaps.py` script.

A master index sits at the top of each file; every task carries **Who / What / Where / When / How** + Done-When.

# AI-Plane & Orchestration

## WS-DEPRED — AI-plane dependency reduction (Hermes→agent-pipe collapse + sidecar consolidations)
<!--
id: WS-DEPRED
title: AI-plane dependency reduction (Hermes→agent-pipe collapse + sidecar consolidations)
theme: AI-Plane & Orchestration
status: proposed
priority: P2
laws: [5, 7, 8]
ssot_keys: ["ai.endpoint", "hermes.endpoint"]
adr: [6]
deps: [WS-BLADE, WS-MIOSSYS]
acceptance: |
  collapse gateway plane to single port; delete redundant databases/containers.
-->

### DEPRED-01 — Collapse the gateway plane to one `:8640` front door + consolidate sidecars  **[P2]**
- **What:** Collapse MiOS-Hermes (`:8642`) into agent-pipe (`:8640`) — the collapse is already ~70% done (Open WebUI already targets `:8640`, and agent-pipe already owns four of six Hermes responsibilities). Ranked: (1) repoint `MIOS_AI_ENDPOINT` `:8642`→`:8640` in `automation/lib/globals.sh:133` (+ `mios.toml [ai]/[hermes]` endpoints; add `8640` to `[security.nohc_allowlist]`) — one edit redirects every `@`-prompt/CLI client and satisfies Law 5 more cleanly; (2) retire the prefilter (`:8641`) hop (`mios-delegation-prefilter.service`); (3) absorb `gateway_sessions` (port `gateway-agent/session.py` get/save into agent-pipe, opt-in replay); (4) decide the browser/CDP path — expose ChromeDev CDP as MCP `browser_*` verbs and keep `mios-hermes-browser.service` (`:9222`) as a pure executor (recommended) vs retaining one `hermes-worker` browser specialist; (5) retire/alias `mios-gateway-agent.service`. Sidecar consolidations: fold the Guacamole DB into pgvector (delete `mios-guacamole-postgres`, −~430 MB), delete `mios-crowdsec-dashboard` (Quadlet + `[image.sidecars]` pin, −~180 MB), swap cockpit-link's `alpine/socat` container for native `systemd-socket-proxyd`, and replace Open WebUI (`:8033`, ~3.5 GB) with a Quickshell/Hyprland thin SSE `/v1` client to `:8640` (gate OWUI to `edge-endpoint`, then remove).
- **Why:** `:8642` today is a thin shell whose own model is `:8640` and whose MCP verbs call back into `:8640` — a genuinely single front door is cleaner than a secret forwarder. The consolidations trim ~4.1 GB + 3 containers + 2 bound-images without touching the ~47 GB engine floor.
- **Files:** `automation/lib/globals.sh`, `usr/share/mios/mios.toml` (`[ai]`/`[hermes]`/`[security.nohc_allowlist]`), `mios-delegation-prefilter.service`, `usr/lib/mios/gateway-agent/session.py` + agent-pipe `server.py`, `usr/lib/mios/mcp` (browser_* verbs), `mios-hermes-browser.service`, `mios-gateway-agent.service`, `mios-guacamole-postgres.container` + `mios-guacamole.container`, `mios-crowdsec-dashboard.container`, `mios-cockpit-link` unit, a new Quickshell `/v1` panel.
- **Accept:** every front-end resolves `MIOS_AI_ENDPOINT` to `:8640`; `:8641`/`:8642` are retired or thin-aliased; Guacamole runs against a pgvector DB/role; `mios-crowdsec-dashboard` + `mios-guacamole-postgres` are gone; a native SSE client streams `/v1/chat/completions` with model picker + session id + RAG upload.
- **Deps:** Open browser/CDP + `hermes` CLI/Discord decisions per the study's OPEN QUESTIONS; OWUI removal release TBD. Pairs with WS-BLADE (OWUI gated to `edge-endpoint`) and WS-MIOSSYS (fewer images to consolidate).


# Deployment & Sovereignty

## WS-MDRIVE — Sovereign "run off M:" deployment (Hyper-V Gen 2 `.vhdx` + Ceph OSD on M:)
<!--
id: WS-MDRIVE
title: Sovereign "run off M:" deployment (Hyper-V Gen 2 .vhdx + Ceph OSD on M:)
theme: Deployment & Sovereignty
status: proposed
priority: P1
laws: [3, 8]
ssot_keys: ["storage.cephfs.enable"]
adr: [5]
deps: []
acceptance: |
  VM boots off M: vhdx with populated /var/home and single-node Ceph storage.
-->

### MDRIVE-01 — Boot the universal image as a Hyper-V Gen 2 VM off `M:\MiOS-images\` with sovereign Ceph storage  **[P1]**
- **What:** Deploy the universal image as a **Hyper-V Generation 2 VM booting a `.vhdx` on `M:\MiOS-images\`**, cut from the OCI image by `bootc install`/bootc-image-builder (`just vhdx` at `Justfile:217` already runs the `bootc install`-class installer that **factory-populates `/var` + `/var/home`**, installs the bootloader, and honors kargs — the direct fix for the raw `wsl --import` failure). Add a **`vhdx-m` Justfile recipe** (after `vhdx:`) that cuts + drops the artifact on M: and prints the `New-VM` one-liner, and a new **`C:\mios-bootstrap\deploy-mios-hyperv-m.ps1`** that loads the tar, cuts the vhdx if missing, `New-VM -Generation 2` off M: with `Set-VMFirmware -SecureBootTemplate MicrosoftUEFICertificateAuthority`, attaches the Ceph OSD vhdx, adds `netsh interface portproxy` for `:8640`, and does the DDA/GPU-P block. **Sovereign storage** = a 2nd dynamic `.vhdx` on M: (`mios-ceph-osd.vhdx`) attached as the single-node Ceph OSD block device backing `/var/home` (`var-home.mount` is `Type=ceph`), so home + container data persist in a file on M: and survive a root-vhdx rebuild. This requires relaxing **`ConditionVirtualization=no`** on `ceph-bootstrap.service` + `mios-ceph-bootstrap.service` to a **config-flag gate** (`[storage.cephfs].enable` / a `/run/mios/ceph-enabled` flag) instead of a hardware gate; the local **20 GiB `/var/home` ext4 partition** already carved by `config/artifacts/vhdx.toml` is the automatic `nofail`+`ConditionPathExists` fallback when Ceph is down (no new code). dGPU via **DDA** (recommended — the 9950X3D iGPU carries the Windows desktop so the whole discrete GPU goes to MiOS) or **GPU-P** (shared, keeps Windows on the dGPU). WSL2 `--import-in-place` is an explicit **disposable preview only** (still no populated `/var` → not the sovereign target; needs a WSL preset masking the bootc-host units).
- **Why:** Confirmed root cause — a bootc image bakes **nothing** into `/var` (Law 2: `/var` is *declared* via tmpfiles, *materialized* at install/first-boot); only the installer populates it. A raw `podman export`/`wsl --import` of a bare rootfs deadlocks on the `bootc-*`/`ostree-*`/composefs host units (no deployment substrate) and has no `/var/home`. Hyper-V Gen 2 is the only candidate that is simultaneously a true bootc host (real UEFI/GPT + populated `/var/home` + honored kargs + working `bootc upgrade`/`rollback`), runs in place off M: as a single dynamically-expanding file, is native to Windows 11 Pro, and can feed the heavy lanes the real dGPU. QEMU-WHPX has no PCI passthrough (heavy lane → CPU); WSL runs the MS kernel and bypasses the bootloader.
- **Files:** `Justfile` (new `vhdx-m` recipe, ~L217), `config/artifacts/vhdx.toml` (unchanged; optionally bump root 150→200 GiB), `usr/lib/systemd/system/ceph-bootstrap.service` + `mios-ceph-bootstrap.service` (`ConditionVirtualization=no` → config gate), `usr/libexec/mios/ceph-bootstrap.sh` (add OSD-on-`/dev/sdb` + fs creation), `usr/share/mios/mios.toml [storage.cephfs].enable`, `usr/lib/systemd/system-preset/95-mios-wsl.preset` (WSL fast-shim, optional), `C:\mios-bootstrap\deploy-mios-hyperv-m.ps1` (new).
- **Accept:** a MiOS Gen 2 VM boots off `M:\MiOS-images\mios-0.3.0.vhdx` with a populated `/var/home`, `bootc status` healthy, and `curl http://localhost:8640/v1/models` answering from Windows via portproxy; with the OSD vhdx attached + `[storage.cephfs].enable=true`, `findmnt /var/home` reports `type ceph` and survives a root-vhdx rebuild; `nvidia-smi` + a heavy-lane inference call succeed in-guest; `bootc upgrade`/`rollback` work.
- **Deps:** re-establish a Linux podman once (BIB/`bootc install` need it); operator decisions on GPU policy (DDA vs GPU-P), Ceph-now-vs-later, OSD sizing, and the `ConditionVirtualization` scope (prefer the flag-file gate over a blanket removal so transient CI VMs don't auto-enable Ceph). VM/operator-gated.


# Storage & Data

*(no active workstreams)*

# Security & Identity

*(no active workstreams)*

# Desktop & UX

*(no active workstreams)*

# Fleet & Federation

## WS-RELTOP — Release topology: GitHub ≡ Forgejo equal publishers; `PUBLISH` capacity gate
<!--
id: WS-RELTOP
title: Release topology: GitHub ≡ Forgejo equal publishers; PUBLISH capacity gate
theme: Fleet & Federation
status: active
priority: P2
laws: [7, 8]
ssot_keys: ["build.curl_trigger_fallback"]
adr: [4]
deps: [WS-MIOSSYS]
acceptance: |
  GitHub and Forgejo are equal publishers; PUBLISH capacity gates the bake on standard runners.
-->

**✅ DONE this session (for CI):** GitHub Actions (`.github/workflows/mios-ci.yml`) and the self-hosted Forgejo runner (`.forgejo/workflows/build-mios.yml`) are declared EQUAL, bit-for-bit build/publish environments (both `podman build`, identical OCI manifests) — neither subordinate. Build is LOCAL-first (MiOS-DEV, 707 GB, bakes the full fleet). `mios-ci.yml` carries a workflow-level `PUBLISH: 'false'` env (L38) — a **capacity** gate, NOT a demotion: a standard `ubuntu-24.04` runner (~66 GB `/mnt`) cannot hold the ~60 GB baked store (one `buildah commit` → exit 125), so GitHub build+lint VALIDATES only while the 707 GB Forgejo runner (and the local build) bake. `PUBLISH` gates the `MIOS_BAKE_BOUND_IMAGES` build-arg (L243) + the rechunk/push/cosign steps (L270+); flip to `'true'` once a runner can hold the bake — or, decisively, after WS-MIOSSYS shrinks the store to ~25 GB so a standard GitHub runner bakes+publishes as a full equal.

### RELTOP-01 — Wire "default-to-GHCR-if-creds-else-local/Forgejo" registry selection into the build driver  **[P2]**
- **What:** Implement the registry-selection logic that both workflows currently hardcode as `ghcr`: default to GitHub/GHCR push+pull when credentials are present, else the local/Forgejo registry. Locate it in the build driver / `install.env` credential detection so both CI environments and the local build resolve the registry the same way.
- **Why:** The topology directive says registry preference is credential-driven, but `mios-ci.yml`/`build-mios.yml` currently hardcode GHCR; the selection belongs in one shared place, not duplicated per workflow.
- **Files:** `.github/workflows/mios-ci.yml`, `.forgejo/workflows/build-mios.yml`, the build driver (`automation/build.sh` / `install.env` credential detection).
- **Accept:** a build with GHCR creds present pushes/pulls GHCR; with none it targets the local/Forgejo registry; both CI runners and the local build share the one selection path; no hardcoded registry remains outside it.
- **Deps:** CI capacity-gate DONE; the `PUBLISH:'true'` flip is unblocked by WS-MIOSSYS.


