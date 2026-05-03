#!/bin/bash
# 'MiOS' v0.2.0 — 38-vm-gating: VM service gating + Hyper-V Enhanced Session
#
# v0.2.0 CRITICAL FIX: GNOME 50 / Mutter 50 completely removed the X11 backend.
# xorgxrdp is an X11 technology — it CANNOT work with Wayland-only Mutter 50.
# The old approach caused a GDM crash loop on Hyper-V, preventing boot.
#
# NEW APPROACH: Use gnome-remote-desktop (GRD) for Enhanced Session.
# GRD provides Wayland-native RDP and can bind to vsock for Hyper-V transport.
# xrdp is kept installed but NOT auto-enabled — it's available as a manual
# fallback for non-GNOME sessions (XFCE, Phosh) only.
#
# HYPER-V BOOT PATH (without Enhanced Session):
#   hyperv_drm → KMS → GDM (Wayland) → llvmpipe software rendering → login
# HYPER-V ENHANCED SESSION PATH:
#   vmconnect → vsock:3389 → gnome-remote-desktop (Wayland RDP) → login
set -euo pipefail

echo "[38-vm-gating] Configuring VM-specific service gating..."

# ═══ GDM / nvidia-powerd / Waydroid + binder gating ═══
# Drop-ins for gdm, nvidia-powerd, waydroid-container, dev-binderfs.mount are
# created by 20-services.sh (WSL_SKIP_SERVICES + bare-metal nvidia-powerd block).
# Do NOT duplicate them here — last writer wins and we want 20's canonical drop-ins.

# ═══ Polkit container workaround ═══
# Managed via usr/lib/systemd/system/polkit.service.d/10-mios-container.conf

# ═══ Cockpit socket drop-in permissions ═══
if [ -f /usr/lib/systemd/system/cockpit.socket.d/listen.conf ]; then
    chmod 644 /usr/lib/systemd/system/cockpit.socket.d/listen.conf
fi

# ═══════════════════════════════════════════════════════════════════════════
# HYPER-V ENHANCED SESSION — WAYLAND-NATIVE VIA GNOME REMOTE DESKTOP
# ═══════════════════════════════════════════════════════════════════════════
echo "[38-vm-gating] Configuring Hyper-V Enhanced Session (gnome-remote-desktop)..."

# 1. Blacklist VMware vsock (conflicts with Hyper-V hv_sock)
# Managed via usr/lib/modprobe.d/blacklist-vmw_vsock.conf

# 2. Ensure hv_sock loads on boot (required for vsock RDP transport)
if ! grep -q 'hv_sock' /usr/lib/modules-load.d/mios.conf 2>/dev/null; then
    echo "hv_sock" >> /usr/lib/modules-load.d/mios.conf
fi

# 3. Polkit rule for colord (prevents "not authorized" errors in RDP sessions)
# Managed via usr/share/polkit-1/rules.d/45-allow-colord.rules

# 4. Hyper-V Enhanced Session service — uses gnome-remote-desktop
# Managed via usr/lib/systemd/system/mios-hyperv-enhanced.service
# and usr/libexec/mios-hyperv-enhanced
systemctl enable mios-hyperv-enhanced.service 2>/dev/null || true

# 5. GNOME Remote Desktop — first-boot setup script
# mios-grd-setup is installed via system_files overlay (08-system-files-overlay.sh)
# into /usr/libexec/mios-grd-setup. No copy needed here.
chmod +x /usr/libexec/mios-grd-setup 2>/dev/null || true

# ── WSL2 systemd-machined gating ─────────────────────────────────────────
# dbus-broker.service.d/wsl2-fix.conf is provided by system_files overlay
# (OOMScoreAdjust only; --audit removal is in 10-mios-no-audit.conf).
# Do NOT overwrite it here — previous versions wrote a broken drop-in with
# ConditionPathExists=|/proc/version which is always true and caused dbus
# to be misconfigured on bare metal.

# Ensure systemd-machined doesn't block dbus in WSL2
# Managed via usr/lib/systemd/system/systemd-machined.service.d/wsl2-optional.conf

echo "[38-vm-gating] VM gating + Hyper-V Enhanced Session (gnome-remote-desktop) configured."
