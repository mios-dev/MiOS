# AI-hint: Defines the multi-stage Docker build process for the MiOS image, incorporating system configurations, automation scripts, and AI model bake parameters into the final bootable container.
# AI-related: /tmp/build/automation/lib/packages.sh, automation/45-coderun-sandbox-build.sh, /usr/share/mios/mios.toml, /usr/share/mios/flatpak-list, /usr/libexec/mios/copy-build-log.sh, mios-bootstrap, mios-dev, mios-sysext-pack, mios-coderun-sandbox, mios-additionalimagestores-perms
ARG BASE_IMAGE=ghcr.io/ublue-os/ucore-hci:stable-nvidia

FROM scratch AS ctx
COPY automation/           /ctx/automation/
COPY usr/                  /ctx/usr/
COPY etc/                  /ctx/etc/
COPY VERSION               /ctx/VERSION
COPY config/artifacts/     /ctx/bib-configs/
COPY tools/                /ctx/tools/
COPY MiOS.md               /ctx/rootmd/MiOS.md
COPY AGENTS.md             /ctx/rootmd/AGENTS.md
COPY CLAUDE.md             /ctx/rootmd/CLAUDE.md
COPY GEMINI.md             /ctx/rootmd/GEMINI.md

COPY .dotfiles/             /ctx/.dotfiles/
COPY .git                  /ctx/.git/
COPY Justfile              /ctx/Justfile

FROM docker.io/library/rust:slim AS rust-builder
WORKDIR /build
ENV CARGO_TARGET_DIR=/build/tools/native/target
COPY src/mios-rs /build/src/mios-rs
COPY tools/native /build/tools/native
COPY usr/share/mios/mios.toml /build/usr/share/mios/mios.toml
COPY automation/55-native-build.sh /build/automation/55-native-build.sh
# Fetch locked host-platform graphs before offline metadata inspection; Windows
# dependencies belong to the separate cross-build lane. The
# shared native installer selects Linux binaries and FHS paths from the SSOT;
# Windows-only artifacts belong to the MiOS-DEV cross-build lane.
RUN --mount=type=cache,target=/usr/local/cargo/registry \
    --mount=type=cache,target=/build/tools/native/target \
    cargo fetch --locked --target host-tuple --manifest-path /build/src/mios-rs/Cargo.toml && \
    cargo fetch --locked --target host-tuple --manifest-path /build/tools/native/Cargo.toml && \
    MIOS_NATIVE_INSTALL_ROOT=/out bash /build/automation/55-native-build.sh

FROM ${BASE_IMAGE}

# MIOS_VERSION: parameterized from the canonical repo-root VERSION file
ARG MIOS_VERSION=0.3.0
ARG SOURCE_DATE_EPOCH
ENV SOURCE_DATE_EPOCH=${SOURCE_DATE_EPOCH}

LABEL org.opencontainers.image.title="MiOS"
LABEL org.opencontainers.image.description="MiOS is a user defined, customisable Linux distro based on Fedora/uBlue/uCore"
LABEL org.opencontainers.image.licenses="Apache-2.0"
LABEL org.opencontainers.image.source="https://github.com/mios-dev/MiOS"
LABEL org.opencontainers.image.version="v${MIOS_VERSION}"
LABEL containers.bootc="1"
LABEL ostree.bootable="1"

COPY --from=rust-builder /out/usr/ /usr/

ARG MIOS_USER=mios
ARG MIOS_HOSTNAME=mios
ARG MIOS_FLATPAKS=
ARG MIOS_AI_MODEL=qwen2.5-coder:7b
ARG MIOS_AI_EMBED_MODEL=nomic-embed-text
# ADR-0025 image profile ([profiles]); empty means [profiles].default.
ARG MIOS_PROFILES_DEFAULT

