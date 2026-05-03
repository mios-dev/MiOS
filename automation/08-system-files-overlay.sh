#!/bin/bash
# ============================================================================
# automation/08-system-files-overlay.sh - 'MiOS' v0.2.0
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
# LAW 5: /var/usrlocal must NOT be mkdir'd during OCI build.
# It is declared in /usr/lib/tmpfiles.d/mios-infra.conf and created at boot.
# If /usr/local is a symlink to /var/usrlocal (typical FCOS layout), skip the
# tar write — the content will be available after first-boot tmpfiles.d runs.
# If /usr/local is a real directory (non-FCOS base), write directly.
if [[ -d "${CTX}/usr/local" ]]; then
    log "  stage 2: overlay /usr/local content"
    if [[ -L /usr/local ]]; then
        local_target="$(readlink -f /usr/local 2>/dev/null || true)"
        log "    /usr/local is a symlink -> ${local_target}; skipping /var write (tmpfiles.d will create at boot)"
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

# --- Stage 3a: /etc/wsl.conf force-install ---------------------------------
# WSL2's wsl.conf parser is unforgiving — a single malformed byte takes down
# systemd-as-PID1, which cascades into a broken user session and home dir.
# Force-install from the canonical reference with explicit perms instead of
# trusting the tar overlay (which can be defeated by a base-image-shipped
# copy or by tar metadata quirks). install -T treats the destination as a
# filename, not a directory, and overwrites unconditionally.
if [[ -f "${CTX}/etc/wsl.conf" ]]; then
    install -m 0644 -o root -g root -T "${CTX}/etc/wsl.conf" /etc/wsl.conf
    log "  stage 3a: force-installed /etc/wsl.conf (mode 0644, root:root)"
fi

# --- Stage 4: /var (Mutable System State Templates) ------------------------
# DEPRECATED: /var population via tar overlay violates zero-trust immutability.
# All mandatory /var structure must be declared in /usr/lib/tmpfiles.d/*.conf.
# if [[ -d "${CTX}/var" ]]; then
#     log "  stage 4: overlay var content"
#     tar -C "${CTX}/var" -cf - . | tar -C /var --no-overwrite-dir -xf -
# fi

# --- Stage 5: /home (User Space Templates) ---------------------------------
# LAW 5: Writing to /var/home during OCI build violates the immutability contract —
# /var is a persistent volume that is NOT populated from the OCI image on deployment.
# Home directory dotfile templates must live in /etc/skel/ and are copied by
# systemd-sysusers when the user is first created at boot.
# This stage is intentionally a no-op; see /etc/skel/ for the skel overlay.
if [[ -d "${CTX}/home" ]]; then
    log "  stage 5: /ctx/home detected — seeding /etc/skel instead of /var/home (LAW 5)"
    install -d -m 0755 /etc/skel
    tar -C "${CTX}/home" -cf - . | tar -C /etc/skel --no-overwrite-dir --strip-components=1 -xf - 2>/dev/null || true
fi

# Normalize permissions on systemd unit and config files.
log "08-overlay: normalizing systemd file permissions"
find /usr/lib/systemd -type f \( -name "*.service" -o -name "*.socket" -o -name "*.timer" -o -name "*.mount" -o -name "*.conf" -o -name "*.target" -o -name "*.path" -o -name "*.slice" -o -name "*.preset" -o -name "*.automount" -o -name "*.swap" \) -exec chmod 644 {} \; 2>/dev/null || true
find /usr/lib/systemd -type d -exec chmod 755 {} \; 2>/dev/null || true

# Logically Bound Images — bind every Quadlet from both vendor and admin paths
# (see ARCHITECTURAL LAW 3 — BOUND-IMAGES).
BDIR="/usr/lib/bootc/bound-images.d"
install -d -m 0755 "${BDIR}"
shopt -s nullglob
for QDIR in /usr/share/containers/systemd /etc/containers/systemd; do
    [[ -d "${QDIR}" ]] || continue
    for q in "${QDIR}"/*.container; do
        name="$(basename "$q")"
        ln -sf "${q}" "${BDIR}/${name}"
        log "  LBI: bound ${name} (${QDIR})"
    done
done
shopt -u nullglob

# ═══ Pathing Compatibility ═══
log "08-overlay: applying pathing compatibility symlinks"

# /etc/wsl.conf is deployed as a real file via Stage 3 overlay (etc/wsl.conf in repo).
# /usr/lib/wsl.conf is a reference stub; do not symlink it over /etc/wsl.conf.

# 1. Standardize /home to /var/home (FCOS/bootc style)
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
