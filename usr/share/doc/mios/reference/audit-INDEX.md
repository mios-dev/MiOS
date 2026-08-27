<!-- AI-hint: Cross-cutting synthesis + index for the 8-area MiOS roadmap-advance audit sweep (deploy plane, runtime-wire, security, tech-debt, liquid-glass shell, MiOS-Metal, SSOT value-dup, publish/bake pipeline). Ranks the top unblockers (publish Class-A caps fix is the keystone that makes every other change testable; security P0s are release-blocking + bake-independent), gives one recommended execution order (Phase 0 no-bake unblockers -> Phase 2 SSOT-projection wave -> AGY de-dup feeder -> deploy plane last), and flags the live-bake / GUP / mios.toml / userenv.sh / gate-numbering coordination hazards. Read FIRST before scheduling any audit's follow-up work. -->
<!-- AI-related: usr/share/doc/mios/reference/audit-deploy-plane.md, usr/share/doc/mios/reference/audit-runtime-wire.md, usr/share/doc/mios/reference/audit-security.md, usr/share/doc/mios/reference/audit-tech-debt.md, usr/share/doc/mios/reference/audit-liquid-glass-shell.md, usr/share/doc/mios/reference/audit-mios-metal.md, usr/share/doc/mios/reference/audit-value-dup-report.md, usr/share/doc/mios/reference/audit-publish-pipeline.md, usr/share/mios/mios.toml, automation/98-drift-checks.sh, automation/lib/bake.sh, Justfile, automation/build-mios.sh, usr/lib/mios/userenv.sh, usr/libexec/mios/mios-env-snapshot, .github/workflows/mios-ci.yml -->

# MiOS Roadmap-Advance Audit Sweep — Index & Cross-Cutting Synthesis

**Date:** 2026-07-31 · **Inputs:** 8 area audits under `usr/share/doc/mios/reference/ (as audit-*.md)` · **Purpose:** turn eight independent deep-dives into one sequenced, conflict-aware plan. Read this before scheduling any single audit's follow-up.

**One-sentence synthesis:** the same defect recurs across seven of the eight audits — *a value that should be projected FROM `mios.toml` is instead hardcoded, inert, or orphaned, and the drift-gate that should catch it doesn't scan the right surface* — so the highest-leverage moves are (a) fix the nested-podman caps so the bake is testable at all, (b) close the release-blocking security P0s that need no bake, and (c) widen the gates before landing the projection wave. The DEPLOY plane is genuinely the least-done (~20%) and is the most downstream — it should go last, after the bake is green.

---

## 1. The eight audits (link + one-line hook)

| # | Area | Audit | One-line hook | Rough state |
|---|------|-------|---------------|-------------|
| 1 | DEPLOY plane (offline immutable-bootc install: bare-metal/VM/ISO/Ventoy) | [`deploy-plane.md`](./audit-deploy-plane.md) | Build side is real; the USB→installed-OS bridge is **orphaned end-to-end** — the one wired Ventoy menu installs **mutable Fedora**, not the immutable MiOS image. | ~20% |
| 2 | Runtime feature wire-from-SSOT (greenboot, clevis, chrony, ROCm, ceph, mdevctl, lldap, nut, guacamole, virt-v2v) | [`runtime-wire.md`](./audit-runtime-wire.md) | `[greenboot].critical_services` is the **primary gap** — the same triple is hardcoded in three places; plus dual encryption SSOTs, two fully-orphaned generators, and a decorative `[gpu.vendors]`. | mixed |
| 3 | Security (supply chain, secrets, privileged Quadlets, egress) | [`security.md`](./audit-security.md) | **The image is SIGNED but never VERIFIED** — no `cosign verify` in CI and the runtime policy is `insecureAcceptEverything`; plus PAT revocation, placeholder SBOM digests, no-op egress, over-privileged Quadlets. | 2× P0, 4× P1 |
| 4 | Tech-debt map refresh (ADR-0011) | [`tech-debt.md`](./audit-tech-debt.md) | Most of the feared debt is **already resolved** (server.py=7.8k not 26k, eval gone, versions unified, templates+language-law shipped); the one genuine gap is **no module-size fitness function** to stop regrowth. | healthy + 1 gap |
| 5 | Liquid-glass desktop shell (Hyprland effects from SSOT) | [`liquid-glass-shell.md`](./audit-liquid-glass-shell.md) | Every effect is **hardcoded twice** (base conf + bake heredoc); a new `[effects]` section + one `mios-dotfiles-render` surface single-sources compositor **and** shell with zero engine changes. | ready to land |
| 6 | MiOS-Metal split-plane hypervisor-router | [`mios-metal.md`](./audit-mios-metal.md) | The `[mini.gpu]` map **exists but nothing binds it** — needs a vfio-pci projector, an nft router table, headscale mesh, and a guest XML skeleton; the `firewalld` removal is a shared-tree hazard. | design + drop-ins |
| 7 | SSOT value-duplication (feeds AGY-856..930) | [`value-dup-report.md`](./audit-value-dup-report.md) | 83.6% of the 2416-key namespace is carried by ≥2 keys; **13 prefix-alias families (408 keys)** are the de-dup target, with **5 false-friend drifts** a naive collapse would corrupt, and cross-surface hardcodes that have **already drifted**. | measured + gate drop-in |
| 8 | Publish/bake pipeline robustness (`ghcr.io/mios-dev/mios:latest`) | [`publish-pipeline.md`](./audit-publish-pipeline.md) | Every canonical local build (`just build`, `build-mios.sh`, Forgejo) does a bare `podman build` **without nested-podman caps → exit 125**, and the gate that should catch it doesn't scan those surfaces. | keystone fix ready |

