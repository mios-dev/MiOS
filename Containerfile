# AI-hint: Defines the multi-stage Docker build process for the MiOS image, incorporating system configurations, automation scripts, and AI model bake parameters into the final bootable container.
# AI-related: /tmp/build/automation/lib/packages.sh, automation/45-coderun-sandbox-build.sh, /usr/share/mios/mios.toml, /usr/share/mios/flatpak-list, /usr/libexec/mios/copy-build-log.sh, mios-bootstrap, mios-dev, mios-sysext-pack, mios-coderun-sandbox, mios-additionalimagestores-perms
# syntax=docker/dockerfile:1.9
ARG BASE_IMAGE=ghcr.io/ublue-os/ucore-hci:stable-nvidia

FROM scratch AS ctx
COPY automation/           /ctx/automation/
COPY usr/                  /ctx/usr/
COPY etc/                  /ctx/etc/
# /home/ is bootstrap territory (mios-bootstrap.git stages user homes via
# profile/ in Phase-3); the build no longer pulls it.
# SSOT: mios.toml [packages.<section>].pkgs lives at
# usr/share/mios/mios.toml and is already shipped via the COPY usr/ above.
# build.sh exports $MIOS_TOML to /ctx/usr/share/mios/mios.toml so
# automation/lib/packages.sh resolves the canonical TOML manifest.
COPY VERSION               /ctx/VERSION
COPY config/artifacts/     /ctx/bib-configs/
COPY tools/                /ctx/tools/
# Repo-root agent MD files. On a clean OCI/bootc image these do NOT otherwise
# exist at / (they're present on a dev box only via the Phase-1 git Total Root
# Merge) -> agent-pipe's _load_agent_contract() silently degrades to "" and every
# agent loses its /MiOS.md identity+grounding contract. Bake the real files (WS-C
# 2026-06-15; baking is safe on BOTH image-only and git-worktree-at-/ deploys --
# unlike a tmpfiles `L+` symlink, which would clobber the tracked file in a worktree).
COPY MiOS.md AGENTS.md CLAUDE.md GEMINI.md /ctx/rootmd/

# repo = ROOT = git tree -- THAT is MiOS. The MiOS root deploys AS a git work
# tree (the Phase-1 Total Root Merge), so .git is a first-class part of the build
# root, not an afterthought. Shipping it makes /tmp/build a real git work tree so
# the source-drift gate (38-drift-checks.sh -> generate-names-registry.py) runs
# `git ls-files` over the full committed source exactly as the drift-gate CI job
# does -- instead of a partial os.walk (no .git) that reports false drift and
# aborts the build. .git lives only in this `scratch` ctx stage and the throwaway
# /tmp/build (both build-time: bind-mounted / rm'd); it is NOT in the final image.
COPY .git                  /ctx/.git/

FROM ${BASE_IMAGE}

# MIOS_VERSION: parameterized from the canonical repo-root VERSION file
# via build-mios.{sh,ps1} (which reads VERSION and passes
# `--build-arg MIOS_VERSION=$(cat VERSION)`). The default tracks the
# current stamp so a manual `podman build` without --build-arg still
# produces a valid image; callers who need a different version pin it
# at the command line.
ARG MIOS_VERSION=0.3.0

LABEL org.opencontainers.image.title="MiOS"
LABEL org.opencontainers.image.description="\MiOS is a user defined, customisable Linux distro based on Fedora/uBlue/uCore"
LABEL org.opencontainers.image.licenses="Apache-2.0"
LABEL org.opencontainers.image.source="https://github.com/mios-dev/MiOS"
LABEL org.opencontainers.image.version="v${MIOS_VERSION}"
LABEL containers.bootc="1"
LABEL ostree.bootable="1"

CMD ["/sbin/init"]

ARG MIOS_USER=mios
ARG MIOS_HOSTNAME=mios
ARG MIOS_FLATPAKS=
# Default AI model selection. Build-time overrides flow from
# mios.toml [ai] (resolved by build-mios.{sh,ps1} interactive prompts).
ARG MIOS_AI_MODEL=qwen2.5-coder:7b
ARG MIOS_AI_EMBED_MODEL=nomic-embed-text

