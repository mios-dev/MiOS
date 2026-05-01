#!/bin/bash
# ============================================================================
# mios-overlay.sh - System-wide FHS Overlay
# ----------------------------------------------------------------------------
# Overlays the local repository (usr/, etc/, var/) onto the system root.
# This "MiOS-ifies" a running host or build-root.
# ============================================================================
set -euo pipefail

# Colors for high-signal output
BLUE="\033[1;34m"
GREEN="\033[1;32m"
YELLOW="\033[1;33m"
RED="\033[1;31m"
NC="\033[0m"

log() { echo -e "${BLUE}[mios-overlay]${NC} $1"; }
warn() { echo -e "${YELLOW}[warn]${NC} $1"; }
error() { echo -e "${RED}[error]${NC} $1"; exit 1; }

# --- Pre-flight ---
[[ "$EUID" -eq 0 ]] || error "Must run as root/sudo"

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

log "Starting overlay from: $REPO_ROOT"

# --- 1. /usr (Infrastructure & Binaries) ---
if [[ -d "usr" ]]; then
    log "Overlaying /usr (excluding /usr/local)..."
    tar -C "usr" -cf - --exclude="./local" . | tar -C /usr --no-overwrite-dir -xf -
fi

# --- 2. /usr/local (Custom Binaries / persistent write-through) ---
if [[ -d "usr/local" ]]; then
    log "Overlaying /usr/local..."
    if [[ -L /usr/local ]]; then
        TARGET="$(readlink -f /usr/local)"
        log "  /usr/local is symlink -> $TARGET; writing through"
        mkdir -p "$TARGET"
        tar -C "usr/local" -cf - . | tar -C "$TARGET" --no-overwrite-dir -xf -
    else
        tar -C "usr/local" -cf - . | tar -C /usr/local --no-overwrite-dir -xf -
    fi
fi

# --- 3. /etc (System Configuration) ---
if [[ -d "etc" ]]; then
    log "Overlaying /etc..."
    tar -C "etc" -cf - . | tar -C /etc --no-overwrite-dir -xf -
fi

# --- 4. /var (System State & tmpfiles initialization) ---
# Note: var in repo is usually empty or template-only. 
# We rely on systemd-tmpfiles for actual directory creation.
if [[ -d "var" ]] && [[ "$(ls -A var)" ]]; then
    log "Overlaying /var..."
    tar -C "var" -cf - . | tar -C /var --no-overwrite-dir -xf -
fi

# --- 5. /home -> /var/home (bootc-style alignment) ---
if [[ -d "home" ]]; then
    log "Overlaying /home templates to /var/home..."
    mkdir -p /var/home
    tar -C "home" -cf - . | tar -C /var/home --no-overwrite-dir -xf -
    
    if [[ ! -L /home ]]; then
        warn "/home is not a symlink; expected /var/home for bootc parity."
    fi
fi

# --- 6. Post-process ---
log "Normalizing systemd unit permissions..."
find /usr/lib/systemd -type f \( -name "*.service" -o -name "*.socket" -o -name "*.timer" \) -exec chmod 644 {} + 2>/dev/null || true

log "Triggering systemd-tmpfiles to initialize /var..."
systemd-tmpfiles --create --prefix=/var 2>/dev/null || true

if command -v restorecon &>/dev/null; then
    log "Relabeling SELinux contexts..."
    restorecon -RF /usr /etc /var 2>/dev/null || true
fi

echo -e "\n${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${GREEN}  [ OK ] MiOS overlay applied successfully${NC}"
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}\n"
