#!/usr/bin/env bash
# Normalize to LF line endings (fixes SC1017)
set -euo pipefail

echo "==> Installing moby-engine (Docker) alongside Podman..."

# shellcheck source=lib/common.sh
source "$(dirname "$0")/lib/common.sh"

# moby-engine conflicts with podman-docker over /usr/bin/docker. Use --allowerasing
# to let dnf resolve the conflict without an explicit remove (§3.9: no dnf remove).
$DNF_BIN "${DNF_SETOPT[@]}" install -y "${DNF_OPTS[@]}" moby-engine

# Enable the Docker socket to ensure it's available on boot
systemctl enable docker.socket

# Ensure the docker group exists so we can map users to it later via sysusers
groupadd -r docker 2>/dev/null || true