# Build context is bind-mounted read-only from the `ctx` stage; the only
# writable copy lives under /tmp/build for scripts that need to mutate it.
RUN --mount=type=bind,from=ctx,source=/ctx,target=/ctx,ro \
    --mount=type=cache,dst=/var/cache/libdnf5,sharing=locked \
    --mount=type=cache,dst=/var/cache/dnf,sharing=locked \
    set -ex; \
    install -d -m 0755 /tmp/build; \
    cp -a /ctx/automation /ctx/usr /ctx/etc /ctx/VERSION /ctx/bib-configs /ctx/tools /tmp/build/; \
    # .git is BEST-EFFORT (never fatal under `set -e`): it makes /tmp/build a git
    # work tree so build.sh can `reset --hard` the pristine tree and the source-drift
    # gate (check 30) runs in-image. If it can't be copied, the gate degrades OPEN
    # (check 30 skips; the drift-gate CI job still validates it) rather than aborting
    # this RUN -- which is what a bare `cp ... /ctx/.git` under set -e would do.
    if [ -d /ctx/.git ]; then \
        cp -a /ctx/.git /tmp/build/.git 2>/dev/null && echo "[ctx] .git -> /tmp/build (git work tree)" \
            || echo "[ctx] WARN: .git copy failed -- source-drift check 30 will skip (drift-gate job covers it)"; \
    else \
        echo "[ctx] WARN: /ctx/.git absent -- source-drift check 30 will skip (drift-gate job covers it)"; \
    fi; \
    # WS-C: bake the repo-root agent MD files to / so a clean image is grounded
    # (agent-pipe reads /MiOS.md; the layered /etc + ~/.config overrides still win).
    install -m 0644 /ctx/rootmd/MiOS.md /ctx/rootmd/AGENTS.md /ctx/rootmd/CLAUDE.md /ctx/rootmd/GEMINI.md /; \
    # Defensive CRLF -> LF normalization. .gitattributes already pins
    # *.sh / *.toml / *.conf / *.yaml / *.json / *.md to LF, but Windows
    # build hosts (OneDrive sync in particular) bypass git's filter and
    # leak CRLF into the working tree. A single \r in a #!/bin/bash file
    # produces "$'\r': command not found" the moment bash sources it,
    # which surfaces as opaque exit-127 build failures hundreds of lines
    # later. Strip CRs from every text file in the writable build context
    # before any script runs -- cheap, idempotent, and immune to where
    # the leak originated. Binary files are skipped via grep -Iq. \
    find /tmp/build -type f \
        \( -name "*.sh" -o -name "*.toml" -o -name "*.conf" \
           -o -name "*.yaml" -o -name "*.yml" -o -name "*.json" \
           -o -name "*.md"  -o -name "*.service" -o -name "*.socket" \
           -o -name "*.timer" -o -name "*.target" -o -name "*.preset" \
           -o -name "*.container" -o -name "*.image" -o -name "*.kube" \
           -o -name "*.volume" -o -name "*.repo" -o -name "*.policy" \
           -o -name "*.rules" \) \
        -exec sed -i 's/\r$//' {} +; \
    export MIOS_TOML=/tmp/build/usr/share/mios/mios.toml; \
    export MIOS_VENDOR_TOML=/tmp/build/usr/share/mios/mios.toml; \
    bash /tmp/build/automation/lib/packages.sh >/dev/null 2>&1 || true; \
    source /tmp/build/automation/lib/packages.sh; \
    # Purge any stale/corrupt repo metadata left in the buildkit cache mount
    # from a previous failed build (zchunk checksum errors, partial syncs, etc.)
    ${DNF_BIN:-dnf5} clean metadata 2>/dev/null || ${DNF_BIN:-dnf} clean metadata 2>/dev/null || true; \
    install_packages_strict base; \
    if [[ -n "${MIOS_FLATPAKS}" ]]; then \
        echo "${MIOS_FLATPAKS}" | tr "," "\n" > /tmp/build/usr/share/mios/flatpak-list; \
    fi; \
    # Propagate operator-chosen model selection to the overlay scripts.
    export MIOS_AI_MODEL MIOS_AI_EMBED_MODEL; \
    bash /tmp/build/automation/08-system-files-overlay.sh; \
    chmod +x /tmp/build/automation/build.sh /tmp/build/automation/*.sh 2>/dev/null || true; \
    chmod +x /usr/libexec/mios/copy-build-log.sh 2>/dev/null || true; \
    CTX=/tmp/build /tmp/build/automation/build.sh; \
    dnf clean all; \
    rm -rf /tmp/build; \
    # /var/cache is bind-mounted by buildkit (--mount=type=cache above) for
    # the duration of this RUN, so trying to rm it returns EBUSY. Skip it;
    # buildkit doesn't bake cache mounts into the layer regardless.
    find /var -mindepth 1 -maxdepth 1 ! -name tmp ! -name cache -exec rm -rf {} +; \
    find /run -mindepth 1 -maxdepth 1 ! -name "secrets" -exec rm -rf {} + 2>/dev/null || true

RUN bootc completion bash > /etc/bash_completion.d/bootc

# OpenSCAP Image Hardening & Compliance Scan (BOOT-02)
# Runs dynamically using oscap-im only if [compliance].enabled is true in mios.toml.
# Requires --network=host to dynamically install SCE scanning/remediation dependencies at build time.
RUN --network=host set -ex; \
    if python3 -c "import tomllib; print(tomllib.load(open('/usr/share/mios/mios.toml', 'rb')).get('compliance', {}).get('enabled', False))" | grep -iq "true"; then \
        chmod +x /usr/libexec/mios/oscap-scan.py; \
        /usr/libexec/mios/oscap-scan.py; \
    fi

# System-extension pack step: intentionally a no-op when no sysext source
# trees are staged in the image. The pack tool at tools/mios-sysext-pack.sh
# consolidates one-or-more `/usr/lib/extensions/source-*` trees into a single
# monolithic SquashFS sysext (mitigation for the overlayfs stacking-depth
# limit on bootc systems). The current build is FHS-overlay-only and stages
# no sysext sources, so this step skips silently. To start packing sysexts:
#   1. Have an earlier automation/*.sh phase populate
#      /usr/lib/extensions/source-<name>/{usr,etc,...} with the files to pack.
#   2. Re-enable the RUN below (un-comment), passing every populated source
#      dir as a positional argument to mios-sysext-pack.sh.
#
# RUN --mount=type=bind,from=ctx,source=/ctx/tools,target=/ctx/tools,ro \
#     bash /ctx/tools/mios-sysext-pack.sh /usr/lib/extensions/source-*

# ── Bake logically-bound images (ARCHITECTURAL LAW 3 -- BOUND-IMAGES) ────────
# automation/08 symlinked every Quadlet into /usr/lib/bootc/bound-images.d/,
# which makes `bootc install` REQUIRE each Quadlet's Image= to already be
# present in container storage. Nothing was actually pulling them, so
# BIB/osbuild's bootc.install-to-filesystem stage failed EVERY deployment
# artifact with: "resolving bound image docker.io/crowdsecurity/crowdsec
# :latest ...: does not resolve to an image ID" (operator-confirmed
# 2026-05-14). This RUN is the missing bake step.
#
# Pull each bound image into /usr/lib/containers/storage -- an additional
# image store in IMMUTABLE /usr. It MUST live under /usr, not /var: the
# big RUN above ends with `find /var ... -exec rm -rf` (bootc treats /var
# as ephemeral), so /var/lib/containers/storage would be wiped. The
# storage.conf layers (/etc + /usr/share) list /usr/lib/containers/storage
# under additionalimagestores, so bootc install AND the running system
# resolve bound images from it with ZERO runtime pulls.
#
# --network=host: podman needs registry egress (same reason the big RUN
# above and `mios build`'s `podman build` use it on the WSL2 dev VM).
# Image= values are already rendered by 15-render-quadlets (run inside
# build.sh, above); the ${VAR:-default} fallback form is resolved here
# defensively. Any bound image that fails to bake fails the build LOUD --
# better than shipping an image whose every deployment artifact 404s.
# MIOS_BAKE_BOUND_IMAGES=0 skips the bake below. Baking 20+ sidecar images into
# one layer can exceed a disk-constrained runner's capacity and fail buildah's
# commit (exit 125 / "closed pipe" while storing the layer -- see the ~15-21 image
# threshold note further down). CI passes 0: build.sh + `bootc container lint` still
# fully validate the MiOS image; the bound images just resolve/pull at bootc DEPLOY
# time instead of being pre-baked. Real (large-disk) builds keep the default (1).
# Bake the bound sidecar images into the additional image store (Law 12
# BAKE-NOT-FETCH / Law 3 BOUND-IMAGES): every deployment artifact ships the
# sidecars offline-complete. The bake is SHARDED into one RUN per group
# (usr/share/mios/mios.toml [build].bake_groups, projected order) so each
# `buildah commit` serializes only that group's layer diff -- a single
# monolithic ~40-60GB commit overran disk-constrained runners (exit 125 /
# "io: read/write on closed pipe" while storing the layer; buildah writes
# ~2-3x the layer diff to temp during commit, containers/podman#22342). The
# heavy GPU-engine group commits FIRST, while the store is smallest, so the
# largest indivisible diff lands with the most free space. --mount=type=cache
# keeps pull/decompress scratch OUT of the committed layer, and the helper
# hard-links duplicate CUDA/torch blobs to shrink each group's diff. Every
# image is still baked -- this only moves layer boundaries, not membership.
# MIOS_BAKE_BOUND_IMAGES=0 skips the bake (PR / CI-validation builds; sidecars
# resolve at bootc deploy time); the published image ALWAYS bakes (default 1).
# NEVER --squash (it would coalesce every group back into one giant commit).
# All bake logic lives in usr/libexec/mios/mios-bake-group (Law 7: no inline
# Quadlet scraping here).
ARG MIOS_BAKE_BOUND_IMAGES=1
RUN --network=host --mount=type=cache,target=/var/tmp/mios-bakescratch \
    MIOS_BAKE_BOUND_IMAGES="${MIOS_BAKE_BOUND_IMAGES}" bash /usr/libexec/mios/57-mios-sys-build.sh
RUN --network=host --mount=type=cache,target=/var/tmp/mios-bakescratch \
    MIOS_BAKE_BOUND_IMAGES="${MIOS_BAKE_BOUND_IMAGES}" bash /usr/libexec/mios/mios-bake-group extra
# additionalimagestores must be world-READABLE (the host shares this store with
# every unprivileged user via /etc/containers/storage.conf's additionalimagestores
# entry). podman pull's defaults leave the per-backend subdirs (overlay-images,
# overlay-containers, overlay-layers, libpod) at mode 0700 -- root-only.
# Unprivileged podman invocations (flatpak shim, `mios` operator shell, anything
# forking podman) then die with: "configure storage: open
# .../overlay-images/images.lock: permission denied".
#
# Only chmod the MAIN storage directory here -- do not touch the per-driver
# subdirectories (overlay, libpod, etc.). Mutating permissions of those inside
# the build container causes buildah commit failures (exit 125) as the image
# count grows (>15-21 images). The deep recursion happens at boot via
# mios-additionalimagestores-perms.service (preset-enabled, commit f5a1ac9),
# which runs chmod -R go+rX on the running host where build-time commit limits
# do not matter.
RUN chmod 0755 /usr/lib/containers/storage

RUN ostree container commit
# bootc container lint MUST be the final instruction (ARCHITECTURAL LAW 4).
RUN bootc container lint
