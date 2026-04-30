FROM fedora:rawhide

# Install MiOS Toolchain
RUN dnf install -y     just     fastfetch     btop     podman     buildah     skopeo     jq     yq     rsync     git     nodejs     npm     sudo     zsh     findutils     grep     sed     gawk     && dnf clean all


# Setup vscode user for Codespaces parity
RUN useradd -m -s /usr/bin/zsh vscode &&     echo "vscode ALL=(ALL) NOPASSWD:ALL" > /etc/sudoers.d/vscode

USER vscode
WORKDIR /workspaces/MiOS
