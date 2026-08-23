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
| `49-cosign-policy.sh:60` | `sha="$(sha256sum /usr/bin/cosign ...)"` | YES — after `install ... /usr/bin/cosign` (`:53`) | non-fatal | safe |
| `57-gnome.sh:127` | `sha="$(sha256sum /tmp/bibata.tar.xz ...)"` | YES — inside `if tar -xf /tmp/bibata.tar.xz` (`:121`) | non-fatal | safe |
| `62-oh-my-posh.sh:69` | `actual="$(sha256sum "${OMP_BIN}.new" ...)"` | YES — after successful download or `exit 0` (`:56-60`) | non-fatal | safe |
| `62-oh-my-posh.sh:89` | `sha="$(sha256sum "${OMP_BIN}" ...)"` | YES — after `mv -f ...new -> OMP_BIN` (`:81`) | non-fatal | safe |
| `36-ceph-k3s.sh:73` | `local_sum=$(sha256sum .../vendored/k3s/k3s ...)` | YES — preceding unguarded `cp` of same file would fail first (`:64`) | non-fatal | safe |
| `36-ceph-k3s.sh:106` | `sha="$(sha256sum /usr/bin/k3s ...)"` | YES — after `install ... k3s` (`:98`) | non-fatal | safe |
| `76-uki-render.sh:51` | `CMDLINE=$(cat "$KERNEL_CMDLINE_DST" \| xargs)` | YES — file generated (`:43`) + installed (`:48`) 3 lines up | non-fatal | safe (minor UUOC) |

**Conclusion:** after the `56-fonts.sh` fix, the missing-file command-substitution class is **currently contained** — there is **no remaining unguarded fatal-path site**. Every survivor is guarded by a preceding successful `mv`/`install`/`tar`/`cp`, a `[ -f ]` test, or a `find … | while read` that only yields existing files.

**But the containment is point-in-time and undefended.** There is **no lint** that prevents the next `x=$(sha256sum $optional_file)` from re-introducing the class — the same structural gap as Class A. See §5 for the proposed `check_setminuse_cmdsub` gate.

**Guard pattern to standardize on** (already used in `56-fonts.sh:118-126`; fold into the helper library):
```bash
sha=""
if command -v sha256sum >/dev/null 2>&1 && [ -f "$asset" ]; then
    sha="$(sha256sum "$asset" | awk '{print $1}')"
fi
printf '...%s...\n' "${sha:-unknown}" >> "$sbom"
```

---

## 3. Resumable-layers plan (checkpointed RUN layers)

### Finding R-1: the bound-image bake is one giant commit again

`usr/share/mios/mios.toml` `[build.bake]` (`:8627-8668`) declares:
```toml
groups = ["sys", "cuda", "extra"]      # :8652
[build.bake.group_members]
sys  = ["sys"]                          # :8666
cuda = ["cuda"]                         # :8667
extra = []                              # :8668  <-- catch-all
firstboot_tokens = ["vllm", "sglang"]   # :8663
runner_disk_budget_gb = 40              # :8628
```
`generate-bake-plan.py:47-52` assigns each image to the **first** group whose token substring-matches, else the **last** group. With `extra = []`, **every** non-`sys`/`cuda`, non-firstboot sidecar (all ~20 docker.io/ghcr images) lands in the single `extra` group → the single `RUN … mios-bake-group extra` (`Containerfile:227`) → **one `buildah commit`**.

This *defeats* the sharding that `mios-bake-group` was built for. Its own header (`usr/libexec/mios/mios-bake-group:5-14`) warns: *"A single monolithic commit overran disk-constrained CI runners: exit 125 / io: read/write on closed pipe … buildah writes ~2-3x the layer's diff to temp during commit."* The machinery (per-group `mios-bake-group <g>`, sharded `plan.d/*.list`, heaviest-first order) all exists and is inert because the SSOT collapses everything into one group.

### Finding R-2: the 60-script pipeline is one non-resumable RUN

`Containerfile:84-149` runs the entire numbered pipeline in one `RUN`. buildkit caches at RUN granularity, so any interruption (reboot, OOM, transient pull 429) re-runs **all 60 scripts** from scratch. There is no checkpoint between "install base packages" and "compile Looking Glass".

### Plan (sequenced, lowest-risk first)

