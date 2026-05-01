#!/usr/bin/env bash
# MiOS init-user-space — initializes XDG user configuration for MiOS
set -euo pipefail

FORCE="${1:-}"
MIOS_CONFIG_DIR="${XDG_CONFIG_HOME:-$HOME/.config}/mios"

mkdir -p "${MIOS_CONFIG_DIR}" \
         "${XDG_DATA_HOME:-$HOME/.local/share}/mios" \
         "${XDG_CACHE_HOME:-$HOME/.cache}/mios" \
         "${XDG_STATE_HOME:-$HOME/.local/state}/mios"

write_if_missing() {
    local file="$1"; shift
    if [[ -f "$file" && -z "$FORCE" ]]; then
        echo "[skip] $file already exists (use --force to overwrite)"
        return
    fi
    cat > "$file"
    echo "[OK]   wrote $file"
}

write_if_missing "${MIOS_CONFIG_DIR}/env.toml" << 'TOML'
# MiOS User Environment Configuration
# Edit these values to override build defaults.
# Run: just build   to apply.

MIOS_USER     = "mios"
MIOS_HOSTNAME = "mios"
MIOS_FLATPAKS = ""
# MIOS_BASE_IMAGE = "ghcr.io/ublue-os/ucore-hci:stable-nvidia"
# MIOS_LOCAL_TAG  = "localhost/mios:latest"
TOML

write_if_missing "${MIOS_CONFIG_DIR}/images.toml" << 'TOML'
# MiOS Image Source Configuration
# Override base images here.

# MIOS_BASE_IMAGE = "ghcr.io/ublue-os/ucore-hci:stable-nvidia"
# MIOS_BIB_IMAGE  = "quay.io/centos-bootc/bootc-image-builder:latest"
# MIOS_IMAGE_NAME = "ghcr.io/mios-dev/mios"
TOML

write_if_missing "${MIOS_CONFIG_DIR}/build.toml" << 'TOML'
# MiOS Build Configuration

# MIOS_LOCAL_TAG = "localhost/mios:latest"
TOML

write_if_missing "${MIOS_CONFIG_DIR}/flatpaks.list" << 'LIST'
# MiOS Flatpak List — one per line, comma-separated or newline-separated
# Example:
# com.spotify.Client
# com.valvesoftware.Steam
LIST

echo ""
echo "[OK] MiOS user-space initialized at: ${MIOS_CONFIG_DIR}"
echo "     Edit env.toml to set your username, hostname, and flatpaks."
echo "     Then run: just build"
