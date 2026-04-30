#!/usr/bin/env bash
set -euo pipefail

echo "==> Configuring firewalld ports for MiOS services..."

# During an OCI container build, the firewalld daemon is not running.
# We MUST use firewall-offline-cmd to write directly to the XML policy files.

# Open essential ports for local/LAN access
firewall-offline-cmd --zone=public --add-port=8080/tcp # Guacamole
firewall-offline-cmd --zone=public --add-port=8443/tcp # Ceph Dashboard
firewall-offline-cmd --zone=public --add-port=6443/tcp # K3s API
firewall-offline-cmd --zone=public --add-port=3389/tcp # RDP
firewall-offline-cmd --zone=public --add-service=ssh
firewall-offline-cmd --zone=public --add-service=cockpit
firewall-offline-cmd --zone=public --add-service=mios-pxe
