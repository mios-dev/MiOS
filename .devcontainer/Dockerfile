# AI-hint: Defines the Fedora-based container environment for MiOS development, installing the core toolchain (podman, bootc, rpm-ostree), Gemini CLI, and configuring the mios-dev user and root overlay bootstrap.
# AI-related: mios-dev, mios-root-overlay
FROM fedora:latest

RUN dnf install -y     just     podman     podman-compose     buildah     skopeo     bootc     bootupd     ostree     rpm-ostree     jq     yq     rsync     git     nodejs     npm     sudo     zsh     findutils     grep     sed     gawk     policycoreutils     util-linux     authselect     openssl     qemu-img     attr     diffutils     && dnf clean all

RUN npm install -g @google/gemini-cli

RUN useradd -m -u 1000 -s /usr/bin/zsh mios-dev &&     echo "Mios-dev ALL= NOPASSWD:ALL" > /etc/sudoers.d/mios-dev

COPY .devcontainer/install-root-overlay.sh /usr/local/bin/mios-root-overlay
RUN chmod +x /usr/local/bin/mios-root-overlay

ENV MIOS_DEVCONTAINER=1
ENV MIOS_VERSION=0.2.0

WORKDIR /mios
USER mios-dev
CMD ["/usr/bin/zsh"]