1. **Re-shard `group_members`** (SSOT-only change, no code). Give `extra` real siblings so no single commit is the whole store, e.g.:
   ```toml
   groups = ["sys", "cuda", "ai-cpu", "infra", "web", "extra"]
   [build.bake.group_members]
   sys    = ["sys"]
   cuda   = ["cuda"]
   ai-cpu = ["llama-swap", "crawl4ai", "searxng", "openedai", "docling"]
   infra  = ["postgres", "pgvector", "redis", "valkey", "crowdsec", "qdrant"]
   web    = ["open-webui", "openwebui", "guacamole", "guacd", "cockpit"]
   extra  = []   # remaining catch-all
   ```
   `generate-bake-plan.py` already writes `NN-<group>.list` deterministically and validates fully-qualified refs (`:188-199`), so this just produces more, smaller lists.

2. **One `RUN` per group in projected order, heaviest first** (`Containerfile`, replacing the single `:227`):
   ```dockerfile
   RUN --network=host --mount=type=cache,target=/var/tmp/mios-bakescratch \
       MIOS_BAKE_BOUND_IMAGES="${MIOS_BAKE_BOUND_IMAGES}" bash /usr/libexec/mios/mios-bake-group ai-cpu
   RUN --network=host --mount=type=cache,target=/var/tmp/mios-bakescratch \
       MIOS_BAKE_BOUND_IMAGES="${MIOS_BAKE_BOUND_IMAGES}" bash /usr/libexec/mios/mios-bake-group infra
   RUN --network=host --mount=type=cache,target=/var/tmp/mios-bakescratch \
       MIOS_BAKE_BOUND_IMAGES="${MIOS_BAKE_BOUND_IMAGES}" bash /usr/libexec/mios/mios-bake-group web
   RUN --network=host --mount=type=cache,target=/var/tmp/mios-bakescratch \
       MIOS_BAKE_BOUND_IMAGES="${MIOS_BAKE_BOUND_IMAGES}" bash /usr/libexec/mios/mios-bake-group extra
   ```
   Each RUN = its own committed layer. With `podman build --layers` (already set inside `57-mios-sys-build.sh:83`; add it to the outer build too), a rebooted/re-run bake **resumes at the in-flight group** — every completed group layer is served from cache. Smaller per-commit diffs also directly reduce the `exit 125` "closed pipe" risk.

3. **Split `57-mios-sys-build.sh` into two RUNs** (or keep the script but call it twice with a `--only sys|cuda` selector) so `mios-sys` and `mios-cuda` checkpoint independently — the `-cuda` layer is the larger of the two and shouldn't force a `-sys` rebuild on retry.

4. **Add `--retry 5 --retry-delay 3s` to the outer `podman build`** in `Justfile:119` and `automation/build-mios.sh:500` (GitHub already has it at `mios-ci.yml:301`; Forgejo already at `build-mios.yml:127`). Transient registry flakes then don't burn a full re-bake.

5. **(Bigger lever, later) Checkpoint the numbered pipeline into bands.** Split `Containerfile:84-149` into ~4-5 RUNs at natural state boundaries (base-packages | hardware+virt | desktop+fonts | ai | finalize/lint), each re-entrant. This is the largest resumability win but requires auditing cross-script shared state first — track as its own change; do not fold into the low-risk items above.

**Net:** items 1-4 are SSOT + Containerfile + two one-line entrypoint edits, fully drift-gate-testable, and convert the bake from "one commit, all-or-nothing" into "N committed checkpoints that resume." Item 5 completes resumability for the script pipeline itself.

---

## 4. Firstboot-tier robustness

**Eviction (correct):** `generate-bake-plan.py:38-41,146-159` drops any image whose ref substring-matches `firstboot_tokens` (`vllm`, `sglang`) from every group list into `plan.d/firstboot.list`, and **validates** (`:162-168`) that each firstboot token and image is still present in `[build.bake].core` — so an evicted whale cannot silently vanish from provenance. This is the mechanism that lands peak bake disk at ~20-25 GB and lets the standard GitHub runner publish (`mios-ci.yml:38-44`).

**First-boot pull (mostly robust):** `usr/libexec/mios/mios-ai-firstboot:635-660` pre-stages `firstboot.list` with (a) `podman image exists` skip, (b) 3× retry with linear backoff, (c) **degrade-open** (`WARN … degrade open`, boot never fails). GGUF and vLLM online-fallback fetches likewise retry 3× (`mios-ai-firstboot:163-176,234-246`).

### Robustness gaps

**F-1 (MEDIUM) — no mirror / auth on the firstboot whale pull.** The bake routes `docker.io` through `mirror.gcr.io` and logs into GHCR to dodge anonymous rate limits (`mios-bake-group:79-86`, `mios-ci.yml:228-241`). The firstboot pull (`mios-ai-firstboot:648-654`) does a bare `podman --root "$STORE" pull` with none of that. A first boot behind a Docker Hub `429 toomanyrequests` on the ~25 GB vLLM + ~22 GB SGLang whales exhausts 3 quick retries and degrades open → the heavy AI lane stays dark until a manual `mios update`. **Fix:** reuse the same `registries.conf` mirror block and optional registry creds in the firstboot pull (extract to the shared helper in §6).

