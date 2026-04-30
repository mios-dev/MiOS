# syntax=docker/dockerfile:1.9
# ============================================================================
# MiOS - Unified Image (v0.1.4)
# ============================================================================
# One image. Every role. Every surface. Every GPU vendor.
#
# Base:     Controlled by MIOS_BASE_IMAGE in .env.mios
#           Default: ghcr.io/ublue-os/ucore-hci:stable-nvidia
# ============================================================================

ARG BASE_IMAGE=ghcr.io/ublue-os/ucore-hci:stable-nvidia # @track:IMG_BASE

# ----------------------------------------------------------------------------
# ctx stage: build context
# ----------------------------------------------------------------------------
FROM scratch AS ctx
COPY automation/           /ctx/automation/
COPY usr/                  /ctx/usr/
COPY etc/                  /ctx/etc/
COPY home/                 /ctx/home/
COPY usr/share/mios/PACKAGES.md                          /ctx/PACKAGES.md
COPY VERSION            /ctx/VERSION
COPY config/artifacts/       /ctx/bib-configs/
COPY tools/             /ctx/tools/

# ----------------------------------------------------------------------------
# main stage
# ----------------------------------------------------------------------------
FROM ${BASE_IMAGE}

LABEL org.opencontainers.image.title="MiOS"
LABEL org.opencontainers.image.description="Unified immutable cloud-native workstation OS"
LABEL org.opencontainers.image.source="https://github.com/MiOS-DEV/MiOS-bootstrap"
LABEL org.opencontainers.image.licenses="Apache-2.0"
LABEL org.opencontainers.image.version="v0.1.4"
LABEL containers.bootc="1"
LABEL ostree.bootable="1"

CMD ["/sbin/init"]

ARG MIOS_USER=mios
ARG MIOS_HOSTNAME=mios
ARG MIOS_FLATPAKS=

# Build context mounted read-only
COPY --from=ctx /ctx /ctx

# Unified Build Pipeline: Install -> Overlay -> Automation -> Cleanup
RUN --mount=type=cache,dst=/var/cache/libdnf5,sharing=locked     --mount=type=cache,dst=/var/cache/dnf,sharing=locked         set -e;     # 1. Install essential security packages     dnf install -y --skip-unavailable --setopt=install_weak_deps=False         policycoreutils-python-utils         selinux-policy-targeted         firewalld         audit         fapolicyd         crowdsec         usbguard         kernel-devel;     # 2. Inject flatpaks if provided     if [[ -n "${MIOS_FLATPAKS}" ]]; then         echo "${MIOS_FLATPAKS}" | tr "," "\n" > /ctx/usr/share/mios/flatpak-list;     fi;     # 3. Rootfs Overlay     bash /ctx/automation/08-system-files-overlay.sh;     # 4. Numbered Pipeline     chmod +x /ctx/automation/build.sh /ctx/automation/*.sh 2>/dev/null || true;     chmod +x /usr/libexec/mios/copy-build-log.sh;     /ctx/automation/build.sh;     # 5. Mandatory Cleanup for bootc lint     dnf clean all;     find /var -mindepth 1 -maxdepth 1 ! -name tmp -exec rm -rf {} +;     find /run -mindepth 1 -maxdepth 1 ! -name "secrets" -exec rm -rf {} + 2>/dev/null || true

# Install bootc bash completions
RUN bootc completion bash > /etc/bash_completion.d/bootc

# -- systemd-sysext consolidation ----------
RUN mkdir -p /usr/lib/extensions/source  && chmod +x /ctx/tools/mios-sysext-pack.sh  && /ctx/tools/mios-sysext-pack.sh /usr/lib/extensions/source || true

RUN rm -rf /ctx  && ostree container commit
RUN bootc container lint
