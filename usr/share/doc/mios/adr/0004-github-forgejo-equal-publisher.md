<!-- AI-hint: GitHub Actions and the self-hosted Forgejo runner are EQUAL bit-for-bit build/publish environments; the CI PUBLISH env is a capacity gate (a standard runner can't hold the ~60GB bake), NOT a demotion — read before changing CI publish/bake logic or registry selection. -->
<!-- AI-related: .github/workflows/mios-ci.yml, .forgejo/workflows/build-mios.yml, Containerfile MIOS_BAKE_BOUND_IMAGES, usr/share/mios/mios.toml [build].rechunk_max_layers + curl_trigger_fallback, /etc/mios/install.env -->
---
adr: 0004
title: GitHub ≡ Forgejo equal-publisher release topology
status: accepted
date: 2026-07-12
deciders: [operator, ai-pair]
tags: [ci, release, topology, publishing, capacity, registry]
laws: [3, 4, 12]
ssot_keys: [build.rechunk_max_layers, build.bake_groups, build.curl_trigger_fallback]
related_ws: [WS-RELTOP]
supersedes: []
superseded_by: []
---

# ADR-0004: GitHub ≡ Forgejo equal-publisher release topology

## Status
Accepted — 2026-07-12. DONE for CI (both pipelines in-tree); the registry-
selection logic and the `PUBLISH` flip are PLANNED (see Consequences).

## Context

MiOS is one rebuildable bootc/OCI image (`ghcr.io/mios-dev/mios:latest`) that
bakes its whole service fleet into the image (Law 3 BOUND-IMAGES, Law 12
BAKE-NOT-FETCH). It is built by two pipelines: GitHub Actions
(`.github/workflows/mios-ci.yml`) and a self-hosted Forgejo runner
(`.forgejo/workflows/build-mios.yml`). Both use **`podman build`** (not
docker/build-push-action) precisely so the OCI manifests, layer digests, labels,
and provenance match bit-for-bit — an operator pulling `ghcr.io/mios-dev/mios:latest`
gets the same image whether the runner was GitHub-side or Forgejo-side.

Two facts create tension:
- **The published image is intentionally large.** The bound-image bake is
  ~60 GB (see ADR-0002); the committed image is ~65–90 GB uncompressed. A
  `buildah commit` needs the store on disk plus ~2–3× transient serialization
  space.
- **A standard GitHub `ubuntu-24.04` runner has ~66 GB usable on `/mnt`.** It
  physically cannot hold the ~60 GB baked store — one `buildah commit` overruns it
  (`exit 125` / "closed pipe"). The 707 GB self-hosted Forgejo runner (and the
  707 GB local MiOS-DEV build) can.

The naive reading — "GitHub can't build it, so Forgejo is the real publisher" —
is **wrong** and the operator explicitly rejected it. Both are first-class; the
only difference is *disk capacity right now*, which is a transient hardware fact,
not an architectural hierarchy.

## Decision

**GitHub Actions and the self-hosted Forgejo runner are EQUAL, bit-for-bit
build/publish environments.** Neither is "the" publisher; do not frame one as
subordinate. On top of that equality:

1. **Build LOCAL-first.** The local build (MiOS-DEV podman machine, 707 GB) is the
   primary/authoritative bake — it bakes the full fleet.
2. **Registry preference:** default to GitHub/GHCR push+pull when credentials are
   present; else the local/Forgejo registry.
3. **`PUBLISH` is a CAPACITY gate, not a demotion.** `mios-ci.yml` carries a
   workflow-level `PUBLISH: 'false'` env. While `false`, the GitHub pipeline
   **fully build- and lint-validates** the image but does **not** bake the bound
   images or push — because a standard runner can't hold the bake. The baked image
   comes from a runner that *can* bake (local MiOS-DEV first, or the 707 GB
   Forgejo runner) and lands in the default registry. `PUBLISH` is one toggle: it
   gates the `MIOS_BAKE_BOUND_IMAGES` build-arg and the rechunk/push/cosign steps.
4. **Flip `PUBLISH: 'true'` once a GitHub runner can hold the full image** — a
   large-disk runner, or (the enabler) after ADR-0002's MiOS-Sys consolidation
   shrinks the bake to ~25 GB so it fits a standard runner. Then GitHub bakes +
   pushes + signs as a full equal.

MiOS-Sys is the **enabler of true equality**: shrinking the bound-image store to
fit a standard runner is exactly what lets GitHub bake and publish without a
special runner. Until then, `PUBLISH=false` is honest capacity accounting.

## Rationale

- **Bit-for-bit parity is the whole point.** Both pipelines use `podman build`;
  the header of `mios-ci.yml` states parity with `build-mios.yml` explicitly.
  Equality of *artifact*, gated only by *capacity*, is coherent and auditable.
- **Law 4 (BOOTC-CONTAINER-LINT) holds on both sides always.** The Containerfile's
  final `RUN bootc container lint` runs in every build; `mios-ci.yml` adds a
  belt-and-suspenders label check (`containers.bootc=1`, `ostree.bootable=1`)
  identical to the Forgejo workflow. So even a `PUBLISH=false` GitHub run fully
  validates the image is a legal bootc image.
- **Law 3 / Law 12.** The bake is what makes every deployment ship offline-
  complete. `PUBLISH=false` doesn't weaken that guarantee for the published image —
  it just declines to *produce* the published image on a runner that can't; the
  bound images still resolve at bootc deploy time (native LBI) for a
  validate-only build, and the real published image is baked elsewhere.
- **Rechunk parity.** When `PUBLISH=true`, both runners run `hhd-dev/rechunk`
  (`[build].rechunk_max_layers`, default 67) so cloud-pulled images match
  self-hosted images bit-for-bit and Day-2 `bootc upgrade` deltas stay small.
- **Precedent.** This mirrors reproducible-build practice: identical build inputs
  and tool (`podman build`) across environments yield identical outputs; the
  runner is interchangeable. GHCR is the default publish registry with a
  local/Forgejo fallback — a standard OCI registry-selection pattern.

## Alternatives considered

- **Declare Forgejo the sole publisher, GitHub a mere PR check.** Rejected by the
  operator: it demotes an equal environment on a transient capacity fact and
  contradicts the bit-for-bit-parity design. `PUBLISH` captures the capacity
  reality without a hierarchy.
- **Make GitHub bake the full image anyway (bigger runner / self-hosted GH
  runner).** Deferred, not rejected: it is exactly what flipping `PUBLISH=true`
  does once such a runner exists. The cheaper path is ADR-0002 shrinking the bake.
- **Skip the bake everywhere and always resolve bound images at deploy.** Rejected:
  violates the "published image ships offline-complete" guarantee (Law 12); a
  published `:latest` must carry its sidecars. Deploy-time resolution is only for
  validate-only CI builds.
- **Use docker/build-push-action on GitHub.** Rejected: it breaks bit-for-bit
  manifest/digest parity with the Forgejo `podman build`. Both must use `podman build`.

## Consequences

Positive:
- One artifact, two interchangeable producers; a `:latest` pull is identical
  regardless of origin.
- CI stays green and useful on standard runners (full validate + lint + smoke)
  without a special runner, while the real bake happens where there's disk.
- The path to full GitHub publishing is a single env flip, gated on a concrete,
  documented capacity threshold.

Negative / honest costs:
- While `PUBLISH=false`, GitHub does not produce the publishable image — publishing
  depends on the local/Forgejo runners. This is a capacity dependency, tracked and
  intended to dissolve when ADR-0002 lands.
- The GitHub runner needs disk-freeing gymnastics even to *validate*
  (`jlumbroso/free-disk-space`, graphroot relocated to `/mnt`, rootful podman to
  avoid user-namespace UID exhaustion, `TMPDIR=/mnt/tmp`) — all documented inline
  in `mios-ci.yml`.

Status — **DONE:** both workflows exist and use `podman build`;
`PUBLISH: 'false'` gates bake+push+rechunk+cosign; the drift-gate + build + smoke
jobs validate on every PR; the Containerfile's `MIOS_BAKE_BOUND_IMAGES` build-arg
is wired to `env.PUBLISH == 'true' && '1' || '0'`.
**PLANNED (WS-RELTOP):** (a) the "default to GHCR if creds else local/Forgejo"
registry-selection logic is not yet centralized — `mios-ci.yml`/`build-mios.yml`
currently hardcode GHCR; it belongs in the build driver / `install.env` credential
detection (confirm the home). (b) Flip `PUBLISH: 'true'` after ADR-0002 shrinks the
bake (or a large-disk GitHub runner appears).

## Implementation

- `C:\MiOS\.github\workflows\mios-ci.yml` — `env.PUBLISH: 'false'` (top of file,
  with the capacity-gate rationale in comments). Jobs: `drift-gate`
  (SSOT-render lint + agent-pipe tests + `38-drift-checks.sh`), `build`
  (`podman build` with `--build-arg MIOS_BAKE_BOUND_IMAGES=${{ env.PUBLISH == 'true'
  && '1' || '0' }}`, bootc-label verify, then rechunk/meta/push/cosign steps all
  `if: env.PUBLISH == 'true'`), and `smoke-test` (PR-only: `MIOS_BAKE_BOUND_IMAGES=0`
  build + a runtime smoke that compiles `agent-pipe/server.py` and asserts
  load-bearing shims/units).
- `C:\MiOS\.forgejo\workflows\build-mios.yml` — the parity pipeline on the 707 GB
  self-hosted runner (bakes + pushes + signs).
- `C:\MiOS\Containerfile` — `ARG MIOS_BAKE_BOUND_IMAGES=1` (published default 1);
  CI passes 0 for validate-only builds. The sharded bake RUNs (ADR-0001) are what a
  capable runner executes when baking.
- `C:\MiOS\usr\share\mios\mios.toml [build]` — `rechunk_max_layers = 67`;
  `curl_trigger_fallback = true` (mios-build-driver triggers a Forgejo CI build
  over HTTP when local `podman build` is unavailable).

## References

- podman build / buildah (bit-for-bit OCI): <https://docs.podman.io/en/latest/markdown/podman-build.1.html>
- GHCR (GitHub Container Registry): <https://docs.github.com/packages/working-with-a-github-packages-registry/working-with-the-container-registry>
- Forgejo Actions: <https://forgejo.org/docs/latest/user/actions/>
- hhd-dev/rechunk (small Day-2 deltas): <https://github.com/hhd-dev/rechunk>
- cosign keyless signing (Sigstore): <https://docs.sigstore.dev/cosign/signing/overview/>
- jlumbroso/free-disk-space: <https://github.com/jlumbroso/free-disk-space>
- containers/podman#22342 (buildah commit transient-space `exit 125`).
- Sibling ADRs: ADR-0002 (MiOS-Sys shrinks the bake → flips `PUBLISH`),
  ADR-0001 (the sharded bake a capable runner executes), ADR-0003 (SBOM provenance).
