#!/usr/bin/env bash
# AI-hint: Firstboot setup script for CephFS mount/automount systemd template units and login profiles.
#          Renders environment variables into templates and enables user automounts.
# AI-related: /usr/share/mios/systemd/home-@.mount.tmpl, /usr/share/mios/systemd/home-@.automount.tmpl, /usr/share/mios/profile.d/mios-xdg-cephfs.sh

set -euo pipefail

# 1. Gate execution on CephFS being enabled
if [ "${MIOS_CEPHFS_ENABLE:-false}" != "true" ]; then
    echo "[cephfs-mount-setup] CephFS integration disabled in SSOT -- exiting."
    exit 0
fi

echo "[cephfs-mount-setup] Initializing systemd mount templates for CephFS..."

# Ensure target directories exist
mkdir -p /etc/systemd/system
mkdir -p /etc/profile.d

# 2. Render templates
# Use envsubst if available, fallback to basic sed rendering
render_template() {
    local src="$1"
    local dest="$2"
    if command -v envsubst >/dev/null 2>&1; then
        envsubst < "$src" > "$dest"
    else
        # Fallback sed rendering for mapped variables
        sed -e "s|\${MIOS_CEPHFS_ENABLE}|${MIOS_CEPHFS_ENABLE:-false}|g" \
            -e "s|\${MIOS_CEPHFS_MONITORS}|${MIOS_CEPHFS_MONITORS:-127.0.0.1:6789}|g" \
            -e "s|\${MIOS_CEPHFS_FS_NAME}|${MIOS_CEPHFS_FS_NAME:-cephfs}|g" \
            -e "s|\${MIOS_CEPHFS_TENANT_ID}|${MIOS_CEPHFS_TENANT_ID:-mios}|g" \
            -e "s|\${MIOS_CEPHFS_DATA_POOL_HOT}|${MIOS_CEPHFS_DATA_POOL_HOT:-cephfs_data_hot}|g" \
            -e "s|\${MIOS_CEPHFS_DATA_POOL_BULK}|${MIOS_CEPHFS_DATA_POOL_BULK:-cephfs_data_bulk}|g" \
            -e "s|\${MIOS_XDG_CACHE_LOCAL_PATH}|${MIOS_XDG_CACHE_LOCAL_PATH:-/run/user/{uid}/.cache}|g" \
            -e "s|\${MIOS_CEPHFS_MOUNT_OPTIONS}|${MIOS_CEPHFS_MOUNT_OPTIONS:-noatime,fsc,_netdev}|g" \
            -e "s|\${MIOS_CEPHFS_KEYRING_DIR}|${MIOS_CEPHFS_KEYRING_DIR:-/etc/ceph/keyring.d}|g" \
            -e "s|\${MIOS_CEPHFS_AUTOMOUNT_IDLE_TIMEOUT_S}|${MIOS_CEPHFS_AUTOMOUNT_IDLE_TIMEOUT_S:-600}|g" \
            "$src" > "$dest"
    fi
}

render_template "/usr/share/mios/systemd/home-@.mount.tmpl" "/etc/systemd/system/home-@.mount"
render_template "/usr/share/mios/systemd/home-@.automount.tmpl" "/etc/systemd/system/home-@.automount"
render_template "/usr/share/mios/profile.d/mios-xdg-cephfs.sh" "/etc/profile.d/mios-xdg-cephfs.sh"

# Make profile script executable
chmod +x /etc/profile.d/mios-xdg-cephfs.sh 2>/dev/null || true

# 3. Apply CephFS client-side caching configs
if [ -x /usr/libexec/mios/mios-ceph-configure ]; then
    echo "[cephfs-mount-setup] Running mios-ceph-configure..."
    /usr/libexec/mios/mios-ceph-configure || true
fi

# 4. Reload systemd and enable services
if command -v systemctl >/dev/null 2>&1; then
    echo "[cephfs-mount-setup] Reloading systemd daemon..."
    systemctl daemon-reload || true
    
    # Enable cachefilesd for client-side caching (fsc)
    echo "[cephfs-mount-setup] Enabling cachefilesd service..."
    systemctl enable --now cachefilesd || true

    # Enable automount for the default 'mios' user
    echo "[cephfs-mount-setup] Enabling CephFS automount for mios user..."
    systemctl enable "home-mios.automount" || true
else
    echo "[cephfs-mount-setup] systemctl not available (offline/chroot environment) -- skipped reload."
fi

echo "[cephfs-mount-setup] Setup completed successfully."
