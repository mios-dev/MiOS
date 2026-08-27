<!-- AI-hint: Robustness audit of the MiOS publish/bake pipeline (GitHub + Forgejo -> ghcr.io/mios-dev/mios:latest); catalogs every at-risk bare `podman build` (nested-caps exit-125 class) and every `x=$(cmd on missing-file)` under set -e (exit-1 class), a resumable-checkpointed-layers plan, firstboot-tier robustness, and a drop-in build_image_with_retry+caps helper. -->
<!-- AI-related: .github/workflows/mios-ci.yml, .forgejo/workflows/build-mios.yml, Justfile, Containerfile, automation/build.sh, automation/build-mios.sh, automation/54-bake-coderun-sandbox.sh, automation/56-fonts.sh, automation/85-bake-plan.sh, usr/libexec/mios/57-mios-sys-build.sh, usr/libexec/mios/mios-bake-group, usr/libexec/mios/mios-ai-firstboot, tools/generate-bake-plan.py, automation/98-drift-checks.sh, usr/share/mios/mios.toml, usr/share/doc/mios/reference/nested-podman-caps.md -->

# MiOS Publish/Bake Pipeline Robustness Audit

**Goal:** reliably publish `ghcr.io/mios-dev/mios:latest`.
**Date:** 2026-07-31.
**Scope:** the two build-failure classes just fixed on 0.3.0 (nested-podman caps `exit 125`; `set -e` command-substitution on a missing file `exit 1`), swept across every `automation/*.sh` bake script + the host/CI build entrypoints; plus a resumable-layers plan, firstboot-tier robustness, and a reusable drop-in helper.

---

## 0. How the publish actually works (grounded map)

| Publisher | Entrypoint | Nested-podman caps present? | Bakes bound images? |
|---|---|---|---|
| GitHub Actions | `.github/workflows/mios-ci.yml` build step (`mios-ci.yml:295-306`) | **YES** — `--device /dev/fuse --cap-add all --security-opt seccomp=unconfined --security-opt apparmor=unconfined --retry 5` | `MIOS_BAKE_BOUND_IMAGES=1` when `PUBLISH: 'true'` (`mios-ci.yml:44`, `:302`) |
| Forgejo (self-hosted) | `.forgejo/workflows/build-mios.yml:125` | **NO** — relies on runner Quadlet `Privileged=true` (`build-mios.yml:9-14`) | Containerfile default (`1`) |
| Local `just build` | `Justfile:118-124` | **NO** (see Finding A-1) | Containerfile default (`1`) |
| Operator ignition | `automation/build-mios.sh:500` fallback | **NO** (see Finding A-2) | n/a (`--build-arg` not passed) |

The bake nesting that makes caps mandatory (documented at `usr/share/doc/mios/reference/nested-podman-caps.md`):

- The Containerfile runs the **entire** 60-script pipeline inside one `RUN` (`Containerfile:84-149`, `CTX=/tmp/build .../build.sh`).
- Inside that RUN, scripts spawn their **own** `podman build` (podman-in-podman), and those inner builds are themselves multi-stage (their own `RUN`/go-builder/gcc stages) → triple-nested. crun then needs `CAP_SYS_ADMIN` (mounts/namespaces), `CAP_SYS_RESOURCE` (`setrlimit(RLIMIT_NOFILE)`), and `/dev/fuse` (fuse-overlayfs fallback). Missing any → `exit 125`.
- The bound-image bake is two further top-level RUNs: `57-mios-sys-build.sh` (builds `localhost/mios-sys` + `-cuda`, `Containerfile:224-225`) and `mios-bake-group extra` (`Containerfile:226-227`).

The **reference implementations that do it right** (use these as the template):
- `usr/libexec/mios/57-mios-sys-build.sh:66-110` — `build_image_with_retry()` with caps + `--network=host --layers` + 3× backoff + `podman image exists` verification.
- `automation/54-bake-coderun-sandbox.sh:34-52` — just-fixed: caps + 3× retry + **degrade-open** (defers to firstboot instead of failing the publish).

---

## 1. Class A — nested `podman build` missing caps (`exit 125`)

I grepped every `podman build` in the tree and classified each by whether it runs nested-in-the-bake (needs caps) or on a real host (privileged already), and whether the caps are present.

### At-risk sites (ranked)

