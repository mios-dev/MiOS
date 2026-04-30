# syntax=docker/dockerfile:1.9
# ============================================================================
# MiOS - Unified Image (v0.2.0)
# ============================================================================

ARG BASE_IMAGE=ghcr.io/ublue-os/ucore-hci:stable-nvidia

# --- ctx stage: build context ---
FROM scratch AS ctx
COPY automation/           /ctx/automation/
COPY usr/                  /ctx/usr/
COPY etc/                  /ctx/etc/
COPY home/                 /ctx/home/
COPY usr/share/mios/PACKAGES.md /ctx/PACKAGES.md
COPY VERSION               /ctx/VERSION
COPY config/artifacts/     /ctx/bib-configs/
COPY tools/                /ctx/tools/

# --- main stage ---
FROM 

LABEL org.opencontainers.image.title="MiOS"
LABEL org.opencontainers.image.version="v0.2.0"
LABEL containers.bootc="1"
LABEL ostree.bootable="1"

CMD ["/sbin/init"]

ARG MIOS_USER=mios
ARG MIOS_HOSTNAME=mios
ARG MIOS_FLATPAKS=

# Copy context
COPY --from=ctx /ctx /ctx

# Unified Build Pipeline
RUN --mount=type=cache,dst=/var/cache/libdnf5,sharing=locked     --mount=type=cache,dst=/var/cache/dnf,sharing=locked     set -ex;     dnf install -y --skip-unavailable --setopt=install_weak_deps=False         policycoreutils-python-utils         selinux-policy-targeted         firewalld         audit         fapolicyd         crowdsec         usbguard         kernel-devel;     if [[ -n "" ]]; then         echo "" | tr "," "\n" > /ctx/usr/share/mios/flatpak-list;     fi;     bash /ctx/automation/08-system-files-overlay.sh;     chmod +x /ctx/automation/build.sh /ctx/automation/*.sh;     /ctx/automation/build.sh;     dnf clean all;     find /var -mindepth 1 -maxdepth 1 ! -name tmp -exec rm -rf {} +;     find /run -mindepth 1 -maxdepth 1 ! -name "secrets" -exec rm -rf {} + 2>/dev/null || true

RUN bootc completion bash > /etc/bash_completion.d/bootc
RUN mkdir -p /usr/lib/extensions/source && chmod +x /ctx/tools/mios-sysext-pack.sh && /ctx/tools/mios-sysext-pack.sh /usr/lib/extensions/source || true
RUN rm -rf /ctx && ostree container commit
RUN bootc container lint
