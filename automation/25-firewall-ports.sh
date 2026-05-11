#!/usr/bin/env bash
set -euo pipefail

# shellcheck source=lib/common.sh
source "$(dirname "$0")/lib/common.sh"

echo "==> Configuring firewalld ports for 'MiOS' services..."

# During an OCI container build, the firewalld daemon is not running.
# We MUST use firewall-offline-cmd to write directly to the XML policy files.
#
# Access surface contract: every 'MiOS' service binds 0.0.0.0 inside its
# Quadlet so it is reachable from
#   - 127.0.0.1 / ::1                 local loopback
#   - host LAN IP                     remote LAN access (bare-metal, VM, WSL2 mirrored)
#   - Podman bridge / cni0 / virbr0   sibling-container access
# Container PublishPort=HOST:CONTAINER directives default to 0.0.0.0 on
# the host port, so the firewall is what actually gates LAN reachability.
#
# Port values resolve through the layered SSOT (mios.toml [ports] →
# tools/lib/userenv.sh → MIOS_PORT_* env vars → automation/lib/globals.sh
# fallbacks). Hardcoded port literals are bugs; lift them.

# Open essential ports for local/LAN access
firewall-offline-cmd --zone=public --add-port=${MIOS_PORT_HERMES}/tcp          # mios-hermes (Hermes-Agent /v1 -- LIVE MiOS agent at /)
firewall-offline-cmd --zone=public --add-port=${MIOS_PORT_HERMES_WORKSPACE}/tcp # mios-hermes-workspace (chat front-end)
firewall-offline-cmd --zone=public --add-port=${MIOS_GUACAMOLE_PORT}/tcp       # mios-guacamole (Browser desktop)
firewall-offline-cmd --zone=public --add-port=${MIOS_CEPH_DASHBOARD_PORT}/tcp  # Ceph dashboard
firewall-offline-cmd --zone=public --add-port=${MIOS_K3S_API_PORT}/tcp         # K3s API
firewall-offline-cmd --zone=public --add-port=${MIOS_RDP_PORT}/tcp             # RDP
firewall-offline-cmd --zone=public --add-port=${MIOS_PORT_FORGE_HTTP}/tcp      # mios-forge HTTP
firewall-offline-cmd --zone=public --add-port=${MIOS_PORT_FORGE_SSH}/tcp       # mios-forge git+ssh
firewall-offline-cmd --zone=public --add-port=${MIOS_PORT_OLLAMA}/tcp          # ollama API (alternate local LLM backend)
firewall-offline-cmd --zone=public --add-port=${MIOS_PORT_COCKPIT_LINK}/tcp    # mios-cockpit-link discovery shim
firewall-offline-cmd --zone=public --add-service=ssh
firewall-offline-cmd --zone=public --add-service=cockpit                       # ${MIOS_PORT_COCKPIT} (host service)
firewall-offline-cmd --zone=public --add-service=mios-pxe
