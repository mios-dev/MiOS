FROM fedora:latest

# 1. Install MiOS Toolchain + System Components
RUN dnf install -y     just     fastfetch     btop     podman     buildah     skopeo     jq     yq     rsync     git     nodejs     npm     sudo     zsh     findutils     grep     sed     gawk     policycoreutils     util-linux     && dnf clean all

# 2. Install Gemini CLI to root (standard system path)
RUN npm install -g @google/gemini-cli

# 3. Setup MiOS Development User
# We use UID 1000 to match common host users for bind-mount permissions
RUN useradd -m -u 1000 -s /usr/bin/zsh mios-dev &&     echo "mios-dev ALL=(ALL) NOPASSWD:ALL" > /etc/sudoers.d/mios-dev

# 4. Environment Metadata
ENV MIOS_DEVCONTAINER=1
ENV MIOS_VERSION=0.2.0

# 5. Prepare system for overlay concept
# Create mount points if they do not exist
RUN mkdir -p /mios /srv /var/home /usr/local

WORKDIR /mios
USER mios-dev
CMD ["/usr/bin/zsh"]