RUN --mount=type=bind,from=ctx,source=/ctx,target=/ctx,ro \
    --mount=type=cache,dst=/var/cache/libdnf5,sharing=locked \
    --mount=type=cache,dst=/var/cache/dnf5,sharing=locked \
    --mount=type=cache,dst=/var/cache/dnf,sharing=locked \
    set -ex; \
    install -d -m 0755 /tmp/build; \
    cp -a /ctx/automation /ctx/usr /ctx/etc /ctx/VERSION /ctx/bib-configs /ctx/tools /ctx/Justfile /ctx/.dotfiles /tmp/build/; \
    if [ -d /ctx/.git ]; then \
        cp -a /ctx/.git /tmp/build/.git 2>/dev/null && echo "[ctx] .git -> /tmp/build" \
            || echo "[ctx] WARN: .git copy failed"; \
    else \
        echo "[ctx] WARN: /ctx/.git absent"; \
    fi; \
    if [ -d /ctx/rootmd ]; then \
        cp -f /ctx/rootmd/*.md / 2>/dev/null || true; \
        chmod 0644 /MiOS.md /AGENTS.md /CLAUDE.md /GEMINI.md 2>/dev/null || true; \
    fi; \
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
    ${DNF_BIN:-dnf5} clean metadata 2>/dev/null || ${DNF_BIN:-dnf} clean metadata 2>/dev/null || true; \
    install_packages_strict base; \
    if [[ -n "${MIOS_FLATPAKS}" ]]; then \
        echo "${MIOS_FLATPAKS}" | tr "," "\n" > /tmp/build/usr/share/mios/flatpak-list; \
    fi; \
    export MIOS_AI_MODEL MIOS_AI_EMBED_MODEL MIOS_PROFILES_DEFAULT; \
    bash /tmp/build/automation/01-system-files-overlay.sh; \
    chmod +x /tmp/build/automation/build.sh /tmp/build/automation/*.sh 2>/dev/null || true; \
    chmod +x /usr/libexec/mios/copy-build-log.sh 2>/dev/null || true; \
    /usr/libexec/mios/miosd drift-check --root /tmp/build; \
    CTX=/tmp/build /tmp/build/automation/build.sh; \
    dnf clean all; \
    rm -rf /tmp/build; \
    find /var -mindepth 1 -maxdepth 1 ! -name tmp ! -name cache -exec rm -rf {} +; \
    find /run -mindepth 1 -maxdepth 1 ! -name "secrets" -exec rm -rf {} + 2>/dev/null || true

RUN bootc completion bash > /etc/bash_completion.d/bootc

RUN --network=host set -ex; \
    if python3 -c "import tomllib; print(tomllib.load(open('/usr/share/mios/mios.toml', 'rb')).get('compliance', {}).get('enabled', False))" | grep -iq "true"; then \
        chmod +x /usr/libexec/mios/oscap-scan.py; \
        /usr/libexec/mios/oscap-scan.py; \
    fi


# MIOS_BAKE_BOUND_IMAGES=0 skips the bake below (for PR / CI-validation builds;
# sidecars resolve at bootc deploy time instead of being pre-baked).
ARG MIOS_BAKE_BOUND_IMAGES=1
RUN --network=host --mount=type=cache,target=/var/tmp/mios-bakescratch \
    MIOS_BAKE_BOUND_IMAGES="${MIOS_BAKE_BOUND_IMAGES}" bash /usr/libexec/mios/57-mios-sys-build.sh
RUN --network=host --mount=type=cache,target=/var/tmp/mios-bakescratch \
    MIOS_BAKE_BOUND_IMAGES="${MIOS_BAKE_BOUND_IMAGES}" bash /usr/libexec/mios/mios-bake-group heavy
RUN --network=host --mount=type=cache,target=/var/tmp/mios-bakescratch \
    MIOS_BAKE_BOUND_IMAGES="${MIOS_BAKE_BOUND_IMAGES}" bash /usr/libexec/mios/mios-bake-group extra
RUN chmod 0755 /usr/lib/containers/storage

CMD ["/sbin/init"]

RUN ostree container commit
RUN bootc container lint
