#!/usr/bin/env bash
set -euo pipefail

echo "=== Configuring GNOME Remote Desktop (GNOME 50) ==="

# Pre-emptively disable/mask legacy xrdp services just in case they bleed in from a base image
systemctl mask xrdp.service xrdp-sesman.service 2>/dev/null || true

# GNOME Remote Desktop handles Wayland headless RDP natively.
# Enablement is handled via usr/lib/systemd/system-preset/90-mios.preset
# Drop-in to wait for network is delivered via system_files overlay.

echo "GNOME Remote Desktop provisioning complete."
