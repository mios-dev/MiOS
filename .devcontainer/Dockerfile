# AI-hint: Defines the unified Fedora development container for the MiOS ecosystem (MiOS, mios-bootstrap, and -dev-loop).
# Floats on Fedora latest, providing full toolchain coverage: Rust, dual Python (3.14 + 3.11), Podman/Docker, and Agent CLIs.
FROM docker.io/library/fedora:latest

# 1. Base OS Packages, Compilers, Runtimes, and Utilities
RUN dnf install -y --setopt=install_weak_deps=False \
        just \
        podman podman-compose podman-docker buildah skopeo \
        bootc bootupd ostree rpm-ostree \
        jq yq rsync git tmux \
        nodejs npm \
        python3 python3-pip python3-devel \
        python3.11 python3.11-devel \
        python3-rich python3-textual python3-psutil python3-pytest python3-jsonschema \
        rust cargo clippy rustfmt gcc gcc-c++ make \
        dbus-daemon dbus-tools gnome-keyring libsecret \
        procps-ng util-linux shadow-utils authselect \
        sudo zsh \
        findutils grep sed gawk diffutils patch \
        ripgrep tar gzip unzip zip \
        openssl qemu-img attr \
        ShellCheck \
    && dnf clean all

# 2. Agent CLIs (System-wide node packages)
RUN npm install -g @anthropic-ai/claude-code @google/gemini-cli

# 3. User Setup (mios-dev UID 1000, matching host bind mount and sudoers)
RUN useradd -m -u 1000 -s /usr/bin/zsh mios-dev \
    && echo "mios-dev ALL=(ALL) NOPASSWD:ALL" > /etc/sudoers.d/mios-dev \
    && chmod 0440 /etc/sudoers.d/mios-dev \
    && visudo -cf /etc/sudoers.d/mios-dev

COPY .devcontainer/install-root-overlay.sh /usr/local/bin/mios-root-overlay
RUN chmod +x /usr/local/bin/mios-root-overlay

# 4. Antigravity CLI (baked into image, not just tolerated)
USER mios-dev
RUN set -eux; \
    tmp="$(mktemp -d)"; \
    curl -fsSL --retry 4 --retry-delay 2 https://antigravity.google/cli/install.sh -o "$tmp/install.sh"; \
    bash "$tmp/install.sh"; \
    /home/mios-dev/.local/bin/agy --version; \
    rm -rf "$tmp"

ENV PATH="/home/mios-dev/.local/bin:${PATH}"
ENV MIOS_DEVCONTAINER=1
ENV MIOS_VERSION=0.3.0

WORKDIR /workspaces/MiOS
CMD ["/usr/bin/zsh"]
