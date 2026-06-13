#!/usr/bin/env bash
# AI-hint: Installs and enables the moby-engine (Docker) package and its systemd socket to provide container runtime capabilities alongside Podman, resolving package conflicts via the defined moby configuration.
# AI-related: docker.socket
# Normalize to LF line endings (fixes SC1017)
set -euo pipefail

echo "==> Installing moby-engine (Docker) alongside Podman..."

# shellcheck source=lib/packages.sh
source "$(dirname "$0")/lib/packages.sh"
source "$(dirname "$0")/lib/common.sh"

# moby-engine conflicts with podman-docker over /usr/bin/docker. install_packages
# routes through dnf which resolves the conflict at install time; mios.toml
# [packages.moby] is the SSOT for every RPM (see CLAUDE.md / CONTRIBUTING.md).
install_packages "moby"

# Enable the Docker socket to ensure it's available on boot
systemctl enable docker.socket

# Ensure the docker group exists so users can be mapped to it later via sysusers
groupadd -r docker 2>/dev/null || true
