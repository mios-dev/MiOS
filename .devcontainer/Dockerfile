FROM fedora:latest

# 1. Install MiOS Toolchain + System Components
RUN dnf install -y \
    just \
    fastfetch \
    btop \
    podman \
    buildah \
    skopeo \
    jq \
    yq \
    rsync \
    git \
    nodejs \
    npm \
    sudo \
    zsh \
    findutils \
    grep \
    sed \
    gawk \
    policycoreutils \
    util-linux \
    && dnf clean all

# 2. Install Gemini CLI to root
RUN npm install -g @google/gemini-cli

# 3. Setup MiOS Development User
RUN useradd -m -u 1000 -s /usr/bin/zsh mios-dev && \
    echo "mios-dev ALL=(ALL) NOPASSWD:ALL" > /etc/sudoers.d/mios-dev

# 4. Prepare MiOS Root Overlay Bootstrap
COPY .devcontainer/install-root-overlay.sh /usr/local/bin/mios-root-overlay
RUN chmod +x /usr/local/bin/mios-root-overlay

# 5. Environment Metadata
ENV MIOS_DEVCONTAINER=1
ENV MIOS_VERSION=0.2.0

WORKDIR /mios
USER mios-dev
CMD ["/usr/bin/zsh"]
