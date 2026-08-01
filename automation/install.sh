#!/usr/bin/env bash
# MIOS_INSTALLER_ROLE=container-build-installer
# AI-hint: Thin redirector to install-fhs.sh -- the single FHS-overlay installer for non-bootc Fedora hosts (rsyncs usr/etc/var/srv onto /, materializes /v1, runs sysusers/tmpfiles, reloads systemd). install.sh and install-fhs.sh were byte-identical; deduped to ONE implementation. Superseded by `mios-apply fhs-host` once the unified git=$ROOT engine lands.
set -euo pipefail
exec bash "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/install-fhs.sh" "$@"
