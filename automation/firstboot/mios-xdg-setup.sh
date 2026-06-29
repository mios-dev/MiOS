#!/usr/bin/env bash
# AI-hint: Firstboot setup script for XDG profile script symlink and user directories init systemd user service.
# AI-related: /usr/share/mios/profile.d/mios-xdg-cephfs.sh, /usr/share/mios/xdg/user-dirs.defaults, /usr/share/mios/systemd/mios-xdg-userdir-init.service

set -euo pipefail

# 1. Gate execution on CephFS being enabled
if [ "${MIOS_CEPHFS_ENABLE:-false}" != "true" ]; then
    echo "[xdg-setup] CephFS integration disabled in SSOT -- exiting."
    exit 0
fi

echo "[xdg-setup] Setting up XDG profiles and user directories initializer..."

# 2. Symlink the baked immutable profile script to /etc/profile.d
mkdir -p /etc/profile.d
ln -sf /usr/share/mios/profile.d/mios-xdg-cephfs.sh /etc/profile.d/mios-xdg-cephfs.sh
echo "[xdg-setup] Symlinked XDG profile script to /etc/profile.d/mios-xdg-cephfs.sh"

# 3. Copy user-dirs.defaults to /etc/xdg/
mkdir -p /etc/xdg
cp /usr/share/mios/xdg/user-dirs.defaults /etc/xdg/user-dirs.defaults
echo "[xdg-setup] Configured /etc/xdg/user-dirs.defaults"

# 4. Install systemd user unit for the operator user
_op_user="${MIOS_USER:-mios}"
if ! getent passwd "$_op_user" >/dev/null; then
    echo "[xdg-setup] Operator user $_op_user not found -- skipping user unit installation."
else
    _op_home=$(getent passwd "$_op_user" | cut -d: -f6)
    _user_systemd_dir="$_op_home/.config/systemd/user"
    
    mkdir -p "$_user_systemd_dir/default.target.wants"
    
    # Copy the user unit to their local config path
    cp /usr/share/mios/systemd/mios-xdg-userdir-init.service "$_user_systemd_dir/mios-xdg-userdir-init.service"
    
    # Enable the unit by creating the target wants symlink manually (robust for OCI builds)
    ln -sf "../mios-xdg-userdir-init.service" "$_user_systemd_dir/default.target.wants/mios-xdg-userdir-init.service"
    
    # Re-own the created files to the operator user
    chown -R "$_op_user:" "$_op_home/.config"
    echo "[xdg-setup] Installed and enabled mios-xdg-userdir-init.service for $_op_user"
fi

echo "[xdg-setup] Setup completed successfully."
