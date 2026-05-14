#!/bin/bash
# 'MiOS' v0.2.4 -- 33-firewall: Firewall configuration script
set -euo pipefail

# shellcheck source=lib/common.sh
source "$(dirname "$0")/lib/common.sh"

echo "[33-firewall] Installing firewall init script..."

# Port values resolve through the layered SSOT (mios.toml [ports] →
# tools/lib/userenv.sh → MIOS_PORT_* env vars → automation/lib/globals.sh
# fallbacks). Hardcoded port literals are bugs; lift them.
#
# We bake the resolved values into the runtime init script via heredoc
# expansion (no single-quotes around EOFW) so the deployed script
# carries the build-time-resolved port set rather than re-resolving at
# every boot.

cat > /usr/libexec/mios-firewall-init <<EOFW
#!/bin/bash
set -euo pipefail
if ! systemctl is-active --quiet firewalld 2>/dev/null; then
    echo "[mios-firewall] firewalld not active -- skipping"
    exit 0
fi
# Default zone: drop (deny all inbound by default)
firewall-cmd --set-default-zone=drop 2>/dev/null || true
# Essential services
for svc in cockpit ssh mdns; do
    firewall-cmd --permanent --add-service="\$svc" 2>/dev/null || true
done
# RDP (GNOME Remote Desktop + Hyper-V vsock)
firewall-cmd --permanent --add-port=${MIOS_RDP_PORT}/tcp --add-port=3390/tcp 2>/dev/null || true
# Samba + NFS
firewall-cmd --permanent --add-service=samba --add-service=nfs --add-service=rpc-bind --add-service=mountd 2>/dev/null || true
# Libvirt
firewall-cmd --permanent --add-port=16509/tcp 2>/dev/null || true
# VNC
firewall-cmd --permanent --add-port=5900-5999/tcp 2>/dev/null || true
# K3s API + kubelet
firewall-cmd --permanent --add-port=${MIOS_K3S_API_PORT}/tcp --add-port=10250/tcp 2>/dev/null || true
# Pacemaker/Corosync
firewall-cmd --permanent --add-port=2224/tcp --add-port=5403-5405/udp 2>/dev/null || true
# mios-hermes (Hermes-Agent /v1 -- canonical OpenAI-API endpoint for the
# LIVE MiOS agent at root; Architectural Law 5)
firewall-cmd --permanent --add-port=${MIOS_PORT_HERMES}/tcp 2>/dev/null || true
# mios-open-webui (web chat front-end -- default chat UI)
firewall-cmd --permanent --add-port=${MIOS_PORT_OPEN_WEBUI}/tcp 2>/dev/null || true
# mios-code-server (VS Code in a browser)
firewall-cmd --permanent --add-port=${MIOS_PORT_CODE_SERVER}/tcp 2>/dev/null || true
# mios-guacamole web (Browser desktop)
firewall-cmd --permanent --add-port=${MIOS_GUACAMOLE_PORT}/tcp 2>/dev/null || true
# ollama API (local LLM + embedding backend; handles all MiOS embedded models)
firewall-cmd --permanent --add-port=${MIOS_PORT_OLLAMA}/tcp 2>/dev/null || true
# CrowdSec dashboard + iVentoy + mios-forge HTTP (port ${MIOS_PORT_FORGE_HTTP} shared by both)
firewall-cmd --permanent --add-port=${MIOS_PORT_FORGE_HTTP}/tcp --add-port=26000/tcp 2>/dev/null || true
# mios-forge git+ssh (non-22 to coexist with sshd)
firewall-cmd --permanent --add-port=${MIOS_PORT_FORGE_SSH}/tcp 2>/dev/null || true
# Cockpit on ${MIOS_PORT_COCKPIT} (already via service but explicit)
firewall-cmd --permanent --add-port=${MIOS_PORT_COCKPIT}/tcp 2>/dev/null || true
# mios-cockpit-link Podman Desktop discovery shim (${MIOS_PORT_COCKPIT_LINK} -> host ${MIOS_PORT_COCKPIT})
firewall-cmd --permanent --add-port=${MIOS_PORT_COCKPIT_LINK}/tcp 2>/dev/null || true
# Trust internal interfaces (including dynamic netavark/k3s bridges via wildcards)
# nftables backend drops unassigned interfaces strictly into the drop zone
for iface in lo podman+ br-+ veth+ virbr0 cni0 flannel.1 waydroid0; do
    firewall-cmd --permanent --zone=trusted --add-interface="\$iface" 2>/dev/null || true
done

# ── Cockpit -- accessible from ALL zones ──
for zone in public libvirt trusted; do
    firewall-cmd --permanent --zone="\$zone" --add-service=cockpit 2>/dev/null || true
    firewall-cmd --permanent --zone="\$zone" --add-port=${MIOS_PORT_COCKPIT}/tcp 2>/dev/null || true
done
firewall-cmd --reload 2>/dev/null || true
echo "[mios-firewall] Firewall configured"
EOFW
chmod +x /usr/libexec/mios-firewall-init

echo "[33-firewall] Firewall init script installed."
