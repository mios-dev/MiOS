#!/usr/bin/env bash
# MIOS_INSTALLER_ROLE=container-build-installer
# AI-hint: Thin redirector to install-fhs.sh -- the single FHS-overlay installer for non-bootc Fedora hosts (rsyncs...
# AI-doc: usr/share/doc/mios/manual/_harvest/automation_install_sh.md
set -euo pipefail
exec bash "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/install-fhs.sh" "$@"
