#!/usr/bin/env bash
set -euo pipefail

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

# Open essential ports for local/LAN access
firewall-offline-cmd --zone=public --add-port=8080/tcp     # mios-ai (LocalAI /v1, Architectural Law 5)
firewall-offline-cmd --zone=public --add-port=8090/tcp     # mios-guacamole (Browser desktop, mapped from container :8080)
firewall-offline-cmd --zone=public --add-port=8443/tcp     # Ceph dashboard
firewall-offline-cmd --zone=public --add-port=6443/tcp     # K3s API
firewall-offline-cmd --zone=public --add-port=3389/tcp     # RDP
firewall-offline-cmd --zone=public --add-port=3000/tcp     # mios-forge HTTP
firewall-offline-cmd --zone=public --add-port=2222/tcp     # mios-forge git+ssh
firewall-offline-cmd --zone=public --add-port=11434/tcp    # ollama API (alternate local LLM backend)
firewall-offline-cmd --zone=public --add-port=19090/tcp    # mios-cockpit-link discovery shim
firewall-offline-cmd --zone=public --add-service=ssh
firewall-offline-cmd --zone=public --add-service=cockpit   # 9090 (host service)
firewall-offline-cmd --zone=public --add-service=mios-pxe
