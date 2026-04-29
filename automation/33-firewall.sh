#!/bin/bash
# MiOS v0.1.1 — 33-firewall: Firewall configuration script
set -euo pipefail

echo "[33-firewall] Installing firewall init script..."

cat > /usr/libexec/mios-firewall-init <<'EOFW'
#!/bin/bash
set -euo pipefail
if ! systemctl is-active --quiet firewalld 2>/dev/null; then
    echo "[mios-firewall] firewalld not active — skipping"
    exit 0
fi
# Default zone: drop (deny all inbound by default)
firewall-cmd --set-default-zone=drop 2>/dev/null || true
# Essential services
for svc in cockpit ssh mdns; do
    firewall-cmd --permanent --add-service="$svc" 2>/dev/null || true
done
# RDP (GNOME Remote Desktop + Hyper-V vsock)
firewall-cmd --permanent --add-port=3389/tcp --add-port=3390/tcp 2>/dev/null || true
# Samba + NFS
firewall-cmd --permanent --add-service=samba --add-service=nfs --add-service=rpc-bind --add-service=mountd 2>/dev/null || true
# Libvirt
firewall-cmd --permanent --add-port=16509/tcp 2>/dev/null || true
# VNC
firewall-cmd --permanent --add-port=5900-5999/tcp 2>/dev/null || true
# K3s API + kubelet
firewall-cmd --permanent --add-port=6443/tcp --add-port=10250/tcp 2>/dev/null || true
# Pacemaker/Corosync
firewall-cmd --permanent --add-port=2224/tcp --add-port=5403-5405/udp 2>/dev/null || true
# CrowdSec dashboard + iVentoy
firewall-cmd --permanent --add-port=3000/tcp --add-port=26000/tcp 2>/dev/null || true
# Cockpit on 9090 (already via service but explicit)
firewall-cmd --permanent --add-port=9090/tcp 2>/dev/null || true
# Trust internal interfaces (including dynamic netavark/k3s bridges via wildcards)
# nftables backend drops unassigned interfaces strictly into the drop zone
for iface in lo podman+ br-+ veth+ virbr0 cni0 flannel.1 waydroid0; do
    firewall-cmd --permanent --zone=trusted --add-interface="$iface" 2>/dev/null || true
done

# ── Cockpit — accessible from ALL zones ──
for zone in public libvirt trusted; do
    firewall-cmd --permanent --zone="$zone" --add-service=cockpit 2>/dev/null || true
    firewall-cmd --permanent --zone="$zone" --add-port=9090/tcp 2>/dev/null || true
done
firewall-cmd --reload 2>/dev/null || true
echo "[mios-firewall] Firewall configured"
EOFW
chmod +x /usr/libexec/mios-firewall-init

echo "[33-firewall] Firewall init script installed."
