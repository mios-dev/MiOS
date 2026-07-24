<!-- AI-hint: MiOS -- Master Roadmap (SINGULAR monolith)
     AI-related: /usr/lib/mios/bake/plan.d/NN-, /etc/mios/blade.d/, /usr/share/mios/artifacts/sbom/bound-images.tsv, /usr/libexec/mios/miosd, /usr/share/mios/vllm/model, mios-bake-group, mios-bakescratch, mios-llm-heavy, mios-llm-heavy-alt, mios-dropin-fanout -->
# MiOS -- Master Roadmap (SINGULAR monolith)

> The one canonical roadmap. Absorbs all former top-level `*-PLAN-*.md` + `concepts/*` planning docs. Workstreams map to `T-*` in TASKS.md.

<!-- ROADMAP_ROLLUP_START -->
### Workstream Status Rollup
- **Done**: 13
- **Active**: 0
- **Proposed**: 3
- **Blocked**: 0
<!-- ROADMAP_ROLLUP_END -->

<!-- ROADMAP_INDEX_START -->
### Workstream Index

**OS-Image & Build**
- `WS-BAKEGATE` — Two-gate model: [build.bake] core allow-list + projected bake-plan ✅
- `WS-BLADE` — Universal-core + blade-type ACTIVATION gate (one image, role by flag) ✅
- `WS-MIOSSYS` — MiOS-Sys shared-base consolidation of the sidecar fleet ✅
- `WS-SBOM` — SBOM-not-hardcode: digests/hashes are build-time provenance, never SSOT literals ✅
- `WS-DOCS` — Planning-docs refactor: ADR system + generated index ✅
- `WS-LANG` — Language-per-domain unification — Rust for native tooling, bash demoted to thin glue (proposed)
- `WS-TEMPLATE` — Compiled file-pattern system — one template per file type + conformance check + Law-14 ✅
- `WS-DEBT` — Technical-debt register — TD-1..TD-8 (shell-mass, version drift, resolver twin, monolith decomposition) (proposed)

**AI-Plane & Orchestration**
- `WS-DEPRED` — AI-plane dependency reduction (Hermes→agent-pipe collapse + sidecar consolidations) ✅

**Deployment & Sovereignty**
- `WS-MDRIVE` — Sovereign "run off M:" deployment (Hyper-V Gen 2 .vhdx + Ceph OSD on M:) (proposed)
- `WS-CAT` — MiOS-Cat unified entry point (one tri-launcher, six verbs, all-platform) ✅
- `WS-CATREPO` — Small MiOS-Repo shadow-config + separate MiOS-Data bulk store (512GB+) + model embedding ✅
- `WS-CATFLAT` — MiOS-Cat tree flatten, de-dup, leave-nothing-behind ✅
- `WS-CONFIG` — Unified config surface: mios.toml ⇄ Portal + configurator + /v1 at :8640/ ✅

**Storage & Data**
(no workstreams)

**Security & Identity**
(no workstreams)

**Desktop & UX**
- `WS-DOTFILES` — SSOT-as-system-dotfiles — one mios.toml projects every dotfile on every platform ✅

**Fleet & Federation**
- `WS-RELTOP` — Release topology: GitHub ≡ Forgejo equal publishers; PUBLISH capacity gate ✅
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
status: done
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
status: done
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
status: done
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
status: done
priority: P2
laws: [7, 8]
ssot_keys: ["image.sidecars"]
adr: [3]
deps: [WS-MIOSSYS]
acceptance: |
  no hand-pinned digests remain in mios.toml; build resolves and records to SBOM.
-->

**✅ DONE (images + model/package/binary hashes):** SSOT (`mios.toml`) refs now carry the TAG intent only (`:latest` = "track newest globally", or a bare version) — a hand-written `@sha256:…` is a hardcode (Law 7). ALL 12 hand-pinned `@sha256` digests were stripped from `mios.toml` (verified: 0 remaining); the 27 rendered Quadlets were regenerated digest-free (verified: 0 `@sha256` in `usr/share/containers/systemd/`; the digest-drift gate is green); and `usr/libexec/mios/mios-bake-group` now resolves each `:latest` at pull time and records `<image>\t<digest>\t<group>` to `/usr/share/mios/artifacts/sbom/bound-images.tsv` (L173-178) — reproducibility comes from the SBOM + baked OCI manifest, not from SSOT digests. This **reverses** the older "pin `@sha256` in `[image.sidecars]` for reproducible builds" convention.

### SBOM-01 — Extend build-time provenance beyond images (model checksums, package version-hashes)  **[P2] ✅ DONE**
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
status: done
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

### DOCS-02 — WS metadata schema + `roadmap-index.py` generator + drift-check  **✅ DONE this session**
- **What:** Give every `WS-*` machine-parseable frontmatter (`id, title, theme, status, priority, laws[], ssot_keys[], adr[], deps[], acceptance`) — KEP-style. Add `tools/roadmap-index.py` that regenerates the top Part/WS index + a status rollup (proposed/active/blocked/done counts) + the Table-of-Contents **from that frontmatter** (fixes the hand-truncated ToC that stops at Part 12), plus a drift-check (`automation/38-drift-checks.sh check_roadmap_index`) that fails if the index is stale or a WS cites a non-existent ADR/law/`ssot_key`. Law-8 SSOT-PROJECTION applied to the planning docs themselves.
- **Files:** `ROADMAP.md` (per-WS frontmatter), `TASKS.md`, new `tools/roadmap-index.py`, `automation/38-drift-checks.sh`.
- **Accept:** `just drift-gate` regenerates the index byte-identically; a WS with a bad `adr:`/`laws:` ref fails the gate; the ToC lists all Parts.
- **Deps:** DOCS-01.

### DOCS-03 — Lean thematic `ROADMAP.md`; archive Parts 1–20 losslessly  **✅ DONE this session**
- **What:** Split the 2,900-line monolith. Keep `ROADMAP.md` as the **current, forward-looking** roadmap grouped by **theme/pillar** (the MiOS "SIGs": OS-Image & Build · AI-Plane & Orchestration · Deployment & Sovereignty · Storage & Data · Security & Identity · Desktop & UX · Fleet & Federation), listing only `proposed/active/blocked` WS. Move the historical/absorbed Parts 1–20 (and every `done` WS) losslessly to `usr/share/doc/mios/roadmap/history/` (dated). Part 21's WS become the seed of the new active roadmap under their themes.
- **Files:** `ROADMAP.md`, `usr/share/doc/mios/roadmap/history/*.md`, `CHANGELOG.md`.
- **Accept:** `ROADMAP.md` is theme-grouped + active-only (~≤600 lines); every archived Part is retrievable under `history/`; the generator's WS rollup total is conserved (nothing lost).
- **Deps:** DOCS-02.