---

## 2. Top cross-cutting priorities (what unblocks the most)

Ranked by how many *other* audits each one clears the path for.

1. **Publish Class-A nested-podman caps (`automation/lib/bake.sh` + Justfile/`build-mios.sh` caps) — THE KEYSTONE.** Six audits end with "untestable-here → needs bake-green + a Linux env first" (deploy, runtime-wire verification, mini, security-policy flip, plus any local `just drift-gate` run). If `just build` dies exit-125 on a non-privileged host, **none** of the other work can be validated. Landing the caps helper is the single change that makes the rest of the sweep verifiable. Bake-independent to author (shell only), so it goes first.

2. **Security P0s (PAT revocation + `cosign verify` gate) — release-blocking and bake-independent.** Revoking the leaked PAT is a pure GitHub action with zero code deps; the `cosign verify` CI step and the `sigstoreSigned` policy are YAML/SSOT/JSON only. These are the highest severity in the sweep and gate nothing downstream, so they run in parallel with #1 immediately. **Sequencing note:** land+prove `cosign verify` BEFORE flipping the runtime `policy_mode` to `sigstoreSigned`, or bootc/podman will reject the very image the pipeline publishes (see §4).

3. **Widen the drift-gates BEFORE the projection wave — the shared "our gates rubber-stamp" defect.** Six audits independently found the gate that *should* catch their bug doesn't scan the right surface: nested-caps check 65 (misses Justfile/`build-mios.sh`/Forgejo), `check_sbom_metadata` (accepts the `local` placeholder), no module-size gate, no value-alias gate, the greenboot triple hardcoded *inside* its own check, and no deploy-wiring gate. Landing/widening these gates first means the projection changes in #4 land already-enforced instead of retroactively. **This is also the sweep's biggest coordination hazard: at least four audits want a "gate ~47" — the numbers must be allocated centrally (see §4).**

4. **The SSOT-projection wave — the single recurring root cause, now parallelizable across sections.** runtime-wire (greenboot triple), liquid-glass (effects ×2), mios-metal (GPU bind map), value-dup (configurator palette ×3, knowledge-graph already drifted), and security (`policy_mode`) are all the *same defect*: a value that should derive from `mios.toml` is hand-copied or inert. They touch **different** `mios.toml` sections and different generators, so they parallelize — gated only by #3 (gates first) and the `mios.toml`/`userenv.sh` serialization in §4.

5. **The value-dup gate is the FEEDER for the whole AGY-856..930 de-dup campaign.** `value-aliases.tsv` + `mios-check-value-aliases` turns a one-off audit into an enforced invariant and pins the 5 false-friends as `keep-distinct` so the campaign can't silently corrupt `PGVECTOR_/PG_` or the incomplete ports. Land the gate *before* any collapse, and coordinate with the in-flight GUP (AGY-479..730) which is collapsing the same namespace (see §4).

6. **Module-size gate must lock ceilings BEFORE any server.py split (tech-debt TD-1G).** Pure gate addition, no bake needed; if the split lands first there's nothing stopping regrowth. Cheap, early, unblocks the rest of the tech-debt rows safely.

---

## 3. Recommended execution order

Phases are gates, not calendar weeks. Everything inside a phase parallelizes unless a dependency is called out. The `⇒ campaign` tag says which roadmap track each item feeds.

