FROM fedora:latest

# 1. Install MiOS Toolchain + Upstream Packages
RUN dnf install -y     just     fastfetch     btop     podman     buildah     skopeo     jq     yq     rsync     git     nodejs     npm     sudo     zsh     findutils     grep     sed     gawk     policycoreutils     && dnf clean all

# 2. Install Gemini CLI to root
RUN npm install -g @google/gemini-cli

# 3. Setup MiOS Development User
RUN useradd -m -s /usr/bin/zsh mios-dev &&     echo "mios-dev ALL=(ALL) NOPASSWD:ALL" > /etc/sudoers.d/mios-dev

# 4. Mirror MiOS Pattern: Working Directory is the repository root
WORKDIR /mios
USER mios-dev

# 5. Environment Metadata
ENV MIOS_DEVCONTAINER=1
ENV MIOS_VERSION=0.2.0

CMD ["/usr/bin/zsh"]
