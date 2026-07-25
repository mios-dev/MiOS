#!/usr/bin/env bash
# MIOS_INSTALLER_ROLE=container-build-installer
# AI-hint: Thin redirector to install-fhs.sh -- the single FHS-overlay installer for non-bootc Fedora hosts (rsyncs usr/etc/var/srv onto /, materializes /v1, runs sysusers/tmpfiles, reloads systemd). install.sh and install-fhs.sh were byte-identical; deduped to ONE implementation. Superseded by `mios-apply fhs-host` once the unified git=$ROOT engine lands.
# 'MiOS' system-side installer (FHS overlay path) -- redirector.
#
# install.sh and install-fhs.sh were byte-for-byte identical FHS-overlay installers (verified).
# Deduped to a single source of truth (install-fhs.sh); this file forwards to it so the historical
# name, the # MIOS_INSTALLER_ROLE marker (check-86 family), and the generate-build-scripts.py LAYERS
# doc-bundle all keep working. The whole ad-hoc rsync path is slated for replacement by
# `mios-apply fhs-host` (git=$ROOT: root-merge the tree onto / then run the universal stage set).
set -euo pipefail
exec bash "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/install-fhs.sh" "$@"