**F-2 (LOW) — no free-disk pre-check before the whale pull.** ~47 GB of images pulled into `/usr/lib/containers/storage` with no `df` guard; a data-partition-less deploy can fill `/`. Add a budget check against `runner_disk_budget_gb` (SSOT already has the key, `mios.toml:8628`).

**F-3 (LOW, verify) — bake-budget gate vs firstboot rows.** `check_bake_budget` (`98-drift-checks.sh:4251-4292`) counts rows in `bound-images.tsv` and fails at `>30`, but `generate-bake-plan.py:233-238` writes firstboot images into that same TSV for SBOM. Confirm the count excludes firstboot rows (or the threshold accounts for them) so the budget gate estimates *baked* size, not *total* size. Also note the threshold `30` is hardcoded while the message interpolates the SSOT `runner_disk_budget_gb` — align them.

---

## 5. Drift-gate extensions (make both classes un-regressable)

**5a. Generalize `check_nested_podman_caps` (`98-drift-checks.sh:4216`)** from a 2-file allowlist to a *scan*: for every `automation/*.sh`, `usr/libexec/mios/*.sh`, the `Justfile`, `automation/build-mios.sh`, and **both** workflow files, if a line invokes `podman build` (and is not an allowlisted host-privileged/firstboot exception), require `--cap-add` + `seccomp=unconfined` on the same logical invocation (or the sourced helper `mios_build_image_with_retry`). Add `.forgejo/workflows/build-mios.yml` to the monitored set (or explicitly document + assert its `Privileged=true` exception).

**5b. Add `check_setminuse_cmdsub`:** flag any `VAR="$(… sha256sum|md5sum|stat|cat …)"` in a `set -e` script where the target is not a preceding `[ -f ]` guard, an `install`/`mv` output, or a `find … | while read` variable. Point violators at the `56-fonts.sh:118-126` guard pattern. This is the fitness function that would have caught the 0.3.0 `56-fonts.sh` bug pre-merge.

**5c.** Extend the `nested-podman-caps.md` "Monitored Invocations" list (`nested-podman-caps.md:47-52`) to name the newly-scanned surfaces so the reference doc matches the gate.

---

## 6. Drop-in artifact — `automation/lib/bake.sh`

A single sourceable library that both the **inner** (nested, in-bake) and **outer** (host/CI) `podman build` sites adopt. It generalizes the proven `57-mios-sys-build.sh:66-110` function, centralizes the caps array (one SSOT for the reference doc + drift gate to key on), and folds in the `56-fonts.sh` sha256 guard.

