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

# Agent CLIs available by default: the Claude Code CLI system-wide here, and
# the Antigravity CLI (agy) plus the dev-loop skill per-user at postCreate,
# by delegating to -dev-loop's own setup script rather than duplicating it.
RUN npm install -g @google/gemini-cli @anthropic-ai/claude-code

# mios-mon's TUI imports rich/textual/psutil and pip-installs them on first run
# if they are missing. Bake them so a fresh container does not spend that first
# run downloading — and so the tool degrades to a clear message rather than a
# FATAL when the network or pip is unavailable.
RUN python3 -m pip install --no-cache-dir rich textual psutil

# Spell the sudoers username exactly as the account and give it an explicit
# (ALL) runas spec. This is hygiene, not a fix: the previous "Mios-dev"
# spelling was measured to work, since sudo matches the username
# case-insensitively here. visudo -cf fails the build on a malformed rule
# rather than shipping one that silently grants nothing — postCreateCommand
# ("sudo bash /usr/local/bin/mios-root-overlay") depends on this drop-in.
RUN useradd -m -u 1000 -s /usr/bin/zsh mios-dev \
    && echo "mios-dev ALL=(ALL) NOPASSWD:ALL" > /etc/sudoers.d/mios-dev \
    && chmod 0440 /etc/sudoers.d/mios-dev \
    && visudo -cf /etc/sudoers.d/mios-dev

COPY .devcontainer/install-root-overlay.sh /usr/local/bin/mios-root-overlay
RUN chmod +x /usr/local/bin/mios-root-overlay

ENV MIOS_DEVCONTAINER=1
ENV MIOS_VERSION=0.3.0

# The Antigravity CLI is baked into the image rather than left to postCreate.
# Two reasons postCreate could not be trusted: a Codespaces prebuild does not
# re-run postCreateCommand for codespaces created from that prebuild, and the
# dev-loop checkout agy used to come from lives in a PRIVATE repo that a public
# repo's codespace token cannot clone -- so it failed silently behind `|| true`.
#
# Guarded on purpose: a transient network failure must degrade to a warning,
# never fail the image build. A failed devcontainer build drops Codespaces into
# a recovery container with nothing installed at all, which is far worse.
USER mios-dev
RUN set -u; tmp="$(mktemp -d)"; \
    if curl -fsSL --retry 4 --retry-delay 2 https://antigravity.google/cli/install.sh -o "$tmp/install.sh" \
       && [ -s "$tmp/install.sh" ] && bash "$tmp/install.sh" >/dev/null 2>&1; then \
         /home/mios-dev/.local/bin/agy --version; \
    else \
         echo "WARNING: Antigravity CLI not installed at build time" >&2; \
    fi; \
    rm -rf "$tmp"
ENV PATH="/home/mios-dev/.local/bin:${PATH}"

WORKDIR /mios
CMD ["/usr/bin/zsh"]
