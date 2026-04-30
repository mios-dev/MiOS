#!/bin/bash
# ============================================================================
# automation/08-system-files-overlay.sh - MiOS v0.2.0
# ----------------------------------------------------------------------------
# Overlay /ctx/ onto the rootfs during the Containerfile build,
# correctly handling the /usr/local -> /var/usrlocal symlink.
#
# v0.2.0 Architecture: Rootfs-Native
#   - Sources now directly from /ctx/usr, /ctx/etc, /ctx/var, /ctx/home
# ============================================================================
set -euo pipefail

# shellcheck source=lib/common.sh
source "$(dirname "$0")/lib/common.sh"

CTX="${CTX:-/ctx}"

log "08-overlay: starting Rootfs-Native overlay"

# --- Stage 1: /usr (everything except /usr/local) --------------------------
if [[ -d "${CTX}/usr" ]]; then
    log "  stage 1: overlay usr content (excluding /usr/local)"
    tar -C "${CTX}/usr" -cf - --exclude='./local' . | tar -C /usr --no-overwrite-dir -xf -
fi

# --- Stage 2: /usr/local via /var/usrlocal ---------------------------------
if [[ -d "${CTX}/usr/local" ]]; then
    log "  stage 2: overlay /usr/local content"
    if [[ -L /usr/local ]]; then
        log "    /usr/local is a symlink -> $(readlink /usr/local); writing through"
        install -d -m 0755 /var/usrlocal
        tar -C "${CTX}/usr/local" -cf - . | tar -C /var/usrlocal --no-overwrite-dir -xf -
    else
        log "    /usr/local is a real directory; writing directly"
        tar -C "${CTX}/usr/local" -cf - . | tar -C /usr/local --no-overwrite-dir -xf -
    fi
fi

# --- Stage 3: /etc (System Config Templates) -------------------------------
if [[ -d "${CTX}/etc" ]]; then
    log "  stage 3: overlay etc content"
    tar -C "${CTX}/etc" -cf - . | tar -C /etc --no-overwrite-dir -xf -
fi

# --- Stage 4: /var (Mutable System State Templates) ------------------------
# DEPRECATED: /var population via tar overlay violates zero-trust immutability.
# All mandatory /var structure must be declared in /usr/lib/tmpfiles.d/*.conf.
# if [[ -d "${CTX}/var" ]]; then
#     log "  stage 4: overlay var content"
#     tar -C "${CTX}/var" -cf - . | tar -C /var --no-overwrite-dir -xf -
# fi

# --- Stage 5: /home (User Space Templates) ---------------------------------
if [[ -d "${CTX}/home" ]]; then
    log "  stage 5: overlay home content"
    mkdir -p /var/home
    tar -C "${CTX}/home" -cf - . | tar -C /var/home --no-overwrite-dir -xf -
fi

# Normalize permissions on systemd unit and config files.
log "08-overlay: normalizing systemd file permissions"
find /usr/lib/systemd -type f \( -name "*.service" -o -name "*.socket" -o -name "*.timer" -o -name "*.mount" -o -name "*.conf" -o -name "*.target" -o -name "*.path" -o -name "*.slice" -o -name "*.preset" -o -name "*.automount" -o -name "*.swap" \) -exec chmod 644 {} \; 2>/dev/null || true
find /usr/lib/systemd -type d -exec chmod 755 {} \; 2>/dev/null || true

# Logically Bound Images
QDIR="/usr/share/containers/systemd"
BDIR="/usr/lib/bootc/bound-images.d"
if [[ -d "${QDIR}" ]]; then
    install -d -m 0755 "${BDIR}"
    shopt -s nullglob
    for q in "${QDIR}"/*.container; do
        name="$(basename "$q")"
        ln -sf "${QDIR}/${name}" "${BDIR}/${name}"
        log "  LBI: bound ${name}"
    done
    shopt -u nullglob
fi

# ═══ Pathing Compatibility ═══
log "08-overlay: applying pathing compatibility symlinks"

# 1. WSL2 looks for /etc/wsl.conf, but we store it in /usr/lib/wsl.conf for immutability
if [[ -f /usr/lib/wsl.conf ]]; then
    ln -sf /usr/lib/wsl.conf /etc/wsl.conf
    log "  WSL: symlinked /etc/wsl.conf -> /usr/lib/wsl.conf"
fi

# 2. Standardize /home to /var/home (FCOS/bootc style)
if [ ! -L /home ] && [ -d /home ] && [ ! "$(ls -A /home)" ]; then
    rm -rf /home
    ln -sf /var/home /home
    log "  Path: symlinked /home -> /var/home"
elif [ ! -e /home ]; then
    ln -sf /var/home /home
    log "  Path: created /home -> /var/home symlink"
fi

log "08-overlay: relabeling overlaid files"
restorecon -RFv /usr/ 2>/dev/null || true
restorecon -RFv /etc/ 2>/dev/null || true

log "08-overlay: complete"