```bash
#!/usr/bin/env bash
# AI-hint: Shared bake helpers -- the canonical nested-podman capability set plus
# a retry+verify image builder, so every bare `podman build` site in the bake
# inherits the exit-125 fix (caps) and exit-1 fix (guarded checksums) from ONE place.
# AI-related: usr/libexec/mios/57-mios-sys-build.sh, automation/54-bake-coderun-sandbox.sh,
#   usr/share/doc/mios/reference/nested-podman-caps.md, automation/98-drift-checks.sh
#
# Usage (inner / nested-in-bake build -- 54/57/firstboot style):
#   source "$(dirname "$0")/lib/bake.sh"          # or /usr/lib/mios/bake.sh at runtime
#   mios_build_image_with_retry localhost/mios-foo:latest ./ctx \
#       --build-arg BASE_IMAGE="$BASE"
#
# Usage (outer / host build -- Justfile, build-mios.sh):
#   source .../lib/bake.sh
#   mios_podman_build_outer -t localhost/mios:latest -f Containerfile .
#
# Both honor set -euo pipefail in the caller and NEVER leak a partial image.

# ── The one true nested-podman capability set (drift-gate keys on this token) ──
# Rationale: usr/share/doc/mios/reference/nested-podman-caps.md.
#   --device /dev/fuse   fuse-overlayfs fallback when kernel overlay-on-overlay is blocked
#   --cap-add all        CAP_SYS_ADMIN (mounts/namespaces) + CAP_SYS_RESOURCE (setrlimit)
#   seccomp/apparmor=unconfined   let inner unshare/clone/mount/pivot_root through
#   --network=host       registry egress from the nested build netns
MIOS_NESTED_BUILD_CAPS=(
    --network=host
    --device /dev/fuse
    --cap-add all
    --security-opt seccomp=unconfined
    --security-opt apparmor=unconfined
)

# mios_build_image_with_retry <target_tag> <context_dir> [extra podman-build args...]
# Retries with exponential backoff, then VERIFIES the image exists (a green
# `podman build` that produced nothing is still a failure). Returns non-zero on
# persistent failure so the CALLER decides fail-hard vs degrade-open (Law 12).
mios_build_image_with_retry() {
    local target_tag="$1" build_dir="$2"; shift 2
    local attempt=1 max_attempts="${MIOS_BAKE_MAX_ATTEMPTS:-3}" backoff="${MIOS_BAKE_BACKOFF:-5}"
    local root_flags=()
    # Optional isolated additional-store root (57-mios-sys-build passes --root/--runroot).
    [[ -n "${MIOS_BAKE_STORE:-}"   ]] && root_flags+=(--root "$MIOS_BAKE_STORE")
    [[ -n "${MIOS_BAKE_RUNROOT:-}" ]] && root_flags+=(--runroot "$MIOS_BAKE_RUNROOT")

    while (( attempt <= max_attempts )); do
        printf '[bake] attempt %d/%d: building %s\n' "$attempt" "$max_attempts" "$target_tag" >&2
        if podman "${root_flags[@]}" build \
                "${MIOS_NESTED_BUILD_CAPS[@]}" \
                --layers \
                -t "$target_tag" \
                "$@" \
                "$build_dir"; then
            if podman "${root_flags[@]}" image exists "$target_tag"; then
                printf '[bake] %s built + verified\n' "$target_tag" >&2
                return 0
            fi
            printf '[bake] WARN: %s reported success but image is absent\n' "$target_tag" >&2
        fi
        printf '[bake] WARN: build %s failed on attempt %d/%d\n' "$target_tag" "$attempt" "$max_attempts" >&2
        (( attempt < max_attempts )) && { sleep "$backoff"; backoff=$(( backoff * 2 )); }
        (( attempt++ ))
    done
    printf '[bake] ERROR: persistent build failure for %s after %d attempts\n' "$target_tag" "$max_attempts" >&2
    return 1
}

# mios_podman_build_outer [podman-build args...]
# For the HOST/CI top-level build (Justfile, build-mios.sh). Adds the caps + a
# retry policy the same way GitHub already does (mios-ci.yml:301). Not nested,
# but the caps are still required because the RUN steps inside spawn nested builds.
mios_podman_build_outer() {
    ${MIOS_BUILD_SUDO:-} podman build \
        "${MIOS_NESTED_BUILD_CAPS[@]}" \
        --retry "${MIOS_BAKE_RETRY:-5}" --retry-delay "${MIOS_BAKE_RETRY_DELAY:-3s}" \
        "$@"
}

# mios_sha256_guarded <file>  -> echoes hex digest or "unknown" (never aborts set -e).
# The exit-1 fix from 56-fonts.sh, reusable: a checksum on a missing/optional
# build artifact must degrade to "unknown", not kill the script.
mios_sha256_guarded() {
    local f="$1"
    if command -v sha256sum >/dev/null 2>&1 && [ -f "$f" ]; then
        sha256sum "$f" | awk '{print $1}'
    else
        echo "unknown"
    fi
}
```

### Adoption diffs

**`Justfile:118-124` (fixes A-1):**
```make
build: preflight flight-status
    bash -c 'source ./automation/lib/bake.sh && \
      MIOS_BUILD_SUDO="" mios_podman_build_outer --no-cache \
        --build-arg BASE_IMAGE={{env_var_or_default("MIOS_BASE_IMAGE","ghcr.io/ublue-os/ucore-hci:stable-nvidia")}} \
        --build-arg MIOS_FLATPAKS={{env_var_or_default("MIOS_FLATPAKS","")}} \
        --build-arg MIOS_USER={{env_var_or_default("MIOS_USER","mios")}} \
        --build-arg MIOS_HOSTNAME={{env_var_or_default("MIOS_HOSTNAME","mios")}} \
        -t {{LOCAL}} .'
```

**`automation/build-mios.sh:499-508` (fixes A-2):**
```bash
# Fallback to direct podman build
source "${MIOS_SHARE_DIR}/automation/lib/bake.sh"
mios_podman_build_outer --no-cache \
    --build-arg BASE_IMAGE="$MIOS_BASE_IMAGE" \
    --build-arg MIOS_USER="$MIOS_USERNAME" \
    --build-arg MIOS_PASSWORD_HASH="$MIOS_PASSWORD_HASH" \
    --build-arg MIOS_HOSTNAME="$MIOS_HOSTNAME" \
    --build-arg MIOS_FLATPAKS="$MIOS_FLATPAKS" \
    -t localhost/mios:latest . \
    || { log_error "Build failed"; return 1; }
```