### DOCS-04 — Status-lifecycle retag (honest done-vs-gated) + cross-ref backfill  **✅ DONE this session**
- **What:** Re-tag every WS to the lifecycle with the 2026-06-22 honesty rule formalized: **`done` = active AND live-fired**, never "built-but-gated" (those become `blocked`/`active`). Backfill each WS's `laws[]`/`ssot_keys[]`/`adr[]` so the cross-reference graph (WS↔T↔ADR↔Law↔SSOT-key) is complete + drift-checkable.
- **Files:** `ROADMAP.md`, `TASKS.md`.
- **Accept:** no WS tagged `done` that is gated-off/never-fired; every `done` claim carries a live-evidence line; the cross-ref drift-check (DOCS-02) passes.
- **Deps:** DOCS-02.

### DOCS-05 — Diátaxis reorg of `/usr/share/doc/mios` + `CHANGELOG.md` + agent-context refresh  **✅ DONE this session**
- **What:** Align the whole doc tree to **Diátaxis** quadrants — *tutorial* (day-0/first-boot), *how-to* (`guides/`), *reference* (`api.md`, `mios.toml`, the ports/laws registries), *explanation* (`concepts/`, `adr/`, `roadmap/`). Add a top-level `CHANGELOG.md` (Keep a Changelog + SemVer) fed from `bootc`-version bumps. Refresh `llms.txt` + `AGENTS.md` so an arriving agent is routed in ≤3 hops: current roadmap → ADR index → SSOT → the 13 laws.
- **Files:** `usr/share/doc/mios/**`, `CHANGELOG.md`, `llms.txt`, `AGENTS.md`.
- **Accept:** each doc sits in exactly one Diátaxis quadrant; `llms.txt` resolves an agent to the current-state entry points in ≤3 hops.
- **Deps:** DOCS-03.


## WS-LANG — Language-per-domain unification (Rust for native tooling; bash demoted to thin glue)
<!--
id: WS-LANG
title: Language-per-domain unification — Rust for native tooling, bash demoted to thin glue

> [!NOTE]
> **Implementation Note (AGY-51):** The native Rust workspace has been scaffolded at `tools/native/` (containing the `mios-version-check` crate). Since no Rust toolchain is present in the host environment, the binary compilation is deferred via `TODO(agy): cargo build`.
>
> **Update (Law 14 landed):** `[laws]` Law 14 **TARGET-LANGUAGES** now MANDATES the language-per-domain contract globally (all platforms), enforced by drift-gate 63 (`check_target_languages`) — no new C#/Batch/Go; existing C# grandfathered in `[laws.target_languages]`. Rust is now **provided as a dependency**, installed during staging via the shared installer contract (`Install-MiosRust` on Windows — winget/rustup-GNU, no MSVC; `mios_ensure_rust` on Fedora — dnf/rustup), so every native component builds on any Windows or Fedora machine. **Next (T-275):** port the first user-facing native component — consolidate the WebView2 wallpaper host + WSLg gui-watch into ONE silent Rust daemon (`wry` WorkerW host + `windows-service`), dropping the Run keys + the terminal/window flash.
-->
theme: OS-Image & Build
status: proposed
priority: P1
laws: [7, 8, 9]
ssot_keys: []
adr: [11]
deps: [WS-DEBT]
acceptance: |
  the correctness-critical orchestration/validation logic (drift-runner, resolver
  core, build driver, verb dispatcher, installer core) moves into one memory-safe
  Rust `miosd` binary invoked by unchanged thin RUNs; the 66 OS-touching steps stay
  shell-thin; the AI plane stays Python; Batch/C# eliminated. Law 8 strengthened.
-->
*Language-per-domain contract (ADR-0011 §2): **Rust** default native tier for tooling/orchestration/validation; **bash** stays thin glue only (the 66 `automation/NN-*.sh` steps, held to the `bash` template); **Python** for the AI plane; **Bun/TS** for the web Portal; TOML SSOT · YAML pipelines · Markdown docs. Go rejected as a second native tier (documented escape hatch only); Batch eliminated; C# `mios-launch.cs` folded into the Rust installer core. All proposed; nothing landed.*