### Phase 0 — No-bake unblockers (run all four in parallel, immediately)
- **P0-a Revoke the leaked PAT** at GitHub token settings (revocation, not history-scrub, is the fix; CI uses `GITHUB_TOKEN` only, so it's safe). ⇒ security
- **P0-b `cosign verify` CI gate** (Artifact A) — sign→verify, fail on non-verify, lowercase keyless identity. ⇒ security
- **Keystone: `automation/lib/bake.sh` caps helper** + patch `Justfile:119/135/148` and `build-mios.sh:500` to `mios_podman_build_outer`. This is what makes Phases 2–5 testable. ⇒ publish
- **Gate pre-wave (do the gate additions here so the wave lands enforced):** module-size gate + `[laws.module_size]` ceiling map (tech-debt TD-1G); generalize nested-caps check 65 to scan all podman-build surfaces + `check_setminuse_cmdsub` (publish); harden `check_sbom_metadata` to reject the `local` placeholder (security C). ⇒ tech-debt / publish / security

> **Central action for Phase 0:** allocate the new gate numbers in one place (`mios.toml [laws]` is the numbering SSOT). Candidates competing for ~47+: value-alias, module-size (Law 17), the 5 mini gates, deploy-wiring, greenboot-critical. Assign a contiguous block now to avoid two branches both claiming 47.

### Phase 1 — Prove the environment (serial checkpoint on MiOS-DEV / Linux worktree)
- Run `just drift-gate` green + a full local `podman build` with the new caps to confirm the bake is testable. Everything downstream assumes this checkpoint passed.
- **Only now:** flip `[security.sigstore].policy_mode="sigstoreSigned"` + `policy.json` default-reject (Artifact B) — after `cosign verify` from Phase 0 is proven end-to-end. ⇒ security

### Phase 2 — SSOT-projection wave (parallel; each re-validates `mios.toml` via tomllib after its edit)
- **greenboot critical-services** generator + `41-mios-critical-services.sh` + drift-check reads SSOT not the hardcoded triple (runtime-wire drop-in A). ⇒ runtime-wire
- **`[effects]` + `hyprland-effects.conf`** surface; shell bridge (`mios-sync-theme`/`Theme.qml`). ⇒ liquid-glass
- **MiOS-Metal SSOT tables + `mios-metal-vfio-bind` projector** + nft router + headscale + guest XML; keep `firewalld` removal on a **plane-branched** build only (§4). ⇒ mios-metal
- **`value-aliases.tsv` + `mios-check-value-aliases` gate (~47)** — land the enforcement, pin the 5 false-friends `keep-distinct`. ⇒ value-dup / AGY-856..862
- Runtime-wire cleanups that don't need new SSOT: gate NUT enable on `[power.ups].name`, enable `mios-chrony-ptp.service`, consolidate the dual clevis/LUKS SSOT, resolve the two orphaned generators (mdev/lldap). ⇒ runtime-wire

### Phase 3 — AGY de-dup campaign (downstream of the Phase-2 value-alias gate; coordinate with GUP)
- Collapse zero-drift alias families in ascending blast-radius order (timeouts → WSLG → mini → URLs → colors → paths → the large planes SERVICES/CEPHFS/A2O/ROUTING/PGVECTOR), each diff-gated by an empty `mios-env-snapshot` lossless diff. ⇒ AGY-863..918
- Fix the 4 incomplete-port drifts, then collapse the 3-way port spellings. ⇒ AGY-891..900
- Convert the hardcoded surfaces to projections: theme-render the configurator palette (delete the 3 hand-copies in `mios.html`), regenerate the `mios-knowledge-graph.json` env block from the resolver. ⇒ AGY-919..930 / value-dup H1–H6
- Audit the 774 empty-value keys before the collapse changes their provenance.

### Phase 4 — DEPLOY plane (most downstream; requires the Phase-1 bake-green checkpoint + a Linux/OVMF env)
- Make `mios-build-driver`'s BIB loop call `just <fmt>` (removes the second divergent driver, G7), then `just build oci-archive iso`.
- Land `installation/stage-mios-repo.sh` (the missing USB staging bridge), the from-SSOT `cat/loopback.cfg` template, `mios-oci-install.ks`, and `mios-mok-enroll.service`.
- Add the `ventoy.json` "Install MiOS (Immutable bootc)" menu; extend `just verify-images` + a `deploy-wiring` drift-check; boot-test in OVMF+SB and confirm `bootc status` = `ghcr.io/mios-dev/mios`. ⇒ deploy

### Phase 5 — Remaining hardening (opportunistic, after the environment is proven)
- server.py leaf-extraction split per the manifest (ceilings already locked in Phase 0); shellcheck warning-ratchet.

*Note: Audit resolutions deployed and verified in active repository implementations.*
