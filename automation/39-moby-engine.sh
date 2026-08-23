#!/usr/bin/env bash
# MIOS_APPLY_CLASS=universal
# AI-hint: Installs and enables the moby-engine (Docker) package and its systemd socket to provide container runtime capabiliti...
# AI-doc: usr/share/doc/mios/manual/automation.md
set -euo pipefail

for _mlog in "$(dirname "${BASH_SOURCE[0]}")/../usr/lib/mios/log.sh" /usr/lib/mios/log.sh; do [ -r "$_mlog" ] && . "$_mlog" && break; done

mios_log "Installing moby-engine alongside Podman"

source "$(dirname "$0")/lib/packages.sh"
source "$(dirname "$0")/lib/common.sh"

install_packages "moby"

systemctl enable docker.socket

groupadd -r docker 2>/dev/null || true
