# syntax=docker/dockerfile:1.9
# ============================================================================
# MiOS - Unified Image (v0.1.4) - FHS Native
# ============================================================================
ARG BASE_IMAGE=ghcr.io/ublue-os/ucore-hci:stable-nvidia

# ----------------------------------------------------------------------------
# main stage
# ----------------------------------------------------------------------------
FROM ${BASE_IMAGE}

LABEL org.opencontainers.image.title="MiOS"
LABEL org.opencontainers.image.description="Unified immutable cloud-native workstation OS"
LABEL org.opencontainers.image.version="v0.1.4"
LABEL containers.bootc="1"
LABEL ostree.bootable="1"

CMD ["/sbin/init"]

# Overlay MiOS FHS components
COPY usr/ /usr/
COPY etc/ /etc/
COPY var/ /var/
COPY v1/ /v1/

# Build Orchestration
RUN --mount=type=cache,dst=/var/cache/libdnf5,sharing=locked \
    --mount=type=cache,dst=/var/cache/dnf,sharing=locked     \
    set -e; \
    chmod +x /usr/lib/mios/automation/build.sh; \
    /usr/lib/mios/automation/build.sh

# Cleanup
RUN rm -rf /var/log/* /var/tmp/* /var/cache/dnf/* /var/cache/libdnf5/* /tmp/* \
 && find /run -mindepth 1 -maxdepth 1 ! -name 'secrets' -exec rm -rf {} + 2>/dev/null || true

RUN bootc completion bash > /etc/bash_completion.d/bootc || true
RUN ostree container commit
RUN bootc container lint
# MiOS Build Trigger: Wed Apr 29 05:22:00 AM UTC 2026
