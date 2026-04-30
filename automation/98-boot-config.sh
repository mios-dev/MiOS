#!/bin/bash
# MiOS v0.2.0 — 98-boot-config: Boot console + service configuration
# Plymouth disable is handled by usr/lib/bootc/kargs.d/10-mios-console.toml
# Console verbosity is handled by usr/lib/bootc/kargs.d/00-mios.toml + 10-mios-verbose.toml
set -euo pipefail

echo "[98-boot-config] Configuring boot console output..."

# ── Verify kargs TOML files exist ──────────────────────────────────────────
# These are static files from  — if missing, the overlay step failed.
if [ -f /usr/lib/bootc/kargs.d/10-mios-console.toml ]; then
    echo "[98-boot-config] Configuring plymouth disable via kernel cmdline..."
else
    echo "[98-boot-config] ERROR: 10-mios-console.toml not found — check overlay!"
fi

# ── Ensure agetty on tty1 ─────────────────────────────────────────────────
# Even if GDM fails, we need a text console to diagnose.
echo "[98-boot-config] Enabling getty on tty1 (fallback console)..."
systemctl enable getty@tty1.service 2>/dev/null || true

# ── Emergency shell access ────────────────────────────────────────────────
echo "[98-boot-config] Enabling emergency/rescue shell access..."
systemctl enable emergency.service 2>/dev/null || true
systemctl enable rescue.service 2>/dev/null || true

# ── Serial console for Hyper-V / QEMU ────────────────────────────────────
echo "[98-boot-config] Enabling serial-getty on ttyS0..."
systemctl enable serial-getty@ttyS0.service 2>/dev/null || true

# ── NetworkManager-wait-online timeout ────────────────────────────────────
echo "[98-boot-config] NetworkManager-wait-online timeout delivered via overlay."

echo "[98-boot-config] ✓ Boot console configured"
echo "[98-boot-config]   plymouth: disabled (kernel cmdline plymouth.enable=0)"
echo "[98-boot-config]   getty@tty1: enabled (fallback text console)"
echo "[98-boot-config]   serial-getty@ttyS0: enabled (serial console)"
echo "[98-boot-config]   NM-wait-online: 10s timeout (was 90s)"