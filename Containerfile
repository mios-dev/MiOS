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

FROM ${BASE_IMAGE}

# MIOS_VERSION: parameterized from the canonical repo-root VERSION file
# via build-mios.{sh,ps1} (which reads VERSION and passes
# `--build-arg MIOS_VERSION=$(cat VERSION)`). The default tracks the
# current stamp so a manual `podman build` without --build-arg still
# produces a valid image; callers who need a different version pin it
# at the command line.
ARG MIOS_VERSION=0.2.4

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
# mios.toml [ai] (resolved by build-mios.{sh,ps1} interactive prompts)
# and propagate to automation/37-ollama-prep.sh via the
# MIOS_OLLAMA_BAKE_MODELS env var. Empty disables the build-time bake.
ARG MIOS_AI_MODEL=qwen2.5-coder:7b
ARG MIOS_AI_EMBED_MODEL=nomic-embed-text
ARG MIOS_OLLAMA_BAKE_MODELS=qwen2.5-coder:7b,nomic-embed-text

# Build context is bind-mounted read-only from the `ctx` stage; the only
# writable copy lives under /tmp/build for scripts that need to mutate it.
RUN --mount=type=bind,from=ctx,source=/ctx,target=/ctx,ro \
    --mount=type=cache,dst=/var/cache/libdnf5,sharing=locked \
    --mount=type=cache,dst=/var/cache/dnf,sharing=locked \
    set -ex; \
    install -d -m 0755 /tmp/build; \
    cp -a /ctx/automation /ctx/usr /ctx/etc /ctx/VERSION /ctx/bib-configs /ctx/tools /tmp/build/; \
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
    bash /tmp/build/automation/lib/packages.sh >/dev/null 2>&1 || true; \
    source /tmp/build/automation/lib/packages.sh; \
    # Purge any stale/corrupt repo metadata left in the buildkit cache mount
    # from a previous failed build (zchunk checksum errors, partial syncs, etc.)
    ${DNF_BIN:-dnf5} clean metadata 2>/dev/null || ${DNF_BIN:-dnf} clean metadata 2>/dev/null || true; \
    install_packages_strict base; \
    if [[ -n "${MIOS_FLATPAKS}" ]]; then \
        echo "${MIOS_FLATPAKS}" | tr "," "\n" > /tmp/build/usr/share/mios/flatpak-list; \
    fi; \
    # Propagate operator-chosen model selection into 37-ollama-prep.sh.
    # The build-mios.{sh,ps1} prompt sets MIOS_OLLAMA_BAKE_MODELS to the
    # selected chat + embed model pair (or operator-supplied custom CSV).
    export MIOS_AI_MODEL MIOS_AI_EMBED_MODEL MIOS_OLLAMA_BAKE_MODELS; \
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
RUN ostree container commit
# bootc container lint MUST be the final instruction (ARCHITECTURAL LAW 4).
RUN bootc container lint
