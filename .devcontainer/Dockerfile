# AI-hint: Defines the Fedora-based container environment for MiOS development, installing the core toolchain (podman, bootc, rpm-ostree), the AI CLIs, and configuring the mios-dev user and root overlay bootstrap.
# AI-related: mios-dev, mios-root-overlay
#
# This is the DEVELOPMENT container for editing this source tree. It is not the
# OS image: that is built by the root Containerfile from ${BASE_IMAGE}
# (ucore-hci). Fedora is pinned rather than floating on :latest so the image
# name and the container's contents cannot drift apart, per the repo's pinning
# convention (newest stable upstream, bumped forward on next touch).
ARG FEDORA_VERSION=44
FROM registry.fedoraproject.org/fedora:${FEDORA_VERSION}

# Core MiOS build/lifecycle toolchain, plus the shared dev toolchain every MiOS
# repo's container carries (see mios-bootstrap and -dev-loop devcontainers).
RUN dnf install -y --setopt=install_weak_deps=False \
        just \
        podman podman-compose buildah skopeo \
        bootc bootupd ostree rpm-ostree \
        jq yq rsync git \
        nodejs npm \
        python3 python3-pip \
        sudo zsh \
        findutils grep sed gawk diffutils patch \
        ripgrep tar gzip unzip zip \
        policycoreutils util-linux authselect \
        openssl qemu-img attr \
        ShellCheck \
    && dnf clean all

RUN npm install -g @google/gemini-cli

# The sudoers username must match the account exactly — sudoers is
# case-sensitive, so a mismatch silently grants nothing and postCreateCommand
# ("sudo bash /usr/local/bin/mios-root-overlay") stalls on a password prompt.
RUN useradd -m -u 1000 -s /usr/bin/zsh mios-dev \
    && echo "mios-dev ALL=(ALL) NOPASSWD:ALL" > /etc/sudoers.d/mios-dev \
    && chmod 0440 /etc/sudoers.d/mios-dev \
    && visudo -cf /etc/sudoers.d/mios-dev

COPY .devcontainer/install-root-overlay.sh /usr/local/bin/mios-root-overlay
RUN chmod +x /usr/local/bin/mios-root-overlay

ENV MIOS_DEVCONTAINER=1
ENV MIOS_VERSION=0.3.0

WORKDIR /mios
USER mios-dev
CMD ["/usr/bin/zsh"]