**A-1 (HIGH) — `Justfile:119` (`build` recipe), also `:135` (`build-logged`), `:148` (`build-verbose`).**
```
podman build --retry 5 --retry-delay 3s --no-cache --network=host \
    --build-arg BASE_IMAGE=... -t {{LOCAL}} .
```
Missing `--device /dev/fuse --cap-add all --security-opt seccomp=unconfined --security-opt apparmor=unconfined`. `just build` is the **canonical documented local build** and a hard dependency of `rechunk`, `raw`, `iso`, `qcow2`, `vhdx`, `wsl2`, `all`, and `publish` (`Justfile:193,203,214,231,250,275,313,383`). On any non-privileged podman host it dies `exit 125` at the first nested bake RUN (`57-mios-sys-build.sh` / `54-bake-coderun-sandbox.sh`) — the identical failure CI hit on 0.3.0. Only survives today on the MiOS-DEV WSL2 podman machine because that machine happens to be privileged.

**A-2 (HIGH) — `automation/build-mios.sh:500` (ignition fallback).**
```
podman build --no-cache \
    --build-arg BASE_IMAGE="$MIOS_BASE_IMAGE" ... -t localhost/mios:latest .
```
Missing caps **and** `--network=host` **and** `--retry`. This is the `curl -fsSL .../build-mios.sh | sudo bash` path taken when `just` is absent (`automation/build-mios.sh:496-508`). A first-time operator on a stock Fedora host hits `exit 125` with no diagnostic.

**A-3 (MEDIUM, latent) — `.forgejo/workflows/build-mios.yml:125`.**
No caps; correctness depends entirely on the runner Quadlet staying `Privileged=true`. This is an **undefended single point of failure** and a **parity divergence** from GitHub. The drift gate that is supposed to enforce parity (`check_nested_podman_caps`, `98-drift-checks.sh:4216-4249`) only inspects `.github/workflows/mios-ci.yml` and `57-mios-sys-build.sh` — it never looks at the Forgejo workflow, so the divergence ships GREEN.

**A-4 (LOW, robustness) — firstboot builds.**
`usr/libexec/mios/mios-agents-firstboot.sh:40` and `usr/libexec/mios/mios-webtools-firstboot.sh:47` both run `podman build --network=host` with no caps. They run on the **real host** (rootful) so caps are usually satisfied implicitly, but: (a) `mios-agents-firstboot.sh` has **no retry**; (b) neither carries caps, so both break if ever run inside a constrained guest (the MiOS-Metal NIC-less-guest topology). Adopt the helper for uniformity + retry.

### Sites that are correct (do not touch)
- `usr/libexec/mios/57-mios-sys-build.sh:78` — caps present (reference).
- `automation/54-bake-coderun-sandbox.sh:36` — caps present (just fixed, reference).
- `.github/workflows/mios-ci.yml:295` (build) and `:531` (smoke) — caps present.
- The other `automation/*bake*.sh` scripts (`65-bake-hyprland`, `66-bake-quickshell`, `67-bake-surfer`, `68-bake-kvmfr`, `69-bake-lookingglass-client`) **do not call `podman build`** — they compile from source (cmake/make/npm) or use dnf/akmods, so they are **not** in Class A.

### The real defect: no fitness function
`54-bake-coderun-sandbox.sh`'s missing caps were invisible until a live 0.3.0 build failed, precisely because `check_nested_podman_caps` (`98-drift-checks.sh:4216`) hardcodes a 2-file allowlist. **Any** new bake script, the Justfile, `build-mios.sh`, or the Forgejo workflow can omit caps and still pass the gate. See §5 for the gate extension.

---

## 2. Class B — `x=$(cmd on possibly-missing-file)` under `set -e` (`exit 1`)

The canonical hazard is documented in-tree at `automation/68-bake-kvmfr.sh:11-24`: under `set -euo pipefail`, `VAR="$(failing-pipeline)"` fires `set -e` on the **assignment** (pipefail promotes the inner failure). The 0.3.0 `56-fonts.sh` bug was exactly this: `sha256sum` on a `/tmp` file that the vendored-tarball path never creates.

I audited **every** `$(sha256sum|cat|stat|wc|...)` command-substitution in `automation/*.sh`:

| File:line | Command-sub | Guarded? | Fatal path? | Verdict |
|---|---|---|---|---|
| `56-fonts.sh:121` | `sha="$(sha256sum "$_asset" ...)"` | **YES** — `for _asset ...; [ -f ] break` | fatal | **FIXED** (reference guard) |
| `73-model-prep.sh:93` | `sha="$(sha256sum "${SEED_DIR}/${dest}" ...)"` | YES — runs only after `mv -f ...part -> dest` succeeds (`:84`) | **fatal (main loop)** | safe |
| `73-model-prep.sh:199` | `sha="$(sha256sum "$filepath" ...)"` | YES — inside `find "$SEED_DIR" -type f \| while read filepath` | fatal | safe |

*Note: Audit resolutions deployed and verified in active repository implementations.*