**`usr/libexec/mios/57-mios-sys-build.sh`** — replace its local `build_image_with_retry` (`:66-110`) with `source /usr/lib/mios/bake.sh` + `MIOS_BAKE_STORE="$STORE" MIOS_BAKE_RUNROOT="$SCRATCH/run" mios_build_image_with_retry ...`. (Keep drift-check 65's `build_image_with_retry`/`image exists` token expectation, or update it to the helper name in the same change — see §5a.)

**`automation/54-bake-coderun-sandbox.sh:34-52`** and the firstboot builds (A-4) — swap the inline retry loops for `mios_build_image_with_retry`, preserving their degrade-open handling (`54` defers to firstboot; agents/webtools `exit 1`/prune).

> Ship the library at **both** `automation/lib/bake.sh` (build-context, for `automation/*.sh` and the Justfile) and `/usr/lib/mios/bake.sh` (runtime, for `usr/libexec/mios/*` firstboot scripts) — Law 15 double-repo: the same file must land in `mios.git` and `mios-bootstrap.git`. `01-system-files-overlay.sh` already stages `automation/lib/*` → wire the runtime copy the same way.

---

## 7. Concrete next actions (ordered)

1. Add `automation/lib/bake.sh` (+ runtime `/usr/lib/mios/bake.sh`) with `MIOS_NESTED_BUILD_CAPS`, `mios_build_image_with_retry`, `mios_podman_build_outer`, `mios_sha256_guarded` (§6).
2. Patch `Justfile:119/135/148` and `automation/build-mios.sh:500` to `mios_podman_build_outer` (fixes A-1, A-2).
3. Re-point `57-mios-sys-build.sh` and `54-bake-coderun-sandbox.sh` (+ the two firstboot builds) at the helper; keep degrade-open semantics (A-4).
4. Re-shard `mios.toml [build.bake].group_members` (kill the empty-`extra` monolith) and add one `RUN mios-bake-group <g>` per group, heaviest-first, in the Containerfile; add `--layers` to the outer build (R-1, R-2 items 1-4).
5. Generalize drift-check 65 to *scan* every `podman build` surface incl. the Forgejo workflow, and add `check_setminuse_cmdsub`; extend `nested-podman-caps.md` monitored list (§5).
6. Give the firstboot whale pull the `mirror.gcr.io` + creds treatment and a `df` budget pre-check (F-1, F-2); verify the bake-budget gate excludes firstboot rows (F-3).
7. Validate on MiOS-DEV: `just drift-gate` (must stay green), then a full `podman build` with the new per-group RUNs; confirm an interrupted+resumed bake reuses completed group layers.

---

## Appendix — evidence index (file:line)

- Publish gate + GitHub caps: `.github/workflows/mios-ci.yml:44,295-306,531`
- Forgejo no-caps / Privileged reliance: `.forgejo/workflows/build-mios.yml:9-14,125`
- Justfile at-risk builds: `Justfile:119,135,148,168`; build deps `:193,203,214,231,250,275,313,383`
- Ignition fallback: `automation/build-mios.sh:496-508`
- Reference nested build: `usr/libexec/mios/57-mios-sys-build.sh:66-110` (caps `:77-86`)
- Reference degrade-open bake: `automation/54-bake-coderun-sandbox.sh:34-52`
- Containerfile RUNs: monolithic pipeline `:84-149`; bound-image bakes `:224-227`; `MIOS_BAKE_BOUND_IMAGES` `:223`
- Bake-plan eviction + validation: `tools/generate-bake-plan.py:38-41,146-168,233-238`
- Per-group bake + pull retry + mirror: `usr/libexec/mios/mios-bake-group:5-14,79-86,116-140`
- SSOT bake config: `usr/share/mios/mios.toml:8627-8668` (`groups:8652`, `group_members:8665-8668`, `firstboot_tokens:8663`, `runner_disk_budget_gb:8628`)
- Firstboot prestage: `usr/libexec/mios/mios-ai-firstboot:635-660`; firstboot builds `mios-agents-firstboot.sh:40`, `mios-webtools-firstboot.sh:47`
- Class B fix reference: `automation/56-fonts.sh:118-126`; hazard doc `automation/68-bake-kvmfr.sh:11-24`
- Drift gates: `automation/98-drift-checks.sh:4216-4249` (nested caps), `:4251-4292` (bake budget)
- Nested-caps reference doc: `usr/share/doc/mios/reference/nested-podman-caps.md:16-25,47-52`