### LANG-01 — Stand up the Rust workspace + port the first fragile bash tool (drift-runner or verb dispatcher)  **[P1]**  (→ T-272)
- **What:** Create the cargo workspace (subcommands `build|drift|verb|resolve|render|cat|scaffold|fmt` → one `miosd` static musl binary) built once in an early cached Containerfile stage and `COPY`'d to `/usr/libexec/mios/miosd`, invoked by **thin RUNs** so the immutable-image contract holds. Port the **first** fragile bash tool — the drift-runner (highest resilience win, lowest coupling; several checks are already Python-in-bash) or the verb dispatcher (removes the 9-verb `eval`-on-agent-args surface) — running old+new side-by-side and diffing to identical before deleting the bash. Collapse the `mios_toml.py` ⇄ `userenv.sh` resolver twin into one crate (`--shell` KEY=VAL emitter + pyo3 face) to end the Law-13 parity drift.
- **Why:** The correctness-critical logic is trapped in fragile bash/batch (44-check drift file in ~3.1k-ln bash, 579-ln build driver, ~150 verb scripts, the resolver twin with no generator binding it). Rust yields a static, single-digit-MB, memory-safe binary cross-compiling to Windows — and one native language serves the "learn from a few files" goal (Law 8) better than two.
- **Files:** the new cargo workspace (location OPEN — `C:\MiOS\src\` is occupied by `mios-launch.cs`+`autounattend/`; candidate `C:\MiOS\tools\native\` or `src\mios-rs\`), `Containerfile` (early Rust stage + `COPY`), `automation/build.sh` (→ thin shim), `automation/38-drift-checks.sh` (checks ported one at a time), `usr/lib/mios/mios_toml.py` + `tools/lib/userenv.sh` (collapse to the crate), the ~150 verb backends.
- **Accept:** `miosd` bakes in a cached stage and is invoked by unchanged thin RUNs; the first ported tool runs byte-identical to the bash it replaces, then the bash is deleted; the resolver twin is one crate with pyo3 + `--shell` faces and `check_userenv_parity` is retired.
- **Deps:** WS-DEBT Phase −1 (shellcheck gate + one version token + one TOML reader unblock the port). ADR-0011. **OPEN QUESTIONS:** native-workspace location; Go escape-hatch; pyo3-vs-subprocess for the AI-plane resolver binding.


## WS-TEMPLATE — Compiled file-pattern system (one template per file type + conformance check + Law-14)
<!--
id: WS-TEMPLATE
title: Compiled file-pattern system — one template per file type + conformance check + Law-14
theme: OS-Image & Build
status: done
priority: P1
laws: [7, 8, 9]
ssot_keys: []
adr: [11]
deps: []
acceptance: |
  ~15 compiled templates (one per authored file type) under usr/share/mios/templates/,
  a `mios new <type>` scaffolder, a golden round-trip compiler, and a
  check_template_conformance drift-check that validates header AND body structure;
  candidate Law 14 (ONE-TEMPLATE-PER-TYPE) registered + enforced (operator-gated).
-->
*A global compiled-template system (ADR-0011 §3) formalizing/extending the AI-hint convention so an agent learns MiOS formatting from a few files. A template = the shared AI-hint header block (produced by the same `mios-ai-tag` engine) + a small per-type body skeleton whose structure is also validated (closing the gap where only the header is checked). Done.*

### TEMPLATE-01 — `usr/share/mios/templates/*.tmpl` (~15) + `mios new <type>` + golden compiler + `check_template_conformance` + candidate Law-14  **[P1]**  (→ T-271)
- **What:** Author ~15 compiled templates (`bash`, `python-tool`, `python-module`, `rust`, `typescript`, `powershell`, `toml-config`, `yaml`, `json-schema`, `markdown-doc`, `adr`, `roadmap`, `systemd-unit`, `quadlet` [generated], `automation-step`) under `usr/share/mios/templates/`, declared in SSOT (`[templates.<type>]`: `match`/`comment`/`required_header`/`required_markers`/`generated`/`scaffold`). Land the scaffolder first as Python `usr/libexec/mios/mios-new` (`mios new <type>`, reusing `mios-ai-tag` for the header, filling canonical fields — next ADR number, next `automation/NN` ordinal, canonical ports — from SSOT, and registering the canonical name), then absorb into `miosd scaffold`. Add a golden round-trip compiler (`tools/compile-templates.py`) and a `check_template_conformance` drift-check (delegating to a Python worker, mirroring `check_hint_coverage → mios-ai-hint-coverage`, degrade-open, soft→hard ratchet). `generated=true` types refuse to scaffold an editable file (scaffold the generator + its `mios.toml` section instead — Law 8 authoritative). **Candidate Law 14 (ONE-TEMPLATE-PER-TYPE):** per ADR-0007 add a `[laws]` row (id 14) + `check_template_conformance` as `enforced_by` — **operator-gated; the `[laws]` edit is deferred for confirmation.**
- **Why:** The AI-hint header + `mios-theme-render` prove the pattern but enforce it piecemeal (header only, no body structure). One compiled, golden-tested template per type makes every file *born from* and *validated against* enforced ground truth — so an agent learns all MiOS formatting from `templates/*.tmpl` + `[templates]`/`[ai_tag]`/`[laws]`. Law 8 mechanically enforced; Law 7/9 via the scaffolder filling canonical fields + registering the name.
- **Files:** `usr/share/mios/templates/*.tmpl` (new, ~15), `usr/share/mios/mios.toml` (`[templates]` schema; candidate `[laws]` id-14 row — operator-gated), `usr/libexec/mios/mios-new` (new; folds into `miosd scaffold`), `usr/libexec/mios/mios-ai-tag` (header machinery, reused), `tools/compile-templates.py` (new), `automation/38-drift-checks.sh` (`check_template_conformance`), `usr/bin/mios`/`Justfile` (`mios new`/`just new`).
- **Accept:** `mios new <type> <name>` produces a conformant file that passes `check_template_conformance` + the golden compiler; a template that can't produce a conformant file fails the build; the header check becomes the header-subset of conformance; Law-14 is proposed with its enforcement wired but the `[laws]` row awaits operator sign-off.
- **Deps:** none hard (Python-first, offline-deterministic); folds into WS-LANG's `miosd` once the Rust workspace exists. ADR-0011. **OPEN QUESTION:** Law-14 confirmation + the next free drift-check number.


## WS-DEBT — Technical-debt register (TD-1..TD-8)
<!--
id: WS-DEBT
title: Technical-debt register — TD-1..TD-8 (shell-mass, version drift, resolver twin, monolith decomposition)
theme: OS-Image & Build
status: proposed
priority: P1
laws: [7, 8, 9]
ssot_keys: []
adr: [11]
deps: []
acceptance: |
  the eight ranked debts (TD-1..TD-8) are tracked with owners + remediation tasks;
  the top three (TD-1 enforce documented conventions, TD-2 collapse version/SSOT to
  one value, TD-3 one TOML reader) land first as near-zero-risk Phase −1 wins that
  unblock the WS-LANG/WS-TEMPLATE work.
-->
*The technical-debt register grounding ADR-0011, re-measured against the live `C:\MiOS` + `C:\mios-bootstrap` trees (server.py=8,961 ln; 44 drift-checks; 3× mios.toml with root=0.2.4 vs SSOT/VERSION=0.3.0; C#/.NET already in-tree at `C:\MiOS\src\mios-launch.cs`). Ranked by severity × reach; the top three are the near-zero-risk Phase −1 prerequisites. All proposed.*

- **TD-1 (Critical) — Fragile-shell mass, conventions documented but not enforced.** ~15k LOC bash across the build chain + ~116 bash verbs; `shellcheck` is only `# shellcheck source=` comments (no CI lint job); 23 verbs lack `set -e`; **9 `eval` on agent-derived args** (injection surface); the 44-check gate is itself fragile bash+grep. → **T-269**.
- **TD-2 (Critical) — Version/SSOT duplication at conflicting values.** 3× `mios.toml` (canonical 10,869 ln vs two ~1.4k-ln roots); `VERSION`/SSOT `mios_version`=0.3.0 but root `C:\MiOS\mios.toml`=**0.2.4**; **37× hardcoded `v0.2.4`** headers; cross-repo divergence of `Get-MiOS.ps1`/`build-mios.ps1`/`mios.toml`/`CLAUDE.md`. Violates Law 9 / ADR-0009. → **T-268**.
- **TD-3 (High) — Hand-rolled parsing of structured formats.** `[packages.*]`/`mios_version`/`enable=` parsed with bespoke `awk`/`grep -m1`/`sed`; JSON via inline `python3 -c`; the **Law-13 resolver twin** (`mios_toml.py` ⇄ `userenv.sh`) must produce byte-identical env with no generator binding them. → folded into WS-LANG (T-272, resolver-core crate).
- **TD-4 (High) — Network-at-build-time, unpinned, WARN-gated-forever.** `55-bake-quickshell.sh`/`56-bake-surfer.sh` clone default branches + build; `build.sh` `NON_FATAL_SCRIPTS` swallows non-zero from ~23 phases. (Remediation: WARN→FAIL on the critical path + pin the bakes; `automation/90-generate-sbom.sh` deliberately out of scope here.)
- **TD-5 (High) — AI-plane decomposition half-finished.** `server.py` is an 8,961-ln god-module; the `mios_pipe/` refactor never reached the 4 largest flat modules incl. `mios_dispatch.py` (the security-critical verb→bash chokepoint); 558 `except Exception` + 9 bare `except:`. → **T-273**.
- **TD-6 (High) — Installer language sprawl + Batch crash-class + quadruplication.** `MiOS-Cat.bat` 1,288 ln / 238 `goto`; MiOS-Cat exists 4×; `build-mios.ps1` 615 KB; the unaccounted C# `mios-launch.cs`. → WS-LANG (installer core → `miosd cat`; retire `.bat`+C#). *(MiOS-Cat files owned by a concurrent agent — not touched here.)*
- **TD-7 (Medium) — Ordinal-filename + substring coupling in the chain.** Duplicate ordinals (three `35-*`, five `38-*`); fatal/non-fatal policy is hand-maintained blobs matched by `grep -qF`. → WS-LANG (build driver owns order/gating/DAG).
- **TD-8 (Low-Med) — Doc/metric over-claim drift + working-tree cruft.** `server.py` "~26k" (actual 8.1k) with no re-derivation gate; ~15 MB gitignored-but-present cruft confuses agents. → the metric-re-derivation gate under WS-TEMPLATE/WS-DEBT.

### DEBT-01 — Phase −1: collapse version/SSOT to one value (TD-2)  **[P1]**  (→ T-268)
- **What:** Strip literal `vX.Y.Z` from all `automation/*.sh` headers; make the two root `mios.toml` (`C:\MiOS\mios.toml` 0.2.4, `C:\mios-bootstrap\mios.toml`) generated projections of the SSOT or delete them; add drift-checks "no literal version in headers" + "root ⊆ SSOT". Near-zero-risk; the highest-reach silent-failure class (a build resolving the wrong copy gets a stale, 7×-smaller manifest).
- **Why:** Every build and every reader can currently bind the wrong version fact. Directly closes a Law 9 / ADR-0009 violation and unblocks the rest.
- **Files:** `C:\MiOS\VERSION`, `C:\MiOS\mios.toml`, `C:\mios-bootstrap\mios.toml`, `usr/share/mios/mios.toml`, all `automation/*.sh` headers, `automation/38-drift-checks.sh` (new checks).
- **Accept:** one authoritative version token; no literal `v0.2.4`/`v0.2.0` in headers; the root `mios.toml` copies are generated-or-deleted and drift-gated; a build can no longer resolve a stale copy.
- **Deps:** none. ADR-0011.

### DEBT-02 — Phase −1: shellcheck CI gate + kill the 9 `eval`-on-agent-args verbs (TD-1)  **[P1]**  (→ T-269)
- **What:** Add a `shellcheck -S warning` CI job over `automation/` + `usr/libexec/mios/` bash; enforce `set -euo pipefail` on the 23 unguarded verbs; audit + eliminate the 9 `eval`-on-agent-derived-args sites (the injection surface on the agent-facing OS-control plane).
- **Why:** The repo documents the conventions (`# shellcheck source=`, `set -e` intent) but never enforces them; the `eval` sites are the highest-severity security debt on the verb chokepoint.
- **Files:** `.github/workflows/mios-ci.yml`, `Justfile`, the 23 unguarded + 9 `eval` verbs under `usr/libexec/mios/`.
- **Accept:** CI fails on a shellcheck warning; the 23 verbs carry `set -euo pipefail`; zero verbs `eval` on agent-derived args.
- **Deps:** none. ADR-0011. Interlocks with WS-LANG (the verb dispatcher port removes the `eval` surface structurally).

### DEBT-03 — Split `mios_dispatch.py` + finish the server.py decomposition (TD-5)  **[P2]**  (→ T-273)
- **What:** Split `mios_dispatch.py` (the security-critical verb→bash chokepoint every verb passes through) out of the 8,961-ln `server.py` monolith into `mios_pipe/`; continue the flat-module extraction (VRAM scheduler, `_db_*`, auth middleware, agent streaming); replace the 9 bare `except:`; add a new gate "no Python file > 800 lines".
- **Why:** The `mios_pipe/` refactor (103 files, 100% hint-tagged) never reached the 4 largest flat modules; the debt is the monolith + the highest-privilege dispatch chokepoint, not the language (Python stays — Law 6).
- **Files:** `usr/lib/mios/agent-pipe/server.py`, `usr/lib/mios/agent-pipe/mios_dispatch.py`, `usr/lib/mios/agent-pipe/mios_pipe/**`, `automation/38-drift-checks.sh` (>800-line gate).
- **Accept:** `mios_dispatch.py` is extracted and live (`check_unwired_modules` confirms); `server.py` shrinks toward a <800-line composition root; no bare `except:`; the line-length gate is green.
- **Deps:** independent track (Python, pure refactor). ADR-0011.


---

## Appendix: Absorbed sources (2026-07-10 consolidation)

ROADMAP.md + TASKS.md are now the **singular** planning SSOT. Folded in:
- **9 top-level `*-PLAN-*.md`** (2026-06-14/15) → **Part 17 / T-167–T-177**. Originals archived under `usr/share/doc/mios/archive/absorbed-plans-2026-06/`.
- **~28 `usr/share/doc/mios/concepts/*` docs** → **Part 18 / T-200–T-241** (actionable deltas); the ~24 pure-reference/architecture docs are kept in place and cross-referenced from their Part.
  - [deploy-model.md](file:///c:/MiOS/usr/share/doc/mios/concepts/deploy-model.md) — Mutable Fedora/FHS overlay, immutable bootc, and virtualized VM/Xbox/Windows execution modes.
- Live dGPU heavy-lane diagnosis → **Part 19 / T-178**.
- Retired the old `combine_roadmaps.py` script.

A master index sits at the top of each file; every task carries **Who / What / Where / When / How** + Done-When.

# AI-Plane & Orchestration

## WS-DEPRED — AI-plane dependency reduction (Hermes→agent-pipe collapse + sidecar consolidations)
<!--
id: WS-DEPRED
title: AI-plane dependency reduction (Hermes→agent-pipe collapse + sidecar consolidations)
theme: AI-Plane & Orchestration
status: done
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


## WS-CAT — MiOS-Cat unified entry point (one tri-launcher, six verbs, all-platform)
<!--
id: WS-CAT
title: MiOS-Cat unified entry point (one tri-launcher, six verbs, all-platform)
theme: Deployment & Sovereignty
status: done
priority: P1
laws: [1, 7, 8, 9, 12]
ssot_keys: ["cat", "cat.repo_partition", "cat.data_partition", "editions", "colors"]
adr: [8]
deps: [WS-MDRIVE]
acceptance: |
  one tri-launcher (.ps1/.sh/.bat) exposes stage/install/build/update/provision/manual
  identically across shells; every legacy entry point becomes a verb back-end;
  `cat install` is headless-identical; the [cat] SSOT block resolves (no dangling
  drivepath/medicatver/cache_path reads).
-->

### CAT-01..04 — Flatten + single-owner · verb dispatch + tri-launcher parity · `[cat]` SSOT + dangling-read fix · fold the web one-liners  **[P1]**  (→ T-256..T-259)
- **What:** Make MiOS-Cat the ONE front door for all of MiOS. (1) `mios-bootstrap` owns MiOS-Cat canonically at `cat/` — `git mv` the deep `src\autounattend\medicat_installer\` nest up to `cat\`, **delete** the byte-identical `C:\MiOS` copy (Law 1 / two-repo rule). (2) One tri-launcher (`MiOS-Cat.{ps1,sh,bat}`) dispatches six SSOT-projected verbs — **stage · install · build · update · provision · manual** — under which every existing entry point (`Get-MiOS.ps1` irm|iex, `bootstrap.{ps1,sh}` curl, the UUP/autounattend ISO pipeline, `mios-kickstart.cfg`, the `just` build) becomes a *sub-system*, not a peer; port the advanced `.bat` logic (MiOS-Repo staging, WinPE DISM, self-update) into the canonical `.ps1` (Law 9 parity), reduce `.bat` to the WinPE/cmd shim. (3) Add a `[cat]` block to `mios.toml` (`drivepath`/`medicatver`/`cache_path`/`repo_partition`/`data_partition`/`models`) and repoint MiOS-Cat to resolve the real 597 KB SSOT — fixing the dangling reads that silently hardcode today (Law 7/8). (4) Collapse `Get-MiOS.ps1`/`bootstrap.{ps1,sh}`/`install.*` bodies to thin `cat install` shims and wire the bidirectional `irm⇄curl` handoff (same front door, two shells).
- **Why:** ~6 parallel install/deploy entry points, none authoritative; the MiOS-Cat tree buried 3–5 levels deep and byte-identical across both repos (a Law-1 problem — `C:\MiOS/usr/` *is* `/usr`); and `drivepath`/`medicatver`/`cache_path` reference keys absent from any `mios.toml` → silent hardcoded fallbacks. One owner, one verb vocabulary, one SSOT is the Law 9 closure on the entry surface.
- **Files:** `C:\mios-bootstrap\cat\MiOS-Cat.{ps1,sh,bat}` + `cat\lib\`, `C:\mios-bootstrap\{Get-MiOS,bootstrap,install}.ps1` + `bootstrap.sh`, `C:\MiOS\src\autounattend\medicat_installer\**` (delete), `usr/share/mios/mios.toml` (`[cat]`), `automation/38-drift-checks.sh` (new `[cat]`/`[colors]`-resolve check).
- **Accept:** one MiOS-Cat home; `C:\MiOS` free of the installer (`diff` finds no cross-repo dup); `cat install` is headless-identical across `.ps1`/`.sh`/`.bat`; `irm …/cat | iex` and `curl …/cat.sh | sh` reach the same verb set; no MiOS-Cat value is hardcoded that has an SSOT home.
- **Deps:** `WS-MDRIVE` supplies the deployment mechanism (`cat install --target hyperv|wsl` delegates to `just vhdx-m` / `deploy-mios-hyperv-m.ps1` / `just wsl2` verbatim — MiOS-Cat only fronts it). ADR-0008.


## WS-CATREPO — Small MiOS-Repo shadow-config + separate MiOS-Data bulk store (512GB+) + model embedding
<!--
id: WS-CATREPO
title: Small MiOS-Repo shadow-config + separate MiOS-Data bulk store (512GB+) + model embedding
theme: Deployment & Sovereignty
status: done
priority: P1
laws: [8, 12]
ssot_keys: ["cat.repo_partition", "cat.data_partition", "cat.models", "ai.bake_models", "ai.vllm.bake_model"]
adr: [8]
deps: [WS-CAT, WS-BAKEGATE]
acceptance: |
  a SMALL always-present MiOS-Repo partition carries the shadow-config brain
  (mios.toml + mios.html + Portal + MiOS-Cat + a small repos-clone); a SEPARATE
  MiOS-Data store (created only on 512GB+ disks) carries the bulk (OCI tar +
  just-all artifacts + model weights + dnf/flatpak/pip mirrors); `cat provision`
  brings a host up fully-featured with ZERO network (Law 12).
-->

### CATREPO-01 — Small MiOS-Repo shadow-config partition (always) + degrade-open fallback  **[P1]**  (→ T-260)
- **What:** `cat stage` populates a SMALL always-present `MiOS-Repo` partition (P3, target ~≤16 GB) with the **shadow-config brain**: `mios.toml` (SSOT), `mios.html` (configurator), the MiOS Portal assets, a self-contained MiOS-Cat copy, and a **small repos-clone** (config/source — not the binary payload). This is the offline embodiment of the ADR-0009 shareable-link surface. Each payload class is degrade-open (online `git clone` → offline copy from `MiOS-Repo/repos/`). **Fix the kickstart path mismatch:** the `.bat` stages repos to one path but `mios-kickstart.cfg` looks under another — align both to a canonical `MiOS-Repo/repos/`. Ventoy-bootable ISOs/WIMs stay on the Ventoy data partition.
- **Why:** The brain (config + Portal + Cat + a small clone) is tiny and belongs on every stick; forcing the 78 GB bulk onto the same "MiOS-Repo" tier bloated every USB and broke the small case. Keeping MiOS-Repo small + always-present is what makes "a link + a stick + a computer" honest.
- **Files:** `cat\MiOS-Cat.{ps1,sh}` (`cat stage`), `usr/share/mios/mios.toml` (`[cat].repo_partition`), `mios-kickstart.cfg` (`%post` repo path), the `MiOS-Repo/` layout.
- **Accept:** a small stick carries the shadow-config brain and a fully offline bare-metal kickstart install succeeds from `MiOS-Repo/repos/`.
- **Deps:** `WS-CAT` (verb engine + `[cat]` SSOT). ADR-0008.

### LOGBOOT-01 — harden+complete the RAG-artifact bootstrap logger  **[P2] ✅ DONE**  (→ T-287)
- **What:** `tools/log-to-bootstrap.sh` publishes the AI-RAG artifacts + wiki to the MiOS-bootstrap repo. Its generated `README.md`/`manifest.json` still advertised the **purged** ollama runtime + the `localhost:11434` native API. Retargeted to the MiOS **`/v1`** lane (Hermes gateway `:8642`, OpenAI-compatible; `mios-llm-light`/`heavy`), added `--retry` to the example call, and switched knowledge-graph injection to `jq --rawfile` (valid JSON). Endpoint is the SSOT `MIOS_AI_ENDPOINT`, not a hardcode.
- **Follow-on:** AGY-103 hardens the PRODUCER of `artifacts/ai-rag/` to match (SSOT-driven, no purged-runtime refs).
- **Files:** `tools/log-to-bootstrap.sh`. Cross-ref: legacy-purge → /v1-only; ai-endpoint-canonical.

### CATREPO-FIX — repos wrongly staged onto MiOS-Data instead of MiOS-Repo  **[P1]**  (→ T-274)
- **Bug (live):** `cat stage` lands the `repos/` clone on the **MiOS-Data** partition — but MiOS-Data is for caches / models / user-DBs / dependencies ONLY. The config/source repos clone belongs on the small always-present **MiOS-Repo** partition (this is the concrete manifestation of the CATREPO-01 kickstart path mismatch).
- **Fix:** correct the staging path in `cat/MiOS-Cat.{bat,ps1}` so `repos/` → `MiOS-Repo/repos/`; assert nothing repo-class writes to MiOS-Data; align `mios-kickstart.cfg`.
- **Accept:** a fresh `cat stage` places `repos/` on MiOS-Repo, MiOS-Data holds only bulk/cache classes.

### CATREPO-02..04 — Separate MiOS-Data bulk store (512GB+) + model embedding + `cat provision` (Law 12) + offline mirrors  **[P1]**  (→ T-261..T-263)
- **What:** On disks ≥ 512 GB (`Get-Disk` gate), `cat stage` creates a **separate** `MiOS-Data` store carrying the **bulk**: the ~78 GB `podman save` OCI tar (offline `podman load`), the `just all` disk artifacts (`raw/iso/qcow2/vhdx/wsl2`, incl. the ADR-0005 VHDX), the `mios.toml`-defined **model weights**, and the offline `dnf`/`flatpak`/`pip` **mirrors** (`reposync`+`createrepo_c`, `flatpak create-usb`, `pip download`). Read the model SSOT keys (`[ai].bake_models` L5744/L6116, `[ai.vllm].bake_model` L6724, `[ai.sglang].bake_model` L6742), fetch+checksum into `MiOS-Data/models/` (never invent — Law 8; resolved-not-hardcoded — WS-SBOM pattern). `cat provision` copies weights to `/usr/share/mios/vllm/model` (+ the GGUF dir) offline. `cat update` re-pulls both stores when online and re-stamps `manifest.json`.
- **Why:** Law 12 (BAKE-NOT-FETCH) realized as offline provisioning — the OCI image bakes engines only (weights a-la-carte per ADR-0001/0002); MiOS-Data is the offline weight+package store so a host deploys fully-featured with zero network — the sovereignty guarantee. Separating bulk from the always-present brain means a 512 GB+ stick is fully offline while a small stick still deploys (degrade-open).
- **Files:** `cat\MiOS-Cat.{ps1,sh}` (`cat stage`/`cat provision`/`cat update`), `usr/share/mios/mios.toml` (`[cat].data_partition`, `[cat].models` → `[ai].bake_models`), `MiOS-Data/{images,models,dnf,flatpak,pip}/`, `automation/38-llamacpp-prep.sh` (checksum pattern).
- **Accept:** on 512 GB+, offline `podman load` + `bootc switch` from USB works; a deployed host's heavy lane comes up with zero network (the `config.json` weight gate present); an offline build/first-boot resolves all packages from USB.
- **Deps:** `WS-CAT`; `WS-BAKEGATE` (the bake-plan that defines what artifacts exist). Model-redistribution licensing is an OPEN QUESTION (ADR-0008 Consequences) — if disallowed, MiOS-Data stores a fetch manifest + checksums instead of weights. ADR-0008.


## WS-CATFLAT — MiOS-Cat tree flatten, de-dup, leave-nothing-behind
<!--
id: WS-CATFLAT
title: MiOS-Cat tree flatten, de-dup, leave-nothing-behind
theme: Deployment & Sovereignty
status: done
priority: P2
laws: [1, 8, 9]
ssot_keys: ["cat"]
adr: [8]
deps: [WS-CAT]
acceptance: |
  cat/ tracks source only; ~6 MB+ tracked cruft gone; no cross-repo double-track;
  a generated ADR root breadcrumb reaches the ADR index in ≤2 hops; drift-gate green.
-->

### CATFLAT-01..03 — Dead-weight purge + leave-nothing-behind · ADR root breadcrumb · seed-copy consolidation  **[P2]**  (→ T-264..T-266)
- **What:** (1) Delete tracked cruft (`Get-MiOS.ps1.bom-bak`, `commit*.patch`, `temp{,2}.txt`, `scratch.ps1`) after verifying no live consumer (flatten-campaign guardrail); drop committed Ventoy/7z/MediCat binaries (downloaded artifacts, not source) and keep the fetch-on-demand logic; fold MediCat i18n down to MiOS strings. (2) Generate an ADR root breadcrumb — `C:\MiOS\ADR.md` + `cat\ADR-0008.md` — from SSOT (Law 8, drift-checked), linked from `llms.txt`/`AGENTS.md`, so the record is discoverable near each repo root without moving the baked ADRs out from `/usr` (Law 1). (3) Resolve the `mios.toml` seed-copy question — the 63 KB `C:\MiOS\mios.toml` + 68 KB `C:\mios-bootstrap\mios.toml` seeds vs the 597 KB SSOT (which is canonical, which is generated); document + regenerate seeds; MiOS-Cat reads only the SSOT.
- **Why:** Leave-nothing-behind: `cat/` should track source only; the ADRs stay baked (Law 1) but need a root-discoverable pointer; the seed copies are the root cause of the dangling-read bug WS-CAT fixes and must be pinned down.
- **Files:** `C:\mios-bootstrap\cat\**` (cruft purge, i18n), `C:\MiOS\ADR.md` (generated), `cat\ADR-0008.md` (generated), `llms.txt`, `AGENTS.md`, `C:\MiOS\mios.toml` + `C:\mios-bootstrap\mios.toml` (seed provenance), the ADR breadcrumb generator (`roadmap-index.py`-class, Law 8).
- **Accept:** `cat/` tracks source only (~6 MB+ cruft gone); an agent reaches the ADR index from repo root in ≤2 hops; one documented SSOT + generated seeds; drift-gate green.
- **Deps:** `WS-CAT` (single-owner flatten must land first). ADR-0008.


## WS-CONFIG — Unified config surface: mios.toml ⇄ Portal + configurator + /v1 at :8640/
<!--
id: WS-CONFIG
title: Unified config surface: mios.toml ⇄ Portal + configurator + /v1 at :8640/
theme: Deployment & Sovereignty
status: done
priority: P1
laws: [5, 7, 8]
ssot_keys: ["portal", "ports.agent_pipe"]
adr: [9]
deps: []
acceptance: |
  mios.html configurator folds INTO the MiOS Portal, served at GET / on :8640
  alongside the OpenAI /v1 API; the Portal is the shareable-link front door; every
  deployment type/config reads/writes mios.toml through it (Laws 7/8).
-->

### CONFIG-01 — Fold `mios.html` into the MiOS Portal at `:8640/` (one web + API front door)  **[P1]**  (→ T-267)
- **What:** Fold the standalone configurator `mios.html` (`usr/share/mios/configurator/`) INTO the MiOS Portal as a configurator *view*, so `mios.toml` + `mios.html` + the Portal are ONE config surface served at `:8640/` by agent-pipe: `GET /` serves the Portal (with the configurator folded in) and `/v1/*` serves the OpenAI API — the SAME single front door (the ADR-0006 convergence). Wire read/write of `mios.toml` from the configurator view through `mios_portal.py`; the Portal "needs config too" resolves as *it is configured through the surface it is*. The Portal (`:8640/`, or its `[portal].public_host` hosted equivalent) is the shareable web LINK that bootstraps the whole pipeline (open → configure → deploy); the USB MiOS-Repo shadow-config (WS-CATREPO / ADR-0008) is its offline embodiment.
- **Why:** Two web surfaces (a standalone configurator + the Portal) meant two things to serve/secure and an ambiguous "where do I configure MiOS?" The Portal is already served by agent-pipe at `GET /` on `:8640`, and ADR-0006 already collapsed the API plane to `/v1` at the same port — folding the configurator in is the natural closure. Everything projecting from one `mios.toml` (Law 8) is what makes "one config surface" honest; addressed by key never literal (Law 7).
- **Files:** `usr/lib/mios/agent-pipe/mios_portal.py` (configurator view + `mios.toml` read/write), `usr/lib/mios/agent-pipe/server.py` (`GET /` + `/v1/*` one door), `usr/share/mios/portal/` (absorb the configurator UI), `usr/share/mios/configurator/mios.html` (folded in / retired standalone), `usr/share/mios/mios.toml [portal]` (L220), `tools/mios-portal-app/` (Android client → same `:8640/`).
- **Accept:** the configurator is a view within the Portal at `:8640/`; `GET /` (Portal) and `/v1/*` (OpenAI API) share the one door; every deployment type's config reads/writes `mios.toml` through the surface; the shareable link + the USB are the same surface online and offline.
- **Deps:** none hard (the Portal + `:8640` `/v1` already exist). Converges with `WS-DEPRED` (the single `:8640` front-door collapse) and is governed by ADR-0007. ADR-0009.


# Storage & Data

*(no active workstreams)*

# Security & Identity

*(no active workstreams)*

# Desktop & UX

## WS-DOTFILES — SSOT-as-system-dotfiles (projection registry + engine + both-sides gate)
<!--
id: WS-DOTFILES
title: SSOT-as-system-dotfiles — one mios.toml projects every dotfile on every platform
theme: Desktop & UX
status: done
priority: P1
laws: [1, 7, 8, 9, 13]
ssot_keys: ["dotfiles.registry", "colors", "theme", "appearance", "terminal", "identity", "btop", "shell", "editor", "git", "ssh"]
adr: [10]
deps: []
acceptance: |
  Every declared dotfile on Linux/Windows/WSL is render-generated from mios.toml
  via [dotfiles.registry.*] + mios-dotfiles-render and check-gated both sides;
  no dotfile is hand-typed; the operator overlay projects the same on every
  deployment. Extends (not replaces) the LANDED mios-theme-render + check-25
  palette/btop projection.
-->
*Generalizes the LANDED palette+btop projection into `mios.toml` = the cross-platform system dotfiles-as-code (ADR-0010). The proof of concept is already in the tree: `usr/libexec/mios/mios-theme-render` gained a **settings-surface** concept this session, `[btop]` (~60 keys) projects the whole `etc/btop/btop.conf` unified Linux+Windows, and drift-check 25 (`check_theme_projection`) auto-extended and is proven green. Everything below (the SSOT `[dotfiles.registry.*]` map, the live-HOME `apply` verb, the new `[shell]`/`[editor]`/`[git]`/`[ssh]` domains) is proposed.*

### DOTFILES-01 — `[dotfiles.registry.*]` map + `mios-dotfiles-render` (arbitrary-key, format-aware merge, live-HOME `apply`) + both-sides gate  **[P1]**  (→ T-270)
- **What:** Promote the hardcoded Python `SURFACES` dict into an SSOT-authored `[dotfiles.registry.<surface>]` map (per-platform `target.<os>`; `kind` = template/json-merge/registry/command/skip; `format`; `sources`; `platforms`; `condition`). Transcribe the existing color+btop surfaces first (pure refactor, check 25 stays green), then fork `mios-theme-render` → `mios-dotfiles-render`: registry from `mios_toml.load_merged()`, `@MIOS:<section>.<key>@` tokens, format-aware `merge` that preserves foreign keys (WT/VS Code `settings.json` never clobbered), per-platform target resolution, and a new **`apply`/`diff` verb writing to live HOME** (`~/.config`, `%USERPROFILE%`, `%LOCALAPPDATA%`). Add the new domains `[shell]`/`[editor]`/`[git]`(→`[identity]`, Law 9)/`[ssh]`(`secret_ref`). Generalize `check_theme_projection` (check 25) → `check_dotfiles_projection` over the full registry; add the Windows runtime half `Test-MiOSProjection`; collapse the scattered `Install-MiOS*` bodies into thin registry-driven `Sync-MiOSDotfiles` calls; add a `mios dotfiles apply/diff/drift` verb (`[verbs.dotfiles_*]`).
- **Why:** MiOS proved operator-defined-SSOT-projection for the palette + `[btop]` end-to-end, but every other dotfile (WT `settings.json`, `.gitconfig`, VS Code, shell rc, GTK, ssh) is hand-maintained or projected imperatively, and the `SURFACES` tuples can't express a per-platform target. This is the literal completion of the pattern (Law 8), layered (Law 1/13), one canonical name per surface (Law 9), no literals (Law 7).
- **Files:** `usr/share/mios/mios.toml` (`[dotfiles.registry.*]`, `[shell]`/`[editor]`/`[git]`/`[ssh]`), `usr/libexec/mios/mios-theme-render` (reference; forks to `mios-dotfiles-render`), `usr/libexec/mios/mios-sync-theme`, `usr/lib/mios/mios_toml.py` + `tools/lib/userenv.sh`, `automation/38-drift-checks.sh` (check 25 → `check_dotfiles_projection`), `Get-MiOS.ps1` (`Sync-MiOSDotfiles`/`Test-MiOSProjection`), `usr/bin/mios`.
- **Accept:** the color+btop surfaces are registry-driven with check 25 green; a `[theme].opacity` edit projects to Linux CSS + the WT `json-merge` block + the WSL bridge with foreign keys intact and both gates pass; `mios dotfiles apply` writes live HOME; no `Install-MiOS*` value is hand-typed that has an SSOT home.
- **Deps:** none hard; interlocks with WS-CONFIG (the Portal edits the `[dotfiles.registry.*]` map) and ADR-0005/0008 (the overlay carries across deployments). Secrets (`secret_ref`) and a deployment-type enum for `condition` are OPEN QUESTIONS (ADR-0010).


# Fleet & Federation

## WS-RELTOP — Release topology: GitHub ≡ Forgejo equal publishers; `PUBLISH` capacity gate
<!--
id: WS-RELTOP
title: Release topology: GitHub ≡ Forgejo equal publishers; PUBLISH capacity gate
theme: Fleet & Federation
status: done
priority: P2
laws: [7, 8]
ssot_keys: ["build.curl_trigger_fallback"]
adr: [4]
deps: [WS-MIOSSYS]
acceptance: |
  GitHub and Forgejo are equal publishers; PUBLISH capacity gates the bake on standard runners.
-->

**✅ DONE this session (for CI):** GitHub Actions (`.github/workflows/mios-ci.yml`) and the self-hosted Forgejo runner (`.forgejo/workflows/build-mios.yml`) are declared EQUAL, bit-for-bit build/publish environments (both `podman build`, identical OCI manifests) — neither subordinate. Build is LOCAL-first (MiOS-DEV, 707 GB, bakes the full fleet). `mios-ci.yml` carries a workflow-level `PUBLISH: 'false'` env (L38) — a **capacity** gate, NOT a demotion: a standard `ubuntu-24.04` runner (~66 GB `/mnt`) cannot hold the ~60 GB baked store (one `buildah commit` → exit 125), so GitHub build+lint VALIDATES only while the 707 GB Forgejo runner (and the local build) bake. `PUBLISH` gates the `MIOS_BAKE_BOUND_IMAGES` build-arg (L243) + the rechunk/push/cosign steps (L270+); flip to `'true'` once a runner can hold the bake — or, decisively, after WS-MIOSSYS shrinks the store to ~25 GB so a standard GitHub runner bakes+publishes as a full equal.

### RELTOP-01 — Wire "default-to-GHCR-if-creds-else-local/Forgejo" registry selection into the build driver  **✅ DONE this session**
- **What:** Implement the registry-selection logic that both workflows currently hardcode as `ghcr`: default to GitHub/GHCR push+pull when credentials are present, else the local/Forgejo registry. Locate it in the build driver / `install.env` credential detection so both CI environments and the local build resolve the registry the same way.
- **Why:** The topology directive says registry preference is credential-driven, but `mios-ci.yml`/`build-mios.yml` currently hardcode GHCR; the selection belongs in one shared place, not duplicated per workflow.
- **Files:** `.github/workflows/mios-ci.yml`, `.forgejo/workflows/build-mios.yml`, the build driver (`automation/build.sh` / `install.env` credential detection).
- **Accept:** a build with GHCR creds present pushes/pulls GHCR; with none it targets the local/Forgejo registry; both CI runners and the local build share the one selection path; no hardcoded registry remains outside it.
- **Deps:** CI capacity-gate DONE; the `PUBLISH:'true'` flip is unblocked by WS-MIOSSYS.


